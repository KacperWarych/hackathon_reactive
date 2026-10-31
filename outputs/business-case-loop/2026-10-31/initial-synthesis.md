# Current business-case decision

Initial synthesis: 2026-10-31. Three agent reports reviewed; no new paid model experiments or customer interviews performed.

## Leading hypothesis
An evidence-backed customer blocker brief for a seller preparing the next follow-up. A new dated customer conversation changes the brief's current concerns and suggested clarification questions, with source quotes and earlier versions available for review.

This best connects a concrete decision with existing report revision features. It is not yet a validated business case. The first demo should show a changed concern, not claim that an old concern was resolved. Synthetic dataset examples establish a test scenario, not buyer demand.

## What is already implemented
Report-bound note/transcript entry, indexing, fresh retrieval, Reactor-backed answer and structured decision revision, version history, report comparisons, citation checks and failure recovery. Refresh is user-triggered. Background monitoring, CRM ingestion and selective notifications are not established product capabilities. The hourly research automation is separate from the application's behavior.

## Ranking
Scores are evidence-limited judgments on 0–5 scales. Weighted total = 8 × value + 7 × reactive fit + 5 × reuse, out of 100. Reactive fit means plausible benefit from new evidence changing a decision; Reactor superiority requires a separate experiment.

| Candidate | Actual value | Reactive fit | Implemented reuse | Total | Confidence |
|---|---:|---:|---:|---:|---|
| Per-customer changed-blocker brief before follow-up | 2 | 3 | 3 | 52 | Medium on reusable mechanics; low on demand and comparative benefit |
| Renewal/onboarding commitment handoff | 2 | 3 | 2 | 47 | Low; ownership, status and account semantics missing |
| Continuously revised discovery/business-case brief | 2 | 2 | 3 | 45 | Low; evidence independence and cross-customer synthesis missing |

Campaign-wide loss totals are deferred: bounded top-k retrieval is not exhaustive counting. The lead reduced optimistic initial reuse scores because customer isolation is a prerequisite, not a minor product polish item.

## Critical findings and disagreements resolved
- The implementation agent found the Salesgen importer drops session metadata containing customer_id/product_id. A query containing a customer name does not enforce account isolation. Preserve/filter explicit identity or use genuinely isolated input histories before a customer-level demo.
- Exact source-quote checks establish traceability, not semantic resolution. English-only confirmation/negation rules are a particular limitation for the Polish dataset. Changed emphasis does not prove resolution.
- The market agent identified a possible contrast with Gong's email-warning clearance rules, but warning clearance and buyer-objection resolution are different semantics. There is no established competitive superiority. See market.md for primary-source links and qualifications.
- General report version comparison already exists; a durable semantic blocker ledger and selective change notifications are different, missing capabilities.
- Reactive-fit analysis separates event-triggered delivery from stateful Reactor memory. Event-triggered stateless RAG may deliver the same value. No comparative result currently establishes a Reactor advantage.

## First concrete validation
Use the synthetic salesgen customer c_0080, history h_2d798c5867bb, sessions s_19ab7f9c7a72 and s_c04dcd1bd2ce, after verifying raw identity and isolating the input. The recorded focus changes from upfront implementation cost to recurring monthly price. Expected output: explain that change with dated evidence and keep the old concern unresolved/unknown unless explicit evidence resolves it.

Add controls: another customer, seller reassurance without buyer confirmation, unrelated update, backdated source and reopened concern. Evaluate customer isolation, source support, detailed current concern, unsupported resolutions, future leakage and preserved versions. This replay has been specified, not executed in this cycle.

Compare manual preparation, on-demand RAG, event-triggered stateless RAG and persistent Reactor on matched evidence. Record review time, correctness, stale-state errors, cost and latency. A full-context recomputation arm can provide an additional quality ceiling when feasible. Define thresholds before collecting results; see reactive-fit.md.

## What would change the decision
- Sellers cannot demonstrate recurring costly context loss: reconsider the buyer/problem.
- Existing CRM tools already solve the exact job adequately: narrow the task or reject it.
- On-demand refresh performs equally well with less burden: retain interactive workflow and drop claims of necessary background reactivity.
- Stateless event-triggered RAG matches Reactor: retain the business workflow but reject an unsupported memory advantage.
- Identity or evidence errors remain material: fix/evaluate those prerequisites before promoting the product claim.

Next cycle: resolve account isolation and build a concrete replay manifest/annotation specification using read-only app inspection and offline artifacts. Do not repeat broad market searches without a decision-relevant question.

## Reports
- [Implementation audit](2026-10-31/implementation.md)
- [Market research and primary sources](2026-10-31/market.md)
- [Reactive fit and discriminating experiment](2026-10-31/reactive-fit.md)
- [Prioritized validation backlog](backlog.md)
