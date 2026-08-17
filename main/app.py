"""CodeMind — RAG-enabled chat application with mode selection.

Modes determine the system prompt personality.
RAG provides dynamic per-user knowledge via vector search.
Fine-tuning (dataset.JSONL) provides the base reasoning style.
"""

import os
import time

from data import SYSTEM_PROMPTS
from main.models import (
    MAX_HISTORY_MESSAGES,
    choose_backend,
    switch_model_interactive,
)
from main.rag import (
    TOP_K,
    VectorStore,
    ingest_text_file,
    ingest_url,
    interactive_ingest,
    is_url,
)


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

MENU = {
    "1": "coding",
    "2": "nextjs",
    "3": "general_qa",
    "4": "url_rag",
    "5": "security_concepts",
}


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
    """Give more room to code/explanation-heavy asks, less to short Q&A."""
    code_signals = ["write", "code", "implement", "function", "script", "class", "algorithm"]
    if any(kw in user_input.lower() for kw in code_signals):
        return 512
    return 220


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

HELP_TEXT = (
    "CodeMind commands:\n"
    "  /help              Show this help message\n"
    "  /ingest <url>      Learn a web page; optionally discover & pick sublinks\n"
    "  /file <path>       Learn a local .txt / .md file\n"
    "  /sources           List everything CodeMind has learned\n"
    "  /clear             Wipe the knowledge base (vector database)\n"
    "  /model             Switch models mid-chat (Ollama or llama.cpp)\n"
    "  /which             Show the active model/backend\n"
    "  /mode              Switch mode (coding, nextjs, general_qa, url_rag, security_concepts)\n"
    "  exit / quit        Leave the chat\n"
    "You can also just paste a URL directly to trigger ingest."
)


def handle_command(user_input: str, store: VectorStore, state: dict) -> bool:
    """Returns True if the input was a recognized command (and was handled)."""
    stripped = user_input.strip()
    lower = stripped.lower()

    if lower == "/help":
        print(HELP_TEXT)
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

    if lower == "/mode":
        print("Available modes:")
        for key, name in MENU.items():
            marker = " <--" if name == state["mode"] else ""
            print(f"  {key}. {name}{marker}")
        choice = input("Pick a mode [1-5]: ").strip()
        mode_name = MENU.get(choice)
        if mode_name is None:
            print("CodeMind: Invalid choice.")
        else:
            state["mode"] = mode_name
            print(f"CodeMind: Switched to {mode_name} mode.")
        return True

    return False


# ---------------------------------------------------------------------------
# Main chat loop
# ---------------------------------------------------------------------------

def chat():
    # --- Mode selection ---
    print("What type of model do you need?")
    for key, name in MENU.items():
        print(f"  {key}. {name}")
    choice = input("Enter number [1-5]: ").strip()
    mode_name = MENU.get(choice, "general_qa")

    # --- Backend selection ---
    backend = choose_backend()
    state = {"backend": backend, "mode": mode_name}

    # --- RAG store ---
    store = VectorStore()

    # --- Chat history ---
    history = [SYSTEM_PROMPTS[mode_name]]

    print(f"\nCodeMind ready. Mode: {mode_name} | Model: {backend.name}")
    print("Type /help for commands (RAG-enabled: paste a URL or use /file to ingest).\n")

    while True:
        try:
            user_input = input("User: ")
        except (KeyboardInterrupt, EOFError):
            print("\nExiting chat.")
            break

        if user_input.strip().lower() in ("exit", "quit"):
            print("Exiting chat.")
            break

        if not user_input.strip():
            continue

        # --- Handle commands ---
        if handle_command(user_input, store, state):
            continue

        # --- Auto-ingest URLs pasted directly ---
        if is_url(user_input.strip()):
            interactive_ingest(user_input.strip(), store)
            continue

        # --- Update system prompt if mode changed ---
        current_sys = SYSTEM_PROMPTS[state["mode"]]
        if history[0] != current_sys:
            history[0] = current_sys

        # --- Append user message ---
        history.append({"role": "user", "content": user_input})
        recent_history = history[-MAX_HISTORY_MESSAGES:]

        # --- Build RAG context ---
        rag_context = build_rag_context(store, user_input)
        messages = [recent_history[0]]  # system prompt
        if rag_context:
            messages.append({"role": "system", "content": rag_context})
        messages += recent_history[1:]  # conversation history

        # --- Call LLM ---
        start = time.time()
        try:
            response = state["backend"].create_chat_completion(
                messages=messages,
                max_tokens=pick_max_tokens(user_input),
                temperature=0.1,
            )
        except Exception as e:
            print(f"CodeMind: Error calling model — {e}")
            history.pop()
            continue
        elapsed = time.time() - start

        bot_reply = response["choices"][0]["message"]["content"]
        print(f"CodeMind: {bot_reply}\n")

        # --- Stats ---
        usage = response.get("usage", {})
        completion_tokens = usage.get("completion_tokens", 0)
        prompt_tokens = usage.get("prompt_tokens", 0)
        tok_per_sec = completion_tokens / elapsed if elapsed > 0 else 0
        print(
            f"[{state['backend'].name} | prompt: {prompt_tokens} tok | "
            f"reply: {completion_tokens} tok | {elapsed:.2f}s | {tok_per_sec:.1f} tok/s]"
        )

        # --- Save to history ---
        history.append({"role": "assistant", "content": bot_reply})


if __name__ == "__main__":
    chat()
