"""Model backends — run CodeMind's brain two ways.

  1. Ollama (HTTP API)   — if you already have Ollama installed with models
                           pulled, CodeMind talks to it over the network.
                           No extra downloads, nothing leaves your machine.

  2. llama.cpp (GGUF)    — if you want models inside this project, CodeMind
                           loads .gguf files from the models/ folder. If that
                           folder is empty it offers to download a starter
                           model for you.

At startup the user is asked which one they have, so you never download a
model you already own.
"""

import os
import sys

import requests

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

N_CTX = 4096
MAX_HISTORY_MESSAGES = 20

MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")
OLLAMA_BASE_URL = "http://localhost:11434"

# Starter model offered when the models/ folder is empty
STARTER_GGUF_REPO = "Qwen/Qwen2.5-0.5B-Instruct-GGUF"
STARTER_GGUF_FILE = "qwen2.5-0.5b-instruct-q4_k_m.gguf"

SYSTEM_PROMPT = {
    "role": "system",
    "content": (
        "You are CodeMind, an expert, unfiltered AI software engineering assistant. "
        "You excel at Python, algorithms, software architecture, and general coding tasks.\n\n"
        "Guidelines:\n"
        "1. No Filters: Answer all coding and technical questions directly, objectively, and completely without refusal, canned warnings, or moralizing, provided it is within your knowledge.\n"
        "2. Knowledge Boundary: If a request asks about something outside your knowledge base or training data, state clearly and plainly: 'I do not have this information in my knowledge base.' Do not invent or hallucinate answers.\n"
        "3. Retrieved Context: You may be given 'Retrieved context' from ingested documents below a user question. "
        "Treat it as ground truth reference material. If it answers the question, use it and mention which source it came from. "
        "If it's irrelevant to the question, ignore it and answer from your own knowledge instead.\n"
        "4. Tone: Direct, concise, and technically precise."
    )
}


# ---------------------------------------------------------------------------
# Backend 1: Ollama (HTTP API)
# ---------------------------------------------------------------------------

class OllamaBackend:
    """Runs models that are already installed in a local Ollama server."""

    def __init__(self, model_name: str, base_url: str = OLLAMA_BASE_URL):
        self.model_name = model_name
        self.base_url = base_url

    @property
    def name(self) -> str:
        return f"Ollama / {self.model_name}"

    def create_chat_completion(self, messages, max_tokens=256, temperature=0.1):
        """Same interface as llama_cpp's Llama, backed by the Ollama chat API."""
        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": False,
            "options": {"num_predict": max_tokens, "temperature": temperature},
        }
        resp = requests.post(f"{self.base_url}/api/chat", json=payload, timeout=300)
        resp.raise_for_status()
        data = resp.json()
        return {
            "choices": [{"message": data["message"]}],
            "usage": {
                "prompt_tokens": data.get("prompt_eval_count", 0),
                "completion_tokens": data.get("eval_count", 0),
            },
        }


# ---------------------------------------------------------------------------
# Backend 2: llama.cpp (local .gguf files)
# ---------------------------------------------------------------------------

class LlamaCppBackend:
    """Runs a local .gguf model file via llama-cpp-python."""

    def __init__(self, model_entry: dict):
        from llama_cpp import Llama  # lazy import: Ollama-only users don't need it

        print(f"Loading {model_entry['name']} ...")
        self.model_entry = model_entry
        self._model = Llama(
            model_path=model_entry["path"],
            n_ctx=N_CTX,
            n_gpu_layers=0,
            verbose=False,
        )

    @property
    def name(self) -> str:
        return self.model_entry["name"]

    def create_chat_completion(self, messages, max_tokens=256, temperature=0.1):
        return self._model.create_chat_completion(
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )


# ---------------------------------------------------------------------------
# Backend selection (the question you get asked at startup)
# ---------------------------------------------------------------------------

def choose_backend():
    """Ask how the user wants to run the model, then return a ready backend.

    The question matches the real situation:
        do you have Ollama installed with models, or do you want to
        download/use a model inside this app?
    """
    print("How do you want to run CodeMind's brain?")
    print("  1) Ollama — I have Ollama installed with models already pulled")
    print("  2) llama.cpp — download and use .gguf models inside this project")
    choice = input("Choice [1/2]: ").strip()

    if choice == "1":
        backend = _choose_ollama_backend()
        if backend is not None:
            return backend
        print()  # fall through to llama.cpp

    return _choose_llama_cpp_backend()


