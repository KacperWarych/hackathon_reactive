"""Follow-up and revision controls composed into the existing report screen."""

import difflib
import json
from datetime import datetime
from zoneinfo import ZoneInfo

import streamlit as st

from .investigations import Investigations, revision_report
from .report_entry_ui import render_report_entry
from .snapshot import is_current


def render_ready_answer(report, pending=True):
    """Display the validated answer without waiting for the decision section."""
    st.subheader("Answer")
    st.write(report["answer_record"]["result"]["answer"])
    if pending:
        st.info("Decision history is pending. You can read the answer and sources while it finishes.")
    else:
        st.warning("Decision history did not finish. Your generated answer is saved below in this revision.")
    with st.expander("Sources for this answer"):
        for n, passage in enumerate(report["retrieval"]["evidence"], 1):
            st.markdown(f"**[E{n}] {passage['date']} · {passage['id']}**")
            st.text(passage["text"])


def generate_report(
    report, store, models_factory, config, prompt="", question_date=None, recover=False, decision_only=False
):
    # Loading a saved revision must not load model weights or require credentials.
    from .retrieval import Retriever

    class LazyRetriever:
        def retrieve(self, question, mode):
            return Retriever(store, models_factory(), config).retrieve(question, mode)

    preview = st.empty()

    def on_answer(ready):
        with preview.container():
            render_ready_answer(ready)

    try:
        result = Investigations(store, LazyRetriever(), config).revise(
            report, prompt=prompt, question_date=question_date, recover=recover,
            decision_only=decision_only, on_answer=on_answer,
        )
    except (OSError, RuntimeError, ValueError):
        # Keep a completed answer visible even if the following decision call fails.
        document = Investigations(store, config=config).document(report)
        revision = document["revisions"][-1]
        if (revision.get("answer_record") or {}).get("result", {}).get("status") == "answered":
            with preview.container():
                render_ready_answer(revision_report(report, document, revision), pending=False)
        raise
    preview.empty()
    return result


def render_investigation(report, store, models_factory, config, configured, busy):
    service = Investigations(store, config=config)
    document = service.document(report)
    error_key = "investigation_error:" + document["id"]
    if notice := st.session_state.pop(error_key, None):
        st.error(notice)
    revisions = [
        r for r in document["revisions"] if r["status"] in ("saved", "complete")
    ]
    selected_id = report.get("revision_id", document["current_revision"])
    selected = next((r for r in revisions if r["id"] == selected_id), revisions[-1])
    latest = selected["id"] == document["current_revision"]
    if not is_current(store, selected["retrieval"]):
        st.warning(
            "Historical report: conversations have changed or its source snapshot is unknown. "
            "Use Revise report to refresh from current evidence."
        )
    changed = (
        revision_report(report, document, selected)
        if report.get("revision_id") != selected["id"]
        else None
    )
    st.caption(
        f"Version {selected['number']} · "
        + ("Latest version" if latest else "Earlier version")
    )
    with st.expander("Report versions and changes"):
        choice = st.selectbox(
            "Saved version",
            [r["id"] for r in revisions],
            index=revisions.index(selected),
            key="versions:" + document["id"] + selected["id"],
            format_func=lambda rid: next(
                f"Version {r['number']} · "
                + datetime.fromtimestamp(
                    r["created_at"], ZoneInfo("Europe/Warsaw")
                ).strftime("%d %b %Y, %H:%M")
                for r in revisions
                if r["id"] == rid
            ),
        )
        if choice != selected["id"]:
            changed = revision_report(
                report, document, next(r for r in revisions if r["id"] == choice)
            )
        if selected.get("prompt"):
            st.write("Follow-up: " + selected["prompt"])
        if selected.get("memory_action") == "reconstructed":
            st.caption(
                "Memory was rebuilt from the saved question, follow-ups, and current source evidence."
            )
        changes = selected.get("changes")
        if changes:
            st.caption(
                f"Answer {'changed' if changes['answer_changed'] else 'unchanged'} · "
                f"Decision history {'changed' if changes['decision_changed'] else 'unchanged'} · "
                f"{len(changes['sources_added'])} sources added · {len(changes['sources_removed'])} removed"
            )
            parent = next(r for r in revisions if r["id"] == selected["parent_id"])
            for field, label in (
                ("answer_record", "Answer changes"),
                ("decision_record", "Decision history changes"),
            ):
                before = (parent.get(field) or {}).get("result", {}).get("answer", "")
                after = (selected.get(field) or {}).get("result", {}).get("answer", "")
                delta = "\n".join(
                    difflib.unified_diff(
                        before.splitlines(),
                        after.splitlines(),
                        fromfile="Previous version",
                        tofile="This version",
                        lineterm="",
                    )
                )
                if delta:
                    st.write(label)
                    st.code(delta, language="diff")
        st.download_button(
            "Download investigation history",
            json.dumps(document, ensure_ascii=False, indent=2),
            file_name=document["id"] + ".json",
            mime="application/json",
        )
    last = document["revisions"][-1]
    incomplete = last["status"] in ("pending", "failed")
    if incomplete:
        if (last.get("answer_record") or {}).get("result", {}).get("status") == "answered":
            render_ready_answer(revision_report(report, document, last), pending=last["status"] == "pending")
        st.warning(
            "The last revision did not finish. Your previous version is preserved. "
            + last.get("error", "")
        )
        with st.expander("Incomplete revision details"):
            st.json(last)
    if not latest:
        st.info("Open the latest saved version above to continue this investigation.")
        return changed
    if changed:
        return changed
    updated = render_report_entry(
        report, document, store, models_factory, config, configured, busy, generate_report
    )
    if updated:
        return updated
    if st.session_state.get("report_entry_pending:" + document["id"]):
        return None
    with st.form("followup:" + document["id"] + selected["id"]):
        st.markdown("**Continue this investigation**")
        prompt = st.text_area(
            "Follow-up prompt",
            value=last.get("prompt", "") if incomplete else "",
            height=100,
            max_chars=2000,
            placeholder="Focus on procurement. What evidence supports the remaining blocker?",
        )
        st.caption(
            "The answer and decision history are revised together. Use Add entry to this report above to record new factual information."
        )
        moment = datetime.fromisoformat(
            (last if incomplete else selected)["retrieval"]["question"]["iso"]
        )
        left, right = st.columns(2)
        date = left.date_input("Revise as of", value=moment.date())
        hour = right.time_input("Revision time", value=moment.time())
        st.caption(
            "Leave the prompt empty to refresh this report from the latest available conversations."
        )
        submit = st.form_submit_button(
            "Restart memory and retry" if incomplete else "Revise report",
            type="primary",
            disabled=not configured or busy,
        )
    if submit:
        try:
            with st.spinner(
                "Refreshing evidence and revising the answer and decision history…"
            ):
                changed = generate_report(
                    report,
                    store,
                    models_factory,
                    config,
                    prompt,
                    None if incomplete and last.get("decision_only") else f"{date.isoformat()} {hour:%H:%M}",
                    recover=incomplete,
                )
        except (OSError, RuntimeError, ValueError) as error:
            st.session_state[error_key] = str(error)
            st.rerun()
    return changed
