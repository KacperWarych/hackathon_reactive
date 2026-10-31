# Interactive report investigations

Open any report under **Previous reports** and use **Continue this investigation**.
Enter a follow-up and select **Revise report**. The service retrieves evidence again,
then generates the answer and structured decision history in the same Reactor history.
Both sections use the same evidence snapshot. Only a fully validated pair becomes the
latest version. The prior version is preserved, including when generation fails.

Leave the follow-up empty to refresh from newly added conversations. Set **Revise as of**
to include their dates. Follow-up text guides analysis; new factual information belongs
in **Add entry**, with its source speaker and conversation date. It is not silently
promoted to factual evidence from a follow-up prompt.

**Report versions and changes** opens earlier saved versions, compares the answer and
decision history with their parent version, and exports the full investigation journal.
Earlier versions are read-only; choose the latest version to continue. Existing saved
reports, including legacy benchmark responses opened from Previous reports, are adopted
as version 0 without modifying the original run records.

## Identity and persistence

- The investigation ID is stable across follow-ups and related answer/decision reports.
- Each revision has its own ID, number, parent, date, prompt, evidence snapshot, and
  audited requests/responses. Completed revisions are immutable.
- The Reactor history ID stays the same while this investigation is active on the agent.
- Benchmark run IDs, question sets, checkpoints, and exports keep their existing behavior.

Journals live at `.data/investigations/inv_<id>/journal.json`; the exact evidence sent
to Reactor is also saved under that directory's `requests/`. The saved UI report points
to its selected investigation revision. File locks serialize revisions within an
investigation, and the existing agent lock prevents interference with benchmark runs.
An out-of-date browser cannot replace a newer saved revision.

The current participant API supports one active history per agent. Switching reports,
running a benchmark, moving the report's date backwards, or changing/removing an already
seen source triggers a new history. The complete saved question and follow-up sequence
is included with freshly retrieved evidence to reconstruct the analysis. Previous
generated answers are never reintroduced as source evidence. New conversations can
extend the active investigation without resetting memory.

When memory is reconstructed, bounded excerpts of the previous answer and validated
decision sections help interpret references such as “your second point.” These are
explicitly labeled generated analysis, have their old citation labels removed, and
cannot support factual claims. Reports from a later date are never loaded into an
earlier time boundary. Truncation is labeled in the request and full versions remain
available in the local journal.

The question and accumulated follow-ups must fit the retriever's 4,000-character input
limit. Each follow-up is limited to 2,000 characters. Exceeding the limit produces an
explicit error rather than silently dropping earlier instructions. Both answer and
decision prompts, including a possible citation correction, fit the configured complete
message budget. Evidence labels are local to each request.

## Failures and recovery

A transport error, timeout, invalid citation, or invalid structured decision result
leaves an incomplete revision in the journal and preserves the current successful pair.
No uncertain request is automatically resent. **Restart memory and retry** creates a
fresh Reactor history and a new audited attempt. The incomplete attempt remains visible.
A completed uncited answer receives at most one citation correction per section in the
same history, matching the benchmark runner's bounded correction behavior.

This is interactive report revision, not background monitoring. Adding a source does not
automatically run Reactor. Resolution quote checks establish traceability, not semantic
truth; the existing structured decision validator continues to apply.
