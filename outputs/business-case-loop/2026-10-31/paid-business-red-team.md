# Paid-business red team — 31 October 2026

## Investment decision today

**Do not fund a domain product build yet. Fund a bounded customer-discovery and paid-concierge test.** None of agency scope triage, support handoff, or sales briefs currently has verified buyer access, observed repeated use, or payment evidence in these reports. The technically strongest replay is not the most investable business. Reuse of existing code lowers one development cost; it does not create demand or distribution.

Conditional discovery order: agency scope packet first if a reachable owner can provide an approved brief and recent change history; support second if a lead can provide representative handoffs and their incumbent output; sales only if sellers can show a recurring preparation problem beyond what CRM notes already solve. This ordering is an execution hypothesis, not a market-size or willingness-to-pay ranking. Do not treat “accessible agency owner” as an established fact.

This report reviews `broad-workflows.md`, `lead-challenge.md`, `initial-synthesis.md`, and the companion reactive/implementation audits. No outreach, interviews, payments, customer data acquisition, new model benchmark, or app edits were performed. Proposed numerical thresholds and test prices below are experiment design choices, not market observations.

## Why nobody might pay

| Candidate | Skeptical buyer's argument | Strongest simple substitute | Fatal bottleneck to investigate |
|---|---|---|---|
| Agency scope triage | “I already know that request is extra. I accept it because arguing costs more than doing it. Another alert doesn't help me.” | Approved scope checklist + shared change log + PM asks for estimate before task starts; general LLM compares brief and request | Owner noticed change but chose not to charge; missing authority/approved baseline; no repeated need for a prepared decision packet |
| Support handoff | “My helpdesk already summarizes the ticket inside the inbox. Your report makes agents copy logs elsewhere and verify everything again.” | Existing escalation template/checklist; deployed helpdesk copilot; whole-thread summary with identical evidence | No incremental improvement over actual tool; access/integration overhead exceeds minutes saved; receiving agent still rereads entire thread |
| Sales brief | “My rep made the last call and remembers it. The latest note already says budget. A summary cannot make the customer buy.” | CRM latest note + next-step field + pre-call checklist; existing call assistant; on-demand whole-thread analysis | Rare context-loss incidents; no meaningful next-action change; exports and review displace selling time |

The agency killer question is: **“Did you fail to notice the scope change, or did you notice it and choose not to charge?”** A detection product does not solve the latter. A source-backed packet might reduce preparation effort for an explicit scope discussion, but that is a different proposition to test. Do not promise recovered revenue, contractual entitlement, or improved client negotiation from a flagged request.

Existing alternatives have real overlap. Productive documents scope/budget workflows; Intercom documents history/notes in Copilot; these primary pages establish baseline features, not their effectiveness or a market gap. Compare against the buyer's actual configuration. [Productive scope workflow](https://productive.io/blog/scope-creep-in-project-management/), [Productive budget scenarios](https://help.productive.io/en/articles/10296200-managing-and-applying-scenarios-to-deals-and-budgets), [Intercom Copilot FAQ](https://www.intercom.com/help/en/articles/9121381-copilot-faqs). The lead supplied an anecdotal claim that an agency already uses a project tracker plus AI comparison and that relationship concerns matter; treat it as a question generator, not prevalence evidence or independent validation.

## Risks a positive demo conceals

**Frequency:** Five scope changes on one troubled project do not imply a weekly workflow across the agency. A support organization may have many tickets but very few complex handoffs. A sales team may have calls but few ownership transfers or genuinely forgotten constraints. Count qualifying decisions per month over the last 60–90 days, not raw messages/calls/tickets.

**Adoption:** “I would use this” is weak. Users may like a polished artifact but decline a separate dashboard. Manual uploads can test value, but measure their effort. If a pilot works only because a founder finds, cleans and explains every source, it has shown a service, not self-serve software. Record that distinction instead of hiding founder labor.

**Data:** Agency approval often lives in verbal conversations; support context may live in logs unavailable to the tool; CRM notes may omit what the rep remembers. No model repairs absent authority or incomplete records. The data owner must identify permitted inputs and a bounded case. Public issue threads and synthetic sales calls are mechanics tests, not representative commercial evidence.

**Trust:** A credible-looking false claim about scope approval, issue resolution, or a customer's commitment can cost more than several minutes saved. Citations only show that text exists; the app does not prove semantic scope or approval authority. The pilot produces reviewable internal drafts. User acceptance cannot be counted merely because the user stopped checking them.

**Economics:** Per-event regeneration, two generated report sections, corrections, retries, evidence review and onboarding may make costs scale faster than useful updates. Alert count is not output value. A system that generates 50 reports to find one actionable change must cost and measure all 50.

**Buying process:** An interested frontline user might have no authority to approve a new processor or subscription. An interested manager might not supply data or allocate reviewer time. Ask who can approve a short paid test and what must happen before they can sign; do not assume owner-led means instant adoption.

## Discovery interview: 25 minutes, evidence before pitch

