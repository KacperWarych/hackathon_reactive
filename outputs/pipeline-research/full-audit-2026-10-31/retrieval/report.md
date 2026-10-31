# Retrieval, evidence, decision, and investigation audit — 2026-10-31

Scope: every function in active `retrieval.py`, `evidence.py`, `investigations.py`, and `decision.py`, plus their index/memory/source interfaces and applicable tests. This report records mechanisms and limits, not natural-data prevalence, measured answer-error rates, or demonstrated remedy superiority. Application files, model weights, remote APIs, and the production database were not modified. No applicable `AGENTS.md` was found in inspected project/workspace ancestor paths. Prior researcher/overseer reports and backlog were read.

Active source root: `/Users/kacperwarych/Desktop/hackathon reactive ai/src/decision_memory`. File hashes are saved in [probe-results.json](probe-results.json). The probe uses temporary SQLite stores, deterministic test models, and the existing cached Qwen tokenizer revision `97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3`, loaded with `local_files_only=True`. No model weights load. `[source.py:N]` below always means the absolute active-source path explicitly linked at that finding.

The highest-priority fixes to test are target-preserving context construction (RET-01), temporal/source-sensitive deduplication (RET-03/04), structured speaker provenance (RET-06), and immutable source-snapshot retrieval (RET-17). Existing tests pass while the new counterexamples reproduce.

## Findings index

| ID | Severity | Classification | Finding |
|---|---|---|---|
| RET-01 | High | Confirmed bug, real tokenizer | Prior-turn context jumps over a long current turn and clips the selected late answer at the default 320-token cap |
| RET-02 | High | Confirmed design limit, known | Two lexical unit options can discard an answer already inside the retrieved chunk |
| RET-03 | High | Confirmed bug | Text deduplication across dates deletes the latest occurrence and its date |
| RET-04 | Medium | Confirmed loss mechanism, real tokenizer | Overlap deduplication discards a short final chunk containing a unique fact |
| RET-05 | Medium | Confirmed design limit, known | Six excerpts cannot fully represent more than six supporting source sessions |
| RET-06 | High | Confirmed provenance bug | Newline role labels inside assistant content are parsed as actual user statements |
| RET-07 | Medium | Confirmed validation language limitation | Explicit Polish confirmations and ordinary English “accept” can be rejected |
| RET-08 | Medium | Explicit assurance limit | Exact quote occurrence and a confirmation word do not establish resolution semantics |
| RET-09 | Low | Explicit heuristic limit | Update-search gate checks lexical coverage and any user update, without same-fact linkage |
| RET-10 | Low | Library/scoring design limitation | Scoped BM25 can have negative IDF and prefer fewer occurrences of an ubiquitous query term |
| RET-11 | Medium | Confirmed audit-metadata bug | Investigation trace counts sources as excerpts and retains removed excerpt IDs/offsets |
| RET-12 | Medium | Confirmed provenance-metadata inconsistency | Decision-only snapshot reuse stamps a new source revision onto old saved evidence |
| RET-13 | Low | Service API limitation; UI mitigates | `recover=True` does not replay failed prompt/date by itself |
| RET-14 | Medium | Confirmed bounded-admission limitation | Expansion budget can admit only old initial candidates while excluding every newly discovered candidate |
| RET-15 | Low | Confirmed timing semantics | Search timing includes query-embedding timing; fields are not exclusive stage durations |
| RET-16 | Medium at scale | Structural performance opportunity | One retrieved chunk still processes every turn in its source session |
| RET-17 | High | Confirmed interleaving bug | Retrieval can rank one source revision and pack another under the original trace revision |

Severity reflects consequence if triggered and project fit, not measured frequency. “High” does not imply every question is affected. No semantic answer was generated in these probes.

## RET-01 — Selected late unit disappears at the default excerpt cap

**Code:** [evidence.py:58](</Users/kacperwarych/Desktop/hackathon reactive ai/src/decision_memory/evidence.py:58>), [evidence.py:61](</Users/kacperwarych/Desktop/hackathon reactive ai/src/decision_memory/evidence.py:61>), [evidence.py:70](</Users/kacperwarych/Desktop/hackathon reactive ai/src/decision_memory/evidence.py:70>).

