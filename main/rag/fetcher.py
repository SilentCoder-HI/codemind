"""Fetching and text extraction — turn raw sources into clean text.

Two kinds of input are supported:
  - URLs        -> fetch_url + extract_text (HTML pages)
  - local files -> read_text_file (.txt)
"""

import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from .config import REQUEST_TIMEOUT, STRIP_TAGS


def fetch_url(url: str) -> str:
    """Download a page and return raw HTML. Raises on network/HTTP errors."""
    headers = {"User-Agent": "Mozilla/5.0 (compatible; CodeMindBot/1.0)"}
    resp = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    return resp.text


def extract_text(html: str) -> str:
    """Strip boilerplate tags and return clean, whitespace-normalized text."""
    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:
        # lxml not installed/built correctly — fall back to Python's built-in parser.
        # Slightly slower, but has zero extra dependencies.
        soup = BeautifulSoup(html, "html.parser")

    for tag_name in STRIP_TAGS:
        for tag in soup.find_all(tag_name):
            tag.decompose()

    text = soup.get_text(separator="\n")
    # Collapse repeated blank lines / spaces left over from stripped tags
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()


def read_text_file(path: str) -> str:
    """Read a local text file (e.g. .txt, .md) and return its clean contents."""
    return Path(path).read_text(encoding="utf-8", errors="replace").strip()


def is_url(s: str) -> bool:
    return bool(re.match(r"^https?://\S+$", s.strip()))
