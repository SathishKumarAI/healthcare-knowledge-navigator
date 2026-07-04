# Feature Spec — F22 Open-access corpus fetch

## Summary
A stdlib-only script that fetches a real, redistributable clinical corpus — open-access
biomedical literature from Europe PMC — so the RAG runs against genuine medical documents
instead of only synthetic samples.

## Problem / why
Demos and evals are more convincing on real literature, but the repo is public, so the corpus
must be freely redistributable. Europe PMC open-access articles are licensed for reuse;
paywalled or non-redistributable material is excluded. The fetch has to be safe to run in CI
(offline-tolerant) and safe to re-run.

## Users & context
A developer/operator prep step, not part of the request path. Populates `data/corpus/`;
`python -m app.ingest` then (re)builds the index over it.

## Behaviour (acceptance criteria)
- WHEN `scripts/fetch_corpus.py` runs THEN for each configured clinical topic it resolves the
  top **open-access** article via the Europe PMC search API and downloads its full text (or
  abstract if full text is unavailable) as `data/corpus/<slug>.txt`.
- WHEN a target file already exists THEN it is skipped (idempotent — re-run adds only new topics).
- WHEN `--dry-run` is passed THEN it prints the articles it would fetch and downloads nothing.
- WHEN `--limit N` is passed THEN only the first N topics are considered.
- WHEN a network/IO error occurs THEN it is logged as `WARN` and skipped, never fatal (CI-friendly / offline-safe).
- WHEN a document is saved THEN it is recorded in `data/SOURCES.md` with its source URL (deduped).

## Rules / logic
- `app`-free, **stdlib only** (`urllib`, `json`, `re`, `html`) — no added dependency.
- `find_open_access(query)` reads the Europe PMC REST search endpoint
  (`https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=(...)+AND+OPEN_ACCESS:Y&format=json&resultType=core`)
  and returns the top result.
- `fetch_document(result)` pulls `.../<source>/<id>/fullTextXML` when the article is in
  Europe PMC full text, otherwise falls back to the result's abstract.
- `_xml_to_text` strips script/style then tags, unescapes entities, and collapses whitespace.
- **Polite / rate-limited**: sends a descriptive `User-Agent` (from `CORPUS_USER_AGENT`,
  defaulting to a public GitHub handle — no personal contact in the repo) and sleeps
  `RATE_LIMIT_SECONDS` (0.5s) between requests.
- **Open access only**: every query is constrained with `AND OPEN_ACCESS:Y`, so no paywalled
  content is fetched.
- **Provenance**: `record_source` appends a `- **<slug>** — <title> (Europe PMC, open access): <url>`
  line to `data/SOURCES.md`, creating the file with a header on first write.
- Topic set (`TOPICS`): hypertension, diabetes, asthma, anticoagulation, sepsis.

## Config / env knobs
- `CORPUS_USER_AGENT` — descriptive UA (a GitHub URL is fine).
- CLI: `--limit N`, `--dry-run`.

## Out of scope (for now)
- Paywalled or non-open-access articles (deliberately excluded for redistributability).
- Full-text search across all sources — one open-access article per configured topic.
- Sibling repos supply their **own** domain sources: finance uses SEC EDGAR 10-Ks;
  engineering uses arXiv `cs.*` + public RFCs. Only the source list differs; the stdlib-only,
  idempotent, rate-limited, provenance-recording shape is shared.

## Data touched
- Reads: Europe PMC (public, open access). Writes: `data/corpus/<slug>.txt`, `data/SOURCES.md`.

## Edge cases
- Topic with no open-access result (skipped with a message) · already-present file (skipped) ·
  duplicate URL in `SOURCES.md` (not re-appended) · full text unavailable (falls back to
  abstract) · unreadable/garbled XML (best-effort decode with `errors="ignore"`).

## Done when
- The script fetches real open-access articles into `data/corpus/`, is idempotent and
  offline-safe, records provenance in `data/SOURCES.md`, and ships no paywalled content —
  verified by a `--dry-run` that lists articles and a re-run that skips existing files.
