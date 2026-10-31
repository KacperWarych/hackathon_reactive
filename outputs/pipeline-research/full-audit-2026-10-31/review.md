# Independent whole-pipeline review — 2026-10-31

The full audit is complete for the inspected source/deployment snapshot. The strongest immediate actions are to restore installed/source API parity, make source/import/run provenance consistent, fix target-preserving evidence construction, and validate confirmations against structured speaker provenance. Model replacement is not supported by this audit.

The final register contains **50 reviewed IDs: 49 distinct accepted items and one merged item**. Among the 49 distinct items, **20 are confirmed bugs/failure mechanisms, 22 are design/input/assurance limitations, and 7 are improvement hypotheses**. A confirmed mechanism may be synthetic or conditional; these are **not 20 observed production incidents**. No recommended remedy was implemented or benchmarked, and no model superiority or current end-to-end accuracy is established.

Canonical structured output: [findings.json](findings.json). Detailed evidence, proposed fixes, and regression criteria are in [ING report](ing-report.md), [RET report](retrieval/report.md), and [RUN report](runtime/report.md). The coordinator's [implementation roadmap](implementation-roadmap.md) orders the shared dependencies.

## Roles and scope

- ING researcher: explicitly dispatched **GPT-6.1 Sol / high**; all 38 definitions in storage, manual ingestion, chunks, memory, index, models, and configuration.
- RET researcher: separate assigned researcher; all 35 definitions, including nested functions, in retrieval, evidence packing, investigation state, and decision validation.
- RUN coordinator: all 66 definitions in transport/evaluation/CLI/UI/app/scripts/vendor client and scorer, plus installed-package deltas.
- Independent overseer: explicitly dispatched **GPT-6 Astra / high**. Dispatch metadata was confirmed by the coordinator; no separate runtime model introspection is asserted. I independently read risk-bearing source, challenged findings, reran probes, reviewed all three final reports, and assigned the grades below.

The corrected AST inventory covers **25 Python files and 139 function definitions**: ING 38, RET 35, RUN 66. The initial quick inventory reported 136 because it omitted three functions nested inside control-flow blocks; the final inventory recursively traverses the full AST and includes them. All were read by the assigned reviewer/researcher. See [source-function-inventory.json](source-function-inventory.json), ING's function matrix, and RET's [function-coverage.json](retrieval/function-coverage.json). Setup scripts, dependency/lock configuration, README contracts, and installed package import behavior were also inspected. Source hash checks at completion found no changes from the full-audit snapshot.

This is inspection coverage, not a claim that every branch was executed. Real neural forward passes, GPU/resource stress, live Reactor transport, dependency vulnerability scanning, and representative end-to-end answer benchmarking were deliberately not run. No application code, installed package, credentials, or production database was modified. No `.env` secrets were read.

## Most important accepted mechanisms

1. **RUN-06:** installed `generate_report` lacks `decision_only`, while current `app.py:270` passes it. I independently reproduced the actual UI test failure under normal installed imports. This is a current deployment mismatch, not merely a hypothetical signature concern.
2. **ING-04, ING-01/03:** ingestion failure can leave pending question writes that a later schema initializer commits; reimports can desynchronize questions and gold; accepted missing turn IDs crash indexing. Import transaction and schema boundaries need repair before interpreting downstream evidence as a coherent dataset.
3. **RUN-01/02 and RET-17:** immutable result/evaluation identities omit material inputs; retrieval can also rank one revision then pack a different same-ID source after an interleaved edit. Preserve source snapshots throughout reads and exports rather than blindly recomputing or resending paid work.
4. **RET-01/02/03/04:** evidence can be lost after retrieval. The default 320-token context bug, lexical unit limit, cross-date text deduplication, and overlap deduplication are distinct mechanisms. RET-02/04 are classified as measured heuristic limitations rather than claiming that every approximate selection rule is a programming bug.
5. **RET-06:** an actual assistant-only structured turn containing a newline `user:` label passes the user-confirmation check after rendering. Structured original-role spans must remain authoritative.
6. **RUN-03/08:** citation numbers can satisfy numeric answer gold; a citation-only response can become an empty factual export marked complete. These are synthetic confirmed failures. The coordinator's historical scan found zero such matches/empty exports in the inspected 21 answered records (14 answerable scored records, not unique questions), so no historical prevalence is claimed.
7. **ING-20 + RET-05:** public sales data provides authoritative customer/call/product IDs, but ingestion discards them. The source contract counts latest state per customer, not calls. Preserving public identity is a prerequisite for a trustworthy aggregate route; evaluation-only outcome labels must remain outside retrieval.

## Independent verification