The selected unit is the short final unit of a 400-word weather monologue followed by “The camera is approved.” It wins lexical matching for “Is the camera approved?” A short assistant message precedes that long user turn. Because the final unit is short, the preceding-turn rule moves `lo` to the assistant turn. Slicing `full[lo:hi]` then includes all 400 earlier words of the *current* turn, not only the selected unit plus bounded prior context. Head truncation at 320 tokens removes the selected camera assertion. The other proposed option does not recover it.

Both whitespace and real Qwen probes report three user units, a selected tail of 4/5 tokens, no target in any default option, target retained with `context_tokens=0`, and target retained with `excerpt_tokens=1000`. The real-tokenizer untruncated first option is 416 tokens. This is a new default-configuration counterexample; the earlier research only proved truncation at a nondefault 60-token cap. The whole source fits a default chunk, so the probe does not depend on an oversized source chunk.

**Fix:** assemble explicitly separated prior-context and selected-unit segments, rather than one contiguous slice across omitted units; allocate mandatory space to the selected unit first, and trim optional context around it. Preserve roles and discontiguous offsets. Do not fix solely by increasing the cap.

**Regression:** late short third unit after a 400-token turn prefix, preceded by a different speaker; assert target retained under default caps, context bounded, offsets/roles correct. Repeat with real tokenizer and both with/without a short following turn.

## RET-02 — Top-two lexical options lose semantic answers

**Code:** [evidence.py:51](</Users/kacperwarych/Desktop/hackathon reactive ai/src/decision_memory/evidence.py:51>).

The eligible units of a correctly retrieved chunk are sorted by exact question-keyword overlap, then earlier offset, and only `eligible[:2]` survives. For “What is my current occupation?”, 400 weather words followed by “I became a lighthouse keeper” yield three units and two answer-free options in both tokenizers. This repeats the prior known finding and distinguishes it from RET-01: here the answer unit is never proposed; there it is proposed then clipped.

**Fix/test:** compare bounded broader unit admission and optional query–unit scoring with current selection on fixed retrieved chunks and fixed final evidence budgets. Add a paraphrase/tie regression with the answer in unit three. Measure assertion retention and added scoring work before claiming quality improvement.

## RET-03 — Repeated wording loses the newest date

**Code:** [evidence.py:89](</Users/kacperwarych/Desktop/hackathon reactive ai/src/decision_memory/evidence.py:89>), [evidence.py:108](</Users/kacperwarych/Desktop/hackathon reactive ai/src/decision_memory/evidence.py:108>).

For two distinct sessions on May 1 and May 25, each saying “I purchased the camera,” the real `Retriever(...).retrieve(..., 'rerank')` with deterministic test models returns both candidates but packs only May 1 for “When was my latest camera purchase?” Identical text is discarded across sessions unless the question matches the aggregation regex. The later-update utility cannot rescue a candidate once `redundant()` rejects its text. Source dates represent distinct events and are the requested answer here.

**Fix:** preserve event/source/date identity during deduplication, particularly for temporal/event queries; if identical support is intentionally collapsed, retain all dates/source IDs and choose the appropriate latest occurrence. Do not blindly retain only the first text.

**Regression:** identical event wording across two dates, original candidate order older first, temporal query; require latest date/source retained. Include non-temporal factual repeats and count queries to check budget tradeoffs.

## RET-04 — Short final chunk loses unique novel tail under overlap deduplication

**Code:** [retrieval.py:34](</Users/kacperwarych/Desktop/hackathon reactive ai/src/decision_memory/retrieval.py:34>), called before reranking at [retrieval.py:163](</Users/kacperwarych/Desktop/hackathon reactive ai/src/decision_memory/retrieval.py:163>).

Using default chunk settings, a first user turn with 448 weather words followed by a short second user turn “camera is approved” makes two Qwen chunks of 451 and 91 tokens. The first ends at the first-turn boundary; the short final chunk contains 80 overlapping tokens and the unique assertion. `distinct([0, 1], rows)` keeps only the first because overlap exceeds 65% of the smaller interval. The only chunk containing “camera is approved” is deleted. The whitespace case also reproduces (449/86 tokens).

This fixes the candidate input order to isolate deduplication; it does not show how often a learned retriever orders the chunks this way, nor claim that every overlap removal loses information. The first attempted one-turn fixture did **not** reproduce because boundary snapping kept the full source in one chunk; it was rejected and replaced by the two-turn fixture.

**Fix:** remove only fully covered or content-equivalent intervals; otherwise merge provenance-aware spans or retain novel tails. If relevance must choose between partially overlapping chunks, compare after reranking and track unique supporting spans.

