# Reactive fit analysis — 31 October 2026

## Recommendation and evidence boundary

Prioritize **a source-cited customer blocker brief that updates when a new conversation changes the next follow-up decision**. The initial buyer hypothesis is a small B2B sales team handling repeated conversations about products with nontrivial purchase decisions. The user is the seller preparing a follow-up; the decision is which unresolved concern to address or clarify next. Demand, willingness to pay, and actual sales impact remain unverified.

The strongest implemented foundation is report-bound entry ingestion, dated retrieval, versioned investigations, explicit speaker attribution, and cited changes/concerns. The strongest unproven proposition is that automatic, selective updates save users enough work to justify an always-current brief. Do not position this as demonstrated background monitoring: `INVESTIGATIONS.md` explicitly says it is interactive report revision, not background monitoring.

Distinguish three claims:

1. **Reactor integration works:** existing three-question demo supports a limited integration/replay claim.
2. **Event-driven updating is valuable:** requires a comparison against user-requested refresh and manual review.
3. **Persistent Reactor investigation memory is superior:** requires comparison against an equally triggered stateless model using the same fresh evidence. Event-driven stateless RAG could deliver the customer value equally well.

This analysis used local code, documentation, and supplied records. It makes no external market-validation claim, and ran no new live Reactor benchmark. No AGENTS.md was found within the inspected Desktop project tree.

## A concrete temporal replay available today

Use the supplied **synthetic** salesgen records, never present them as real customer traction. In history `h_2d798c5867bb`, customer `c_0080`, Magdalena Grabowska, CRM product:

| Boundary | Evidence | Supported conclusion |
|---|---|---|
| 4 September 2026, 10:07 | `s_19ab7f9c7a72` | Customer repeatedly describes approximately PLN 2,000 upfront implementation cost as the primary obstacle; a cheaper alternative is also mentioned. |
| 25 September 2026, 11:20 | `s_c04dcd1bd2ce` | Customer now focuses on PLN 89 versus approximately PLN 50 per employee monthly and says the recurring difference is unaffordable. |

The useful update is **the emphasis of the recorded concern has changed from upfront implementation to recurring price**. It is not evidence that implementation cost was resolved. Both remain in the historical record. A seller could now clarify current cost/value requirements instead of repeatedly answering the older implementation objection. That proposed next question is generated advice, not a recorded customer commitment.

The system should preserve the before/after evidence, identify the new source and date, retain uncertainty about the older concern, and suppress irrelevant updates. A classification of both calls as merely “price” misses the business-relevant change. This makes the case a stronger temporal test than a generic category flip.

Replay the first call alone, generate the brief, add the second call, refresh, and inspect the version diff. The existing report-bound entry flow can demonstrate this manually. Automatic source detection and notification would be additional work. Use only records available at each time boundary; evaluator annotations must stay outside all model inputs.

## When reactivity earns its cost

Reactivity is useful when all these conditions hold:

- Information arrives between user visits and can change an impending decision.
- The affected customer/report can be identified reliably.
- A meaningful change can be distinguished from repeated or irrelevant conversation.
- The time saved or mistake avoided exceeds review burden and operating cost.
- A human can inspect the supporting statement before acting.

Ordinary RAG is sufficient for occasional historical questions with no time-sensitive downstream action. Manual report refresh is sufficient when the seller is already reviewing every new call and reliably updates the brief. Campaign-wide counts need exhaustive customer-level analysis and deduplication; making top-k retrieval reactive does not solve completeness. A cron job that repeatedly regenerates the same answer is not evidence of product value.

## Discriminating experiment

Run the same temporal cases through four conditions:

| Arm | Trigger and analysis | What it isolates |
|---|---|---|
| A | Human reviews transcript and updates a short customer note | Current-workflow baseline |
| B | User requests a fresh RAG brief when preparing follow-up | On-demand assistance |
| C | New entry triggers stateless RAG with current evidence and saved question/follow-up instructions | Incremental value of event-driven delivery |
| D | Same trigger and evidence, persistent Reactor investigation with current versioned workflow | Incremental value of stateful continuity |

Keep model, retrieval configuration, evidence budgets, sources, evaluation criteria, and available task instructions constant for C versus D; reset history for C and preserve it for D. If the API cannot provide an equivalent stateless run, disclose the confound. Existing source/agent-history switching may reconstruct memory, so log real history resets rather than labelling all D runs continuously stateful. Use a separate permitted test agent or serialized evaluation; the app has one active history per agent and cannot safely compete with a running benchmark.

First use a bounded screening set of 20 chronological sequences: 10 substantive changes and 10 controls. Include changes in detailed reason without category change, explicit resolution, reopening, contradictory statements, seller speculation, unchanged concerns, unrelated additions, delayed/backdated entries, duplicate entries, and unknown customer. Available supplied cases should be identified by source ID; any added controlled fixture must be labelled synthetic test data. Do not claim statistical significance from this small pilot.

