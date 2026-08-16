"""Command-line chat frontend for CodeMind.

Glues the pieces together:
  - `rag` package     -> ingest documents + retrieve relevant chunks
  - `models` module   -> choose a backend (Ollama or llama.cpp) and run the LLM
  - this module       -> the interactive chat loop + slash commands
"""

import os
import time

from .models import MAX_HISTORY_MESSAGES, SYSTEM_PROMPT, choose_backend, switch_model_interactive
from .rag import TOP_K, VectorStore, ingest_text_file, interactive_ingest, is_url


# ---------------------------------------------------------------------------
# RAG context helper
# ---------------------------------------------------------------------------

def build_rag_context(store: VectorStore, user_input: str) -> str:
    """Query the vector store and format the top-k chunks as a system message."""
    results = store.query(user_input, k=TOP_K)
    if not results:
        return ""
    lines = ["Retrieved context (from previously ingested pages):"]
    for r in results:
        snippet = r["text"].strip().replace("\n", " ")
        if len(snippet) > 600:
            snippet = snippet[:600] + "..."
        lines.append(f"- [source: {r['source']}] {snippet}")
    return "\n".join(lines)


def pick_max_tokens(user_input: str) -> int:
    """Cheap heuristic: give more room to code/explanation-heavy asks, less to short Q&A."""
    code_signals = ["write", "code", "implement", "function", "script", "class", "algorithm"]
    if any(kw in user_input.lower() for kw in code_signals):
        return 512
    return 220


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def handle_command(user_input: str, store: VectorStore, state: dict) -> bool:
    """Returns True if the input was a recognized command (and was handled)."""
    stripped = user_input.strip()
    lower = stripped.lower()

    if lower == "/help":
        print(
            "CodeMind commands:\n"
            "  /ingest <url>       fetch a page; choose to ingest just it, or discover & pick sublinks\n"
            "  /file <path>        read a local .txt/.md file and add it to the knowledge base\n"
            "  /sources            list all ingested source URLs\n"
            "  /clear              wipe the vector database\n"
            "  /model              switch models mid-chat (same history + vector store carry over)\n"
            "  /which              show which model/backend is currently active\n"
            "  exit / quit         leave the chat\n"
            "You can also just paste a URL directly to trigger the same ingest flow."
        )
        return True

    if lower.startswith("/ingest"):
        parts = stripped.split(maxsplit=1)
        if len(parts) < 2 or not is_url(parts[1]):
            print("CodeMind: Usage: /ingest <valid http(s) url>")
            return True
        interactive_ingest(parts[1].strip(), store)
        return True

    if lower.startswith("/file"):
        parts = stripped.split(maxsplit=1)
        if len(parts) < 2 or not os.path.isfile(parts[1]):
            print("CodeMind: Usage: /file <path to a .txt/.md file>")
            return True
        path = parts[1].strip()
        try:
            n = ingest_text_file(path, store)
            print(f"CodeMind: Ingested {n} chunks from {path}.")
        except Exception as e:
            print(f"CodeMind: Failed to ingest file — {e}")
        return True

    if lower == "/sources":
        sources = store.list_sources()
        if not sources:
            print("CodeMind: No sources ingested yet. Use /ingest <url>, /file <path>, or paste a link.")
        else:
            print("CodeMind: Ingested sources:")
            for s in sources:
                print(f"  - {s}")
        return True

    if lower == "/clear":
        store.clear()
        print("CodeMind: Vector database cleared.")
        return True

    if lower == "/which":
        print(f"CodeMind: Currently using {state['backend'].name}")
        return True

    if lower == "/model":
        new_backend = switch_model_interactive(state["backend"])
        if new_backend is not None:
            state["backend"] = new_backend
            print(f"CodeMind: Switched to {new_backend.name}. Chat history and ingested sources are unchanged.")
        return True

    return False


# ---------------------------------------------------------------------------
# Main chat loop
# ---------------------------------------------------------------------------

def chat():
    backend = choose_backend()
    state = {"backend": backend}

    store = VectorStore()
    history = []

    print("CodeMind ready. Type /help for commands (RAG-enabled: paste a URL or use /file to ingest).")
    print(f"Active model: {state['backend'].name}")

    while True:
        user_input = input("User: ")
        if user_input.lower() in ["exit", "quit"]:
            break
        if not user_input.strip():
            continue

        if handle_command(user_input, store, state):
            continue

        if is_url(user_input.strip()):
            interactive_ingest(user_input.strip(), store)
            continue

        history.append({"role": "user", "content": user_input})
        recent_history = history[-MAX_HISTORY_MESSAGES:]

        rag_context = build_rag_context(store, user_input)
        messages = [SYSTEM_PROMPT]
        if rag_context:
            messages.append({"role": "system", "content": rag_context})
        messages += recent_history

        start = time.time()
        response = state["backend"].create_chat_completion(
            messages=messages,
            max_tokens=pick_max_tokens(user_input),
            temperature=0.1,
        )
        elapsed = time.time() - start

        bot_reply = response["choices"][0]["message"]["content"]
        print("CodeMind:", bot_reply)

        usage = response.get("usage", {})
        completion_tokens = usage.get("completion_tokens", 0)
        prompt_tokens = usage.get("prompt_tokens", 0)
        tok_per_sec = completion_tokens / elapsed if elapsed > 0 else 0
        print(
            f"[{state['backend'].name} | prompt: {prompt_tokens} tok | "
            f"reply: {completion_tokens} tok | {elapsed:.2f}s | {tok_per_sec:.1f} tok/s]"
        )

        history.append({"role": "assistant", "content": bot_reply})
