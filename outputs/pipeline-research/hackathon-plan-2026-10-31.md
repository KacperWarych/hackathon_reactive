# Hackathon implementation plan — 31 October 2026

## Recommendation and checked status

Keep BM25, Qwen3-Embedding-0.6B, RRF, Qwen3-Reranker-0.6B and Reactor. Fix execution and evidence correctness before trying another model. No matched project evaluation establishes a better replacement.

All 25 audited Python files still match the full-audit fingerprints. The installed package still differs in decision.py, investigation_ui.py and investigations.py and lacks report_entry_ui.py. I reran the installed-package UI test: Build decision view still crashes with `generate_report() got an unexpected keyword argument 'decision_only'`. The prior source-only suite passed 88 tests; that is historical evidence, not a fresh full-suite run. Application code was not modified for this plan.

Planning assumption: one-machine hackathon demo, existing dataset, a customer-history question followed by a new entry and a revised answer. Estimates below are engineering estimates including focused tests, not promises or measured benefits. Do not attempt all 49 audit findings before presenting.

## Ordered implementation tickets

Paths below are relative to `/Users/kacperwarych/Desktop/hackathon reactive ai`. Each ticket should be a separate reviewable change. Dependencies: A first; B/C/D can be developed separately; E after evidence changes; F on the final installed package.

| Order | Work and minimal implementation | Files / audit IDs | Acceptance gate | Estimate |
|---|---|---|---|---|
| A — blocker | Reinstall the frozen package, restart the app, verify import location and source/package parity. Repeat after final changes. | README install procedure; RUN-06 | Installed `test_build_decision_view_uses_one_request_and_can_recover` passes; new report-entry flow imports and works. | 20–40 min |
| B — evidence | Preserve original turn role, ID and source offsets with evidence. Validate confirmation quotes against actual user-turn spans, never speaker labels parsed from text. Keep identical wording from different sessions/dates eligible; collapse only true duplicates from the same source occurrence. | `src/decision_memory/evidence.py`, `decision.py`, `retrieval.py`; RET-06, RET-03 | Assistant text containing a newline `user:` cannot confirm anything. A genuine user quote still works. Repeated wording across dates retains the newer occurrence for a latest-state question. | 2–4 h |
| C — output | Centralize citation removal for answer-content validation, local matching and export. Reject citation-only/empty answers before marking completion. Keep official scoring semantics intact; change the adapter/input preparation, not vendor scoring rules. | `reactor.py`, `evaluation.py`, export call sites; RUN-03, RUN-08 | `[E1]` alone is invalid and cannot match numeric gold `1`; `1 [E2]` remains answer `1`; normal cited answers and abstentions retain intended behavior. | 45–90 min |
| D — only if importing in the demo | Validate required turn IDs, uniqueness, roles, dates and references before writes. For the demo-sized import, stage/parse first and wrap SQL publication in one rollback boundary. Remove nested connection contexts that commit midway through the import. Do not replace gold while validation is incomplete; SQLite and a filesystem gold file are not one atomic transaction, so stage and publish to a fresh split and keep it nonselectable/incomplete until all outputs are published and discard it on failure. Use a fresh demo split to avoid needing comprehensive merge/replace semantics. | `store.py`; ING-03, ING-04 | A malformed final row changes neither questions nor sessions; subsequent Memory initialization cannot commit failed-import leftovers. Missing turn IDs fail at import with an actionable error. Existing gold remains unchanged after validation failure. | 1–2 h |
| E — update integrity | Fingerprint all eligible (session_id, date, content_hash) tuples to detect stale answer/report reuse, including additions/deletions/date changes; reject reuse as current data and require refresh. Preserve the old snapshot identity when generating a decision from old evidence. For the demo, run import/index/query sequentially in one process; guard operations, not just button appearance. | `reactor.py`, `investigations.py`, entry UI/index entry points; RUN-01, RET-12, mitigation for ING-08/RET-17 | Add a new eligible entry, delete a session, change its date, or edit content under the same session ID: old output is explicitly historical and refresh uses new evidence. Decision-only generation does not restamp old evidence as current. No overlapping index/query in the demo workflow. | 1–2 h |
| F — release gate | Freeze a small diagnostic set, run existing source tests and focused installed-package tests, then rehearse the complete UI sequence using fake transport first. Record code/model/data identities. Use a fresh evaluation/run namespace so old cached scores cannot masquerade as new results. | tests + demo checklist; RUN-02, RUN-09, RUN-10 | Every demonstrated feature passes its cases below. Report actual outcomes and timing; do not present retrieval recall as answer accuracy. | 1–2 h |

For the assumed live-entry/state-revision demo, A/B/C/E/F are roughly **5–10 engineering hours** before contingency. D adds 1–2 hours only if the demo imports external files; a fixed preingested corpus does not require importer hardening before presentation. If only four hours remain, do A, C, F and the relevant portion of B; use a prevalidated frozen corpus, omit live ingestion/updates, and hide decision resolutions unless structured-role validation passes. Do not present disabled features as completed.

The documented installation command, from the project directory, is:

```sh
UV_CACHE_DIR=.cache/uv UV_PYTHON_INSTALL_DIR=.python .tools/uv sync --frozen --no-editable --reinstall-package decision-memory
```

