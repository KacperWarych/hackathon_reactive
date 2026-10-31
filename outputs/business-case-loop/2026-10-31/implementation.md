# Implementation fit audit — 2026-10-31

## Verdict

The strongest reusable slice is an evidence-backed, evolving **single-customer blocker brief**: a seller or account manager adds the latest conversation; the same report updates the current concerns, changed facts, proposed resolutions requiring semantic review, and next questions while preserving citations and earlier versions. This is a concrete human-triggered reactive workflow already largely present. Market demand and willingness to pay remain hypotheses. Automated CRM monitoring, prioritization and outreach are not implemented.

Inspected the authoritative app at `/Users/kacperwarych/Desktop/hackathon reactive ai` read-only, plus the shared workspace's research README and staged-output inventory. No AGENTS.md was found at the project root or checked ancestor paths. No app changes, model downloads or paid API calls were made. This is source/artifact inspection, not a new end-to-end test.

## What exists

| Capability | Evidence in authoritative app | Business implication |
|---|---|---|
| Add a dated Customer/Seller note or transcript to an existing investigation, index it, regenerate both answer and decision history | `src/decision_memory/report_entry_ui.py:12-88` | A new customer update can change the working brief without starting over. |
| Stable investigation identity, immutable successful revisions, stale-view rejection, retry and saved-entry recovery | `src/decision_memory/investigations.py:138-182`; `INVESTIGATIONS.md` | The user can audit what changed and recover from model/service failure. |
| Fresh retrieval with history/time boundaries and separation of follow-up instructions from factual evidence | `src/decision_memory/investigations.py:184-219` | Supports “what is true now?” versus “what was true before?” questions. |
| Structured goals, concerns, changes, resolutions, missing information, interpretations and next questions | `src/decision_memory/decision.py:5-23` | Already close to a customer/deal handoff brief. |
| Exact user quote and source-label validation for proposed resolutions | `src/decision_memory/decision.py:27-60` | Useful traceability; not semantic proof that the issue is resolved. |
| Local BM25/dense/hybrid retrieval, reranking, bounded evidence, Reactor integration | `README.md`; `src/decision_memory/retrieval.py` | Reusable evidence layer rather than a complete sales operations platform. |

Current reactive boundary: clicking **Save entry and refresh report** triggers ingestion → indexing → retrieval → answer/decision revision. Standalone entry creation only saves/indexes. The app has no background event subscription, material-change alerting, CRM write-back or external action loop. The business-case heartbeat should not be confused with an implemented product capability.

## Constraints that change the business choice

1. **Customer identity is not a first-class stored boundary.** Salesgen has one campaign history containing 176 calls; source session metadata contains customer_id/product_id, but `store.py:137-150` persists session identity, dates, turns and their hash, not `meta`. A name-specific query can retrieve relevant text but does not enforce customer isolation. A trustworthy customer product needs explicit identity retention/filtering, or separately scoped per-customer histories.
2. **Campaign totals are out of scope for top-k retrieval.** README explicitly warns of incomplete population coverage. Salesgen aggregate labels count customers using latest outcomes, not call counts. Ranking rejection causes requires a complete extraction ledger with customer deduplication, latest-state rules and deterministic counting.
3. **Polish resolutions have a concrete mismatch.** `decision.py:55-59` only recognizes English confirmation/negation terms. A valid Polish confirmation can be rejected, while Polish negation lacks equivalent checks. This matters because salesgen is Polish. Do not demonstrate Polish “confirmed resolution” as production reliable without fixing and evaluating this.
4. **The evidence dataset is synthetic.** `salesgen_dataset_fail/README.md` identifies ElevenLabs seller and simulated-customer conversations. It can test pipeline behavior but cannot validate actual buyer need, call economics or real-world accuracy.
5. **Serial service state limits operational scale.** One active Reactor history per agent and local locking; switching reports may reconstruct memory. This is acceptable for an assisted demo but unproven for concurrent teams.
6. **No claim of live-call coaching.** Existing demo Reactor responses took about 21–42 seconds, plus retrieval; investigation revisions generate two sections. That favors post-call workflows over real-time intervention.

## Current measurement evidence (and stale documentation)

`outputs/evaluation-report.md` says stress evaluation and complete test indexing are pending, but `.data/evaluation/offline-summary.json` now records both as complete. Prefer the underlying artifact over the stale prose. Its recorded rerank configuration achieved 96.74% mean packed session recall and 91.49% complete packed coverage on held-out validation; stress results fall to 82.73% and 72.73%. These are retrieval coverage, not business-answer accuracy, and may predate later app changes. The summary says Reactor answer quality is not measured by offline preparation. The three live development demos are an integration smoke test, not a sales benchmark. I did not establish completed live validation or full test submission from the inspected files.

## Three candidate uses

The following scores are judgments on 1–5 scales, not measurements. Implementation fit concerns the reusable report slice, not a deployable product: identity scoping remains a prerequisite. Reactive workflow suitability does not establish that Reactor outperforms stateless retrieval, another model, or simple rules; that needs a controlled comparison.

| Candidate | Existing implementation fit | Plausible reactive workflow fit (not proven Reactor necessity) | Key missing proof/work | Judgment |
|---|---:|---:|---|---|
| Post-call current customer blocker brief for a seller/account manager | 3 | 3 | Real transcripts, explicit customer scope, customer-verified changes, time saved | Best near-term wedge. |
| Customer onboarding/escalation handoff brief | 2 | 3 | Real handoff cases, multi-person roles, ownership/status fields, workflow validation | Strong alternative if interviews show more costly repeated context loss. |
| Sales campaign loss analysis/coaching dashboard | 2 | 3 | Full-call extraction, identity ledger, deduplication, deterministic aggregates, real labels | Plausible later product; current top-k architecture cannot substantiate campaign totals. |

## Smallest credible demo

Use one customer and two dated conversations, each clearly labeled as real permissioned data or synthetic demonstration material. Start with a report asking: “What currently prevents this customer from moving forward, what changed, and what should the seller clarify next?” Show the first cited brief. Add the second conversation through the existing report-entry flow, where the customer explicitly changes a requirement or rejects the seller's assumption. Show the new version, quoted evidence, and before/after comparison. Show an unsupported question producing missing-information/abstention behavior. Do not require a resolution claim for this first demo; it can demonstrate changed evidence without triggering the Polish validator problem. Do not imply an automatic incoming-call integration.

Success gates: correct customer scope; changed blocker supported by new source; old blocker not silently retained as current; no inference promoted to confirmed resolution; old report preserved; reviewer can find evidence rapidly. Track total refresh time and human review time. Baseline against a seller reading the same transcripts and writing the brief manually.

## Concrete next tasks for the recurring loop

1. Evaluate 10–20 paired conversations with changed customer intent and a human-reviewed latest-blocker label; record factual error, stale-state error, abstention and review time. Use existing local data for rehearsal, permissioned real examples for business validation.
2. Design customer identity preservation/filtering, including same-name customers and multiple products; do not allow a campaign history to masquerade as a customer boundary.
3. Diagnose and test Polish confirmation/negation handling before choosing resolution detection as the headline feature.
4. Interview sales/account-management users about their last missed contextual update, frequency, cost and current workaround; compare the blocker-brief wedge with onboarding handoff.
5. Keep aggregate campaign analysis as an explicitly separate candidate requiring a ledger architecture; reject research conclusions that equate retrieval recall with exhaustive analytics.

Lead review: initial optimistic candidate scores were reduced to reflect missing account isolation and unproven reactive advantage; see latest.md for the reconciled three-dimensional ranking.
