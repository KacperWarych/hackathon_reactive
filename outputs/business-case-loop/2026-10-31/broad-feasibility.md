# Broad feasibility red team — 2026-10-31

## Scope and epistemic status

This is a hypothesis-led feasibility assessment grounded in the implementation audit, not market research or validated pricing. Buyer demand, distribution, economics and willingness to pay below are hypotheses to test. No app code changed and no external service was invoked. Current implementation references are in `implementation.md` beside this report.

**Hackathon demo winner:** a project scope-change brief reacting to a new client message, because attendees can understand the before/after contradiction and inspect its evidence quickly. **Nearest existing-data demo:** a sales blocker update. **Business candidate to validate first:** scope-change handling for small agencies delivering fixed-scope client projects, with support escalation as a second candidate only if permissioned data and a distribution partner are readily available. None is a proven business winner.

## Reusable kernel, not finished product

Implemented: dated source ingestion; role-labeled text; history/date-scoped retrieval; report plus structured decision interpretation; fresh report after manually adding a source; immutable earlier versions and evidence snapshots; source citation checks; failure recovery. The core primitive is **new source → revised answer about a bounded case → reviewable difference**.

Not implemented: reliable entity matching, arbitrary multi-person actors, authoritative state transitions, task ownership, integrations, automatic triggers/alerts, importance filtering, action execution, access control appropriate to teams, and business-specific evaluation. Quote matching does not prove a concern is resolved. Reactor has not been shown to outperform stateless retrieval or rules. Reuse is strongest for an assisted case-review interface; it decreases substantially when a pitch requires unattended action.

## Candidate comparison

All judgments are qualitative hypotheses. “Rules alternative” means a simpler baseline should be tested before assuming AI is necessary.

| Candidate and concrete trigger | User job and minimum honest demo | Reuse / delivery friction | Rules alternative and attractive trap |
|---|---|---|---|
| **Project scope drift:** client message introduces an incompatible requirement | Delivery lead sees agreed scope, new request, contradiction and clarification needed; show original acceptance and later change | High report reuse; actor/authority distinctions and explicit project boundary needed; two documents suffice for demo | Rules handle changed structured tickets and budgets. Trap: calling every new request scope creep or declaring contractual entitlement. |
| **Support escalation:** new customer reply contradicts assumed fix | Support lead receives unresolved issue, attempted fixes, latest customer evidence and next diagnostic question | High chronology reuse; internal/customer roles, ticket identity and PII handling needed; realistic data access harder | Rules handle reopened status/SLA breach. Trap: autonomous diagnosis or promising root-cause truth from chat alone. |
| **Customer onboarding handoff:** customer dependency changes after handoff | Implementation manager sees changed prerequisite, affected next step and unanswered question | High narrative reuse; owners and dependency graph absent; requires access across sales/onboarding sources | A checklist is better for missing mandatory fields. Trap: rebuilding a project tracker without solving missing cross-source context. |
| **Recruiting requirement drift:** hiring manager changes role must-have | Recruiter sees old/new requirement and which search assumptions need review | Medium reuse; source authority and position identity needed; avoid candidate screening in first demo | Structured requisition versions solve explicit edits. Trap: candidate ranking, inferred sensitive attributes, or automating employment decisions. |
| **Procurement change review:** supplier revises an offer or delivery condition | Buyer compares changed promises to recorded requirements and drafts clarification questions for human review | Medium reuse; tables, numeric extraction and document versioning are additional work | Spreadsheet diff is better for price/quantity changes. Trap: asserting legal compliance or savings without verified numeric/document coverage. |
| **Decision invalidation:** new evidence contradicts an earlier project decision assumption | Project lead sees the original assumption, new source, decision potentially affected and a review question | High conceptual fit, medium actual reuse; explicit decision-to-assumption links absent | Expiry dates/rules handle stale documents. Trap: generic knowledge assistant with no accountable owner or recurring decision workflow. |
| **Sales blocker update:** latest call changes why a prospect will not buy | Seller gets current concern, change since last call, evidence and next clarification | Highest data availability, high report reuse; imported customer metadata is discarded, so identity boundary must be fixed | Rules handle stage changes and reminders. Trap: causal revenue claims, invented “true objection,” full campaign totals from top-k evidence. |
| **Incident handoff:** new incident note undermines current hypothesis | Incoming engineer sees tested hypotheses, contradictory observation and unanswered diagnostic questions | Medium reuse; telemetry/tool ingestion and incident roles missing; static note demo is feasible | Alert rules and incident timelines solve structured events. Trap: claiming root cause or autonomous remediation without system evidence. |

## Deep candidate A: fixed-scope project change clarification

**Buyer hypothesis.** Small agencies or consultancies delivering fixed-scope projects may repeatedly lose margin or time when accepted requirements change across messages. The user is the person accountable for delivery and client clarification. Avoid an enterprise-wide knowledge product: one project, an approved baseline, and incoming client changes is a tractable initial unit.

**First value.** User pastes an approved brief and a later message. In one session the system produces (1) the quoted original requirement, (2) quoted new request, (3) whether these may conflict, (4) missing authority/context, and (5) a draft clarification question. “May conflict” is an interpretation, not a contractual finding. No background integration is necessary to establish the first useful result.

**Existing slice reused.** Report entry/refresh, date boundaries, original excerpts, history versions and failure recovery. The current Customer/Seller mapping can support a narrowly labeled client/agency demo only if the mapping is disclosed. A production system needs source actor identity and authority: an internal idea cannot override an approved client requirement. New requests do not establish acceptance or billability.

