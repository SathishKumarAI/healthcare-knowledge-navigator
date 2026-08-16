# STATUS — healthcare-knowledge-navigator (MED)

**Last touched:** 2026-08-16 · **Branch:** `chore/sync-from-fin-2026-08` · **Tree:** clean

## What this is

One of three siblings that share a RAG engine by file copy. The reference implementation
is `../ai-due-diligence-copilot` (FIN); this repo is the **clinical-reference** domain —
same retrieval stack, different corpus, different system prompt, different eval set.

Shared engine: 16 files listed in `ENGINE_MANIFEST.sha256`, copied by
`scripts/sync_engine.py`. Everything else is this repo's own.

## Where it stopped

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

Nothing is owed. If FIN changes the engine, re-run the sync below and re-run the gate.

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
- Nothing here has been pushed.

## Commands

```bash
PY=../ai-due-diligence-copilot/.venv/Scripts/python.exe
$PY -m pytest && $PY -m ruff check app tests eval scripts && $PY -m mypy app
$PY scripts/sync_engine.py --check          # drift vs this repo's manifest
# from FIN, to push engine changes here:
#   python scripts/sync_engine.py --to ../healthcare-knowledge-navigator
```