**Regression:** default-generated two-turn boundary fixture; verify the unique final assertion remains after deduplication for both candidate orders, plus true-contained duplicate and cross-session cases.

## RET-05 — Six excerpts limit exhaustive multi-source aggregation

**Code:** [evidence.py:107](</Users/kacperwarych/Desktop/hackathon reactive ai/src/decision_memory/evidence.py:107>), [retrieval.py:66](</Users/kacperwarych/Desktop/hackathon reactive ai/src/decision_memory/retrieval.py:66>).

Seven short distinct support sources yield six packed sessions under default caps. Prior independently reviewed local counts found 13/59 salesgen gold sets above six sessions (maximum 43); this is a source-coverage ceiling, not a measured answer-error rate, because gold can be nonminimal or a recorded total can suffice. Current coverage warning and answer instructions acknowledge the problem and should be retained.

**Fix/test:** route genuine complete-population questions through evidence-linked enumeration/aggregation with explicit scope, entity deduplication, and coverage accounting; first separate cases answered by sufficient explicit totals. Compare exact counts and provenance, without claiming that increasing `max_excerpts` alone solves completeness.

## RET-06 — Assistant prose can spoof user provenance

**Code:** [decision.py:60](</Users/kacperwarych/Desktop/hackathon reactive ai/src/decision_memory/decision.py:60>); the same role-regex parsing exists in [evidence.py:143](</Users/kacperwarych/Desktop/hackathon reactive ai/src/decision_memory/evidence.py:143>).

An actual structured source with **one assistant turn and zero user turns** contains `Suggested wording:\nuser: Integration is resolved.` It passes through the real `extract_options`, producing a role-labeled excerpt. `validate_decision` accepts “Integration is resolved” as the required user confirmation quote because it reparses the embedded newline `user:` as an authentic role boundary. Assistant transcripts, quoted examples, or adversarial content can therefore satisfy the validator's traceability gate. Expansion planning can also mistake the same text for a buyer update.

This is a provenance parsing bug, distinct from the explicitly disclaimed semantic guarantee in RET-08. The validator promises matching user text; there is no user text in this fixture.

**Fix:** retain structured turn roles and exact source offset maps through rendering; validate quotes against original cited user-turn spans, never raw role-like strings. Escape or fence content when rendering, while preserving exact quoted source text via offsets. Reuse structured roles in expansion planning.

**Regression:** assistant-only source containing line-start `user:` and `user (continued):`; reject user confirmation, and do not satisfy update-search gate. Also test a user quote containing `assistant:` and an actual user confirmation after a real assistant turn.

## RET-07 — Confirmation whitelist excludes supported language/forms

**Code:** [decision.py:64](</Users/kacperwarych/Desktop/hackathon reactive ai/src/decision_memory/decision.py:64>), [decision.py:67](</Users/kacperwarych/Desktop/hackathon reactive ai/src/decision_memory/decision.py:67>).

Exact genuine user quotes “Potwierdzam, integracja została zatwierdzona.” and “We accept your proposal.” both fail the explicit-confirmation regex; “The integration was approved.” passes. The memory cues and temporal query support already include Polish, so the decision view has inconsistent language support. This is a bounded lexical validation limitation, not a claim that semantic resolution should automatically be inferred for arbitrary text. It can force repeated repair or leave a revision incomplete despite a faithful quote.

**Fix/test:** define supported-language/form policy explicitly and align confirmation detection with it. Accept supported morphological forms (`accept` versus `accepted`) with negation/hypothetical tests. Use human-labeled positive and negative Polish/English quote sets; do not blindly copy cue regexes as semantic proof.

## RET-08 — Quote matching is not semantic verification

**Code:** [decision.py:1](</Users/kacperwarych/Desktop/hackathon reactive ai/src/decision_memory/decision.py:1>), [decision.py:62](</Users/kacperwarych/Desktop/hackathon reactive ai/src/decision_memory/decision.py:62>).

“integration works” is accepted when excerpted from “It is not true that integration works.” Likewise, “Lunch has been paid” can support a structurally valid entry whose claimed resolution is “Integration resolved.” The quote may omit the surrounding negation or concern linkage. This repeats deferred prior diagnostics and is an **explicit assurance limit**, not a violation of a promised semantic verifier. `decision.py` and `INVESTIGATIONS.md` state the limitation.

