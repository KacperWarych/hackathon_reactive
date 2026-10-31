"""Local evidence explorer. Run with: .venv/bin/streamlit run app.py"""
import json
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import streamlit as st

# Keep this checkout's UI and package in sync even after a regular installation.
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from decision_memory.config import Config, data_root, digest, load_env
from decision_memory.decision import SECTIONS, validate_decision
from decision_memory.entry_ui import render_entry_form
from decision_memory.investigation_ui import generate_report, render_investigation
from decision_memory.models import Models
from decision_memory.reactor import agent_lock
from decision_memory.retrieval import Retriever
from decision_memory.store import Store, iso_date

st.set_page_config(page_title="Reactive AI", page_icon="✳", layout="wide")
load_env()
DATA = data_root()
CONFIG = Config()

st.markdown("<style>" + Path(__file__).with_name("ui.css").read_text() + "</style>", unsafe_allow_html=True)


@st.cache_resource
def models():
    return Models(CONFIG)


REPORTS = DATA / "ui_reports"

def save_report():
    report = st.session_state.get("active_report")
    if not report:
        return
    for field in ("retrieval", "answer_record", "decision_record"):
        report[field] = st.session_state.get(field)
    REPORTS.mkdir(parents=True, exist_ok=True)
    path = REPORTS / (report["id"] + ".json")
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    temporary.replace(path)


def open_report(report):
    st.session_state["active_report"] = report
    for field in ("retrieval", "answer_record", "decision_record"):
        st.session_state[field] = report.get(field)
    st.session_state["page"] = "Report"


def navigate(page):
    st.session_state["page"] = page


store = Store()
page = st.session_state.get("page", "Ask")
with st.container(key="navigation"):
    brand, links = st.columns([1, 1.7], vertical_alignment="center")
    with brand:
        st.markdown('<a class="brand" href="https://rxai.dev/" target="_blank"><svg viewBox="320 310 440 460" aria-hidden="true"><path d="M623.619 433.393C627.823 433.393 631.95 433.651 636 434.141C631.976 378.727 585.779 335 529.341 335H351V647H445.278V433.393Z"/><path d="M529.075 647.077L528.972 647H445V744.897H623.293L623.422 745H726L631.654 647.077Z"/><path d="M538 548.127L631.768 647C686.72 642.774 730 596.397 730 539.78C730 483.162 688.875 439.17 635.898 433C636.078 435.618 636.206 438.237 636.206 440.907C636.206 497.498 592.927 543.901 538 548.127Z"/></svg>Reactive AI</a>', unsafe_allow_html=True)
    with links:
        nav = st.columns([1, 1, 1.5])
        for col, name in zip(nav, ("Ask", "Add entry", "Previous reports")):
            col.button(name, key="nav:" + name, on_click=navigate, args=(name,),
                       type="primary" if page == name or (page == "Report" and name == "Previous reports") else "secondary", use_container_width=True)

configured = all(os.environ.get(k) for k in ("REACTOR_BASE_URL", "REACTOR_AGENT_ID", "REACTOR_ACCESS_KEY"))
busy = False
if configured:
    try:
        with agent_lock(os.environ["REACTOR_BASE_URL"], os.environ["REACTOR_AGENT_ID"]):
            pass
    except RuntimeError:
        busy = True

