#!/usr/bin/env python3
"""Fetch a real, open corpus for the healthcare domain (feature F22).

Source: **Europe PMC** — a database of open-access biomedical and life-sciences
literature. We query the public REST API for open-access articles on common clinical
topics and save each article's full text (or, if full text is unavailable, its
abstract). Only ``OPEN_ACCESS`` content is fetched, so this corpus is safe to ship in a
public repo — no paywalled or non-redistributable material is downloaded.

Design:
- **stdlib only** (urllib) — no extra dependency, runs anywhere.
- **Idempotent** — skips files already present; re-run to add new topics only.
- **Polite** — sends a descriptive User-Agent and rate-limits requests.
- **Offline-safe** — network errors are logged and skipped, never fatal (CI-friendly).
- **Provenance** — every download is recorded in ``data/SOURCES.md`` with its URL.

Usage:
    python scripts/fetch_corpus.py                 # fetch defaults into data/corpus/
    python scripts/fetch_corpus.py --limit 3       # first 3 topics only
    python scripts/fetch_corpus.py --dry-run       # list what would be fetched

Set a contact for the User-Agent (a GitHub URL is fine):
    CORPUS_USER_AGENT="my-project (github.com/you)" python scripts/fetch_corpus.py
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CORPUS_DIR = PROJECT_ROOT / "data" / "corpus"
SOURCES_FILE = PROJECT_ROOT / "data" / "SOURCES.md"

# Europe PMC has no hard UA requirement, but we identify the requester politely.
# Only a public GitHub handle is used — no personal contact details in the repo.
USER_AGENT = os.environ.get(
    "CORPUS_USER_AGENT", "rag-learning-companion (github.com/SathishKumarAI)"
)
RATE_LIMIT_SECONDS = 0.5  # be gentle on the shared public API.

SEARCH_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
FULLTEXT_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest"

# A small set of common clinical topics. Each becomes one open-access document, so
# they exercise the clinical RAG over guideline- and study-style prose.
TOPICS: list[tuple[str, str]] = [
    ("hypertension", "hypertension management guideline"),
    ("diabetes", "type 2 diabetes management guideline"),
    ("asthma", "asthma treatment guideline"),
    ("anticoagulation", "atrial fibrillation anticoagulation guideline"),
    ("sepsis", "sepsis management guideline"),
]

_TAG_RE = re.compile(r"<[^>]+>")
_SCRIPT_STYLE_RE = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.DOTALL | re.IGNORECASE)
_WS_RE = re.compile(r"[ \t]{2,}")
_NL_RE = re.compile(r"\n{3,}")


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310 - fixed EBI host
        return resp.read()


def _xml_to_text(raw: bytes) -> str:
    text = raw.decode("utf-8", errors="ignore")
    text = _SCRIPT_STYLE_RE.sub(" ", text)
    text = _TAG_RE.sub(" ", text)
    text = html.unescape(text)
    text = _WS_RE.sub(" ", text)
    text = "\n".join(line.strip() for line in text.splitlines())
    return _NL_RE.sub("\n\n", text).strip()


def find_open_access(query: str) -> dict | None:
    """Return the top open-access result for a query, or None.

    Result dict has: id, source, title, isOpenAccess, hasPMC, abstractText.
    """
    params = urllib.parse.urlencode(
        {
            "query": f"({query}) AND OPEN_ACCESS:Y",
            "format": "json",
            "resultType": "core",
            "pageSize": "1",
            "sort": "CITED desc",
        }
    )
    meta = json.loads(_get(f"{SEARCH_URL}?{params}"))
    results = meta.get("resultList", {}).get("result", [])
    return results[0] if results else None


def fetch_document(result: dict) -> tuple[str, str] | None:
    """Return (text, source_url) for a result: full text if in PMC, else abstract."""
    source = result.get("source", "")
    ext_id = result.get("id", "")
    pmcid = result.get("pmcid", "")
    if result.get("inEPMC") == "Y" and pmcid:
        url = f"{FULLTEXT_URL}/{source}/{ext_id}/fullTextXML"
        try:
            text = _xml_to_text(_get(url))
            if text:
                return text, url
        except (urllib.error.URLError, TimeoutError, OSError):
            pass  # fall back to abstract below
    abstract = result.get("abstractText", "")
    if abstract:
        title = result.get("title", "")
        url = f"https://europepmc.org/article/{source}/{ext_id}"
        return f"{title}\n\n{_xml_to_text(abstract.encode('utf-8'))}", url
    return None


def record_source(slug: str, title: str, url: str) -> None:
    SOURCES_FILE.parent.mkdir(parents=True, exist_ok=True)
    header = "# Corpus sources\n\nOpen-access documents fetched by `scripts/fetch_corpus.py`.\n\n"
    if not SOURCES_FILE.exists():
        SOURCES_FILE.write_text(header, encoding="utf-8")
    line = f"- **{slug}** — {title} (Europe PMC, open access): {url}\n"
    existing = SOURCES_FILE.read_text(encoding="utf-8")
    if url not in existing:
        SOURCES_FILE.write_text(existing + line, encoding="utf-8")


def fetch(limit: int | None, dry_run: bool) -> int:
    CORPUS_DIR.mkdir(parents=True, exist_ok=True)
    topics = TOPICS[:limit] if limit else TOPICS
    saved = 0
    for slug, query in topics:
        dest = CORPUS_DIR / f"{slug}.txt"
        if dest.exists():
            print(f"skip {slug}: already present")
            continue
        try:
            result = find_open_access(query)
            time.sleep(RATE_LIMIT_SECONDS)
            if not result:
                print(f"skip {slug}: no open-access result found")
                continue
            title = result.get("title", slug)
            if dry_run:
                print(f"would fetch {slug}: {title}")
                continue
            doc = fetch_document(result)
            time.sleep(RATE_LIMIT_SECONDS)
            if not doc:
                print(f"skip {slug}: no full text or abstract available")
                continue
            text, url = doc
            dest.write_text(text, encoding="utf-8")
            record_source(slug, title, url)
            saved += 1
            print(f"saved {slug}: {len(text):,} chars -> {dest.relative_to(PROJECT_ROOT)}")
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            print(f"WARN {slug}: fetch failed ({exc}); skipping")
    return saved


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Fetch open healthcare corpus (Europe PMC open-access literature)."
    )
    ap.add_argument("--limit", type=int, default=None, help="max topics to fetch")
    ap.add_argument("--dry-run", action="store_true", help="list topics, download nothing")
    args = ap.parse_args()
    n = fetch(args.limit, args.dry_run)
    if not args.dry_run:
        print(f"\nDone. {n} new document(s) in {CORPUS_DIR.relative_to(PROJECT_ROOT)}.")
        print("Next: python -m app.ingest  (re)builds the index over the new corpus.")


if __name__ == "__main__":
    main()
