"""Central configuration for the RAG pipeline.

Every tuning knob lives here so you can experiment in one place.
See docs/rag-explained.md for what each setting does and how to play with it.
"""

import os

# Where the Chroma vector database is stored on disk (git-ignored).
DB_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "vector_db",
)

COLLECTION_NAME = "codemind_docs"
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"  # small (~80MB), fast on CPU, good general-purpose embeddings

CHUNK_SIZE = 800        # characters per chunk (roughly ~150-200 tokens)
CHUNK_OVERLAP = 150      # overlap between consecutive chunks so context isn't cut mid-thought
TOP_K = 4                # how many chunks to retrieve per query
REQUEST_TIMEOUT = 15     # seconds, for URL fetches

# Tags that never contain useful body content — stripped before text extraction
STRIP_TAGS = ["script", "style", "nav", "header", "footer", "form", "noscript", "svg", "iframe"]
