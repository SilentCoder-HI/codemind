"""Interactive crawling & bulk-ingestion helper for CodeMind.

Given a URL, lets the user choose to:
  1. Ingest just that single page, or
  2. Discover same-domain sublinks on that page (e.g. the different tutorial
     tabs on a docs site), pick which ones to ingest, and bulk-ingest them.

Only ever follows links on the SAME domain as the page you gave it —
it will never crawl off-site, so pointing it at a docs site won't
accidentally start pulling in the whole internet.
"""

from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from .chunker import chunk_text
from .fetcher import extract_text, fetch_url
from .store import VectorStore


def get_same_domain_links(url: str, html: str) -> list:
    """Extract unique same-domain links from a page's HTML, each with its visible link text."""
    soup = BeautifulSoup(html, "html.parser")
    base_domain = urlparse(url).netloc

    seen = set()
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith("#") or href.startswith("mailto:") or href.startswith("javascript:"):
            continue

        full_url = urljoin(url, href).split("#")[0]  # resolve relative links, drop fragments
        parsed = urlparse(full_url)
        if parsed.netloc != base_domain:
            continue  # same-domain only
        if full_url in seen:
            continue
        seen.add(full_url)

        label = a.get_text(strip=True) or full_url
        links.append({"url": full_url, "label": label})
    return links


def ingest_page_list(urls: list, store: VectorStore) -> int:
    """Ingest a list of URLs one by one, printing progress per page. Returns total chunks added."""
    total = 0
    for i, url in enumerate(urls, 1):
        print(f"  [{i}/{len(urls)}] Fetching {url} ...")
        try:
            html = fetch_url(url)
            text = extract_text(html)
            if not text:
                print("    -> skipped (no extractable text)")
                continue
            chunks = chunk_text(text)
            n = store.add_chunks(chunks, source=url)
            total += n
            print(f"    -> {n} chunks added")
        except Exception as e:
            print(f"    -> failed: {e}")
    return total


def interactive_ingest(url: str, store: VectorStore):
    """
    Main entry point: given a URL, ask the user whether to ingest just this page
    or discover and selectively bulk-ingest sublinks from it.
    """
    print(f"Fetching {url} to check the page...")
    try:
        html = fetch_url(url)
    except Exception as e:
        print(f"Failed to fetch {url} — {e}")
        return

    print("How do you want to ingest this?")
    print("  1) Just this page")
    print("  2) Discover sublinks on this page and pick which to ingest")
    choice = input("Choice [1/2]: ").strip()

    if choice != "2":
        text = extract_text(html)
        if not text:
            print("No extractable text found on that page.")
            return
        n = store.add_chunks(chunk_text(text), source=url)
        print(f"Ingested {n} chunks from {url}.")
        return

    links = get_same_domain_links(url, html)
    if not links:
        print("No same-domain sublinks found. Ingesting just this page instead.")
        text = extract_text(html)
        if text:
            n = store.add_chunks(chunk_text(text), source=url)
            print(f"Ingested {n} chunks from {url}.")
        return

    print(f"\nFound {len(links)} same-domain links on this page:")
    for i, link in enumerate(links, 1):
        print(f"  {i}. {link['label'][:60]}  ({link['url']})")

    print("\nEnter which ones to ingest:")
    print("  - comma-separated numbers, e.g. 1,3,5")
    print("  - 'all' to ingest everything listed")
    print("  - 'none' to cancel")
    selection = input("Selection: ").strip().lower()

    if selection in ("none", ""):
        print("Cancelled.")
        return

    if selection == "all":
        selected_urls = [l["url"] for l in links]
    else:
        try:
            indices = [int(x.strip()) for x in selection.split(",") if x.strip()]
            selected_urls = [links[i - 1]["url"] for i in indices if 1 <= i <= len(links)]
        except (ValueError, IndexError):
            print("Couldn't parse that selection. Cancelled.")
            return

    if not selected_urls:
        print("Nothing selected. Cancelled.")
        return

    print(f"\nIngesting {len(selected_urls)} page(s)...")
    total = ingest_page_list(selected_urls, store)
    print(f"\nDone. {total} total chunks ingested from {len(selected_urls)} page(s).")
