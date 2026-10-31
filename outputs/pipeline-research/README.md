# Extraction pipeline research group

Established 2026-10-31. Daily heartbeat: 09:00 Europe/Warsaw, in the originating chat. Automation ID: `extraction-pipeline-research-group`.

## Scope and roles

The project installer points to `/Users/kacperwarych/Desktop/hackathon reactive ai`. Inspect that project read-only and compare with the staged `outputs/report-entry-implementation` snapshot. Reports belong here. Do not assume the staged copy is current.

The lead coordinates and reports meaningful improvements to the user. Each solution area gets a researcher (GPT-6.1 Sol, high reasoning) and an independent overseer (GPT-6 Astra, high reasoning). Groups run in bounded waves or sequentially within available agent slots. The researcher and overseer communicate directly: the overseer challenges findings, the researcher responds with evidence or revises, and the overseer sends the graded report to the lead. Model choices reflect role complexity, not a measured model comparison; disclose any fallback.

Cover ingestion/chunking, embeddings and lexical retrieval, fusion/reranking, evidence packing, structured extraction/state tracking, and evaluation. Start from concrete failures and compare alternatives under matched data and budgets.

## Review requirements

Grade each recommendation from 0 to 5 on evidence strength, project fit, expected benefit, and feasibility (5 is strongest/best). Grades are judgments, not performance measurements. Include code/source references, reproduction or experiment design, limitations, tradeoffs, and confidence. Clearly separate observed defects, measured gains, and untested hypotheses. Public benchmark rankings alone cannot establish the best project solution.

Save dated researcher and overseer reports, including the critique/response exchange. Maintain a backlog of unresolved questions and completed experiments so future cycles do not repeat work without new evidence.

The loop performs research and inexpensive local checks. Application changes, heavy model downloads, paid API experiments, and publication are outside this research task. Report meaningful new findings, failures, or decisions needed; otherwise stay quiet. Each scheduled wakeup ends after a bounded research cycle.

## Completed whole-pipeline audit

The 31 October full audit is available in [AUDIT.md](full-audit-2026-10-31/AUDIT.md), with 49 distinct reviewed findings and proposed improvements, full-function coverage, independent grades, reproducible probes and an implementation roadmap. Consult it and the updated backlog before the next daily cycle.
