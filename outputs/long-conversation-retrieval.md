# Long-conversation retrieval implementation

Implemented 2026-10-31 in `/Users/kacperwarych/Desktop/hackathon reactive ai`.

- Incremental extractive turn memory with source offsets, roles, English/Polish cue hints, and tokenizer-aware invalidation. Hints do not establish deal state.
- Original exchanges, contextual short replies, deduplication, and bounded evidence: 2,000 evidence-text tokens, 8,000 characters, six excerpts, 320 tokens per excerpt, and a separate 16,000-character full-request cap.
- Conditional update/missing-term expansion: one extra query, at most 12 additional rerank candidates, no repeated scoring of initial candidates.
- Persistent query/rerank caches keyed by input and model revision; unchanged chunk vectors reused after conversation appends. Reused retrievers invalidate source candidates after ingestion.
- Trace timings/cache metrics, source spans, token/excerpt counts, and evaluation p50/p95; offline budget-sweep script.
- Existing indices remain compatible. The installed Python package was rebuilt offline. Other agents retain UI and investigation ownership.

Validation: 61 tests passed in isolated staging. After the UI agent updated its files, all 60 tests in the current shared project passed; Ruff passed for backend and budget script.

On 12 real salesgen BM25 queries, mean serialized input fell from 13388 to 3743 characters (72.0% smaller), with evidence text averaging 798 Qwen tokens. Median local retrieval rose from 9 to 66 ms. Reactor latency and answer accuracy have not been measured.

Quality limit: broad population/count questions may require dozens of source sessions. Smaller bundles reduce their coverage, while the previous pipeline also lacked complete coverage. The trace flags these questions and Reactor is instructed to require a recorded total or complete set, otherwise abstain. Complete-history aggregation remains a separate workflow.

Artifacts: `long-conversation-retrieval.patch`, `retrieval-budget-comparison.json`, `retrieval-budget-sweep.json`. The sweep used the six-excerpt cap; it therefore binds before larger token budgets on these short source exchanges. Sweep cache warmup differs by budget and must not be interpreted as Reactor timing.