Restart Streamlit afterward. Testing with `PYTHONPATH=src` alone does not verify the package the normal app uses.

## Add only when required by the demo

**Polish confirmations (RET-07):** if showing resolution states over the Polish Salesgen calls, this is part of ticket B, not optional polish. Add narrowly scoped Polish/English acceptance patterns with negation/speculation tests; accept a supported positive phrase, reject `nie potwierdzam`, and retain ambiguous cases as unresolved. Structured quote provenance does not prove that a quote resolves the same concern. Keep the quote and context visible rather than claiming semantic verification. Allow another 1–2 hours.

**Evidence packing (RET-01/02/04/ING-16):** next quality improvement after the core. Preserve the selected target unit before adding bounded context; retain unique overlap tails; broaden the hard top-two unit candidate gate only under unchanged final budgets. Add the exact synthetic clipping, paraphrase and unique-tail regressions from the audit. Real tokenizer tests are required for sentence-boundary changes, with a `memory.SCHEME` bump and affected memory-record rebuild. Bump `chunk_scheme` and reindex only if chunk generation or embedding inputs also change. Start with target-first packing (1–2 hours), then make further changes only if diagnostic cases fail. The public-corpus follow-up found zero selected-unit clipping in its scoped enumeration; it did not disprove the synthetic bug or measure answer-quality gains.

**Campaign counts / customer grouping (ING-20, RET-05):** required if the pitch promises totals or customer-level analytics. Preserve public customer_id, call_id, product_id and date. Route totals through complete eligible-population enumeration and explicit latest-per-customer rules, with unknown outcomes reported separately. Six retrieved excerpts cannot establish a campaign total. Gold outcome labels must stay evaluation-only. Test repeated customers, cutoff dates, ties, missing identity, contradictory outcomes and unknown classifications against a manually checked fixture. Budget this as a separate feature, roughly 1–2 days, not a cap increase. Otherwise label aggregate questions unsupported and demonstrate source-backed individual-history answers; do not imply reliable customer filtering without IDs.

**Reconnect recovery (RUN-07):** if a reconnect is part of the demo, persist a minimal pending-entry/index/refresh record and reload it. Test interruption after save and after indexing, proving no duplicate entry or blind request resend. Otherwise keep the rehearsed flow short and provide an explicit reopen/refresh path; a browser session is not durable job storage.

**Official submission/export:** if required, add RUN-11 exact expected question-ID set validation, RUN-04 constrained citation-repair prompts and RUN-12 explicit completion counts. Verify exported answers after citation removal. Never label a partial run complete. Preserve the original evidence constraints during repair and account for repair message size.

## Demo acceptance set

Use temporary data and a fake Reactor adapter for deterministic automated tests. A later real-service rehearsal needs its own latency/cost budget; this plan does not claim one was run.

1. App starts through the normal installed import; build a decision view and open a report entry.
2. Exact fact and paraphrased question both retain the supporting assertion in the evidence actually sent.
3. Same assertion on two dates answers a latest-state query with correct provenance.
4. Assistant-authored `user:` text cannot become customer confirmation; real user confirmation can.
5. Polish positive, negative and speculative confirmations behave conservatively when enabled.
6. No supporting evidence produces an explicit unknown/abstention, not a fabricated resolution.
7. Citation-only response is rejected; a numeric answer is not accidentally supplied by a citation label.
8. Malformed import rolls back; a valid new entry indexes and refreshes the report when enabled.
9. Editing an existing source cannot reuse an old answer as current; old report evidence retains its snapshot identity.
10. Export contains nonempty validated answers and accurate completion status; unsupported aggregate requests are declined or use the separately tested aggregate route.

Save the input cases and observed results with the final source/data/model fingerprints. Include at least one new case beyond the audit reproductions to avoid merely fitting the fixes to known examples.

## Defer beyond the hackathon

Model swaps and broad ablation studies; vector database migration; generalized distributed locking/worker queues; full cache lineage architecture; cache garbage collection; exhaustive parser grammar; multi-device fallback engineering; performance rewrites without observed demo latency problems; semantic entailment/state-resolution research. Keep existing models/config frozen during rehearsal.

Fresh demo splits and sequential operations are scoped workarounds, not fixes for arbitrary reimports or concurrent users. If judges need those behaviors, promote the corresponding audit tickets rather than silently relying on the workaround.

## Agent ownership and review

Use GPT-6.1 Sol/high for bounded implementation tickets and regression cases; GPT-6 Astra/high independently checks the proposed diff and acceptance evidence. The coordinator integrates one ticket at a time and runs installed-package gates. Evidence/decision changes share files, so give B and its optional packing follow-up one owner. This role allocation follows the requested research setup; it is not a measured claim that either model is superior on this project.

## Evidence links

- [Current fix check and hashes](hackathon-fix-check-2026-10-31.json)
- [Full independently reviewed audit](full-audit-2026-10-31/AUDIT.md)
- [Finding register and grades](full-audit-2026-10-31/findings.json)
- [Scoped public-corpus follow-up](heartbeat-2026-10-31-0900/ret01-public-report.md)
- [Independent hackathon scope review](hackathon-plan-review-2026-10-31.md)
