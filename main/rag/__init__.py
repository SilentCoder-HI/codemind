"""CodeMind RAG package — ingest, embed, store and retrieve documents locally.

Public API:
    VectorStore              - the Chroma-backed vector database
    ingest_url(url, store)   - fetch + extract + chunk + store a web page
    ingest_text_file(path, store) - read + chunk + store a local text file
    interactive_ingest(...)  - crawl-and-pick flow for web pages
    query helpers / config constants
"""

from .chunker import chunk_text
from .config import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    COLLECTION_NAME,
    DB_DIR,
    EMBEDDING_MODEL_NAME,
    REQUEST_TIMEOUT,
    STRIP_TAGS,
    TOP_K,
)
from .fetcher import extract_text, fetch_url, is_url, read_text_file
from .store import VectorStore
from .web import ingest_page_list, interactive_ingest


def ingest_url(url: str, store: VectorStore) -> int:
    """Full pipeline for a web page: fetch -> extract -> chunk -> embed -> store.

    Returns the number of chunks added.
    """
    html = fetch_url(url)
    text = extract_text(html)
    if not text:
        raise ValueError("No extractable text found on that page.")
    chunks = chunk_text(text)
    return store.add_chunks(chunks, source=url)


def ingest_text_file(path: str, store: VectorStore) -> int:
    """Full pipeline for a local text file: read -> chunk -> embed -> store.

    Returns the number of chunks added.
    """
    text = read_text_file(path)
    if not text:
        raise ValueError(f"No readable text found in {path}")
    chunks = chunk_text(text)
    return store.add_chunks(chunks, source=f"file:{path}")


__all__ = [
    "CHUNK_OVERLAP",
    "CHUNK_SIZE",
    "COLLECTION_NAME",
    "DB_DIR",
    "EMBEDDING_MODEL_NAME",
    "REQUEST_TIMEOUT",
    "STRIP_TAGS",
    "TOP_K",
    "VectorStore",
    "chunk_text",
    "extract_text",
    "fetch_url",
    "ingest_page_list",
    "ingest_text_file",
    "ingest_url",
    "interactive_ingest",
    "is_url",
    "read_text_file",
]