- Full active-source regression suite: **88 passed in 2.61 seconds**, using temporary data, offline flags, disabled bytecode writes, and no pytest cache. This is source validation, not deployed-artifact validation.
- Existing installed-import UI test: **1 failed in 0.27 seconds**, reproducing RUN-06 `unexpected keyword argument 'decision_only'` at `app.py:270`.
- New source UI-recovery demonstration: **1 passed in 0.42 seconds**; confirms the saved entry remains in SQLite but its retry control disappears in a fresh browser session (RUN-07).
- Independently reran ING synthetic probes, including separate-connection concurrency probes, and real-Qwen-tokenizer sentence-boundary controls. Results are saved beside the report, including `ing-overseer-final-rerun.log` and `ing-tokenizer-overseer-rerun.log`.
- Independently reran RET's final probe against active source, including real tokenizer checks, the corrected two-turn overlap fixture, role spoofing through actual extraction, candidate-admission and trace metadata controls, and RET-17 source interleaving. Results: `retrieval/overseer-final-rerun.log` and `retrieval/probe-results.json`.
- Independently reran RUN-01–05 and RUN-08 using fake transport/temp stores. RUN-08 confirmed `checked_status=answered`, `export_complete=true`, and empty exported answer. Results: `runtime/overseer-rerun.log`.
- Independently reran ING-20 against public input only: 176 sessions, 147 customer IDs, 29 customers with multiple calls, zero imported sessions retaining metadata; the probe confirms no evaluation files were read. See `ing20-overseer-rerun.log`.
- Verified active-file hash stability, final report IDs, and register counts. No real-device reliability, natural-data failure frequency, neural ranking quality, or remedy speedup was inferred from fake models or controlled timing delays.

## Concrete critique, responses, and dispositions

**ING:** I rejected the interpretation that all omitted histories must be deleted on reimport; the accepted ING-01 problem is inconsistent stored questions versus replaced annotations. I required ING-02 to use a supported dataset directory with a questions file, and ING-08 to use separate SQLite connections with a barrier. Both were verified. I downgraded mutable cached returns and a deliberately invalid custom vector producer (ING-11/14) to hypotheses: current callers do not mutate records, and production `Models.embed` already rejects NaNs. MPS allocation failure remains mock-only recovery coverage, unknown speaker labels remain grammar ambiguity, and cue matches remain hints. Fixed-temp concurrent writing is retained as a conditional concurrency limitation rather than claiming an observed unprotected production collision. The researcher accepted these critiques and revised the final report. ING-16 gained a real tokenizer/newline control; punctuation-space boundaries fail while newline boundaries work.

**RET:** My first truncation objection assumed adjacent 80/200/80-token segments would fit the default cap. The researcher identified the actual gap: changing `lo` to the previous turn also restores hundreds of omitted tokens in the current turn. The real-tokenizer counterexample and context-disabled control confirmed RET-01. I rejected the initial one-turn RET-04 fixture because it generated only one chunk; the corrected two-turn fixture generates 451/91-token chunks and loses the unique tail. I required RET-06 to originate from a real structured assistant turn, which now reproduces the provenance failure. RET-12 now preserves documented saved-snapshot reuse and targets false current-revision labeling. RET-09 does not claim its example requires another search; RET-10 is a tuning hypothesis, RET-13 acknowledges UI replay, RET-14 is an admission tradeoff, RET-15 is inclusive timing semantics, and RET-16 claims work amplification without speedup. All critiques were explicitly accepted.

**RUN:** The coordinator accepted that source-change detection must reject/relabel stale reuse rather than automatically resend paid requests. Citation leakage is local scorer integration, not a vendor regression; a citation-free negative control was added. Citation-repair weakening remains prompt-level evidence, not a demonstrated harmful live answer. The wrong-weekday discrepancy has unknown/likely limited prevalence. For RUN-07 I corrected the duplicate assertion: identical date/content entry creation already deduplicates; only changed date/content can create a different session. RUN-13 separates subprocess-envelope hardening from benchmark-snapshot selection. RUN-11 is classified as a readiness-design limitation rather than inventing an official-ID guarantee. These revisions appear in the final runtime report.

**Merge/rejections:** ING-15 is merged into RET-09 and is not counted twice. No final ID is wholly discarded; several stronger draft interpretations were rejected and the corresponding item survives only in its narrower supported class. RUN-13a/b are subitems of one ID and do not inflate the count. The optional environment/bootstrap provenance note is not an additional finding ID.

## Grading interpretation

Each dimension is 0–5, where 5 is strongest: **E** evidence for the diagnosed mechanism, **F** project fit, **B** expected benefit if fixed/tested, **I** implementation feasibility. Grades are independent reviewer judgments. High E for a performance mechanism does not mean its speedup was measured; B is a hypothesis. Severity reflects consequence under the stated trigger and is not a frequency estimate. The consolidated register is the final independent grading; group-report priorities are provisional and can differ. Detailed fixes and validation are in the group reports and each register row.