**Recommendation/test:** preserve the existing honest disclaimer; optionally expose structured concern/confirmation links, full-sentence quote boundaries, original speaker, entity, modality, and chronology for human inspection or an independently evaluated semantic check. Build span-level tests for negation outside quoted substrings, unrelated facts, missing earlier concerns, and genuine linked resolution; keep official session scoring unchanged.

## RET-09 — Update-search hints do not verify same-fact coverage

**Code:** [evidence.py:130](</Users/kacperwarych/Desktop/hackathon reactive ai/src/decision_memory/evidence.py:130>).

The gate returns no expansion reason when the source set has a camera-integration approval “for our office printer” on one date and the current camera-integration security blocker on another. It unions query terms over chunks and checks that at least one relevant user block has update/confirmation cues; those checks do not link the update to the questioned fact or require a later completion for that blocker. The probe already contains the current blocker, so it does **not** prove a wrong answer or that expansion was needed. The function docstring correctly calls this a conservative hint rather than an answerability check.

**Recommendation/test:** retain that characterization. If expansion should depend on unresolved fact coverage, use linked entity/fact/time diagnostics evaluated on labeled missing-update cases. Measure extra-search rate and retrieval gains; do not turn the current cue gate into a sufficiency certificate.

## RET-10 — Negative BM25 IDF in small scoped corpora

**Code:** [retrieval.py:114](</Users/kacperwarych/Desktop/hackathon reactive ai/src/decision_memory/retrieval.py:114>), [retrieval.py:145](</Users/kacperwarych/Desktop/hackathon reactive ai/src/decision_memory/retrieval.py:145>).

`BM25Okapi([terms('camera camera camera camera camera'), terms('camera lens')])` assigns `camera` IDF `-0.2011797`; query scores are approximately `-0.3602` and `-0.2492`, so the document with one occurrence ranks above the document with five. The package's epsilon floor is relative to an average IDF that can itself be negative. This is library/scoring behavior, not an application or library correctness bug, and repeated terms do not guarantee actual semantic relevance. It warrants awareness because the lexical corpus is a single time-filtered history, which may be small.

**Recommendation/test:** record zero/negative IDF and tie rates on scoped histories; compare a nonnegative-IDF formulation or alternative lexical baseline using frozen relevance labels, especially small and ubiquitous-topic corpora. No superiority claim is established by this two-document probe.

## RET-11 — Trace no longer matches sent excerpts

**Code:** [investigations.py:234](</Users/kacperwarych/Desktop/hackathon reactive ai/src/decision_memory/investigations.py:234>), [investigations.py:242](</Users/kacperwarych/Desktop/hackathon reactive ai/src/decision_memory/investigations.py:242>), [retrieval.py:234](</Users/kacperwarych/Desktop/hackathon reactive ai/src/decision_memory/retrieval.py:234>).

`evidence` is grouped by session, but investigation postprocessing sets `excerpt_count=len(evidence)`. At default budgets, a real retrieval of two selected excerpts from one session changes from count 2 to count 1 despite removing no evidence; `selected_excerpts` still has two entries. In a separate 6,000-character configuration probe, investigation budgeting removes two of six source groups, yet trace `selected_excerpts` retains IDs/offsets from all six. The code moves `evidence_tokens` to `retrieved_evidence_tokens` on pruning, but does not similarly preserve/recompute selected excerpts. This can mislead assertion diagnostics and inspection of what was sent.

**Fix:** distinguish selected excerpt count from rendered source count; maintain `retrieved_selected_excerpts` separately and recompute actual sent excerpt IDs/offsets/counts/tokens after budgeting. Budget/prune at an explicit excerpt representation before rendering sources.

**Regression:** one session with two nonoverlapping selected excerpts and no pruning; multiple sessions with budget pruning; assert every sent offset belongs to sent source text and counts use their stated units.

## RET-12 — Saved snapshot gets contradictory source revision metadata

**Code:** [investigations.py:196](</Users/kacperwarych/Desktop/hackathon reactive ai/src/decision_memory/investigations.py:196>), [investigations.py:198](</Users/kacperwarych/Desktop/hackathon reactive ai/src/decision_memory/investigations.py:198>), [investigations.py:203](</Users/kacperwarych/Desktop/hackathon reactive ai/src/decision_memory/investigations.py:203>).

