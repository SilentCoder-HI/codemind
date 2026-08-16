# How CodeMind's RAG works (learning guide)

This is the "understand it from the ground up" guide. Read it top to bottom,
then re-read each file with this in your head. By the end you should be able
to explain RAG to someone else.

## The one-paragraph idea

RAG stands for **Retrieval-Augmented Generation**. The LLM alone only knows
what it was trained on. RAG gives it *your* documents at question time:

1. You feed in a document (a URL or a .txt file).
2. It is cut into chunks and converted into **vectors** (lists of numbers
   that capture meaning).
3. Those vectors are stored in a database.
4. When you ask a question, the question is also turned into a vector and the
   database returns the **most similar chunks**.
5. Those chunks are pasted into the prompt as "Retrieved context", and the
   LLM answers *grounded in that context* — so it can talk about your
   documents, not just the internet.

## The pipeline, stage by stage

```
                INGEST (learn)                       ASK (retrieve + answer)
              ┌─────────────────────┐              ┌──────────────────────────┐
              │ URL / .txt file      │              │ your question             │
              └──────────┬──────────┘              └─────────────┬────────────┘
                         │                                       │
              fetch/extract (fetcher.py)               embed question
                         │                                       │
                         ▼                                       ▼
                 clean text                                ┌───────────┐
                         │                                  │  Chroma   │
                         ▼                                  │ database  │
              chunk_text (chunker.py)      ───────────────► │ (vectors) │
                         │                  embed + store   └─────┬─────┘
                         ▼                                       │
                   chunks of text                        top-k similar
                         │                                 chunks (query)
                         │                                       │
                         ▼                                       ▼
                 vector_db/ on disk                    "Retrieved context"
                                                              │
                                                              ▼
                                                        LLM answers using it
                                                       (models.py + cli.py)
```

### 1. Getting the text — `main/rag/fetcher.py`

- `fetch_url()` downloads the HTML (with a polite User-Agent).
- `extract_text()` removes boilerplate (`<script>`, `<style>`, `<nav>`,
  `<footer>`, ...) via BeautifulSoup, then normalizes whitespace.
- `read_text_file()` does the same job for a local `.txt` / `.md` file.

**Why strip tags?** Raw HTML is 90% noise. Embedding noise makes retrieval
worse. Clean text = better vectors = better answers.

### 2. Chunking — `main/rag/chunker.py`

`chunk_text()` slices text into overlapping pieces. Defaults:
- `CHUNK_SIZE = 800` characters (~150-200 tokens)
- `CHUNK_OVERLAP = 150` characters, so a thought split across the boundary
  is still captured by the neighboring chunk.

**Why chunk at all?** Embedders and LLM context windows have limits, and a
whole 10,000-word document as one vector would dilute meaning. Small chunks
retrieve precisely.

### 3. Embedding — `main/rag/store.py`

`VectorStore` uses `all-MiniLM-L6-v2`, a small sentence-transformer
(~80MB, fast on CPU). It maps text -> a 384-dimension vector where similar
meanings sit close together.

`add_chunks()` embeds every chunk and saves it with its `source` metadata.

### 4. Storing — Chroma

Chroma is the vector database. It persists to `vector_db/` on disk
(git-ignored — it's regenerated at runtime). It uses **cosine similarity**
(`hnsw:space: cosine`) for searching.

### 5. Retrieval — `VectorStore.query()`

Your question is embedded with the same model, then Chroma finds the `TOP_K`
(=4) closest chunks. Each result carries its `text`, `source`, and
`distance` (smaller = more similar).

### 6. Generation — `main/cli.py`

`build_rag_context()` formats the top-k chunks as:

```
Retrieved context (from previously ingested pages):
- [source: https://...] the actual chunk text...
```

This is injected as a system message. `SYSTEM_PROMPT` in
`main/models.py` tells the LLM to treat it as ground truth and cite the
source — this is what stops the model from hallucinating about your docs.

## Where the knobs live — and what to try

All in `main/rag/config.py` (retrieval) and `main/models.py` (LLM):

| Setting | Default | What happens if you change it |
|---|---|---|
| `TOP_K` | 4 | Higher = more context but more noise; lower = sharper but may miss things |
| `CHUNK_SIZE` | 800 | Smaller = precise retrieval; larger = richer context per chunk |
| `CHUNK_OVERLAP` | 150 | Higher = fewer cut-off thoughts, more duplicate text |
| `EMBEDDING_MODEL_NAME` | `all-MiniLM-L6-v2` | Try `all-mpnet-base-v2` for better (slower) embeddings |
| `N_CTX` | 4096 | LLM context window; raise if long docs push prompts out |
| `temperature` (cli.py) | 0.1 | Lower = factual/safe; higher = creative/random |

**Daily experiments:** change one knob, ingest a doc, ask the same question,
and compare. That's the fastest way to build an intuition for RAG.

## Glossary

- **Embedding** — a vector (list of numbers) representing meaning.
- **Chunk** — a piece of a document, small enough to embed and retrieve well.
- **Vector DB** — a database optimized for "find the most similar vector"
  queries (here: Chroma).
- **Top-k** — the k most similar chunks retrieved for a question.
- **Retrieved context** — the document text injected into the prompt.
- **Augmented generation** — the LLM generating an answer using that context.
