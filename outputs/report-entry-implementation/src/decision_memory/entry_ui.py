"""Conversation entry form for the selected dataset and history."""
from datetime import datetime
from zoneinfo import ZoneInfo

import streamlit as st

from .entries import add_entry, export_entries
from .index import Index


def render_entry_form(store, split, history_id, models, config):
    scope = f"{split}:{history_id}"
    with st.expander("Add a conversation"):
        st.caption(f"Save a new conversation to {split} · {history_id}.")
        st.write("Label each speaker as Customer: or Seller: (user: and assistant: also work). Include the customer's name in the conversation when relevant.")
        with st.form("entry:" + scope):
            now = datetime.now(ZoneInfo("Europe/Warsaw"))
            date = st.date_input("Conversation date", value=now.date())
            hour = st.time_input("Conversation time", value=now.time().replace(second=0, microsecond=0))
            text = st.text_area("Conversation transcript", height=200, max_chars=100000,
                                placeholder="Seller: Hello, Anna. Has your budget changed?\nCustomer: Yes, the budget was approved today.")
            submit = st.form_submit_button("Save conversation", type="primary")
        if submit:
            try:
                sid = add_entry(store, split, history_id, f"{date.isoformat()} {hour:%H:%M}", text)
            except (ValueError, OSError) as error:
                st.error(str(error))
            else:
                st.session_state["entry_pending:" + scope] = sid
        if st.session_state.get("entry_pending:" + scope):
            retry = st.button("Retry indexing", key="retry:" + scope)
            if submit or retry:
                try:
                    with st.spinner("Making the conversation searchable…"):
                        Index(store, models(), config).build(split, [history_id])
                except (OSError, RuntimeError, ValueError) as error:
                    st.warning(f"Conversation saved, but indexing did not finish: {error}. Retry indexing to make it searchable.")
                else:
                    st.session_state.pop("entry_pending:" + scope, None)
                    st.session_state["entry_notice"] = "Conversation saved and searchable. For questions about it, set ‘Answer as of’ to its date or later."
                    st.rerun()
        st.download_button("Download added conversations", export_entries(store, split, history_id),
                           file_name=f"{split}-added-histories.jsonl", mime="application/x-ndjson")