Recruit only after explicit user authorization for outreach. In this task, prepare questions and do not contact anyone. Aim for five qualified participants per candidate initially; “qualified” means responsibility for the named decision and at least one recent example. Ask permission to review de-identified artifacts, not indiscriminate inbox access.

1. “Walk me through the last time you [handled a changed client request / received a difficult support escalation / prepared a follow-up after new customer information]. What happened, when, and who made the decision?”
2. “Show me what you looked at and the note or task you produced. Which parts took time? What was missing?” Observe the actual workflow if permitted; separate recalled estimates from timed work.
3. “How often did this happen in the last month? Show the cases/calendar/queue you use to count.” Record zero and uncertain counts honestly.
4. “What went wrong last time? What observable consequence followed? Was that consequence caused by missing information, noticing it too late, or a deliberate decision?” Do not lead with suggested lost revenue.
5. “What did your existing tool or template do? Have you tried changing that setup? Why was it insufficient?” Ask to see incumbent output on the same case.
6. “Who had authority to approve the scope/fix/next action? Where is that recorded?” Mark missing authority, not model failure.
7. “If this were prepared for you tomorrow, where would you actually review it? What would you still need to verify?” A request for a new integration is an adoption cost, not automatic demand.
8. “What have you spent—money or staff time—to solve this already? Who approves a paid test?” Record actual precedent, not hypothetical maximum willingness-to-pay.
9. Only now show a short candidate output using supplied or explicitly synthetic data. Ask the participant to perform the real decision task and explain errors. Do not ask whether they “like” it.
10. “Will you supply two representative cases by an agreed date, designate a reviewer, and use the output for the next qualifying live decision?” Record the commitment and whether it happens. Discuss a specific paid pilot only after scoped data and safety expectations are clear.

Candidate-specific probes:

- **Agency:** “Which changes did you notice and absorb deliberately? Would a clearer source-backed packet have changed anything? Who prepares the estimate? How often is the baseline disputed or verbal?” A packet does not replace estimation or negotiation.
- **Support:** “Show a handoff where the next agent repeated an already-failed step. Did the incumbent have the full thread? How often does that exact failure recur? Which diagnostic omissions matter?” Test the configured incumbent, not a straw-man summary.
- **Sales:** “Show a follow-up harmed by a stale concern or forgotten commitment. Did another rep take over? Why didn't the latest CRM note solve it? What exact next question would have changed?” Do not claim better close rates from a better brief.

## Behavioral evidence ladder

| Evidence | What it supports | What it does not support |
|---|---|---|
| Positive reaction / survey intent | Output is understandable or appealing | Adoption, paid demand, time saved |
| Recent artifact-backed problem | A real problem happened | Frequency, solvability, buying intent |
| Representative data supplied + reviewer assigned | Ability and some willingness to test | Sustained usage or payment |
| Output used on next qualifying decision without repeated founder chasing | Workflow relevance | Net benefit or durable product fit |
| Measured improvement over current alternative | Local incremental value | Population ROI or scalability |
| Approved and paid scoped pilot | Willingness to pay for that scope/service | Willingness to pay for unsupported self-serve software |
| Voluntary second paid period on new cases | Stronger recurring value signal | Broad market fit |

Do not count a promised referral, unsigned intent letter, or free pilot as cash demand. Keep refunds, discounts, founder relationships and bespoke work visible in the evidence ledger.

## A concrete paid-concierge pilot to test

**Offer under test, aligned with the lead's agency offer:** a two-week internal decision-brief service for one project and at most five decision episodes. It produces cited internal packets and a short record of changed assumptions, unresolved questions and human corrections, with human source verification and a ledger. Delivery happens in the participant's agreed existing workflow. No automatic external messages, status changes, billing decisions, diagnosis or customer contact. Support and sales variants need their own equally bounded case scope before offering; they are not included free in the agency pilot.

**Candidate test price:** PLN 750 for the bounded two-week pilot, proposed solely as a falsifiable offer amount, not a claim about market price or value. Confirm delivery capacity and projected cost before quoting; if the budget cannot cover promised scope, reduce scope or revise the offer openly. Do not subsidize unlimited custom integrations to manufacture acceptance. The price and deliverables should be fixed before presenting the offer; record later changes rather than count them as equivalent wins. This research task authorizes neither invoicing nor collecting payment.

**Price plausibility challenge:** five episodes make the effective test price PLN 150 per episode if all are used, and more per episode if fewer qualify. On a pure time-saving proposition, the required net hours saved per episode are `150 / buyer's hourly value in PLN`. At an explicitly hypothetical PLN 150/hour that means one net hour per episode; at hypothetical PLN 300/hour it means 30 minutes. These are arithmetic examples, not observed labor rates or ROI. If packets save only five minutes, this price likely needs a separately demonstrated benefit, such as reduced decision-packet preparation/rework across the project; do not replace missing evidence with claimed recovered revenue. Human verification may also consume the provider's entire margin. Reject or re-scope an offer whose measured economics do not work.

