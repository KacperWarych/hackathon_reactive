# Runtime, evaluation, UI, and delivery audit

Research performed by lead coordinator; independent review requested from `/root/overseer` (GPT-6 Astra/high). Scope is the active Desktop project source plus its actually installed package. No application changes or live Reactor requests. All probes use temporary data and fake transport. Priority P1 means fix before trusting output/benchmark or relying on affected user flow; P2 is important correctness/reliability work; P3 is lower-impact robustness. These priorities are not measured prevalence.

## Confirmed findings

### RUN-01 — Saved answers have no source-revision guard (P1)

`src/decision_memory/reactor.py:124–141` binds a run to questions/config/agent but not source content. `export_predictions`, lines 187–216, checks current session membership without checking content/date revision. Probe changes session `s1` from approved to NOT approved, resumes the same run, and observes zero new calls and an exported approved answer. Old answers may remain useful historical snapshots, but the system does not enforce or clearly distinguish that interpretation from current-data export.

**Solution:** bind every run to immutable source snapshots, question/date scope, source hashes, pipeline revision and model revisions. At resume/export, reject mismatches or explicitly offer historical-snapshot export; require a new run for current sources. Never silently resend paid requests. **Acceptance:** same-ID content/date changes invalidate current-data reuse; historical snapshot remains reproducible; unchanged resume performs zero duplicate sends.

### RUN-02 — Evaluation cache survives changed questions, gold, corpus, and implementation (P1)

`evaluation.py:109–120` keys reports only by manifest, config, and modes. The manifest contains IDs, not question text or gold/source hashes. `config.py:49–51` includes a manually maintained `pipeline_version=3`, not the actual build revision. Probe edits question text and gold evidence under the same IDs; the second evaluation makes no retrieval calls and retains packed recall 1.0. Source changes are likewise absent from the identity. Stale comparisons can be frozen as the winning method.

**Solution:** version dataset snapshot, question content, annotations, source revision, model/preprocessing identity and code build; validate each resumed row against that identity. Propagate identity through frozen selection, preparation summary and answer evaluation. **Acceptance:** each material input change produces a new/incomplete report; unchanged run resumes; incompatible frozen selections are rejected. Do not recompute a whole-project hash on every query—use a release/build identifier with verified dirty-source fingerprint at run start.

### RUN-03 — Citation numbers contaminate answer matching (P1)

`evaluation.py:181` passes citation-bearing answer text directly to `vendor.score.answer_matched`. Its normalization turns `[E1]` into tokens containing `1`. Probe: unrelated answer `The budget is approved [E1].` with gold `1` is `automatic_match`; the same sentence without the citation does not match. This is the local integration of the provided scorer, not a claimed regression in the upstream scoring rules.

**Solution:** run the same canonical citation stripping for local evaluation and export, preserve original text for audit, and score only answer content. Keep official scorer semantics intact. **Acceptance:** citation numbers cannot satisfy numeric gold; real answer `1 [E2]` still matches; grouped citations and ranges handled according to the supported syntax.

### RUN-05 — Ingested dates can be rejected by the transport (P3)

`store.py:12–18` parses a weekday without verifying consistency. `vendor/reactor_client.py:177–190` explicitly validates it. Probe: `2023/05/20 (Mon) 10:00` is accepted into the store but rejected by the transport (that date is Saturday). The run may already have reset remote history before discovering the bad date.

**Solution:** one shared canonical date validator; reject inconsistent weekdays at ingestion and transmit the canonical ISO-derived wall-clock date. **Acceptance:** wrong weekday fails before storage/remote state changes; all documented formats round-trip. This does not assert invalid dates occur in the supplied corpus.

### RUN-06 — Installed runtime differs from tested source and breaks a current UI call (P1)

Normal `.venv/bin/python` imports `.venv/lib/python3.12/site-packages/decision_memory`, while the 88-test source run used `PYTHONPATH=src`. Three installed modules differ (`decision.py`, `investigation_ui.py`, `investigations.py`), and installed `report_entry_ui.py` is missing. Current `app.py:270` calls `generate_report(..., decision_only=True)`; the installed function rejects that keyword with `TypeError`. The app catches OSError/RuntimeError/ValueError there, so that error escapes. Installed code also lacks the new entry-in-report flow and bounded decision schema repair.

**Solution:** refresh the regular installation using the repository's documented frozen reinstall command, then restart the app. Add a deployment/import smoke check and build/source revision display; test the installed artifact as well as source. The audit does not perform the reinstall. **Acceptance:** installed/source hashes match the intended release, normal import accepts the current API, and Build decision view/Add entry to report work under the documented launch command. See `deployment-parity.json`.

### RUN-07 — Entry indexing/refresh recovery disappears after a new browser session (P2)