if page == "Previous reports":
    st.title("Previous reports")
    st.caption("Your questions, answers, and the evidence behind them.")
    paths = sorted(REPORTS.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    legacy_paths = sorted((DATA / "runs").glob("*/results/*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    paths += legacy_paths
    search = st.text_input("Search reports", placeholder="Find a question…")
    count = 0
    seen = set()
    for path in paths:
        try:
            report = json.loads(path.read_text())
            if "result" in report:
                if report["result"].get("status") != "answered" or report["retrieval"]["question"]["question_id"].startswith("decision_"):
                    continue
                report = {"id": "imported_" + digest(str(path))[:24],
                          "created_at": datetime.fromtimestamp(path.stat().st_mtime, ZoneInfo("Europe/Warsaw")).strftime("%d %b %Y, %H:%M"),
                          "retrieval": report["retrieval"], "answer_record": report,
                          "decision_record": None, "evaluation": None, "generation_attempted": True}
            question_text = report["retrieval"]["question"]["question"]
        except (OSError, ValueError, KeyError, TypeError):
            continue
        if report["id"] in seen:
            continue
        seen.add(report["id"])
        if search.casefold() not in question_text.casefold():
            continue
        count += 1
        with st.container(border=True):
            st.subheader(question_text)
            st.caption(report["created_at"] + " · " + report["retrieval"]["question"]["split"])
            st.caption("Answer ready" if report.get("answer_record") else "Evidence saved · answer pending")
            if st.button("Open report", key=digest(str(path))):
                open_report(report)
                save_report()
                st.rerun()
    if not count:
        st.info("No matching reports yet. Ask a question to create one.")
    store.close(); st.stop()

if page in ("Ask", "Add entry"):
    stats = store.stats()
    if not stats:
        st.info("Import the supplied conversations to begin.")
        st.code("memory ingest --split dev")
        store.close(); st.stop()
    if page == "Ask":
        st.markdown('<div class="ambient" aria-hidden="true"><i></i><i></i><i></i></div>', unsafe_allow_html=True)
    with st.container(key="ask_stage" if page == "Ask" else "entry_stage"):
        if page == "Ask":
            st.markdown('<div class="ask-heading"><div class="signal" aria-hidden="true">'+ '<i></i>'*9 + '</div><h1>What’s on your mind?</h1><p>Answers grounded in your conversations.</p></div>', unsafe_allow_html=True)
        else:
            st.title("Add entry")
            st.caption("Give your next answer more context.")
        with st.popover("Conversation settings", use_container_width=False):
            splits = [s["split"] for s in stats]
            split = st.selectbox("Dataset", splits, index=splits.index("salesgen") if "salesgen" in splits else 0)
            history_ids = [r[0] for r in store.db.execute("SELECT DISTINCT history_id FROM sessions WHERE split=? ORDER BY history_id", (split,))]
            hid = st.selectbox("History", history_ids, key="scope:" + split)
            sessions = store.sessions(split, hid)
            st.caption(f"{len(sessions)} conversations")
            methods = ["full", "rerank", "hybrid", "dense", "bm25"]
            mode = st.selectbox("Search method", methods, format_func=lambda m: {"full":"Hybrid + updates", "rerank":"Hybrid + reranking", "hybrid":"Hybrid", "dense":"Semantic", "bm25":"Keyword"}[m])
            latest = max((s["iso"] for s in sessions), default=datetime.now().isoformat())
            date = st.date_input("Answer as of", value=datetime.fromisoformat(latest).date(), key="date:"+split+hid)
            hour = st.time_input("Time", value=datetime.fromisoformat(latest).time(), key="time:"+split+hid)
            st.caption("Only conversations on or before this moment are included.")
        if page == "Add entry":
            if notice := st.session_state.pop("entry_notice", None):
                st.success(notice)
            render_entry_form(store, split, hid, models, CONFIG)
            store.close(); st.stop()
        with st.form("ask_form", border=False):
            text = st.text_area("Your question", height=120, max_chars=4000, placeholder="Ask anything about your conversations…", label_visibility="collapsed")
            submit = st.form_submit_button("Create report", type="primary", use_container_width=True)
        st.caption(f"{split} / {hid}")
        if submit:
            if not text.strip():
                st.warning("Write a question to create your report.")
            else:
                stamp = f"{date.isoformat()} {hour:%H:%M}"
                question = {"split": split, "history_id": hid, "question": text.strip(), "question_date": stamp,
                            "iso": iso_date(stamp), "question_id": "custom_" + digest([split, hid, text.strip(), stamp])[:16]}
                try:
                    with st.spinner("Connecting the evidence…"):
                        retrieval = Retriever(store, models(), CONFIG).retrieve(question, mode)
                    evaluations = sorted((DATA / "evaluation").glob("retrieval-*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
                    evaluation = None
                    if evaluations:
                        try:
                            evaluation = json.loads(evaluations[0].read_text())
                        except (OSError, ValueError):
                            pass
                    report = {"id": uuid.uuid4().hex, "created_at": datetime.now(ZoneInfo("Europe/Warsaw")).strftime("%d %b %Y, %H:%M"),
                              "retrieval": retrieval, "answer_record": None, "decision_record": None, "evaluation": evaluation}
                    open_report(report)
                    save_report()
                    st.rerun()
                except (OSError, RuntimeError, ValueError) as error:
                    st.error(f"Could not create the report: {error}")
    store.close(); st.stop()

report = st.session_state.get("active_report")
if not report:
    navigate("Ask"); st.rerun()
retrieval = st.session_state["retrieval"]
st.title(retrieval["question"]["question"])
st.caption("Reactive AI report · " + report["created_at"])
# Generate each missing section once. Failed or unavailable services leave a saved,
# readable partial report with explicit retry controls.
if not report.get("generation_attempted"):
    report["generation_attempted"] = True
    if configured and not busy and retrieval["evidence"]:
        try:
            with st.spinner("Writing the answer and decision history…"):
                open_report(generate_report(report, store, models, CONFIG))
            report = st.session_state["active_report"]
            retrieval = st.session_state["retrieval"]
        except (OSError, RuntimeError, ValueError) as error:
            st.warning(f"The report could not be completed: {error}")
    else:
        st.info("Evidence is saved. Answer generation is unavailable while the service is busy or unconfigured, or when no evidence was found.")
    save_report()
try:
    updated = render_investigation(report, store, models, CONFIG, configured, busy)
    if updated:
        open_report(updated)
        save_report()
        st.rerun()
except (OSError, RuntimeError, ValueError) as error:
    st.error(str(error))

evidence_search = ""
evidence_order = "Relevance"
evidence_tab, decision_tab, evaluation_tab = st.tabs(["Answer and evidence", "Decision history", "Evaluation"])
with evidence_tab:
    if retrieval is None:
        st.info("Your evidence will appear here. Write a question above, choose your filters, then select Find evidence.")
    else:
        left, right = st.columns([.85, 1.15], gap="large")
        with left:
            st.subheader("Answer")
            record = st.session_state.get("answer_record")
            if record:
                st.caption("Reactive AI answer · " + record["retrieval"]["question"]["question_date"])
                st.write(record["result"]["answer"])
                if record["result"].get("abstained"):
                    st.info("Reactive AI reported insufficient evidence.")
            else:
                st.write("Evidence is ready. No answer has been generated yet.")
            if st.button("Generate answer", disabled=not configured or busy or not retrieval["evidence"]):
                try:
                    with st.spinner("Generating answer…"):
                        open_report(generate_report(report, store, models, CONFIG))
                    save_report()
                    st.rerun()
                except (OSError, RuntimeError, ValueError) as e:
                    st.error(str(e))
            st.caption(f"{len(retrieval['evidence'])} source sessions · {retrieval['trace']['message_chars']:,} message characters")
            with st.expander("How the evidence was found"):
                st.json(retrieval["trace"])
            st.download_button("Download evidence", json.dumps(retrieval, ensure_ascii=False, indent=2),
                               file_name="evidence.json", mime="application/json")
        with right:
            st.subheader("Original conversations")
            if not retrieval["evidence"]:
                st.warning("No excerpts were selected. This does not prove the history contains no answer.")
            evidence_search = st.text_input("Contains text", placeholder="Filter excerpts…")
            evidence_order = st.selectbox("Sort excerpts", ["Relevance", "Newest first", "Oldest first"])
            numbered = list(enumerate(retrieval["evidence"], 1))
            if evidence_order != "Relevance":
                numbered.sort(key=lambda item: iso_date(item[1]["date"]), reverse=evidence_order == "Newest first")
            if evidence_search.strip():
                numbered = [(n, p) for n, p in numbered if evidence_search.casefold().strip() in p["text"].casefold()]
            st.caption(f"Showing {len(numbered)} of {len(retrieval['evidence'])} source conversations")
            if retrieval["evidence"] and not numbered:
                st.info("No excerpts match this text. Clear Contains text to see all evidence.")
            for position, (n, passage) in enumerate(numbered):
                with st.expander(f"[E{n}] {passage['date']} · {passage['id']}", expanded=position == 0):
                    st.text(passage["text"])
                    st.caption("Source turns: " + ", ".join(passage.get("turn_ids", [])))

with decision_tab:
    st.subheader("Recorded state and changes")
    st.write("This view separates source statements, interpretations, and possible next questions. A proposed solution does not establish acceptance.")
    if st.button("Build decision view", disabled=not configured or busy or not retrieval or not retrieval["evidence"]):
        try:
            with st.spinner("Reactive AI is reconstructing the decision history…"):
                open_report(generate_report(report, store, models, CONFIG, decision_only=True))
                save_report()
                st.rerun()
        except (OSError, RuntimeError, ValueError) as e:
            st.error(str(e))
    decision_record = st.session_state.get("decision_record")
    if decision_record and decision_record["result"].get("abstained"):
        st.info("The selected evidence is insufficient to establish a decision history.")
    elif decision_record:
        obj, error = validate_decision(decision_record["result"]["answer"], decision_record["retrieval"]["evidence"])
        if error:
            st.warning(error + " Original response shown below.")
            st.write(decision_record["result"]["answer"])
        else:
            st.caption("Source references and quoted confirmations are checked automatically. Interpretations still require review.")
            for section in SECTIONS:
                st.markdown("**" + section.replace("_", " ").capitalize() + "**")
                if not obj[section]:
                    st.caption("Not established by the selected evidence.")
                for item in obj[section]:
                    st.write(item["text"] + " " + " ".join(f"[{s}]" for s in item["sources"]))
                    if item.get("confirmation_quote"):
                        st.text(item["confirmation_quote"])
    elif not configured:
        st.info("Connect the answer service to generate this view. Retrieved excerpts remain available in the evidence tab.")

with evaluation_tab:
    st.subheader("Evaluation")
    st.caption("Retrieval diagnostics for this report")
    st.json(retrieval["trace"], expanded=False)
    evaluation = report.get("evaluation")
    if evaluation:
        st.caption("Latest benchmark snapshot at report creation. These aggregate results do not score this custom question.")
        st.dataframe(evaluation.get("summary", {}), use_container_width=True)
        with st.expander("Benchmark question results"):
            st.dataframe(evaluation.get("rows", []), use_container_width=True)
    else:
        st.info("No benchmark evaluation was available when this report was created.")
    st.caption("Retrieval coverage is not final answer accuracy.")
st.download_button("Download report", json.dumps(report, ensure_ascii=False, indent=2), file_name="reactive-ai-report.json", mime="application/json")
store.close()
