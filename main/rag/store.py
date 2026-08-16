"""Persistent vector store backed by Chroma with a local embedder.

This is where chunks live as vectors. On every question we embed the question
and ask Chroma for the closest chunks (cosine similarity).
"""

import os
import uuid

import chromadb
from chromadb.utils import embedding_functions

from .config import COLLECTION_NAME, DB_DIR, EMBEDDING_MODEL_NAME, TOP_K


class VectorStore:
    """Thin wrapper around a persistent Chroma collection with a local embedder."""

    def __init__(self, db_dir: str = DB_DIR, collection_name: str = COLLECTION_NAME):
        os.makedirs(db_dir, exist_ok=True)
        self.client = chromadb.PersistentClient(path=db_dir)

        # Chroma will download this model from HuggingFace on first run and cache it locally.
        self.embedder = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=EMBEDDING_MODEL_NAME
        )

        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.embedder,
            metadata={"hnsw:space": "cosine"},
        )

    # -- ingestion -----------------------------------------------------

    def add_chunks(self, chunks, source: str):
        """Embed and store a list of text chunks, tagged with their source URL."""
        if not chunks:
            return 0
        ids = [str(uuid.uuid4()) for _ in chunks]
        metadatas = [{"source": source} for _ in chunks]
        self.collection.add(documents=chunks, metadatas=metadatas, ids=ids)
        return len(chunks)

    # -- retrieval -------------------------------------------------------

    def query(self, text: str, k: int = TOP_K):
        """Return the top-k most relevant chunks for a query string."""
        if self.collection.count() == 0:
            return []
        n = min(k, self.collection.count())
        results = self.collection.query(query_texts=[text], n_results=n)
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        dists = results.get("distances", [[]])[0]
        return [
            {"text": d, "source": m.get("source", "unknown"), "distance": dist}
            for d, m, dist in zip(docs, metas, dists)
        ]

    # -- housekeeping ----------------------------------------------------

    def list_sources(self):
        """Return the unique set of ingested source URLs."""
        if self.collection.count() == 0:
            return []
        data = self.collection.get(include=["metadatas"])
        return sorted({m["source"] for m in data["metadatas"] if "source" in m})

    def clear(self):
        """Wipe the entire collection."""
        name = self.collection.name
        try:
            self.client.delete_collection(name)
        except Exception:
            pass
        self.collection = self.client.get_or_create_collection(
            name=name,
            embedding_function=self.embedder,
            metadata={"hnsw:space": "cosine"},
        )