**Authority gap:** human source checking does not create an approved baseline or turn a request into authorization. If the owner cannot identify who approved the relevant version, the packet must mark that unknown and ask for clarification. An owner who knowingly absorbs extras has not demonstrated demand for detection; test whether preparing a defensible discussion packet is itself repeated, costly work they will pay to reduce.

**Before the offer:** use one or two retrospective, permissioned cases to establish that the output is reviewable and technically feasible. Avoid an open-ended free trial. If prospective customers cannot share even this minimal material, stop rather than build a connector on speculation.

**Pilot method:**

1. Record baseline workflow and actual alternative, elapsed prep/review time, corrections and source availability. Define a qualifying event and a useful decision packet before testing.
2. Alternate comparable cases between the current workflow and assisted workflow; avoid always assigning easy cases to the product. For agency projects, match task complexity rather than replaying the same decision after the user already learned the answer.
3. Have the named reviewer accept, edit or reject each claim and record the concrete next action. Keep disputed cases as disputed, not model wins.
4. Count all participant effort: obtaining/de-identifying inputs, upload, checking sources, correcting errors and using the report. Track provider effort and inference cost separately.
5. Hold one midpoint check for failures; do not silently change the target metric or add concierge labor without recording it.
6. At the end, request a concrete second paid period on new cases at the agreed sustainable scope. A polite satisfaction score is not the continuation metric.

Primary measure is **net participant time saved on a correctly completed decision task**. Secondary measures: useful packets / delivered packets, unprompted reuse, decisions changed with evidence, false claims, and review burden. Revenue recovered or tickets closed faster may be explored only with observed causality limits; neither is a required promise of this pilot.

## Proposed kill and continuation gates

These are small-sample managerial gates, not estimates of market prevalence or production reliability. Freeze them before starting a candidate's discovery cohort; record deviations explicitly.

| Stage | Continue only if | Kill, narrow, or pause if |
|---|---|---|
| Five qualified interviews | At least three show a recent artifact-backed recurring problem, and at least two provide usable cases with a reviewer within seven agreed days | Praise without evidence; problem caused mainly by deliberate choice or missing authority; checklist/configuration resolves it |
| Minimal retrospective test | At least two reviewers identify a concrete useful decision or reduction in prep effort beyond their actual alternative | Output only restates facts; source curation costs more than saved work; incumbent is equal or better |
| First three concrete offers to qualified buyers | At least one paid acceptance, subject to explicitly documented procurement timing | Zero accepts and no specific dated procurement path; repeated demands for an entirely different product. Do not endlessly relabel nonbuyers as unqualified |
| Two-week pilot | At least 70% of available qualifying events are actually used/reviewed; at least 25% median net participant time reduction; no worse judged decision quality | Low event frequency prevents a usable comparison; reminders/manually curated data drive all usage; negative net time benefit |
| Trust gate throughout | No unsupported authorization/full resolution, cross-case attribution or concealed incomplete evidence in delivered claims | A critical error pauses delivery and triggers review; do not average it away with correct trivial cases |
| Recurrence | At least one of the first two completed paid pilots buys a second period for new cases with a named operator and sustainable scope | Pilot valued only as one-off consulting or discounted founder service; no repeat budget |

The paid-offer gate tests willingness to pay at the proposed scope/price. A failure does not prove the entire market absent; it does prohibit declaring validation and directs a specific revision to buyer, job, channel or price. Low event volume may support a one-time report service, but undermines a recurring reactive product.

## Unit economics and Reactor's role

For each pilot record:

`participant net minutes saved = baseline task minutes − assisted review/task minutes − input preparation/upload minutes`

`provider contribution = collected revenue − inference/retrieval/storage costs − direct provider labor cost − paid integration/support costs`

Value the provider's time explicitly; “founder time is free” can hide an unviable service. Report onboarding separately and show plausible repeat-period cost. Do not convert minutes to currency without the buyer's own loaded labor-rate assumption. Do not price API calls using unverified numbers; measure actual billed usage or label it unknown.

Buyers purchase a reliable decision aid, not Reactor memory. Begin the workflow test with whichever implementation delivers honestly at bounded cost. Separately compare: current practice; whole-context/on-demand analysis; structured state plus event-triggered stateless generation; persistent Reactor. Match data access, model where possible and output requirements. Count answer and structured-decision calls, corrections and retries.

Retain Reactor only if it improves meaningful correctness or lowers complete workflow cost at comparable reliability. If it only makes the architecture more impressive, remove it from the sales proposition. If updates are only needed at handoff/planning time, deliver on demand. “Reactive AI” is an implementation hypothesis whose failure need not kill an otherwise useful business, and whose success does not establish one.

## Direct challenges sent to peer agents

- Market/workflow researcher: distinguish missed scope from deliberately absorbed work; demand actual incumbent comparison and behavioral evidence rather than pain-category popularity.
- Implementation reviewer: include source preparation, review, corrections and founder labor; a concierge test must not conceal integration costs or become months of engineering before payment evidence.
- Lead: do not let the recurring research loop substitute for customer contact. Once a bounded offer and test exist, the next uncertainty is access to real buyers and data. Further idea expansion cannot settle it.