`report_entry_ui.py:59–60` stores pending entry ID/date/index status only in `st.session_state`; `entry_ui.py:27–39` has the same volatile pattern. UI probe saves an entry, simulates indexing failure, sees Retry entry refresh, opens the saved report in a fresh AppTest session, and finds the retry control gone although the entry still exists in SQLite. The failed refresh before investigation journaling is not durably tracked. Exact same-date/same-content re-entry is idempotent. Re-entry with a changed timestamp or text can create a second record; the demonstrated defect is loss of the durable recovery control, not unavoidable duplication.

**Solution:** durably record entry-to-report operation ID, saved session ID, indexing state and refresh state in SQLite/journal; resume idempotently after reconnect/restart. Include standalone Add entry jobs. **Acceptance:** restart after each stage yields a visible retry with the original entry and no duplicate save. See `test_ui_recovery_probe.py`, one passing demonstration test and `ui-recovery-results.json`.

### RUN-08 — Citation-only output is accepted, then exported as an empty factual answer (P2)

`reactor.py:68–83` only requires nonempty raw answer and a citation. `export_predictions:200–203` strips citations afterward. Probe `[E1]`, `abstained=False` passes `checked_result` and exports `answer=""` with `complete=true`. Such a submission is structurally present but has no answer.

**Solution:** canonicalize/strip citation syntax before nonempty-answer validation and revalidate export rows. Reject or request the existing bounded correction; do not fabricate abstention. **Acceptance:** citation-only/punctuation-only answers cannot mark a result complete; supported factual text and explicit abstention remain valid.

## Verified limitations and improvement proposals

### RUN-04 — Benchmark citation repair weakens the original instructions (P2, effect unmeasured)

`reactor.py:86–89,172–178` constructs repair from the raw question, dropping `retrieval.reactor_question` instructions about same-fact updates, speaker/action distinctions and complete count coverage. Probe confirms these strings are absent. The investigation service wraps an already constrained text, so this finding is specifically the benchmark `run_questions` route. Conversation history still contains the initial instructions; no live harmful answer is demonstrated.

**Solution:** compose one immutable base prompt and append correction instructions; reserve/check its message budget before first send. **Acceptance:** initial and repair share all evidence/scope constraints, one correction maximum, transport uncertainty never blindly retried.

### RUN-09 — Timing comparisons confound cache/load state and use a convenience sample (P2)

`scripts/benchmark_budgets.py:28,33–40` takes the first N ordered questions, uses one model object, and visits budgets in fixed order. Its note correctly acknowledges warming. `evaluation.py:117–120` likewise visits modes in fixed order, while `freeze:156–158` uses latency to break quality ties. Cold model setup may burden one candidate while later candidates reuse query/rerank caches. This is a comparison-design limitation, not dishonest reporting.

**Solution:** freeze history-disjoint stratified IDs, report cold initialization and warmed query latency separately, randomize/counterbalance configuration order, repeat paired trials, and record device, peak memory, cache state, package/build/model/source identities. Treat confidence intervals and quality/latency tradeoffs explicitly. **Acceptance:** all compared modes get identical cache treatment and samples; large/small budgets do not win solely from run order. Existing explanatory notes should remain.

### RUN-10 — Model selection optimizes session recall, not sufficient/correct answers (P2)

`evaluation.freeze:156–160` maximizes packed recall then all-required session coverage then speed. No span retention, supported-state precision, abstention or final answer quality affects that choice. This is particularly important after the prior cycle reproduced packed recall 1 despite lost answer text. Session-level gold remains legitimate official evidence scoring.

**Solution:** retain official metrics, add an independently labeled span/state diagnostic set and later held-out end-to-end answer evaluation; Salesgen already supplies 176 evaluation-only call labels (`outcome`, `fault`, `primary_reason`) that can seed a human-audited extraction diagnostic, with the dataset author's ambiguity caveat and without ever passing labels to retrieval; select subject to error/coverage constraints, then compare runtime. Mark a retrieval-only winner as provisional for answer quality. **Acceptance:** a solution that loses answer spans or increases unsupported resolutions cannot silently be presented as an overall pipeline winner. Cross-reference RET recommendations rather than count the known metric blind spot twice.

### RUN-11 — Completion/readiness is tied to counts/config, not an exact benchmark release (P2)

`reactor.py:204–215` recognizes the official test set by split name and 146 unique ingested questions; it does not compare an expected ID/content manifest. Existing test `test_all_official_questions_required_for_submission_ready` intentionally proves 146 synthetic IDs can be marked ready. `scripts/live_run.py:53–65` accepts an offline summary with matching config, without validating summary/source/manifest identity or all completion flags. Config alone cannot distinguish reimports under the same split.

**Solution:** record a dataset-release manifest/digest at trusted import and validate exact questions, source snapshot, completed tuning/validation/stress/test-index stages, frozen selection and build identity before readiness. Preserve custom-dataset export separately. **Acceptance:** wrong 146 IDs, changed corpus, incomplete summary and stale summary fail readiness; correct release works. Shares lineage infrastructure with RUN-01/02 but addresses the final readiness gate.

