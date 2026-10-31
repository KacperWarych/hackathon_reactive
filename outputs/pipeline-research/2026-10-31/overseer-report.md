# Reviewed pipeline findings — 2026-10-31

Decision: prioritize evidence-unit selection and its measurement before changing embedding/reranker models. This cycle found reproducible failure mechanisms, not a measured improvement in deployed answer accuracy. No application code was changed, no weights downloaded, and no paid API experiments run.

Researcher: `gpt-6.1-sol`, high reasoning, explicitly dispatched. Overseer: `gpt-6-astra`, high reasoning, explicitly dispatched by the coordinator (tool accepted; no separate runtime model introspection). The active project `/Users/kacperwarych/Desktop/hackathon reactive ai/src/decision_memory` and staged workspace source were identical in a recursive diff excluding `__pycache__`. No applicable AGENTS.md found in workspace or inspected ancestor locations.

| Recommendation | Evidence strength | Project fit | Expected benefit | Feasibility | Review |
|---|---:|---:|---:|---:|---|
| Retain answer-bearing units when a relevant chunk contains lexical ties/paraphrases | 4/5 | 5/5 | 4/5 | 4/5 | Highest implementation experiment priority; observed synthetic failure, population prevalence unknown |
| Add span/state sufficiency evaluation alongside official session metrics | 5/5 | 5/5 | 4/5 | 4/5 | First measurement prerequisite; directly exposes an observed metric blind spot |
| Test a coverage-aware route for multi-session counts/totals | 5/5 | 4/5 | 3/5 | 3/5 | Structural ceiling measured; solution cost and answer benefits unmeasured |

Scores are reviewer judgments, not benchmark results. Expected-benefit grades express hypotheses. Evidence grades measure support for the diagnosed problem, not proof that the proposed remedy works.

## 1. A correct upstream chunk can lose its answer

At [evidence.py:51](</Users/kacperwarych/Desktop/hackathon reactive ai/src/decision_memory/evidence.py:51>), options are ranked using exact keyword overlap and position; only the first two eligible memory units are retained. In a controlled 405-word user turn containing 400 weather filler words followed by “I became a lighthouse keeper,” the question “What is my current occupation?” produces three units, two options, and no answer in the packed evidence. This isolates packing after upstream retrieval has already supplied the correct chunk.

The researcher initially used a whitespace tokenizer. I independently reran the same probe using the real cached Qwen tokenizer, revision `97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3`; the result persisted. See [overseer-real-tokenizer-results.json](overseer-real-tokenizer-results.json). No neural weights were loaded. This does not establish how often the failure occurs in natural data, or that semantic unit reranking is the best fix.

Next experiment: freeze candidate chunks and compare current top-two lexical unit selection with a bounded broader-unit fallback, retaining the same 2,000-token/six-excerpt budget. Add semantic unit reranking only after measuring whether a cheaper fallback helps. Measure answer-span retention, preservation of role/context, packed session coverage, and packing latency on a small independently annotated set. Keep repeated/filler and paraphrase cases separate from naturally sampled records.

## 2. Session coverage hides lost answer spans

[evaluation.py:98](</Users/kacperwarych/Desktop/hackathon reactive ai/src/decision_memory/evaluation.py:98>) compares session IDs. A completely unrelated passage from the annotated source session scores `packed_recall=1.0`, `packed_all_required=true`, and `packed_precision=1.0`; so does the answer-losing packing probe above. This is correct for the session-level metric and is not an implementation bug in that scorer.

Preserve official scoring and add a small auxiliary set with answer-bearing spans/turns and supported state transitions. Distinguish supported buyer acceptance, proposal, negation, unrelated entities, and later updates. Do not substitute an uncalibrated LLM judge for a stated ground-truth protocol. Report retrieval and packing failures separately before comparing models.

## 3. Six excerpts impose a source-coverage ceiling

Default `max_excerpts=6` and [evidence.py:107](</Users/kacperwarych/Desktop/hackathon reactive ai/src/decision_memory/evidence.py:107>) permit at most six distinct evidence sessions. Independently counted active `gold-salesgen.jsonl`: 59 questions, 13 with more than six distinct gold evidence sessions, maximum 43. Consequently all-gold-source retention is structurally impossible for those 13 with that cap. This is not a 13/59 answer-error rate: annotated sources can be nonminimal, and explicitly recorded totals can suffice.

Test an aggregate route that first distinguishes explicit recorded totals from requests needing complete enumeration. Any enumeration must establish its source population and identity handling; top-k retrieval does not establish completeness. Preserve existing coverage warnings and abstention behavior while this is unvalidated. A larger excerpt count alone is not a demonstrated solution under a fixed message budget.

## Independent checks and critique exchange

- Read active source and verified it matches the staged source excluding bytecode.
- Reexecuted the researcher probe against active code; all reported outputs reproduced.
- Reexecuted with the cached production Qwen tokenizer; the headline answer-loss counterexample reproduced.
- Independently counted distinct gold sessions: 13/59 over six, max 43.
- Ran active `tests/test_long_memory.py` and `tests/test_decision.py` with `PYTHONDONTWRITEBYTECODE=1`, a temporary data directory, offline flags, and `-p no:cacheprovider`: **20 passed in 0.15 s**. These passing regressions do not cover or refute the new counterexample.

Overseer critique: restrict headline recommendations to the three above; do not extrapolate the `excerpt_tokens=60` head-truncation probe to the default 320-token configuration; do not call the source-coverage ceiling an answer-error rate; preserve official session scoring. Researcher response: accepted all points, explicitly excluded the small-budget case from default findings, kept update-gate and display-validator probes as deferred raw diagnostics, and revised the report accordingly. The researcher also incorporated the independent real-tokenizer verification.

## Reproduction and limits

Run the research probe with the existing active project's `.venv/bin/python`, `PYTHONPATH` set to its `src`, `MEMORY_PROJECT_DIR` set to the active project, and offline/bytecode-disabled flags. The probe creates its own temporary SQLite store. It writes only its report beside the script. The cached-tokenizer verification replaces the probe's `Tokenizer` factory with `AutoTokenizer.from_pretrained` on the local embedding snapshot using `local_files_only=True`; all other probe logic remains unchanged.

No end-to-end Reactor answer measurement, neural-model comparison, natural-data span benchmark, or measured remedy gain was produced. Ingestion/chunking and hybrid/reranking were inspected but not changed; the current highest-confidence causal failure is downstream of retrieval. Model superiority is unestablished. Future experiments are recorded in [backlog.md](../backlog.md).
