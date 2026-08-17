# STATUS — healthcare-knowledge-navigator (MED)

**Last touched:** 2026-08-17 · **Branch:** `chore/sync-from-fin-2026-08` · **Tree:** clean

## What this is

One of three siblings that share a RAG engine by file copy. The reference implementation
is `../ai-due-diligence-copilot` (FIN); this repo is the **clinical-reference** domain —
same retrieval stack, different corpus, different system prompt, different eval set.

Shared engine: 16 files listed in `ENGINE_MANIFEST.sha256`, copied by
`scripts/sync_engine.py`. Everything else is this repo's own.

## Where it stopped

**PR #1 is open and rebuilding.** The three sync commits that had only ever existed on
one disk are pushed. `quality` and `web` pass — **the first time this repo's CI has run
`pytest` and `mypy` at all**. `docker` failed on a base-image CVE, which is fixed in the
same PR and verified locally.

Synced from FIN and verified, **not developed further**. FIN is where the work happens;
this repo receives it.

Gate on 2026-08-16, run with FIN's virtualenv (this repo has no `.venv` of its own):

```
ruff format --check   42 files already formatted
ruff check            All checks passed!
mypy app              Success: no issues found in 19 source files
pytest                84 passed
sync_engine --check   in sync
```

## Next action

1. **Merge PR #1** when green.
2. **Take FIN's provider work.** FIN merged its PR #20: the provider seam now has
   independent `LLM_PROVIDER` / `EMBED_PROVIDER` halves, an OpenAI-compatible adapter, and
   a Chroma collection keyed on the embedding model. Run the sync below, **plus a
   hand-copy** of the provider block in `app/config.py` (~83 lines),
   `tests/test_providers.py`, and the `langchain-openai` line in `requirements.txt`. The
   engine now *imports* `ProviderName` and `LOCAL_HOSTS` from `app/config.py`, so a sync
   without the config block will not import. Then relock and regenerate the manifest.
3. **`chunk_size` 1000 → 400.** Approved 2026-08-17. This repo is still at FIN's old value
   because `config.py` is never synced. Measured on this repo's own
   `eval/qa_dataset.jsonl`, dense hit@1 does **not** improve — see the umbrella
   `../STATUS.md` for the table. Ship it for citation precision, and say so in the commit:
   at 1000 every document is a single chunk, so `app/grounding.py:240` verifies a claim
   against an entire document's token set and any claim assembled from scattered facts
   "verifies". Do not borrow FIN's hit-rate justification.

## What arrived in the last sync, and why it matters here

Five engine files changed (`cache.py`, `grounding.py`, `main.py`, `rag.py`,
`retrieval.py`). Three of them fix problems this repo had too:

- **Source diversity cap.** One uploaded document producing many near-identical chunks
  could fill every `top_k` slot and own the answer — no prompt injection needed. Capped
  at `MAX_CHUNKS_PER_SOURCE=2`.
- **Engine self-heal.** `python -m app.ingest` runs out of process and resets the Chroma
  collection under a serving API, which used to poison the instance until restart (every
  request 500). It now rebuilds in place.
- **Grounding fixes.** Grouped citation markers (`[1, 2, 3]`) were unparsed; absence
  claims ("the documents do not state X") were scored as fabrications.

Security bumps, same CVEs as FIN and reachable the same way — `/v1/upload` feeds
untrusted PDFs and images into these libraries:

- `pypdf` 5.9.0 → 6.16.1 (2 HIGH, DoS via crafted inline images)
- `pillow` 11.3.0 → 12.3.0 (13 HIGH, incl. heap out-of-bounds write)

The prompt gained a traceability rule. `- Surface relevant cautions, contraindications,
and monitoring requirements.` instructed the model to produce material that is by
definition not in the passages, which the grounding verifier then flagged as unsupported.
Cautions are still surfaced; they must cite a passage now. Measured on FIN's corpus, the
equivalent change moved mean grounding 0.808 → 0.902 and removed every repeat offender.

**This has not been measured on the clinical corpus.** Do that before trusting it here —
the rule is more consequential in a domain where a withheld caution is the dangerous
failure, not a cosmetic one.

## Traps

- **No `.venv`.** Run tooling with `../ai-due-diligence-copilot/.venv/Scripts/python.exe`.
- **`app/config.py` is NOT in the engine manifest.** The last sync shipped a `main.py`
  referencing `settings.max_chunks_per_source` while this repo's config had no such
  field — it would have crashed on startup and no check would have caught it. Config,
  Dockerfile, CI, lockfiles and the web app all drift silently. After any sync, grep for
  settings the new engine code reads.
- **`requirements.lock` is what ships**, not `requirements.txt`. The Dockerfile installs
  from the lock. Editing the ranges without running `scripts/lock.sh` changes nothing.
- **CRLF was wrong here and is now fixed.** This tree held 2457 CR across `app/*.py` and
  all 12 manifest entries were wrong — passing on Windows, failing on every Linux
  checkout. Fixed by refreshing through `.gitattributes` (`git rm --cached -r . &&
  git reset --hard`, no content change) plus FIN's `sync_engine.py`, whose generator now
  writes the manifest with `newline="
"`. That is the recipe if it returns.
- **`.github/workflows/ci.yml` embeds this repo's name** in the `docker build` tag and the
  Trivy `image-ref`. Copying FIN's file wholesale retags this image as FIN's — substitute
  the name.
- **A green Trivy run is not a Trivy run that stays green.** FIN's `docker` job passed and
  this one failed on the identical base image minutes later, purely because Trivy's DB
  updated. The Dockerfile now runs `apt-get upgrade` in the runtime stage.
- **This repo still chunks at 1000** while FIN moved to 400 — see "Next action". The
  collection is `healthcare_kb`, and note it is now suffixed with a hash of the embedding model
  once FIN's provider work lands.

## Commands

```bash
PY=../ai-due-diligence-copilot/.venv/Scripts/python.exe
$PY -m pytest && $PY -m ruff check app tests eval scripts && $PY -m mypy app
$PY scripts/sync_engine.py --check          # drift vs this repo's manifest
# from FIN, to push engine changes here:
#   python scripts/sync_engine.py --to ../healthcare-knowledge-navigator
```
