# Lead challenge: avoid replacing a broad search with a longer idea list

Date: 2026-10-31. Research design and hypotheses; no new customer validation.

## Three different competitions

1. Hackathon: can a viewer understand a changed decision in two minutes, using an honest replay and a small adaptation of current code?
2. Business: does an identifiable buyer repeatedly lose enough time or money to adopt and pay for a change in workflow?
3. Reactive AI: does new information invalidate or refine an earlier state, and does persistent Reactor memory add anything over fresh retrieval plus explicit state?

A candidate winning one competition does not automatically win the others. Changing a recommendation is not evidence that a model remembers better. A persistent state ledger is not the same thing as hidden model history.

## Why another summary is a weak starting point

Current alternatives already support much of the obvious workflow. Notion documents meeting transcription, summaries and action items; Linear provides project health updates and chronological progress changes; Confluence provides a decision report. These primary sources demonstrate overlap, not independent evidence of buyer demand or proof that they lack other capabilities.

- https://www.notion.com/help/ai-meeting-notes
- https://linear.app/docs/initiative-and-project-updates
- https://support.atlassian.com/confluence-cloud/docs/insert-the-decision-report-macro/

The narrower hypothesis worth testing is: new evidence changes whether a prior decision remains usable, and the system identifies the specific affected decision plus the reason a person should review it. For example, a client asks for approval of bookings after a project was scoped around instant self-booking. The useful output is a possible scope conflict tied to the approved baseline, not a generic meeting recap or an automatic assertion that extra payment is owed.

## Angles and decisive questions

| Angle | Decisive question | Evidence required |
|---|---|---|
| Pain | Which recent mistake or repeated effort would disappear? | Concrete practitioner example with source artifacts |
| Buyer | Who can approve spending and what is their workaround? | Interview/pilot decision, not assumed persona |
| Timing | Must the update appear before a decision, or is on-demand enough? | Observed decision cadence and comparison |
| Semantic need | Is meaning/scope ambiguous enough to need AI? | Cases where rules fail, with ground truth |
| Memory need | Does persistent Reactor beat stateless recomputation? | Matched evidence/model comparison |
| Data | Can a first user supply the complete relevant history? | Accessible, permissioned and scoped examples |
| Authority | Which source can approve, supersede or retract a decision? | Explicit provenance and authority policy |
| Identity | Are people/projects/products separated reliably? | Same-name and cross-case counterexamples |
| Integration | Can value be delivered before building connectors? | Manual import pilot with measured effort |
| Adoption | Will the user inspect another surface? | In-workflow review and repeat usage |
| Economics | Does saved work exceed review and compute cost? | Measured useful-update rate, latency and review time |
| Competition | Is the exact problem already solved well enough? | Like-for-like task comparison, not feature omission |
| Failure | What happens when a relevant change is missed or falsely flagged? | Reviewer workflow, abstention and false-positive costs |
| Evaluation | Can someone reliably judge the right answer? | Independent annotations and disagreement handling |
| Demo | Can the before/after decision be understood immediately? | A short replay with unrelated and adversarial updates |

## Economics without invented prices

Track baseline preparation time, assisted review time, useful changes per week, irrelevant events, number of generated sections, correction calls, retrieval cost and end-to-end latency. Compute net time saved as baseline effort minus review effort minus workflow overhead. Any monetary estimate must expose the assumed labor rate and current verified API prices. Do not invent TAM, ARR potential or ROI from vendor copy. Start with one scoped case per refresh; cross-project fan-out can multiply cost and false alerts.

## Change detection is not authorization

A request can be tentative, rejected, accepted, superseded or withdrawn. The product needs to distinguish those states. A new message should not silently rewrite the approved baseline. Similarly, a workaround can fix one symptom while leaving another open. A decision-invalidation assistant should propose review, not declare every downstream decision wrong.

## Stop rules

Reject or narrow a candidate if a short checklist performs equally well; if the user must manually curate more context than the output saves; if source authority cannot be established; if no real repeated decision exists; or if the result is an attractive demo with no path to available data or a reachable buyer. Keep useful workflows even if the special Reactor advantage fails, but describe them honestly.
