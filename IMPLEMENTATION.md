# Implementation status

## Delivered

- Isolated Python 3.12 environment, uv dependency lock, and pinned Qwen model revisions.
- Streaming archive ingestion, SQLite metadata, history-specific dates, and content-cached vectors.
- BM25, dense, hybrid, reranked hybrid, and bounded expansion retrieval through one shared interface.
- Original excerpts, history/date isolation, per-search rank traces, and complete-message size checks.
- Reactor participant-kit integration, exclusive local agent locking, durable request records, explicit uncertain-request recovery, and strict submission export.
- Streamlit evidence explorer with supplied/custom questions, relevance/date ordering, real evidence replay, decision-view validation, and evaluation reports.
- Deterministic tuning/validation manifests of 50 questions each, ten held-out larger histories, and three genuine development examples.
- Resumable offline preparation and documented live validation/test commands.

## Verified locally

- 36 tests passed; Ruff passed, including bounded citation correction and stopping safely if correction fails.
- Both compact Qwen models loaded and ran on Apple MPS.
- Development ingestion: 470 histories, 22,428 session occurrences, 526 questions.
- Test ingestion: 15 histories, 3,000 sessions, 146 questions.
- Three real development examples evaluated using all five retrieval methods. All methods recovered the gold sessions for the two answerable examples. The third example is unanswerable; retrieval coverage cannot establish correct abstention.
- Explorer inspected in the browser with an actual saved evidence result.
- Reactor credentials configured and verified with three real development demo questions: two automatic answer matches and one correct abstention. Both answerable examples had citation evidence F1 of 1.0. See `outputs/evaluation-report.md` for measured results and limits.
- A real structured decision view passed validation and is replayable for the changed-fact example. It records the routine change and leaves unsupported resolutions empty.
- Completed 50-question offline tuning and 50-question retrieval validation. The frozen selection is hybrid retrieval plus reranking; stress indexing remains in progress.

## Remaining completion gates

The full offline indexing, tuning, validation, and stress workflow was launched with `scripts/prepare.py`. Read `.data/prepare.log` for current progress. Successful completion writes `.data/evaluation/offline-summary.json`; the summary must match the current configuration fingerprint. A running process or a three-example smoke test is not a completed benchmark.

Reactor credentials are now configured. Real cited answers for the three demonstration questions are saved in `.data/runs/demo-live/`. The live validation workflow is running via `scripts/live_run.py`; it waits for matching offline completion metadata before processing all 146 test questions. The application must complete those runs and export every validated test prediction before the full acceptance criteria are met.

See README.md for setup, recovery, evaluation, and submission commands. Demo answers and retrieved evidence are replayable in the explorer without another Reactor request.