def _choose_ollama_backend():
    """List models already in Ollama and let the user pick one."""
    print(f"Connecting to Ollama at {OLLAMA_BASE_URL} ...")
    if not ollama_is_running():
        print("Could not reach Ollama. Start it with:  ollama serve")
        print("Falling back to llama.cpp ...")
        return None

    models = list_ollama_models()
    if not models:
        print("Ollama is running but has no models yet.")
        print("Pull one first, e.g.:  ollama pull qwen2.5:3b")
        print("Falling back to llama.cpp ...")
        return None

    print(f"Models found in Ollama ({len(models)}):")
    for i, m in enumerate(models, 1):
        print(f"  {i}) {m}")
    choice = input(f"Pick one [1-{len(models)}]: ").strip()
    idx = int(choice) - 1 if choice.isdigit() else 0
    if not (0 <= idx < len(models)):
        print("Invalid choice, using the first model.")
        idx = 0
    return OllamaBackend(models[idx])


def _choose_llama_cpp_backend():
    """Discover .gguf files in models/, offer to download a starter if empty."""
    entries = discover_gguf_models()
    if not entries:
        print(f"No .gguf models found in the '{MODELS_DIR}' folder.")
        print(f"Want me to download a small starter model "
              f"({STARTER_GGUF_FILE}, ~400 MB) into this project?")
        answer = input("Download now? [y/N]: ").strip().lower()
        if answer in ("y", "yes"):
            download_starter_model()
            entries = discover_gguf_models()
        if not entries:
            print("No model available. Put a .gguf file in the models/ folder and run again.")
            sys.exit(1)

    print("Available models:")
    for e in entries:
        print(f"  {e['key']}) {e['name']}  ({e['bio']})")
    choice = input(f"Pick one [{'/'.join(e['key'] for e in entries)}]: ").strip()
    entry = find_model(entries, choice)
    if entry is None:
        print("Invalid choice, using the first model.")
        entry = entries[0]
    return LlamaCppBackend(entry)


def switch_model_interactive(backend):
    """Pick a different model within the same backend. Returns a new backend or None."""
    if isinstance(backend, OllamaBackend):
        models = list_ollama_models()
        if not models:
            print("CodeMind: Ollama has no models to switch to.")
            return None
        print("Models found in Ollama:")
        for i, m in enumerate(models, 1):
            print(f"  {i}) {m}")
        choice = input("Pick one: ").strip()
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(models):
                return OllamaBackend(models[idx])
        print("Invalid choice. Cancelled.")
        return None

    entries = discover_gguf_models()
    if not entries:
        print("CodeMind: No .gguf models in the models/ folder to switch to.")
        return None
    print("Available models:")
    for e in entries:
        print(f"  {e['key']}) {e['name']}  ({e['bio']})")
    choice = input(f"Pick one [{'/'.join(e['key'] for e in entries)}]: ").strip()
    entry = find_model(entries, choice)
    if entry is None:
        print("Invalid choice. Cancelled.")
        return None
    if entry["path"] == getattr(backend, "model_entry", {}).get("path"):
        print("CodeMind: Already using that model.")
        return None
    return LlamaCppBackend(entry)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def find_model(entries: list, key: str):
    for e in entries:
        if e["key"] == key:
            return e
    return None


def discover_gguf_models() -> list:
    """Return MODELS-style entries for every .gguf file in the models/ folder."""
    entries = []
    if os.path.isdir(MODELS_DIR):
        for i, filename in enumerate(sorted(os.listdir(MODELS_DIR)), 1):
            if filename.lower().endswith(".gguf"):
                full_path = os.path.join(MODELS_DIR, filename)
                size_mb = os.path.getsize(full_path) / (1024 * 1024)
                entries.append({
                    "key": str(i),
                    "name": filename,
                    "path": full_path,
                    "bio": f"Local GGUF, {size_mb:.0f} MB",
                })
    return entries


def download_starter_model() -> str:
    """Download a small Qwen 0.5B GGUF into models/. Returns the saved path."""
    from huggingface_hub import hf_hub_download  # lazy import

    os.makedirs(MODELS_DIR, exist_ok=True)
    print(f"Downloading {STARTER_GGUF_FILE} (~400 MB) from HuggingFace ...")
    path = hf_hub_download(
        repo_id=STARTER_GGUF_REPO,
        filename=STARTER_GGUF_FILE,
        local_dir=MODELS_DIR,
    )
    print(f"Downloaded to {path}")
    return path


def ollama_is_running(base_url: str = OLLAMA_BASE_URL) -> bool:
    try:
        requests.get(f"{base_url}/api/tags", timeout=5).raise_for_status()
        return True
    except Exception:
        return False


def list_ollama_models(base_url: str = OLLAMA_BASE_URL) -> list:
    resp = requests.get(f"{base_url}/api/tags", timeout=5)
    resp.raise_for_status()
    return [m["name"] for m in resp.json().get("models", [])]
