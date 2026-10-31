# Pipeline research backlog

Updated 2026-10-31 after the whole-pipeline audit. Research remains separate from implementation: no application fixes have been applied by this audit.

The completed audit covers 25 Python files and 139 function definitions plus setup, configuration, dataset contracts and installed-package differences. The reviewed register contains 49 distinct items: 20 confirmed failure mechanisms, 22 limitations and 7 improvement hypotheses. The extra merged ID is retained only for traceability.

Canonical artifacts: [full audit](full-audit-2026-10-31/AUDIT.md), [independent review](full-audit-2026-10-31/review.md), [reviewed register](full-audit-2026-10-31/findings.json), [fix order and acceptance gates](full-audit-2026-10-31/implementation-roadmap.md).

| Order | Work package | IDs / completion gate | Status |
|---|---|---|---|
|1|Installed/source parity|RUN-06: deployed UI accepts current API and passes normal-import smoke tests|Proposed; observed failure reproduced|
|2|Import/schema/transaction consistency|ING-01/02/03/04/08/17: validate, roll back and reconcile safely|Proposed; targeted probes available|
|3|Public identity and source snapshot integrity|ING-20,RET-06/12/17,RUN-01/02/11: preserve public IDs, structured roles and immutable revisions|Proposed; corpus contract checked|
|4|Answer-bearing evidence retention|RET-01/02/03/04,ING-16: default-budget/real-tokenizer regressions and matched packing experiments|Proposed; loss mechanisms reproduced|
|5|Reliable output and recovery|RUN-03/04/05/07/08,RET-11/13: canonical scoring, durable retry and consistent traces|Proposed; UI and adapter probes available|
|6|Coverage and extraction evaluation|RET-05/07/08/09/14,RUN-09/10/12: frozen human-audited spans/state; call gold evaluation-only; latest-per-customer aggregation|Pending benchmark design|
|7|Performance and defensive checks|Remaining P2/P3 items in reviewed register: measure before adopting complexity|Pending controlled experiments|

Future cycles: first check source/deployment/data changes against the saved hashes and register; do not report unchanged known findings as new. Investigate remaining hardware/real-neural/remote behavior only within authorized resources. Compare alternative models only after stage attribution and matched quality/cost measurements; no model winner is established. Report meaningful new evidence, regressions or decisions required.

Completed checks: 88 source tests pass; installed UI reproduction fails as expected; independent groups reproduced synthetic import, concurrency, packing, provenance, cache, output and recovery mechanisms. No remote Reactor experiments or model-weight downloads. Source hashes stable at delivery. Earlier first-cycle backlog preserved in 2026-10-31/initial-backlog.md.

## Scheduled follow-up — 31 October, 09:00 Europe/Warsaw

Source check: all 25 audited Python files remain unchanged; no added/removed Python sources. The four known installed-package discrepancies are unchanged. Model revisions and data/dependency hashes are recorded in `heartbeat-2026-10-31-0900/snapshot.json`; the data hashes establish this cycle's identity rather than claiming comparison with an unavailable earlier full data baseline.

RET-01 public-only exposure check: 176 Salesgen sessions, 2,694 turns, 2,701 units, 403 chunks, and 23,777 history/time-eligible question/chunk opportunities. Two short late units meet structural prerequisites, but neither loses selected-unit text at default budgets; zero exposed opportunities found. A 337-token expanded context still preserves the selected unit because only later optional context is clipped. This is an exposure enumeration and extraction control, not actual neural retrieval or answer-accuracy evaluation; the prior synthetic RET-01 counterexample remains valid. No gold labels were supplied to this probe, no weights loaded, and no production edits made.

Researcher and independent overseer exchanged a method critique and reran the diagnostic. Detailed artifacts: `heartbeat-2026-10-31-0900/`. No new finding or user action; the 49-item reviewed register remains unchanged. Next bounded research topic: test retention on a fixed public long-conversation sample beyond Salesgen, or compare a research-only target-preserving packer against the existing counterexample set under identical budgets. Do not repeat this unchanged exposure enumeration without changed inputs.
