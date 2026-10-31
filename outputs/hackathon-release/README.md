# A–F implementation acceptance — 31 October 2026

Implemented the bounded individual-history → entry → revised-report demo, including ticket D import hardening. Model and dependency locks are unchanged. Independent agent review found and then verified fixes for plain-fact duplicate recency and stale answer evaluation; no remaining actionable findings in its scoped review.

| Ticket | Implementation and diagnostic evidence |
|---|---|
| A | Frozen, regular package installed in this workspace; every package Python file matches source. Installed UI tests exercise decision build/recovery and report-entry flow. Fresh Streamlit process returned HTTP 200 `ok` on localhost:8511 and was stopped after the smoke check. |
| B | Selected original user-turn spans carry IDs, roles, source hashes and offsets. Spoofed newline speaker labels, excluded quotes, negative/speculative Polish confirmations are rejected. Distinct source occurrences remain eligible; temporal identical wording selects the newer date, including plain facts without update cues. Target-first packing and unique overlap tails have synthetic regressions. |
| C | One citation-content utility is used for completion checks, local answer matching and export. Citation-only and punctuation-only residue fail; factual numbers survive. Vendor scoring files are unchanged. |
| D | Full import validation precedes writes. SQL, gold publication and commit-failure tests prove rollback/cleanup, including Memory initialization afterward and second-connection visibility. Existing gold changes require a fresh split. |
| E | Complete eligible-source fingerprints detect additions, deletions, dates and same-ID edits. Decisions cannot restamp historical evidence. Resume/export/evaluation reject stale output; UI labels historical reports and refresh retrieves current evidence. Reentrant process lock serializes service operations. Future or other-history changes intentionally do not invalidate the snapshot. |
| F | Reusable `scripts/release_gate.py` runs source and normally installed suites, lint and parity checks in a fresh namespace. JSON records lock/model/code/fixture/package identities and elapsed times. Logs are retained beside it. |

The deterministic acceptance inputs are frozen in the hashed test files. They cover:

1. Normal app startup, decision build, report-entry controls (`test_investigation_ui.py`, `test_report_entry_ui.py`).
2. Exact and paraphrased questions retain the supporting assertion in evidence supplied to fake transport (`test_exact_and_paraphrased_questions_send_supporting_assertion`).
3. Latest-state provenance for repeated wording, including plain-price facts (`test_long_memory.py`).
4. Assistant role spoofing versus genuine user confirmation (`test_decision.py`, `test_long_memory.py`).
5. Polish positive, negative and speculative acceptance (`test_decision.py`).
6. Empty evidence and explicit abstention (`test_unanswerable_revision_is_completed_abstention`).
7. Citation-only rejection and numeric answer scoring/export (`test_reactor.py`).
8. Malformed import rollback and actual entry/index/report refresh with fake transport (`test_dataset.py`, `test_report_entry_ui.py`).
9. Every source mutation, historical snapshot preservation, scoped nonchanges, and serialized nested services (`test_snapshot.py`, `test_investigations.py`).
10. Export completeness and canonical content; aggregate prompt complete-coverage constraint (`test_reactor.py`, `test_campaign_count_prompt_requires_complete_coverage`).

Additional cases beyond audit reproductions include future/other-history non-invalidation, unrelated newer wording preserving relevance, and deferred SQL commit failure after gold publication.

No real Reactor request, neural model quality test, real-tokenizer sentence-boundary change, or production-data rehearsal was performed. Timing is automated test execution, not service latency. Fake retrieval diagnostics do not establish answer accuracy. Campaign-wide aggregation, durable reconnect recovery and authoritative official-submission ID manifests remain deferred. Existing aggregate prompts require recorded totals or complete coverage and otherwise insufficient evidence; this demo does not claim campaign analytics.

Import/gold cleanup is exception-safe, not a cross-filesystem crash-atomic transaction. Operation serialization is one-process only. Stop separate CLI writers during the demo. Historical reports without the new provenance or snapshot fields require an explicit refresh.

Final gate: [20261031T083717Z-741783be](20261031T083717Z-741783be/release.json). Source and installed suites each passed **156 tests**; lint and source/package parity passed. Recorded wall times: source 3.721s, installed 3.471s, lint 0.055s.