After a source is edited at the same session ID/date, decision-only mode intentionally reuses the saved evidence. That behavior is explicitly documented and is **not itself a stale-retrieval bug**. However, `_revise` calculates a fresh `question.history_revision` from the edited corpus, copies the parent's old retrieval/trace/evidence, then replaces its question with the fresh metadata. The probe confirms saved old text retained, question fingerprint changed, and trace history revision unchanged. Old trace and new question fingerprints already use different constructions during normal operation; the specific defect here is stamping the new corpus identity onto intentionally old content, not merely comparing unlike hash strings.

**Fix:** preserve the snapshot's corpus revision/content hashes for decision-only builds and record current-source revision separately, optionally with a source-changed indicator. Do not silently force fresh retrieval for a documented saved-snapshot operation. Bind evidence to immutable content hashes and source offsets, not only IDs/dates.

**Regression:** edit a same-ID/date source, build saved decision view, require old snapshot revision plus an explicit current revision/staleness field; ordinary revise should use fresh evidence and its revision consistently.

## RET-13 — Recovery API relies on caller replay

**Code:** [investigations.py:157](</Users/kacperwarych/Desktop/hackathon reactive ai/src/decision_memory/investigations.py:157>), [investigations.py:161](</Users/kacperwarych/Desktop/hackathon reactive ai/src/decision_memory/investigations.py:161>), mitigation [investigation_ui.py:130](</Users/kacperwarych/Desktop/hackathon reactive ai/src/decision_memory/investigation_ui.py:130>).

After a failed attempt with a supplier-focused follow-up and June 2 time boundary, `service.revise(last_success, recover=True)` recovers using the parent's original query and June 1 date; it does not reuse the failed prompt/date. It only restores the failed `decision_only` flag. The current UI mitigates this by prepopulating failed prompt/date and resubmitting them. Consequently this is a service API usability limitation, **not a confirmed current UI recovery bug**.

**Recommendation/test:** either document caller responsibility explicitly, or use a dedicated retry-attempt operation that defaults to the failed request's prompt/date and accepts intentional edits separately. Regression should cover API-only retry plus UI-supplied overrides and failed decision-only mode.

## RET-14 — Newly found expansion evidence can receive zero admission slots

**Code:** [retrieval.py:190](</Users/kacperwarych/Desktop/hackathon reactive ai/src/decision_memory/retrieval.py:190>), [retrieval.py:198](</Users/kacperwarych/Desktop/hackathon reactive ai/src/decision_memory/retrieval.py:198>).

A deterministic search-ranking fixture with default `retrieve_k=40`, `rerank_k=40`, and `expansion_k=12` creates 80 initial hybrid candidates. Expansion search finds 20 additional candidates. Merging the preserved initial reranked 40 with the fused union and taking the first 52 admits only old initial candidates; none of the 20 expansion-only candidates reaches final reranking/packing. Branch corroboration and fusion order consume the added 12 slots. Identical test documents mean cache reuse produces only 40 actual reranker document calls; the relevant observation is candidate admission, not 52 inference calls.

This is a confirmed bounded-admission limitation, not a claim that expansion is always useless or that RRF is broken. Favoring corroborated initial evidence can improve precision. The “genuinely new update-search candidates” comment does not describe expansion-only provenance: the admitted documents can be merely previously unreranked initial candidates.

**Experiment:** compare explicit initial-unreranked versus expansion-only queues, possibly reserving a small expansion-only quota while retaining initial support. Measure missing-update recall and precision on frozen candidate labels with the same total reranking budget; a quota has a real precision tradeoff.

**Regression:** the fixed 80-initial/20-new fixture should make branch provenance visible and enforce the selected admission policy, rather than assuming every new candidate must fit.

## RET-15 — Stage times overlap

**Code:** [retrieval.py:128](</Users/kacperwarych/Desktop/hackathon reactive ai/src/decision_memory/retrieval.py:128>), [retrieval.py:139](</Users/kacperwarych/Desktop/hackathon reactive ai/src/decision_memory/retrieval.py:139>), [retrieval.py:158](</Users/kacperwarych/Desktop/hackathon reactive ai/src/decision_memory/retrieval.py:158>).

`search_seconds` wraps `query_vector`, which also accumulates `query_embedding_seconds`. An intentionally delayed fake embed confirms the same ~40 ms is present in both values. This establishes nested timing semantics; no inspected consumer was shown to sum them, so it is not evidence that a reported end-to-end duration is wrong. Total `seconds` is wall time and remains separate.