| ID | Classification | Severity | E / F / B / I | Disposition |
|---|---|---|---|---|
| ING-01 | confirmed bug | P2 | 5 / 5 / 4 / 4 | accepted |
| ING-02 | confirmed bug | P2 | 5 / 5 / 3 / 4 | accepted |
| ING-03 | confirmed bug | P2 | 5 / 5 / 4 / 4 | accepted |
| ING-04 | confirmed bug | P1 | 5 / 5 / 5 / 4 | accepted |
| ING-05 | limitation | P3 | 4 / 4 / 3 / 4 | accepted |
| ING-06 | limitation | P3 | 5 / 4 / 3 / 5 | accepted |
| ING-07 | limitation | P3 | 5 / 4 / 4 / 5 | accepted |
| ING-08 | confirmed bug | P2 | 5 / 5 / 4 / 4 | accepted |
| ING-09 | confirmed bug | P3 | 4 / 4 / 3 / 4 | accepted |
| ING-10 | limitation | P3 | 3 / 4 / 3 / 3 | accepted |
| ING-11 | hypothesis | P3 | 3 / 3 / 2 / 4 | accepted |
| ING-12 | limitation | P3 | 4 / 4 / 3 / 5 | accepted |
| ING-13 | hypothesis | P2 | 5 / 5 / 3 / 5 | accepted |
| ING-14 | hypothesis | P3 | 3 / 3 / 2 / 4 | accepted |
| ING-15 | limitation | P3 | 5 / 4 / 3 / 3 | merged into RET-09 |
| ING-16 | confirmed bug | P2 | 5 / 5 / 4 / 4 | accepted |
| ING-17 | limitation | P3 | 5 / 4 / 3 / 4 | accepted |
| ING-18 | hypothesis | P3 | 5 / 4 / 3 / 4 | accepted |
| ING-19 | limitation | P3 | 4 / 4 / 3 / 3 | accepted |
| ING-20 | limitation | P1 | 5 / 5 / 5 / 4 | accepted |
| RET-01 | confirmed bug | P1 | 5 / 5 / 5 / 4 | accepted |
| RET-02 | limitation | P1 | 5 / 5 / 5 / 4 | accepted |
| RET-03 | confirmed bug | P1 | 5 / 5 / 4 / 4 | accepted |
| RET-04 | limitation | P2 | 5 / 5 / 4 / 4 | accepted |
| RET-05 | limitation | P2 | 5 / 5 / 4 / 3 | accepted |
| RET-06 | confirmed bug | P1 | 5 / 5 / 5 / 3 | accepted |
| RET-07 | limitation | P2 | 5 / 5 / 4 / 4 | accepted |
| RET-08 | limitation | P2 | 5 / 5 / 4 / 3 | accepted |
| RET-09 | limitation | P3 | 4 / 4 / 3 / 3 | accepted |
| RET-10 | hypothesis | P3 | 5 / 4 / 3 / 4 | accepted |
| RET-11 | confirmed bug | P2 | 5 / 5 / 4 / 5 | accepted |
| RET-12 | confirmed bug | P2 | 5 / 5 / 4 / 4 | accepted |
| RET-13 | limitation | P3 | 4 / 3 / 2 / 4 | accepted |
| RET-14 | limitation | P2 | 5 / 5 / 3 / 3 | accepted |
| RET-15 | limitation | P3 | 5 / 4 / 2 / 5 | accepted |
| RET-16 | hypothesis | P2 | 5 / 5 / 4 / 3 | accepted |
| RET-17 | confirmed bug | P1 | 5 / 5 / 5 / 4 | accepted |
| RUN-01 | confirmed bug | P1 | 5 / 5 / 5 / 4 | accepted |
| RUN-02 | confirmed bug | P1 | 5 / 5 / 5 / 4 | accepted |
| RUN-03 | confirmed bug | P1 | 5 / 5 / 4 / 5 | accepted |
| RUN-04 | limitation | P2 | 5 / 5 / 4 / 5 | accepted |
| RUN-05 | confirmed bug | P3 | 5 / 4 / 2 / 5 | accepted |
| RUN-06 | confirmed bug | P1 | 5 / 5 / 5 / 5 | accepted |
| RUN-07 | confirmed bug | P2 | 5 / 5 / 4 / 4 | accepted |
| RUN-08 | confirmed bug | P2 | 5 / 5 / 4 / 5 | accepted |
| RUN-09 | limitation | P2 | 4 / 5 / 4 / 4 | accepted |
| RUN-10 | limitation | P2 | 5 / 5 / 5 / 4 | accepted |
| RUN-11 | limitation | P2 | 5 / 5 / 4 / 4 | accepted |
| RUN-12 | limitation | P2 | 4 / 5 / 4 / 4 | accepted |
| RUN-13 | hypothesis | P3 | 3 / 4 / 3 / 4 | accepted |

## Unresolved evidence and next step

The next implementation cycle should first repair the installed artifact and data/snapshot integrity boundaries, then rerun only the affected regression probes against both source and installed imports. Add a small frozen assertion/state set and use the existing call-level gold only as evaluation labels, never retrieval inputs. Evaluate packing variants with fixed candidate lists and budgets before changing retrieval models. Preserve historical snapshots and explicitly measure cold/warm cache conditions. No benchmark numbers in this audit demonstrate an implemented improvement.
