# Extraction-pipeline research — 2026-10-31

Researcher runtime: **gpt-6.1-sol, high reasoning**. Independent review: `/root/overseer`. Scope: recommendations only; no production edits, model downloads, model-weight inference, paid API calls, or production database writes.

## Decision

Prioritize evidence selection and its evaluation before changing embedding or reranking models. Three recommendations follow, grounded in executable counterexamples and local gold-label counts. They establish possible failure mechanisms, not their prevalence or downstream answer-error rates.

The active project is `/Users/kacperwarych/Desktop/hackathon reactive ai`. Its `src/decision_memory` sources are identical to `outputs/report-entry-implementation/src/decision_memory` in this workspace, excluding bytecode caches (`diff -qr` returned no differences). No applicable AGENTS.md was found. The probes imported the active source and used its installed Python interpreter. Source-file SHA256 fingerprints are recorded in `probe-results.json`.

## 1. Preserve semantically relevant units after chunk retrieval

**Measured mechanism.** A retrieved 405-word user message contains `I became a lighthouse keeper.` after 400 filler words. For `What is my current occupation?`, the memory extractor emits three units, but `extract_options` generates only the first two. Neither packed excerpt contains the answer. Yet the answer was present in the upstream retrieved chunk. The overseer independently reproduced this result using the actual cached Qwen tokenizer, revision `97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3`, without loading model weights or using the network; see `overseer-real-tokenizer-results.json`.

**Cause and code.** [memory.py:54](/Users/kacperwarych/Desktop/hackathon%20reactive%20ai/src/decision_memory/memory.py:54) splits long turns into units of up to 200 tokenizer tokens. [evidence.py:51](/Users/kacperwarych/Desktop/hackathon%20reactive%20ai/src/decision_memory/evidence.py:51) finds units overlapping the retrieved chunk, sorts by exact keyword overlap, breaks ties by earlier offset, and retains only `eligible[:2]` at line 54. Thus a semantic retriever or reranker can recover the correct chunk while a later lexical selector removes its relevant assertion. Default chunk target is 450 tokens ([config.py:32](/Users/kacperwarych/Desktop/hackathon%20reactive%20ai/src/decision_memory/config.py:32)), so a chunk can overlap more than two memory units.

**Recommendation.** Experiment with query–unit relevance selection or a bounded candidate-per-unit scoring pass, retaining the original source offsets and the existing final evidence budget. Compare against a cheap baseline that allows more than two unit options before final selection. Keep all other retrieval and packing settings fixed. Merely increasing the final token budget cannot recover a unit never proposed as an option.

**Limit.** The researcher's base probe uses a whitespace tokenizer and a deliberately constructed lexical tie; the overseer's independent verification uses the real tokenizer. Both isolate control flow; neither measures neural retrieval quality or production prevalence. The separate `excerpt_tokens=60` probe clips a short target reply after prior context; this is a configuration-specific observation and does **not** demonstrate truncation at the default 320-token cap. No default-cap truncation defect is claimed.

**Next experiment.** Hand-label 20–30 held-out retrieved chunks with paraphrased answers, late assertions, and short contextual replies. Compare target-assertion retention under current first-two selection, expanded option generation, and query–unit scoring at identical 2,000-token/six-excerpt budgets. Measure additional scoring work and retention before calling Reactor.

## 2. Route broad counts through coverage-aware aggregation

**Measured structural limit.** Local `gold-salesgen.jsonl` contains 59 questions; 13 have more than six labeled evidence sessions, with a maximum of 43. Dev and dev-large each contain 526 questions and require at most six labeled sessions. These counts are reproduced by `probe.py` and include source hashes.

**Cause and code.** Default `max_excerpts=6` is [config.py:40](/Users/kacperwarych/Desktop/hackathon%20reactive%20ai/src/decision_memory/config.py:40). The selection loop stops at that cap ([evidence.py:107](/Users/kacperwarych/Desktop/hackathon%20reactive%20ai/src/decision_memory/evidence.py:107)); rendering groups selected excerpts by session at lines 97–104. Therefore at most six distinct source sessions can enter the final evidence bundle, and full labeled-session coverage is impossible for those 13 sales questions under this route. This remains true even if the token budget increases. Existing `coverage_warning` and count-question instructions already acknowledge incomplete coverage ([retrieval.py:66](/Users/kacperwarych/Desktop/hackathon%20reactive%20ai/src/decision_memory/retrieval.py:66), [retrieval.py:231](/Users/kacperwarych/Desktop/hackathon%20reactive%20ai/src/decision_memory/retrieval.py:231)).

**Recommendation.** Test a separate bounded aggregation workflow: enumerate the eligible population using the same history/time scope, extract evidence-linked per-entity records, deduplicate explicitly, compute totals, and supply Reactor with the computed result plus its coverage accounting. Use ordinary top-k retrieval when an explicit recorded total answers the question. If population coverage is unknown, expose that uncertainty rather than deriving a complete count from a selected subset.

