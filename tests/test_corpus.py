"""Offline tests for the F22 Europe PMC corpus fetcher's pure helpers (no network)."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("fetch_corpus", ROOT / "scripts" / "fetch_corpus.py")
fetch_corpus = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fetch_corpus)  # type: ignore[union-attr]


def test_xml_to_text_strips_tags_and_scripts():
    raw = b"<article><title>Sepsis</title><style>.x{}</style><script>bad()</script><p>Fluids &amp; care</p></article>"
    text = fetch_corpus._xml_to_text(raw)
    assert "Sepsis" in text
    assert "Fluids & care" in text  # entity unescaped
    assert "bad()" not in text  # script body removed
    assert "<" not in text  # tags gone


def test_find_open_access_returns_top_result(monkeypatch):
    resp = {"resultList": {"result": [
        {"id": "PMC123", "source": "PMC", "title": "Hypertension guideline", "isOpenAccess": "Y"},
    ]}}
    monkeypatch.setattr(fetch_corpus, "_get", lambda url: json.dumps(resp).encode())
    result = fetch_corpus.find_open_access("hypertension management")
    assert result is not None
    assert result["id"] == "PMC123"
    assert result["isOpenAccess"] == "Y"


def test_find_open_access_none_when_no_results(monkeypatch):
    monkeypatch.setattr(fetch_corpus, "_get", lambda url: json.dumps({"resultList": {"result": []}}).encode())
    assert fetch_corpus.find_open_access("nonexistent topic") is None


def test_fetch_document_falls_back_to_abstract():
    # inEPMC != "Y" -> no full-text call; uses the abstract (no network needed).
    result = {
        "source": "MED", "id": "999", "title": "Asthma stepwise therapy",
        "abstractText": "<p>Start with a low-dose ICS.</p>", "inEPMC": "N",
    }
    doc = fetch_corpus.fetch_document(result)
    assert doc is not None
    text, url = doc
    assert "Asthma stepwise therapy" in text
    assert "low-dose ICS" in text
    assert url == "https://europepmc.org/article/MED/999"
