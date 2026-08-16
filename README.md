# CodeMind — My Local RAG Assistant

A fully **local, offline-first** AI assistant I'm building to **learn RAG
(Retrieval-Augmented Generation) from scratch** — by actually building it.

> Give it a URL or a text file → it reads and learns it → ask it anything →
> it answers using what it learned, with the source.

Everything runs on my own machine. No cloud API. My data never leaves my PC.

## Why I'm building this

I'm learning RAG because I want an AI assistant that knows **my** stuff — not
just the internet it was trained on. The dream is simple:

1. I paste a URL or drop a `.txt` file.
2. CodeMind ingests it and learns it (that's the RAG part).
3. Then I can ask it anything about that material and it answers correctly,
   from *my* documents.

I'm building it piece by piece so I truly **understand** how retrieval works
instead of just calling a black-box library. I work on this project daily and
make it a little better every time. It's my own open-source project — my
sandbox to experiment, break things, and learn.

If you're reading this on GitHub: this is a learning project, built in the
open, on purpose. Progress over polish.

## Two ways to run the brain (no wasted downloads)

At startup CodeMind asks you **the important question**:

```text
How do you want to run CodeMind's brain?
  1) Ollama — I have Ollama installed with models already pulled
  2) llama.cpp — download and use .gguf models inside this project
```

- **Pick 1 (Ollama)** if you already have Ollama on your system with models
  pulled. CodeMind connects to it over HTTP (`localhost:11434`), lists your
  models, and you pick one. **No new downloads.**
- **Pick 2 (llama.cpp)** to keep models inside this project. CodeMind looks in
  the `models/` folder for `.gguf` files. If it's empty, it **offers to
  download a small starter model** (Qwen2.5 0.5B, ~400 MB) right there.

So if you have Ollama models, you never download another model again.

## How it works (the RAG pipeline)

```
URL / .txt  ──►  fetch + extract text   ──►  chunk into pieces
                                                      │
                 embed chunks as vectors  ◄───────────┘
                                                      ▼
   your question  ──►  embed question  ──►  find top-4 similar chunks (Chroma)
                                                      │
                                                      ▼
                      inject chunks as "Retrieved context" into the LLM prompt
                                                      │
                                                      ▼
                     CodeMind answers, grounded in YOUR documents
```

Read **[docs/rag-explained.md](docs/rag-explained.md)** for the full
stage-by-stage learning guide — that file exists to teach me (and you) RAG.

## Features

| Feature | Where | What it does |
|---|---|---|
| **Ollama backend** | `main/models.py` | Use models already installed in your local Ollama |
| **llama.cpp backend** | `main/models.py` | Load `.gguf` files from `models/`, with in-app download |
| **Web ingestion** | `main/rag/fetcher.py` + `web.py` | Paste a URL, it learns the page; or discover & bulk-ingest same-domain sublinks |
| **File ingestion** | `main/rag/fetcher.py` | `/file notes.txt` — learn from any local text file |
| **Vector database** | `main/rag/store.py` | Chroma + local `all-MiniLM-L6-v2` embeddings, persisted on disk |
| **Retrieval** | `main/rag/store.py` | Top-4 most relevant chunks per question |
| **Grounded answers** | `main/cli.py` | Retrieved context injected into the prompt with source citations |
| **Chat history** | `main/cli.py` | Last 20 messages kept, survives model switches |
| **Token metrics** | `main/cli.py` | Reply time, tokens used, tok/s per answer |

## Quick start

```bash
# 1. Create & activate a virtualenv (already exists as env/)
source env/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the chat — it will ask how you want to run the model
python -m main
```

```text
How do you want to run CodeMind's brain?
  1) Ollama — I have Ollama installed with models already pulled
  2) llama.cpp — download and use .gguf models inside this project
Choice [1/2]: 1
Connecting to Ollama at http://localhost:11434 ...
Models found in Ollama (2):
  1) qwen2.5:3b
  2) nomic-embed-text
Pick one [1-2]: 1
CodeMind ready. Type /help for commands (RAG-enabled: paste a URL or use /file to ingest).
Active model: Ollama / qwen2.5:3b
User: /ingest https://python.langchain.com/docs/
User: what are the main modules of langchain?
```

## Commands

| Command | What it does |
|---|---|
| `/help` | Show all commands |
| `/ingest <url>` | Learn a web page; optionally discover & pick sublinks |
| `/file <path>` | Learn a local `.txt` / `.md` file |
| `/sources` | List everything CodeMind has learned |
| `/clear` | Wipe the knowledge base (vector database) |
| `/model` | Switch models mid-chat (works for Ollama and llama.cpp) |
| `/which` | Show the active model/backend |
| `exit` / `quit` | Leave the chat |

You can also just paste a URL directly — it triggers the same ingest flow.

## Project structure

```
codemind/                     # repo root (parent)
├── main/                     # the Python package (sub — different name on purpose)
│   ├── __init__.py           # package info + version
│   ├── __main__.py           # entry point: `python -m main`
│   ├── cli.py                # chat loop, commands, RAG prompt building
│   ├── models.py             # ★ two backends (Ollama / llama.cpp) + model download
│   └── rag/                  # ★ the RAG engine (learn this folder first)
│       ├── __init__.py       # public API + one-call ingest pipelines
│       ├── config.py         # every tuning knob lives here
│       ├── fetcher.py        # fetch URL / read file → clean text
│       ├── chunker.py        # split text into overlapping chunks
│       ├── store.py          # Chroma vector store + embeddings + retrieval
│       └── web.py            # interactive crawling & bulk ingestion
├── api/
│   └── model.py              # standalone Ollama-chat script (raw API example)
├── docs/
│   └── rag-explained.md      # ★ the learning guide: how RAG works here
├── tests/
│   └── test_rag.py           # unit tests for chunking + extraction
├── models/                   # put .gguf files here (or let CodeMind download one)
├── requirements.txt
├── README.md
├── env/                      # virtualenv (git-ignored)
└── vector_db/                # Chroma data, created at runtime (git-ignored)
```

**Where to start reading:** `main/rag/config.py` → `main/rag/fetcher.py` →
`main/rag/chunker.py` → `main/rag/store.py` → `main/cli.py`. Then read
`docs/rag-explained.md` alongside them.

## My learning routine

A repeatable daily practice that actually builds RAG intuition:

1. **Ingest something real** — a doc page you use, your own notes, a `.txt`.
2. **Ask one question** — note the answer and the source it cites.
3. **Tweak ONE knob** in `main/rag/config.py` (`TOP_K`, `CHUNK_SIZE`,
   `CHUNK_OVERLAP`, `EMBEDDING_MODEL_NAME`).
4. **Ask the same question again** — see how the answer changed.
5. **Read one function** you haven't traced yet, then try to explain it out
   loud (the Feynman technique). That's the real learning.

## Adding models

**Ollama path:** nothing to do in the code. Pull a model with
`ollama pull qwen2.5:3b` and pick it at startup.

**llama.cpp path:** drop any `.gguf` file into `models/` (or say "yes" when
CodeMind offers to download a starter model). It's auto-discovered and listed
by name + size — no code changes needed.

## Configuration cheatsheet

| Setting | File | Default | Meaning |
|---|---|---|---|
| `TOP_K` | `main/rag/config.py` | `4` | Chunks retrieved per question |
| `CHUNK_SIZE` | `main/rag/config.py` | `800` | Characters per chunk (~150-200 tokens) |
| `CHUNK_OVERLAP` | `main/rag/config.py` | `150` | Overlap so context isn't cut mid-thought |
| `EMBEDDING_MODEL_NAME` | `main/rag/config.py` | `all-MiniLM-L6-v2` | Local embedding model |
| `N_CTX` | `main/models.py` | `4096` | LLM context window |
| `MAX_HISTORY_MESSAGES` | `main/models.py` | `20` | Chat history length |
| `MODELS_DIR` | `main/models.py` | `models/` | Where `.gguf` files live |
| `OLLAMA_BASE_URL` | `main/models.py` | `http://localhost:11434` | Where Ollama listens |
| `temperature` | `main/cli.py` | `0.1` | Lower = more factual |

## Roadmap (my to-do list)

- [ ] Add `/delete <url>` to remove a single source
- [ ] Reranker (`cross-encoder`) on top of Chroma retrieval
- [ ] Hybrid search: BM25 keyword + vector
- [ ] Web UI (FastAPI / Streamlit) frontend
- [ ] PDF / Markdown ingestion
- [ ] Tag sources so I can scope questions to a folder

## Notes

- The inner package is named `main/` (not `codemind/`) so the parent folder
  and the package never share a name.
- `api/model.py` is a tiny standalone example of talking to Ollama's HTTP API
  directly — the same logic `main/models.py` uses inside the app.
- Everything runs offline after the initial model/embedding downloads.
- Tests: `python -m unittest discover tests`