**Recommendation/test:** rename inclusive search time or collect exclusive lexical/dense-search and query-embedding fields. Test with controlled fake model delay; document inclusion/exclusion and avoid summing nested fields. The delay is a probe mechanism, not production latency measurement.

## RET-16 — Session-wide work remains after narrow retrieval

**Code:** [evidence.py:37](</Users/kacperwarych/Desktop/hackathon reactive ai/src/decision_memory/evidence.py:37>), [evidence.py:39](</Users/kacperwarych/Desktop/hackathon reactive ai/src/decision_memory/evidence.py:39>), [evidence.py:51](</Users/kacperwarych/Desktop/hackathon reactive ai/src/decision_memory/evidence.py:51>); [retrieval.py:208](</Users/kacperwarych/Desktop/hackathon reactive ai/src/decision_memory/retrieval.py:208>).

For one retrieved chunk covering one eligible turn in a 1,000-turn source, the real option builder calls `memory.records` 1,000 times, rebuilds the complete rendering/spans/units, then filters for the chunk. Original-turn JSON is fetched for every retrieved session in full. Cache hits avoid retokenizing persisted units, but do not remove session-wide JSON loading/rendering/record lookups. This is proven work amplification; no real latency, memory bottleneck, or speedup was measured.

**Experiment/fix:** persist immutable session rendering plus turn/unit offsets keyed by content hash/tokenizer scheme, retrieve intersecting units via indexed spans, and expand only bounded adjacent context. Benchmark real long sessions with cold/warm caches and unchanged evidence before adopting the added index complexity.

**Regression:** instrument records/turn materialization counts for a narrow chunk in a large session; keep correctness tests for offset, role, and context equivalence. Report runtime only after measured experiments.

## RET-17 — Mixed source revisions within one retrieval

**Code:** [retrieval.py:105](</Users/kacperwarych/Desktop/hackathon reactive ai/src/decision_memory/retrieval.py:105>), [retrieval.py:112](</Users/kacperwarych/Desktop/hackathon reactive ai/src/decision_memory/retrieval.py:112>), [retrieval.py:208](</Users/kacperwarych/Desktop/hackathon reactive ai/src/decision_memory/retrieval.py:208>).

Metadata/candidate chunks are read before search/reranking. Original turns are fetched later by session ID, without binding their `content_hash` to the retrieved chunk's immutable content hash. A deterministic interleaving probe edits the same session during a fake reranker call from “The camera lens is approved” to “Radio purchase was rejected,” at the same date. Retrieval succeeds and packs the new radio text under candidate chunk IDs and history revision computed from the old camera source. The edited source was never reindexed. This simulates a source edit during model work; it uses no concurrent remote calls and no production writes.

The mechanism can occur with another ingestion/entry writer because investigation/agent locks do not establish a shared source snapshot. The single-connection callback proves the missing revision binding, not observed real-world race frequency. If an external caller already enforces source immutability for the entire operation, that caller avoids the condition; `Retriever` itself does not enforce it.

**Fix:** pack from the immutable `contents` row associated with each retrieved chunk's content hash; snapshot eligible session metadata and bind IDs/dates/hashes at operation start. Alternatively detect source-revision change before return and retry/abort boundedly, without returning mixed provenance. Apply consistent snapshot semantics to investigation eligible-source fingerprints as well.

**Regression:** mutate same-ID/date source during search/rerank, and remove/move a session at the same boundary; require either complete old snapshot, complete reindexed fresh snapshot, or a clear retryable source-change error. Never combine old chunk offsets/revision with newly fetched content.

## Coverage and successful checks

