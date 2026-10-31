# Paid concierge pilot hypothesis — 2026-10-31

## Proposed offer

**Source-backed change decision packets and a maintained reviewed ledger for a small agency:** over two weeks, manually review up to five potential scope changes across one active client project. Deliver an evidence-linked change brief by the next agreed business day, helping the agency decide what to clarify with its client.

The agency supplies a clearly approved baseline and selected later messages. The operator checks the sources, uses the existing report workflow where appropriate, verifies every material claim, and delivers the final brief. This is a human-delivered service experiment, not an automated product or an implemented monitoring feature. It makes no contractual, legal, billing or margin-recovery determination.

**Testable offer price:** PLN 750 for the capped two-week pilot, before applicable taxes. This is an experimental asking price chosen for transparent workload arithmetic below, not a researched market price or estimate of willingness to pay. Do not claim a discount, savings or ROI. No offer has been sent, accepted or charged.

The offer is preparation and record maintenance. It does not assume the agency fails to notice extra work, and it does not promise recovered revenue. A lead may knowingly accept extra work to preserve a relationship; a report does not solve unwillingness to charge.

## Who qualifies

Target hypothesis: an agency delivery lead responsible for one fixed-scope project who can provide at least three recent ambiguous client-change episodes and has authority to try a paid service. Prefer a project where approved scope is identifiable and the lead already spends time reconstructing scattered commitments.

Discovery gate: ask whether the last painful episode involved failure to notice a request, time spent reconstructing evidence/preparing a decision, or an intentional commercial concession. Test preparation burden against a shared change tracker plus checklist and a whole-thread LLM using the same sources. If the agency already knows and documents the change but deliberately absorbs it, reject the premise that more detection will help.

Disqualify for the initial pilot: no identifiable baseline; no permission to share source excerpts; mostly structured ticket changes already tracked adequately; exclusively urgent real-time decisions; or need for legal judgments, complete inbox monitoring or automatic client communication.

## Deliverables and limits

Included:
- One onboarding session of up to 45 minutes to establish project identity, approved baseline, source roles and reviewer.
- Up to five submitted change episodes. Each episode includes the prior baseline and up to five relevant messages/documents or 10,000 words total; larger cases require an explicitly revised scope.
- A brief containing the original requirement and source, new request and source, proposed material difference, authority/acceptance status, unresolved questions, and a suggested clarification for agency review.
- One correction pass per episode and one closing review comparing usefulness and review time with the current process.
- A maintained reviewed change ledger preserving submitted versions, approval uncertainty, owner decision and the human-reviewed conclusion; it is manually maintained during this pilot.

Excluded: automatic inbox/CRM ingestion, continuous monitoring, guaranteed detection of all changes, legal interpretation, estimating delivery cost or scheduling impact without agency input, issuing change orders/invoices, client outreach, and taking action on the agency's behalf. No tool or agent contacts a third party under this analysis task.

## Required inputs and onboarding

1. Agency identifies a project owner and permitted reviewer; confirms it can supply the selected materials.
2. Owner supplies the approved baseline, approval source/date, project identifier and actor/authority map. Clarify which people can request changes and which can approve them.
3. Owner selects three historical episodes for a baseline trial, including one harmless clarification and one unapproved internal suggestion. Their later outcome is held separately for assessment.
4. Agree delivery window, word/case limits, format, retention/deletion expectations and excluded judgments before accepting a paid engagement. These operational arrangements are prerequisites, not capabilities already supplied by the local app.
5. Run the first episode manually. If the owner cannot tell which baseline was approved, resolve that ambiguity with them before generating a confident change claim.

## Smallest implemented reuse and gaps

Reuse: dated source excerpts, fresh retrieval after a manually added entry, cited answer and decision interpretation, prior report versions, reviewable evidence and failure recovery. Keep one project in one explicitly scoped history; a source-only offline preparation is possible, but a new generated Reactor report requires configured service access.

Gaps: current app only models Customer/Seller roles; it does not enforce arbitrary approval authority. Its imported campaign metadata does not establish per-customer/project identity. It has no explicit approved-baseline registry, source-sharing workflow, team permissions or automatic connectors. Source quote validation does not prove semantic acceptance. Therefore the concierge operator must maintain project/actor/baseline records outside the generated report and verify interpretation manually. The pilot must not present those manual controls as product features.

No application changes or live API runs were made for this offer. Before operational use, choose a source handling arrangement appropriate to the actual customer, and verify access, retention and service costs.

## Operator workflow

1. Intake: confirm project and episode boundary, approved baseline and newest source timestamp.
2. Triage: reject duplicates/out-of-scope material; distinguish explicit request, hypothetical suggestion, acknowledgment and approval.
3. Prepare evidence: preserve source speaker, date and exact excerpts. Record missing context rather than filling gaps.
4. Generate or draft: use the existing report flow as an aid if applicable; manually fill authority/baseline distinctions it cannot represent.
5. Verify: check every asserted change against both old and new sources; label interpretation, acceptance uncertainty and unsupported cost/schedule effects.
6. Deliver privately to the designated agency reviewer. The reviewer decides whether to ask the client for clarification.
7. Record effort, corrections and reviewer judgment. Obtain the final disposition later where available; do not treat silence as approval.

## Success criteria and stop gates

Provisional thresholds below are proposed pilot decision rules, not observed results. Agree them with the participant before delivery.

