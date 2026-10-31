"""Capture report evidence and refresh the same investigation after indexing."""

from datetime import datetime
from zoneinfo import ZoneInfo

import streamlit as st

from .entries import add_entry
from .index import Index


def render_report_entry(report, document, store, models, config, configured, busy, generate):
    scope = document["id"]
    pending_key = "report_entry_pending:" + scope
    notice_key = "report_entry_notice:" + scope
    pending = st.session_state.get(pending_key)
    question = report["retrieval"]["question"]
    incomplete = document["revisions"][-1]["status"] in ("pending", "failed")
    if notice := st.session_state.pop(notice_key, None):
        st.success(notice)
    with st.expander("Add entry to this report", expanded=bool(pending)):
        st.caption(
            f"New evidence for {question['split']} · {question['history_id']}. "
            "Saving refreshes this report’s answer and decision history."
        )
        if not configured:
            st.info("Connect the Reactor service to save an entry and refresh this report.")
        elif busy:
            st.info("The service is busy. You can save and refresh when it is available.")
        if incomplete and not pending:
            st.info("Retry the incomplete revision below before adding another entry.")
        with st.form("report_entry:" + scope + document["current_revision"], clear_on_submit=False):
            kind = st.radio("Entry type", ["Note", "Conversation transcript"], horizontal=True)
            speaker = st.selectbox(
                "Note source", ["Customer", "Seller"],
                help="For notes, choose who supplied the information. Transcripts use their own speaker labels.",
            )
            text = st.text_area(
                "New entry", height=160, max_chars=100000,
                placeholder="Paste a customer update or call note. For transcripts, use Customer: and Seller: labels.",
            )
            now = datetime.now(ZoneInfo("Europe/Warsaw"))
            left, right = st.columns(2)
            date = left.date_input("Entry date", value=now.date())
            hour = right.time_input("Entry time", value=now.time().replace(second=0, microsecond=0))
            st.caption("The refreshed report includes evidence through the later of its current date and this entry’s date.")
            submit = st.form_submit_button(
                "Save entry and refresh report", type="primary",
                disabled=not configured or busy or bool(pending) or incomplete,
            )
        if submit:
            try:
                transcript = f"{speaker}: {text.strip()}" if kind == "Note" else text
                stamp = f"{date.isoformat()} {hour:%H:%M}"
                sid = add_entry(store, question["split"], question["history_id"], stamp, transcript)
            except (ValueError, OSError) as error:
                st.error(str(error))
            else:
                pending = {"session_id": sid, "date": stamp, "indexed": False}
                st.session_state[pending_key] = pending
        retry = False
        if pending:
            st.info("Entry saved. Refresh is pending; retrying uses the same saved entry.")
            retry = st.button(
                "Restart memory and refresh entry" if incomplete else "Retry entry refresh",
                key="report_entry_retry:" + scope, disabled=not configured or busy,
            )
        if pending and (submit or retry):
            try:
                if not pending["indexed"]:
                    with st.spinner("Making the new entry searchable…"):
                        Index(store, models(), config).build(question["split"], [question["history_id"]])
                    pending["indexed"] = True
                moment = max(datetime.fromisoformat(question["iso"]), datetime.fromisoformat(pending["date"]))
                with st.spinner("Refreshing the answer and decision history…"):
                    updated = generate(
                        report, store, models, config,
                        question_date=moment.strftime("%Y-%m-%d %H:%M"), recover=incomplete,
                    )
            except (OSError, RuntimeError, ValueError) as error:
                st.warning(f"Your entry is saved. The report could not refresh: {error}")
                # Render recovery controls from the updated journal on the next run.
                st.session_state[notice_key + ":error"] = str(error)
                st.rerun()
            else:
                st.session_state.pop(pending_key, None)
                st.session_state[notice_key] = "Entry saved. The answer and decision history have been refreshed."
                return updated
        if error := st.session_state.pop(notice_key + ":error", None):
            st.warning(f"Your entry is saved. The report could not refresh: {error}")
    return None
