"""Chunking — split long text into overlapping pieces for embedding.

Chunk size and overlap are the first knobs you should experiment with:
  - smaller chunks  -> more precise retrieval, but less context per answer
  - larger chunks   -> richer context, but more unrelated text in each chunk
"""

from .config import CHUNK_OVERLAP, CHUNK_SIZE


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP):
    """Split text into overlapping character-based chunks."""
    chunks = []
    start = 0
    length = len(text)
    while start < length:
        end = start + chunk_size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= length:
            break
        start = end - overlap
    return chunks