| Module/function(s) | Inspection/test coverage and result |
|---|---|
| retrieval `terms`, `fuse` | Identifier punctuation/components and reciprocal-rank tie handling read; existing identifier/fusion tests pass; RET-10 explores scoped lexical behavior |
| retrieval `distinct` | Every overlap/session branch read; same-session unique-tail loss RET-04; cross-session preservation existing test passes |
| retrieval `expand`, `reactor_question` | All seed/suffix/fallback and coverage/instruction branches read; heuristic limits RET-09/14; count-prompt tests pass |
| retrieval `message_size`, `pack` | Complete-message budget path, errors, detail forwarding read; existing budget tests and RET-01/02 pass/reproduce |
| `Retriever.__init__`, `retrieve` including nested helpers | Mode validation, scope/date SQL, source revision cache key, BM25/dense/fusion, rerank caches, expansion admission, original fetch, trace fields read; existing scope/cache/invalidation/empty-history tests pass; RET-03/14/15/17 probe boundaries |
| evidence `keywords`, `extract_options` | STOP/Unicode/code tokens, source rendering, spans/units, lexical ties, context and token clipping, cue/turn metadata read; RET-01/02/06/16 |
| evidence `select_options` and nested `redundant`, `render`, `utility` | Token/character/message/excerpt budgets, grouping, temporal bonus, exact/overlap dedup read; RET-03/05/11 |
| evidence `expansion_reason` | No candidates, missing keywords, temporal/date/update checks, user-block regex read; existing Polish/assistant-proposal tests pass; RET-06/09 |
| investigation `investigation_id`, `revision_report`, `previous_analysis`, nested `excerpt` | Path validation, deep copies, future-report guard, generated-context warning and truncation read; existing identity/revision/backward-date/switching tests pass |
| `InvestigationError`, `Investigations.__init__`, `_path`, `_lock`, `_read`, `document` | Journal adoption/atomic writes, nonblocking locks, persisted seed read; existing no-call adoption/two-writer tests pass |
| `Investigations.revise`, `_revise` and nested `size`, `transmit`, `answer` | Entire revision/preflight/source checks/reset/context/budget/journal/request/repair/publish/failure flow read; 21 investigation tests pass; RET-11/12/13/17 probe provenance/diagnostics boundaries |
| decision `decision_prompt`, `validate_decision`, repair constant | Full schema/labels/quote/negation/confirmation parser read; existing schema/speaker/quote tests pass; RET-06/07/08 |

Executed active `test_retrieval.py`, `test_long_memory.py`, `test_decision.py`, and `test_investigations.py`: **55 passed in 0.49 s**, with bytecode disabled, offline flags, temporary test data and `-p no:cacheprovider`. These tests verify protections such as history/time scoping, changed-source invalidation between calls, cache specificity, bounded expansion/reranking work, strict schema fallback, locking, failed-pair preservation, stale-report refusal, and one repair per completed invalid response. They do not cover the new adversarial boundaries.

The complete AST-backed [function-coverage.json](function-coverage.json) records **35 reviewed definitions including nested functions**: 12 retrieval, 7 evidence, 14 investigation, and 2 decision functions. Coverage means source and interaction review plus the mapped tests/probes; it does not mean every branch has an executable adversarial probe.

Prior known session-metric blindness belongs to `evaluation.py`: correct session IDs can score full recall while the answer span is absent. This audit reuses that reviewed observation and recommends auxiliary assertion/span checks without changing official session metrics. It is deliberately not relabeled as a new retrieval bug.

## Reproduce

```sh
PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
PYTHONPATH='/Users/kacperwarych/Desktop/hackathon reactive ai/src' \
'/Users/kacperwarych/Desktop/hackathon reactive ai/.venv/bin/python' \
'outputs/pipeline-research/full-audit-2026-10-31/retrieval/probe.py'
```

The script overwrites only its adjacent `probe-results.json` and temporary synthetic stores. The real-tokenizer checks are optional only if the known local snapshot is missing; saved results identify that they ran. Synthetic embedding/reranking fixtures isolate routing and packing behavior; they are not evaluations of Qwen neural quality. No model comparison or paid answer generation is claimed.

## Independent critique and response

The independent overseer `/root/overseer` challenged an initial default-truncation intuition: ordinary 80-token context plus 200-token units fits 320. Accepted; RET-01 was refined to the actual skipped-unit-contiguity bug and real-tokenizer controls with context disabled/larger cap. The overseer reproduced the updated case. The one-turn overlap fixture did not produce two chunks; that attempted finding was rejected and replaced with the verified default two-turn fixture for RET-04.

Accepted additional critique: RET-06 must use a real structured assistant turn through extraction, rather than just assert its speaker; saved probes now do. RET-12 treats saved decision-snapshot reuse as documented behavior and targets revision metadata, preserving snapshot workflow. RET-09 does not imply the shown current-blocker evidence needs expansion. RET-10 is scoring behavior with a tuning experiment, not a library bug. RET-13 acknowledges current UI replay mitigation. RET-14 is a bounded-admission tradeoff, not proof expansion is universally useless. RET-15 records nested semantics without asserting an existing consumer sums them. RET-16 claims work amplification without invented runtime gains. All were incorporated in this report.

Independent review status: draft and saved probes sent for final reread; final critique/results will be recorded beside this report or appended below.
