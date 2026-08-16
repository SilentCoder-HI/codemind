"""Unit tests for the pure functions in the RAG pipeline.

Run from the repo root:  python -m unittest discover tests
(These tests avoid Chroma/the LLM — they only check chunking + extraction.)
"""

import os
import tempfile
import unittest

from main.rag import chunk_text, is_url
from main.rag.fetcher import extract_text, read_text_file


class TestChunker(unittest.TestCase):
    def test_long_text_makes_multiple_chunks(self):
        text = "word " * 1000
        chunks = chunk_text(text, chunk_size=200, overlap=50)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(c.strip() for c in chunks))

    def test_short_text_is_one_chunk(self):
        self.assertEqual(chunk_text("hello world"), ["hello world"])

    def test_overlap_reuses_text(self):
        text = "x" * 500
        chunks = chunk_text(text, chunk_size=200, overlap=50)
        joined = "".join(chunks)
        self.assertEqual(len(joined), len(text) + len(chunks) * 50 - 50)


class TestExtractText(unittest.TestCase):
    def test_strips_script_and_style(self):
        html = (
            "<html><body><p>Hello world</p>"
            "<script>bad_javascript()</script>"
            "<style>.hidden{}</style>"
            "<footer>footer noise</footer>"
            "</body></html>"
        )
        text = extract_text(html)
        self.assertIn("Hello world", text)
        self.assertNotIn("bad_javascript", text)
        self.assertNotIn("hidden", text)
        self.assertNotIn("footer noise", text)


class TestTextFile(unittest.TestCase):
    def test_reads_txt_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("This is my knowledge.\n")
            path = f.name
        try:
            self.assertEqual(read_text_file(path), "This is my knowledge.")
        finally:
            os.unlink(path)


class TestIsUrl(unittest.TestCase):
    def test_http_urls(self):
        self.assertTrue(is_url("https://example.com/page"))
        self.assertTrue(is_url("http://x.io"))

    def test_non_urls(self):
        self.assertFalse(is_url("example.com"))
        self.assertFalse(is_url("not a url"))


if __name__ == "__main__":
    unittest.main()