### RUN-12 — Partial answer metrics and transport latency need explicit denominators (P2/P3)

`evaluation.py:170–196` skips missing/failed requests; reported abstention recall uses only completed gold-abstention cases. It does expose expected/completed counts and correctly says failures are incomplete. It does not supply failure breakdowns/by-type completion, whole-manifest lower-bound quality, or full wall-clock cost including retry/backoff/history reset. Vendor successful retry latency is from the last `ask` attempt; saved `reactor_latency_s` sums known returned latencies, so it is not total user-visible time.

**Solution:** retain conditional quality, label its denominator, add whole-manifest completion/error rates and per-type metrics; record monotonic total request/run elapsed time and component times including waiting/retries/history resets. **Acceptance:** timeouts cannot improve the headline quality by disappearing from its denominator, and a retry-heavy run's wall-clock latency is represented. No claim that current automatic matches are official accuracy.

### RUN-13 — Runtime/report operations need stronger resilience boundaries (P3; two separate proposals)

**RUN-13a, transport boundary:** `Reactor.call:48–57` has no parent-process deadline or strict response schema; vendor answer waits are bounded, but a stuck child/startup or malformed shape is not contained by the wrapper. 

**RUN-13b, benchmark snapshot:** `app.py:162–168` selects the newest evaluation JSON regardless of split/config/completeness and embeds it into every report. It explicitly calls it an aggregate snapshot, but does not verify relevance. Fixed-name JSON temp writes outside a lock also deserve concurrent-writer tests; ingestion reviewer owns the common `atomic_json` issue.

**Solution:** parent deadline with explicit uncertain-outcome state, bounded child output and typed envelope validation; never automatic resend after kill. Select benchmark references by compatible dataset/build/mode, display identity/date, and reference immutable reports rather than duplicating every full row. **Acceptance:** hung/malformed fake subprocess leaves an auditable pending/failed request; unrelated/incomplete benchmarks are not attached; completed reports reopen without models or credentials. These are hardening proposals, not observed live outages.

## Coverage, checks, and limits

Read every function in `reactor.py`, `evaluation.py`, `cli.py`, `entry_ui.py`, `report_entry_ui.py`, `investigation_ui.py`, `app.py`, `scripts/prepare.py`, `scripts/live_run.py`, `scripts/benchmark_budgets.py`, `vendor/reactor_client.py`, and `vendor/score.py`; inspected setup.sh, pyproject.toml, Streamlit config and installed-package deltas. Overseer inventory includes function-level coverage. Retrieval researcher owns investigation state machine and decision validation internals; ingestion researcher owns storage/config/models internals.

Full source suite: **88 passed in 2.60 s** offline with bytecode/cache disabled and temporary data. Additional UI recovery demonstration: **1 passed in 0.39 s**. Runtime probes RUN-01/02/03/04/05/08 passed as defect demonstrations, not remediation tests. Installed signature check fails as predicted for `decision_only`; the existing `test_build_decision_view_uses_one_request_and_can_recover` also fails through the normal installed import (1 failed in 0.34 s) with that exact TypeError, using temporary data and fake transport. A read-only scan of historical saved runs found 21 answered records, 14 answerable scored records, zero citation-only numeric matches and zero empty-after-stripping answers (current gold comparison; records may overlap questions). Thus RUN-03/08 remain reproduced possible failures rather than observed historical incidence. See `historical-output-check.json`. No new end-to-end Reactor, real neural ranking comparison, measured remedy improvement, concurrent stress benchmark, or hostile-network test was run. Existing safe retry behavior, per-agent lock, scoped citation membership, history/date filtering and preservation of previous report revisions were inspected and not mislabeled as absent.

## Reviewer exchange

Overseer independently reran initial RUN-01–05 probes and reproduced them. Critiques accepted: stale runs should retain historical snapshot value but reject/relabel current-data reuse rather than auto-resending; citation contamination belongs to local evaluation integration and must not silently rewrite official scoring; repair weakening is a prompt-level limitation, not a proven answer failure; wrong weekday has low expected prevalence. Root added citation-stripped negative control for RUN-03 and verified default installed import/signature for RUN-06. Further critique accepted: same-date/same-text entry saves are idempotent, so RUN-07 now limits duplication risk to changed timestamp/content; RUN-13 separates transport and benchmark-snapshot proposals. Final grades are in the overseer's consolidated review.

Additional dataset-contract inspection: Salesgen public source contains 176 sessions with customer/product/call metadata, 147 distinct customers, 59 questions, and no gold evidence dated after its question cutoff. Its bundled scorer is byte-identical to the vendored scorer. The separate 176-row `calls_gold.jsonl` is evaluation-only. Public metadata loss at ingestion is assigned to ING-20/RET-05; saved aggregate-only inspection is `salesgen-contract-check.json`.