**Limit.** **13/59 is a source-coverage ceiling, not a measured 22% answer-error rate.** Gold evidence sets may be nonminimal, and an explicit recorded total can support an answer without reproducing every gold session. The report does not establish whether the 13 questions have such totals or whether source grouping already identifies the correct population. A complete sweep is a proposed experiment, not implemented behavior.

**Next experiment.** Audit the 13 cases for (a) explicit sufficient totals, (b) truly exhaustive enumeration requirements, and (c) ambiguous or nonminimal gold. On category (b), compare current retrieval with a full eligible-population pass on exact count accuracy, duplicate handling, support provenance, wall time, and Reactor input size. This audit can precede any paid answer-generation run.

## 3. Add assertion-level diagnostics beside official session metrics

**Measured blind spot.** `evidence_metrics` returns `packed_recall=1.0`, `packed_all_required=true`, and `packed_precision=1.0` when the packed passage is unrelated weather text but has the gold session ID. It also reports full packed recall for recommendation 1's bundle after the relevant assertion was lost.

**Cause and code.** [evaluation.py:98](/Users/kacperwarych/Desktop/hackathon%20reactive%20ai/src/decision_memory/evaluation.py:98) compares sets of candidate and packed session IDs. This correctly implements a session-level metric; it cannot test whether a selected excerpt preserves the supporting assertion. The local challenge specification explicitly requires session evidence and says turn-level evidence is not scored ([format.md:36](/Users/kacperwarych/Downloads/memory-challenge-main/format.md:36)); citation scoring is also session-level at line 49. **Keep the official metric unchanged.**

**Recommendation.** Add a separate small, human-audited assertion/span diagnostic set and report retention at four boundaries: retrieved chunk, proposed unit options, packed excerpts, and final supported state/answer. Include original concern plus later confirmation, intention versus completed action, negation, source speaker, and same-entity linkage. Reuse `selected_excerpts` offsets and turn IDs already emitted at [retrieval.py:234](/Users/kacperwarych/Desktop/hackathon%20reactive%20ai/src/decision_memory/retrieval.py:234). Do not derive span truth solely from known-incomplete turn flags.

**Limit.** No new gold span dataset or supported-state accuracy measurement exists in this cycle. The display validator's own docstring explicitly disclaims automatic semantic verification ([decision.py:1](/Users/kacperwarych/Desktop/hackathon%20reactive%20ai/src/decision_memory/decision.py:1)); additional exploratory quote-validation probes are recorded as assurance limits, not violations of a promised semantic verifier.

**Next experiment.** Re-label 20–30 existing answerable examples across multi-session, temporal, and knowledge-update categories. Report both the official session metrics and manually audited assertion retention. Use these diagnostics to attribute losses to retrieval, packing, or reading before comparing model families.

## Reproduction and validation

From this workspace:

```sh
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH='/Users/kacperwarych/Desktop/hackathon reactive ai/src' \
'/Users/kacperwarych/Desktop/hackathon reactive ai/.venv/bin/python' \
outputs/pipeline-research/2026-10-31/probe.py
```

The probe writes only its result JSON in this research directory and temporary SQLite files. It reads gold JSONL files for counts and imports active source. It does not open the production database. `probe-results.json` records deterministic results and source hashes. Earlier historical retrieval reports have config fingerprint `22f65eba...`; current default fingerprint was `2ed66ae5...`. Historical numbers therefore are not presented as fresh compact-packing benchmarks.

Independent overseer verification: `test_long_memory.py` and `test_decision.py` passed, 20 tests in 0.15 seconds. Existing regression coverage and these counterexamples address different cases; passing tests do not establish assertion retention.

## Primary-source context

[LongMemEval, ICLR 2025](https://arxiv.org/abs/2410.10813) separates indexing, retrieval, and reading, and studies session decomposition, key expansion, and time-aware query expansion. It supports testing stage attribution; it does not establish that any proposed change improves this pipeline. [Qwen3-Embedding-0.6B's official model card](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B) documents instruction-aware retrieval use; its model-family benchmarks do not measure this packer's assertion retention. No model superiority claim is made here.

## Overseer critique and explicit revision

The draft included five possible avenues. The overseer asked for three reproducible priorities and challenged overgeneralizing the small-cap truncation probe, treating the 13/59 count as an error rate, and replacing official session scoring. **Accepted:** the final report contains exactly the three recommendations above; truncation is explicitly limited to the 60-token configuration; the sales count is only a structural labeled-source ceiling; and assertion evaluation is auxiliary to the correct official metric. Update-gate and quote-validator observations remain exploratory raw results rather than headline recommendations.

Unresolved: prevalence of unit loss on real conversations, sufficient-total availability in aggregate cases, accurate population/entity linking, compact-packing answer quality, and model-stage latency under a controlled cold/warm-cache protocol. The highest-value immediate follow-up is the small hand-labeled retention audit in recommendation 1, reused for recommendation 3.