- At least four of five briefs rated useful for the next client/project conversation.
- No wrong-project source and no unsupported claim that a change was approved in the delivered, human-checked briefs.
- Customer review time must be recorded. A brief only saves time if verification/editing does not consume the preparation time it replaces.
- At least three comparable episodes have baseline manual preparation time and pilot reviewer time; report raw observations rather than extrapolating a small sample into annual savings.
- Customer explicitly elects a second paid period at the same capped terms or provides a concrete reason not to. Interest and praise are not retention.
- Operator time and actual service costs remain within the price envelope. If they do not, reduce scope, improve workflow or reprice explicitly before another period.

Stop or redesign if baseline/authority ambiguity cannot be resolved, material source omissions repeatedly invalidate briefs, the customer already gets equivalent results from its ticket process, review effort eliminates time savings, or useful change frequency is too low for recurring purchase. A single serious delivered false approval requires investigating the workflow before the next delivery.

## Transparent illustrative economics

These numbers are **operating assumptions**, not market rates, measured productivity or API pricing. PLN is used to make the asking-price experiment concrete. Replace every assumption with observed pilot data.

Let:
- P = pilot revenue, proposed PLN 750 before applicable taxes.
- W = operator time value, assumed PLN 100/hour solely for planning.
- H0 = onboarding + closing/admin hours, assumed 1.25 hours.
- N = reviewed episodes, capped at 5.
- M = total active operator minutes per episode: data preparation, import, source verification, correction, ledger maintenance and delivery. Record generation wait separately; include it in M when it prevents other work. Also record customer intake/review time outside operator labor, because it affects adoption.
- C = actual incremental model/service/tool cost attributable to the pilot; **unknown until measured**. Do not substitute an invented per-token price.
- A = attributable acquisition cost; unknown and excluded from contribution below, then deducted separately.

Direct contribution before acquisition, taxes and general overhead:

`P - W × (H0 + N × M/60) - C`

| Scenario assumption | Episode minutes M | Total operator hours | Labor allowance | Contribution before C and A |
|---|---:|---:|---:|---:|
| Simple, well-scoped inputs | 15 | 2.50 | PLN 250 | PLN 500 |
| Base planning assumption | 30 | 3.75 | PLN 375 | PLN 375 |
| Difficult review/corrections | 60 | 6.25 | PLN 625 | PLN 125 |

With these assumptions, allowable combined C + A before the illustrative contribution reaches zero is PLN 500/375/125 respectively. This is a break-even ceiling, not a spending recommendation. Existing subscriptions are not automatically free: show incremental cash cost and allocated shared cost separately. Track answer-plus-decision calls, citation corrections, retries and failed generations as costs too. Record observed elapsed delivery time separately from active labor. Do not infer margins from model generation time alone.

At zero service/acquisition cost, this price supports at most 7.5 total operator hours, leaving 6.25 hours after H0, or 75 minutes per episode for five episodes. Positive costs lower that limit. For any desired contribution G, the maximum sustainable average episode minutes is:

`60 × (((P - C - A - G)/W) - H0) / N`

This service can have positive direct contribution and still be a poor business if finding each customer is expensive, owner time is not scalable, or active projects generate too few recurring events. No revenue projection is justified before paid acceptance and repeat use.

## Concierge first, SaaS later

Concierge tests whether the brief changes an actual delivery decision and whether someone pays repeatedly. It also exposes manual authority/identity work that an appealing demo hides. Do not automate these ambiguities before learning their frequency.

A SaaS hypothesis becomes worth considering only after repeated paid use reveals a common intake pattern, predictable review burden and a reachable distribution channel. Required product work then includes reliable project/actor scope, approved baseline/version records, source permissions, relevant integrations, event deduplication, change significance controls and domain evaluations. Report generation alone is insufficient.

Retention risks: project completion ends demand; clients may submit too few episodes; a competent delivery lead may internalize the checklist after one period; manual copying may become intolerable; or noisy alerts may create more conflict than value. Test per-project/episode billing against recurring periods after actual usage, rather than forcing a subscription assumption.

## Comparison with support and sales pilots

| Dimension | Agency scope triage | Support handoff | Sales blocker brief |
|---|---|---|---|
| Unit delivered | One potential scope-change brief | One reopened/escalated case handoff | One updated customer blocker brief |
| Permissioned input | Approved brief + selected client/internal messages | De-identified ticket with attempts/results | Customer-scoped call notes/transcripts |
| Immediate reviewer | Delivery/project lead | Escalation recipient | Seller/account manager |
| Manual verification focus | Request vs approval, baseline and authority | Suggested vs attempted fixes, recurrence | Customer statements vs seller inference, latest concern |
| Stronger simple alternative | Structured scope/change log | Existing ticket summary/checklist | CRM notes and follow-up checklist |
| Main friction | Low/irregular event frequency; disputed scope | Data sensitivity; tool integration; existing summaries | Identity mismatch; crowded workflow; unproven causal impact |
| Implemented reuse | High report reuse; authority gap | High report reuse; actor/status gap | Highest dataset alignment; customer scope gap |
| Economic measurement | Minutes per reviewed change; corrections | Minutes per handoff; false attempted-action claims | Minutes per brief; stale/unsupported concern claims |

Do not reuse the PLN 750 price mechanically across these offers: their event volume, urgency, acquisition burden and review cost may differ. Compare willingness to submit actual examples and pay for the bounded deliverable before choosing a market. The scope pilot currently wins on clarity and low integration needs, not proven demand or superior economics.