Then validate the value proposition with at least three consenting practitioners using de-identified real sequences they can judge. Ask each to complete the same follow-up preparation task under counterbalanced conditions, with a reviewer blind to arm assessing the recommendation and evidence. Do not fabricate willingness-to-pay or infer sales lift from simulated call accuracy.

Measure:

- Correct current concern **and its detailed reason**, supported historical change, and unresolved/unknown state.
- Unsupported resolution, seller-statement laundering, wrong customer, future leakage, and stale answer rates.
- Meaningful-change detection precision/recall; notifications per actual change; duplicate/no-change notifications.
- Time from new entry to usable brief, human preparation time, review burden, request count, latency, and cost per useful update.
- Practitioner judgment: whether the brief changes a concrete next step and whether they would reuse it next week.

Provisional gates, declared before running: at least 9/10 substantive changes correct; no unsupported resolution, wrong-customer attribution, or future leakage; at most 1/10 false notifications on controls; median preparation time at least 30% below manual baseline without lower decision quality. These are pilot acceptance targets, not measured results or statistically validated thresholds. Trigger-to-brief latency should be below the workflow's actual follow-up preparation deadline; do not invent a real-time need.

Retain eventing only if C or D improves usable-brief availability/review effort over B. Prefer D over C only if it meaningfully improves correctness, follow-up reference handling, or cost/latency without extra stale-memory errors. If no material advantage appears, retain the current interactive brief and stop claiming special reactivity benefits. If current-user preparation time barely changes, revisit the buyer/task before building connectors.

## Scoring rubric for the recurring loop

Score each dimension 0–5 and calculate `8 × actual value + 7 × reactive fit + 5 × reuse` out of 100. Every score needs evidence and a confidence label; unknowns should remain explicit. A high reuse score cannot establish a business case.

| Dimension | 0 | 3 | 5 |
|---|---|---|---|
| Actual user value, 40% | No identifiable user or decision | Specific recurring job and practitioner-confirmed pain; alternatives understood | Repeated real use with measured net benefit and credible adoption/payment evidence |
| Reactive fit, 35% | Static question; fresh facts change nothing | New events materially alter a dated decision, with bounded useful triggers | Controlled comparison shows value over on-demand refresh and acceptable false-update burden |
| Implemented reuse, 25% | Requires a different product/data architecture | Existing retrieval and UI useful but substantial new state/integration needed | Core workflow demonstrated with current versioning, citations and entries; gaps narrowly bounded |

Provisional evidence-limited ordering:

| Candidate | Value | Reactive fit | Reuse | Total | Confidence |
|---|---:|---:|---:|---:|---|
| Evolving per-customer blocker brief before follow-up | 2 | 3 | 4 | 57 | Medium on reuse; low on demand/reactive advantage |
| General personal decision-history assistant | 1 | 2 | 5 | 47 | High on implementation similarity; low on buyer/task |
| Campaign refusal totals and seller-coaching dashboard | 2 | 2 | 2 | 40 | Low; exhaustive aggregation absent |

Scores are prioritization judgments, not measured market facts. None clears a validated-business-case threshold. Promote only after evidence improves; do not increment scores because another research pass repeats the same claims. Explicitly record whether the next experiment tests market value, eventing value, or stateful Reactor advantage.

## Important limits and next concrete tasks

1. Create a replay manifest with the two cited sessions and expected dated concern states, plus controls. Evaluate the existing manual report flow before adding automation.
2. Build an evaluator ledger separating traceability from semantic correctness. The current resolution validator checks exact user quotes and English confirmation/negation cues; this is not multilingual semantic verification and may miss valid Polish confirmations or misread their meaning.
3. Compare B/C/D with saved request/response and version histories. Existing report generation produces an answer and structured decision pair, so count both calls and correction calls in latency/cost.
4. Validate one narrow seller workflow with practitioners. Evidence that a concern changed is not evidence that a proposed response wins sales.
5. First close the identity gap for any account-scoped claim: the implementation reviewer found that `store.py` ingestion drops Salesgen session `meta`, including `customer_id` and `product_id`; the dataset is one campaign history. Name-based retrieval is therefore not enforced customer scope. The narrow demo must inspect source identity explicitly, and deployment needs preserved structured customer/product identifiers plus filtering. The rubric's reuse score reflects a strong report foundation, not completed per-account isolation.
6. Only after the pilot gates, prototype bounded report invalidation on new source revision, deduplication, selective updates, and an inspectable change queue. CRM/call connectors, background triggers, notification policy, and human review are unimplemented work, not current capabilities. Do not claim differentiation through verified resolution until semantic evaluation demonstrates it; a competitor's alert dismissal behavior does not establish our own correctness.

Sources inspected: Desktop project's `README.md`, `INVESTIGATIONS.md`, `IMPLEMENTATION.md`, `outputs/evaluation-report.md`, `salesgen_dataset_fail/README.md`, `salesgen_dataset_fail/public/histories.jsonl`, `salesgen_dataset_fail/public/questions.jsonl`, and `src/decision_memory/decision.py`. Evaluation documentation reports three live demo examples and incomplete larger gates; this analysis has not independently reverified current run completion.
