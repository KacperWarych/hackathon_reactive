# Decision memory

Local hybrid retrieval over the Reactive AI conversation dataset, with a source-focused evidence explorer. This is a personal decision-memory prototype. The provided records are not presented as real sales deals.

**Stack:** BM25, Qwen3-Embedding-0.6B, reciprocal rank fusion, Qwen3-Reranker-0.6B, one bounded update-search pass, and Reactor for final answers. The model revisions are pinned in `models.lock.json`; Python dependencies are pinned in `uv.lock`.

## Start

```sh
cd '/Users/kacperwarych/Desktop/hackathon reactive ai'
sh scripts/setup.sh
.venv/bin/memory ingest --split dev
.venv/bin/memory ingest --split test
.venv/bin/memory manifests
.venv/bin/memory index --manifest tune --manifest validation
.venv/bin/streamlit run app.py
```

Open [the local explorer](http://localhost:8501). It binds only to localhost. Indexing is incremental and may take substantial time; begin with `--limit-histories 1` to profile your machine. Keyword-only indexing uses `--lexical-only` and does not load neural model weights, but uses the same pinned Qwen tokenizer. The UI never substitutes fabricated answers for unavailable Reactor access.

The setup script installs an isolated Python 3.12 environment. It does not modify your shell startup files. MPS is selected when available, followed by CUDA and CPU. Set `MEMORY_DEVICE=cpu` to force CPU. An unsupported MPS operation or memory failure is reported and switches the loaded models to CPU.

The application package uses a regular installation so Python does not depend on an editable `.pth` file, which can be skipped when macOS marks that file hidden. After editing package source, rerun `UV_CACHE_DIR=.cache/uv UV_PYTHON_INSTALL_DIR=.python .tools/uv sync --frozen --no-editable --reinstall-package decision-memory` to refresh the installed code.

## Reproducible offline preparation

```sh
.venv/bin/python -u scripts/prepare.py > .data/prepare.log 2>&1
```

This imports the supplied archives, creates deterministic manifests, indexes selected development histories, compares all five retrieval variants on tuning, freezes the winner, evaluates held-out validation and ten larger histories, and indexes all test histories. It does not contact Reactor unless `--live` is supplied. Resume the same command after interruption: embeddings and question-level evaluation results are checkpointed. Keep the same dataset files and model lock when resuming.

Completion writes `.data/evaluation/offline-summary.json` with the selected method, measured reports, stress results, and test-index counts. The three development examples have replayable evidence snapshots; generated answers require Reactor access.

Downloads are expected in `~/Downloads`: `dev.tar.gz`, `dev-large.tar.gz`, and `test.tar.gz`. Override with `scripts/prepare.py --downloads /path/to/archives`. Archives are streamed rather than expanded blindly. Development gold is written to `.data/evaluation/` and is never passed to the retriever.

## Individual commands

```sh
# Examine an indexed question; all methods use the same chunks and history/date scope.
.venv/bin/memory retrieve --split dev --question-id QUESTION_ID --mode full --out .data/evidence.json

# Tuning: BM25, dense, hybrid, reranked hybrid, and full update search.
.venv/bin/memory evaluate --manifest tune
.venv/bin/memory freeze .data/evaluation/retrieval-tune-REPORT_ID.json
.venv/bin/memory evaluate --manifest validation --modes selected

# Stress test on the same held-out questions with larger histories.
.venv/bin/memory ingest --split dev-large --manifest stress
.venv/bin/memory index --manifest stress
.venv/bin/memory evaluate --manifest stress --modes selected

# Prepare the complete test split.
.venv/bin/memory index --split test
```

Manifests target 50 questions each, ten per question type, with abstention cases and disjoint histories. Question variants sharing a history stay together. Dev and dev-large versions use the same partition. `--mode selected` requires a completed tuning report and matching frozen configuration; explicit `--mode full` is available for exploratory runs.

## Reactor configuration and submission

Copy `.env.example` to `.env` if needed and configure `REACTOR_BASE_URL`, `REACTOR_AGENT_ID`, and `REACTOR_ACCESS_KEY` locally. Never commit or paste the key. This application uses the supplied participant kit's protocol and final-answer parsing. The original scripts are preserved in `src/decision_memory/vendor/`; see `NOTICE.md`.

```sh
.venv/bin/memory run --manifest validation --run-id validation --mode selected
.venv/bin/memory evaluate --run-id validation
.venv/bin/memory run --split test --run-id test-final --mode selected
.venv/bin/memory export --run-id test-final --out .data/submission/predictions.jsonl
```

Alternatively, add `--live` to `scripts/prepare.py` to continue through both live runs after offline preparation.

If offline preparation is already running, start live validation now and continue with test predictions when that preparation finishes:

```sh
.venv/bin/python -u scripts/live_run.py > .data/live-run.log 2>&1
```

This uses run IDs `validation-live` and `test-final`. Resume with the same command. It waits for an idle local agent and matching offline completion metadata, and stops for review on an uncertain or invalid Reactor outcome. A completed run writes `.data/submission/predictions.jsonl` and `.data/runs/benchmark-summary.json`.

One agent has one active history. Runs acquire an OS-level lock shared across local processes. All questions for a history run sequentially and chronologically. The app cannot interrupt a benchmark run. Do not use the same agent simultaneously from another computer or tool; local locking cannot control those clients.

Every outgoing request is checkpointed before transmission. Completed answers are skipped on resume. A timeout, crash, unknown citation, or factual answer still uncited after one correction stops the run and remains incomplete. It is **not** converted into abstention. Inspect the saved request/result before using `--retry-uncertain`; that flag knowingly permits repeating a possibly accepted request. Changing the run's question set, mode, or model/configuration fingerprint requires a new run ID.

For a known completed answer that omits all citations, the runner asks Reactor once for a corrected final answer with source labels. Both requests and responses are retained. If that correction is still uncited or encounters a transport failure, the run stops for review. It never adds citations to model output itself.

Submission export validates all 146 test questions and checks citations against each question's own history. Missing or failed answers block a full export. `--allow-partial` is for diagnostics and does not make an incomplete result submission-ready. Final answers are never manually edited.

## Evidence and interpretation

The explorer shows original roles and dates, selected excerpts, candidate ranks, update queries, and saved Reactor responses. Prepared examples are genuine development questions for a purchase, an updated fact, and missing evidence. Their saved answers become replayable only after running them through Reactor.

Excerpts open in relevance order; use the date sort to follow the timeline. The full retrieval variant reranks up to 40 initial candidates. It searches again only when its heuristic detects missing question terms or missing update evidence, with one expansion query and at most 12 new candidates. Initial scores are reused rather than recomputed. These heuristics do not prove answer completeness.

Long conversations are indexed as before, then reduced to original, role-labeled exchanges for Reactor. Short replies retain nearby context. The default limits are 2,000 evidence-text tokens, 8,000 evidence characters, six excerpts, and 320 tokens per excerpt; the entire serialized request must still fit 16,000 characters. Token counts use the pinned embedding tokenizer, so they estimate Reactor's token usage. Set these limits through `Config` when comparing budgets.

Extractive memory caches each speaker turn by content and tokenizer revision, so appended conversations reuse unchanged turns. It stores source offsets and English/Polish cue labels for concerns, requirements, updates, confirmations, and hypothetical statements. These are retrieval hints, not verified blocker states or generated summaries. Existing indices work immediately; memory records fill lazily during retrieval or on the next index run. Unchanged chunk vectors are reused after appends, and query vectors/reranking scores persist in a bounded, model-versioned cache. Source revisions invalidate a reused retriever after dataset changes.

Retrieval traces include cache hits/misses, selected source spans, evidence tokens, excerpt counts, reranked document counts, and stage timings. A count/total question carries a coverage warning: a bounded evidence sample cannot establish a population total. Reactor must use a recorded total or a demonstrably complete set, or report insufficient evidence. Campaign-wide aggregation still requires a separate complete-coverage workflow.

To compare budgets without contacting Reactor:

```sh
PYTHONPATH=src .venv/bin/python scripts/benchmark_budgets.py --split salesgen --limit 20 --mode bm25 --out outputs/budget-sweep.json
```

The script compares 1,000/2,000/4,000 evidence tokens and records retrieval p50/p95, input size, cache behavior, and gold-session coverage when annotations exist. The six-excerpt cap may bind before the larger token budgets. It does not measure Reactor latency or answer accuracy. Evaluation reports separately expose p50/p95 for saved Reactor responses.

Decision views require source references for each entry. Resolutions additionally require an exact quote from a cited user statement. This checks traceability, not whether a quote semantically proves resolution. The UI labels interpretation and recommendations separately and falls back to the original cited response if structure validation fails. Similarity, fusion, and reranker scores are not confidence probabilities.

## Evaluation and tests

```sh
.venv/bin/pytest -q
.venv/bin/ruff check --no-cache src/decision_memory app.py --exclude vendor
```

Retrieval reports contain gold-session recall at 20 distinct candidate sessions, all-required-evidence coverage, packed evidence recall/precision, and timing, including breakdowns by question type. Candidate coverage and selected evidence are not final citations. Answer reports distinguish automatic matches, correct/wrong abstention, and unjudged answers. They do not claim official LLM-judged accuracy.

Tests cover isolation, dates, metadata reuse, chunk coverage and overlap, token/excerpt/message budgets, short confirmations in long conversations, English/Polish update hints, incremental memory/vector reuse, neural cache reuse, source invalidation, product tokens, citation validation, resumability, transport failures, locking, and structured decision validation. Unit fixtures are synthetic and used only for tests; demonstration examples come from the supplied data.

Local artifacts live in `.data/`: the SQLite database, model cache, manifests, evaluation reports, and replayable run records. They are ignored by Git. The first implementation intentionally omits alternative model families, fine-tuning, cross-deal sales analytics, fictional demos, and external actions.

## Salesgen dataset

Import the unpacked dataset and build its retrieval index from the project directory:

```bash
memory ingest --split salesgen --source ./salesgen_dataset_fail
memory index --split salesgen
```

Select `salesgen` in the app's Dataset selector. The directory loader also accepts
`public/` directly (public inputs only). Existing archive commands still work.
Gold answers are stored separately for evaluation; call-level gold labels are never imported.
The 176 Polish calls use `user` for the customer and `assistant` for the seller.

For a quick lexical-only check, use `memory index --split salesgen --lexical-only`
and `memory retrieve --split salesgen --question-id QUESTION_ID --mode bm25`.
Full/hybrid retrieval requires the regular index command above.
Dataset-wide counting questions require complete customer-level analysis; top-k
retrieval alone does not establish accurate campaign totals.

## Adding conversations in the app

Choose a dataset and history, then open **Add a conversation**. Enter the date,
time, and transcript with `Customer:` / `Seller:` (or `user:` / `assistant:`)
speaker labels. Save to store the conversation and update its retrieval index.
If indexing fails, the saved conversation remains available for a retry.
Questions only use conversations on or before their **Answer as of** date.

Manual additions live in the local SQLite database and survive reimporting the
original dataset. **Download added conversations** exports them in histories
JSONL format. Original dataset files and gold labels are not changed.

Code organization: `entries.py` handles parsing, storage and export;
`entry_ui.py` contains the entry form; `app.py` composes the explorer.
