# Pipeline research backlog

Updated 2026-10-31. Research only; do not modify production or run paid/heavy experiments without separate authorization.

| Order | Experiment | Completion criterion | Status |
|---|---|---|---|
| 1 | Annotate 15–20 history-disjoint questions with answer-bearing turns/spans, including paraphrases and state changes; preserve session gold | Reviewer agrees on span sufficiency, role, negation, entity, chronology labels; freeze IDs before comparison | Next |
| 2 | Fixed-candidate, fixed-budget packer ablation: top-two lexical units vs broader bounded unit candidates; semantic reranking only if justified | Paired span retention and state-support metrics, packed session coverage, latency; no model-superiority claim without comparison | Pending |
| 3 | Inspect the 13/59 salesgen items with >6 gold sources: explicit recorded total vs complete enumeration vs unsupported population | Classify all 13 and test a bounded aggregate route on copied data; do not interpret gold source count as answer necessity | Pending |
| 4 | Check short reply retention across excerpt/context budgets and real tokenizers | Reproduce with default 320-token excerpt or clearly identify only affected configurations | Deferred; 60-token case proven only |
| 5 | Assess update-search gate and structural decision validator with labeled fact links/negation context | Separate heuristics/display checks from semantic proof; estimate frequency on real examples before remedy | Deferred synthetic diagnostics |
| 6 | Revisit embedding/reranker candidates only after attributing errors to retrieval instead of packing | Matched corpus, candidates, budgets, latency/memory, current config hash and model revision; held-out histories | Deferred |

Completed first cycle: active/staged source parity verified; synthetic packer answer loss reproduced with whitespace and cached Qwen tokenizer; session-metric blind spot reproduced; 13/59 gold source ceiling independently counted; 20 existing targeted tests passed. No remedy gain measured. Reports and probes: `2026-10-31/`.