**Smallest honest demo.** Three source entries: agreed website scope includes one language; client later requests a second language; agency internally proposes an option without client acceptance. Ask what changed and what must be clarified. The report identifies the request and preserves “not yet agreed.” Add a client confirmation with clear wording and show a proposed update requiring review. Synthetic records are explicitly labeled. Show manual triggering, not claimed email monitoring. If the validator cannot represent roles/confirmation correctly, demonstrate concerns/changes and leave resolutions empty.

**Data access and distribution.** The founder can test with a few permissioned project snippets rather than requesting complete inbox access. A plausible distribution experiment is an opt-in template/report shared with agency delivery leads; no outreach is sent by this research loop. The test asks users to supply a recent actual scope misunderstanding and measures whether the output would change their next action. A polished demo without such examples does not validate demand.

**Economics and adoption.** Chargeability hypothesis is avoided margin loss or reduced review time, but a report can be too infrequent to sustain a subscription. Measure events per active project/month, accepted-useful reports/event, review minutes and model cost/report. Two model outputs plus retrieval/correction may be excessive if a simple text comparison suffices. Batch non-urgent changes and only refresh affected cases in a later architecture. A tool outside the team's existing communication surface incurs copy/paste cost; early manual entry is useful for validation but could cap retention.

**Trust failure.** False alarms can make normal clarification adversarial. The output should ask the project lead to clarify scope, not label client misconduct or generate an invoice. Show uncertainty and authority explicitly. If users must reread every source to trust the result, time saved may disappear.

**Falsification test.** Blindly compare the current prototype, stateless retrieval/report, and a simple diff/checklist baseline on 10 real permissioned change episodes, including harmless elaboration and conflicting internal suggestions. Independent reviewer grades correct material change, false conflict, missing authority, action usefulness, and review time. Stop/pivot if structured ticket updates cover most events or users rarely act on the brief. Initial numerical thresholds should be chosen with users, not invented as validation results.

## Deep candidate B: support escalation continuity

**Buyer hypothesis.** A support lead inheriting a long, reopened case needs to understand what the customer actually tried and what remains unresolved. This is a more concrete purchase-adjacent job than generic summarization, but support tooling may already supply adequate summaries; the task must prove an advantage on changing or contradictory evidence.

**First value.** One ticket with an early agent suggestion, customer's attempted fix, and later failure. Produce attempted action versus suggested action, current reported symptom, contradicted assumption, missing diagnostic detail and cited handoff. No autonomous technical remedy.

**Existing slice reused.** Source chronology, before/after report revision, distinction between suggestions and confirmed actions, evidence replay. Missing: actual ticket/customer identity, internal notes vs customer statements, multiple agents, diagnostic artifact support and explicit timestamps for recurrence. Customer says “fixed” followed by “still failing” is a valuable challenge case, but phrase matching cannot itself establish durable resolution.

**Smallest honest demo.** Start with a closed-looking thread where agent recommended cache clearing but customer never confirmed doing so. Add “I tried it; the problem returned this morning.” Refresh and show that “recommended” becomes “attempted, ineffective/temporary according to customer,” with no invented root cause. This demonstrates why a mutable latest-state summary matters. Include one benign message that should not change issue status.

**Data access and distribution.** De-identified ticket exports supplied by a willing support team are preferable to integrating a live helpdesk first. Evaluate with the escalation recipient, not just the case author. A small helpdesk consultancy or existing team relationship could provide distribution; this is an untested access route. Data often contains credentials/customer details, so export selection and redaction impose real operational cost.

**Economics and adoption.** High case volume can support recurring value but also multiply inference and review costs. The key metric is handoff preparation/review minutes saved with no increase in misdiagnosis or repeated customer questions. Trigger only on escalation/reopening initially, not every message. Continuous automatic refresh on all messages is an attractive cost trap. Existing ticket summaries are a strong baseline; the proposed differentiator is verified distinction between attempted/suggested and latest/obsolete evidence.

**Trust failure.** A convincing wrong handoff causes engineers to skip diagnostic steps or repeat already-failed fixes. Every “tried,” “fixed,” and “recurred” claim needs supporting actor and time. Initial output stays advisory. For production, support evidence permissions must propagate into report visibility.

**Falsification test.** Collect paired pre/post-update cases including contradiction, genuine fix, recurrence, customer silence and irrelevant reply. Compare human handoff time and unsupported action claims against current workflow and stateless baseline. Reject the product if summaries already solve the problem or escalation recipients still need the full transcript for most cases.

## Cross-cutting business gates

- **Time to value:** one useful bounded case before integrations; measure user editing and verification time, not model output speed alone.
- **Distribution:** identify a reachable workflow owner with repeated pain. A category name and large market do not supply a channel.
- **Data access:** proof from permissioned actual cases is required; synthetic data only proves demo behavior.
- **Economics:** calculate observed requests/event, tokens/request, correction rate, events/customer and human-review time. No price or margin conclusion is supported yet.
- **Trust:** entity boundary, source authority and temporal conflict handling precede confident state labels.
- **Adoption:** a recurring report must arrive at an actual decision point; another dashboard can add work.
- **Platform fit:** distinguish event-driven usefulness from unique Reactor necessity. Run the same evidence and budget through stateful Reactor and stateless reporting before making a memory advantage claim.

## Attractive traps to deprioritize

A universal “AI that updates all your decisions”; campaign aggregate analytics built on top-k evidence; real-time call coaching on this latency profile; autonomous sales outreach; legal/contract enforcement; HR candidate selection; incident auto-remediation; complete replacement for CRM/project/helpdesk systems. Each adds expensive requirements unrelated to the already working kernel.

## Next loop task

Choose two candidates based on access to real examples, not the highest speculative score. Get one permissioned example for each; write a falsifiable workflow claim and define its simple baseline; evaluate the same change episode in the current report flow. Keep scope-change handling, support escalation, onboarding and sales as separate hypotheses until evidence distinguishes them. Save negative findings as well as attractive demos.
