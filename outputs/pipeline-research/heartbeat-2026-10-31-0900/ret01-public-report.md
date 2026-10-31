# RET-01 public Salesgen exposure follow-up — 2026-10-31 09:00 Warsaw

**Result:** zero RET-01 selected-late-unit clipping exposure in this public Salesgen snapshot. This supplies corpus-specific negative evidence; it establishes neither a general safety guarantee nor an answer-error rate. The previously reproduced synthetic default-budget failure remains valid. No new application defect or implementation decision is reported from this bounded cycle.

Researcher: inherited **GPT-6.1 Sol / high**, as dispatched; no separate runtime model introspection. Independent review: `/root/overseer`. Bounded cycle began 08:01:28 UTC. No application edits, gold reads, production database writes, neural weights, downloads, or live calls. Only public `salesgen_dataset_fail/public/histories.jsonl` and `questions.jsonl` were loaded. No transcript text is included in saved outputs; the one source example is an opaque SHA256-derived ID.

| Denominator / exposure | Count |
|---|---:|
| Public histories / questions | 1 / 59 |
| Sessions / turns / memory units | 176 / 2,694 / 2,701 |
| Default chunks | 403 |
| Eligible question–chunk opportunities | 23,777 |
| Proposed top-two unit options over those opportunities | 47,554 |
| Short late units with a preceding turn | 2 |
| Such units partially or entirely clipped | **0** |
| Eligible question–chunk opportunities proposing a clipped late unit | **0** |
| Distinct affected questions / sources / turns | **0 / 0 / 0** |

Method: cached real Qwen tokenizer revision `97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3`, `local_files_only=True`; production `Memory.records` and default `chunk_turns`; temporary SQLite only. For each unit, the probe reproduces the exact default 80-token context expansion, role prefix, and 320-token cap. RET-01 structural candidates require a short later unit inside a turn, with an earlier turn available. Actual selected-unit truncation requires capped source `end < selected_unit.end`; entire loss requires `end <= selected_unit.start`. These offset tests avoid counting harmless truncation of following context.

Both structural candidates occur in one public source. They contain 55 and 30 selected-unit tokens, with expanded excerpts of 337 and 282 tokens. Their selected-unit ends occur at token 294 and 282, so neither selected unit is clipped. The 337-token example exceeds the excerpt cap only because of later context: treating every oversized expanded excerpt as RET-01 exposure would incorrectly report it as affected.

For every public question, the scan applies the same history ID and `session.iso <= question.iso` filters, then tests real default chunk spans and exact lexical top-two unit ordering. This measures **proposed-option exposure if that chunk is retrieved**, over exhaustive candidate opportunities. It does not execute BM25/dense ranking, reranking, final evidence packing, or answer generation, and it does not claim that all 23,777 opportunities would enter a real request. Because no source unit meets the clipping condition, no affected-case counterfactual exists in this corpus. One distinct nonaffected structural unit proposed by actual public-question/default-chunk selection was checked through real `extract_options`: exact source offsets cover the selected unit with default context and with `context_tokens=0`; both retain the exact text. The second structural candidate did not enter a sampled actual-question top-two control. This is a control of one nonaffected unit, not validation of every unit or a remedy gain.

Hashes and all aggregate values are recorded in [ret01-public-results.json](ret01-public-results.json); executable method is [ret01-public-exposure.py](ret01-public-exposure.py). Relevant active source hashes match the full-audit baseline. Public histories SHA256: `fcd4c06e00819325642ed18019055b43ba5fa19e49b591ca6782be042e294e53`; public questions SHA256: `6abef0779c2c33f0527cdf88d428ad4394cafe6cfebb9b78ad3a6cbc4f69b3ff`. The measured probe runtime is about 1.2 seconds on this installed environment, excluding import/startup overhead; no speedup comparison is made.

Next experiment: include independently annotated natural long-monologue examples from an authorized public corpus alongside the synthetic RET-01 regression. Freeze retrieved chunks, ensure selected late units actually contain supporting assertions, and compare target-preserving context construction against current packing at identical budgets. Salesgen alone provides no affected RET-01 examples in this snapshot and cannot estimate the fix's benefit. Do not reprioritize the separate RET-02/03/04 mechanisms from this result.

Independent critique and response: the overseer required default chunks and correct history/time scope; distinct source/turn/question denominators; separation of exhaustive candidate opportunities from actual retrieval; exact source-offset loss checks; explicit zero counters; a context-zero control; and no extrapolation from a zero result to other corpora. Accepted and incorporated. The final control records both exact substring retention and source-offset coverage. The overseer independently reran the probe; final acknowledgment is recorded by the coordinator/reviewer alongside this cycle.
