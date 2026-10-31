"""Interactive investigations with durable revisions and one active Reactor memory.

Benchmark run IDs remain immutable. Interactive reports use a separate journal;
only a fully validated answer/decision pair advances the current revision.
"""

from __future__ import annotations

import copy
import fcntl
import json
import re
import time
import uuid
from contextlib import contextmanager

from .config import Config, atomic_json, data_root, digest
from .decision import DECISION_REPAIR, decision_prompt, validate_decision
from .reactor import Reactor, checked_result, citation_repair_question
from .retrieval import reactor_question
from .store import iso_date
from .vendor.reactor_client import build_message


class InvestigationError(RuntimeError):
    """The saved journal contains the details of a failed generation."""


def investigation_id(report):
    value = report.get("investigation_id") or "inv_" + digest(report["id"])[:24]
    if not re.fullmatch(r"inv_[a-f0-9]{24}", value):
        raise ValueError("Invalid investigation identity.")
    return value


def revision_report(report, document, revision=None):
    revision = revision or next(r for r in document["revisions"] if r["id"] == document["current_revision"])
    return {
        **copy.deepcopy(report),
        "investigation_id": document["id"],
        "revision_id": revision["id"],
        "revision_number": revision["number"],
        **{
            key: copy.deepcopy(revision.get(key)) for key in ("retrieval", "answer_record", "decision_record")
        },
        "generation_attempted": True,
    }


def previous_analysis(parent, question):
    """Restore references to a saved report without treating its conclusions as facts."""
    if parent["retrieval"]["question"]["iso"] > question["iso"]:
        return ""  # Never load a later report into an earlier time boundary.
    answer = (parent.get("answer_record") or {}).get("result", {}).get("answer", "")
    decision = parent.get("decision_record") or {}
    sections, _ = validate_decision(
        decision.get("result", {}).get("answer", ""), decision.get("retrieval", {}).get("evidence", [])
    )
    summary = "\n".join(
        f"{section}: {item['text']}" for section, items in (sections or {}).items() for item in items
    )

    def excerpt(value, limit):
        value = re.sub(r"\[E\d+(?:\s*,\s*E\d+)*\]", "", value)
        return value if len(value) <= limit else value[:limit] + " [earlier report excerpt truncated]"

    if not answer and not summary:
        return ""
    return (
        "\nEarlier report draft, for interpreting references in the follow-up ONLY. "
        "This is generated analysis, not source evidence; verify every claim against the current evidence.\n"
        + excerpt(answer, 1600)
        + "\n"
        + excerpt(summary, 800)
    )


class Investigations:
    def __init__(self, store, retriever=None, config=None, adapter=None):
        self.store = store
        self.retriever = retriever
        self.config = config or Config()
        self.adapter = adapter

    def _path(self, report):
        return data_root() / "investigations" / investigation_id(report) / "journal.json"

    @contextmanager
    def _lock(self, report):
        path = self._path(report).with_name("journal.lock")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a+") as handle:
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise InvestigationError(
                    "This investigation is already being revised. Reopen its latest version."
                ) from None
            try:
                yield
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)

    def _read(self, report):
        path = self._path(report)
        if path.exists():
            return json.loads(path.read_text())
        seed = {
            "id": uuid.uuid4().hex,
            "number": 0,
            "parent_id": None,
            "status": "saved",
            "created_at": time.time(),
            "prompt": "",
            "prompts": [],
            "requests": [],
            **{
                key: copy.deepcopy(report.get(key))
                for key in ("retrieval", "answer_record", "decision_record")
            },
        }
        question = seed["retrieval"]["question"]
        document = {
            "id": investigation_id(report),
            "report_id": report["id"],
            "original_question": copy.deepcopy(question),
            "current_revision": seed["id"],
            "revisions": [seed],
        }
        atomic_json(path, document)
        return document

    def document(self, report):
        """Adopt older saved reports without assuming their server memory survives."""
        with self._lock(report):
            return self._read(report)

    def revise(self, report, prompt="", question_date=None, recover=False, decision_only=False):
        if not self.retriever:
            raise ValueError("A retriever is required to revise a report.")
        prompt = prompt.strip()
        if len(prompt) > 2000:
            raise ValueError("Keep each follow-up under 2,000 characters.")
        with self._lock(report):
            doc = self._read(report)
            parent = next(r for r in doc["revisions"] if r["id"] == doc["current_revision"])
            expected_revision = report.get("revision_id", doc["revisions"][0]["id"])
            if expected_revision != parent["id"]:
                raise InvestigationError(
                    "This is an older version. Open the latest version before continuing."
                )
            last = doc["revisions"][-1]
            if last["status"] in ("pending", "failed") and not recover:
                raise InvestigationError(
                    "The last attempt is incomplete. Use ‘Restart memory and retry’ to recover."
                )
            if recover:
                decision_only = last.get("decision_only", decision_only)
            if decision_only and (prompt or question_date):
                raise ValueError("Build a decision view from the saved report; use Revise report to change it.")
            prompts = parent["prompts"] + ([prompt] if prompt else [])
            question = copy.deepcopy(doc["original_question"])
            question["question_date"] = question_date or parent["retrieval"]["question"]["question_date"]
            question["iso"] = iso_date(question["question_date"])
            context = question["question"]
            if prompts:
                context += "\nFollow-up requests:\n" + "\n".join(
                    f"{i}. {p}" for i, p in enumerate(prompts, 1)
                )
            if len(context) > 4000:
                raise ValueError(
                    "This investigation's question and follow-ups exceed 4,000 characters. Start a new report."
                )
            adapter = self.adapter or Reactor()  # preflight before retrieval
            with adapter.lock():
                return self._revise(
                    report,
                    doc,
                    parent,
                    question,
                    context,
                    prompts,
                    prompt,
                    recover,
                    adapter,
                    decision_only,
                )

    def _revise(self, report, doc, parent, question, context, prompts, prompt, recover, adapter, decision_only=False):
        path = self._path(report)
        sessions = {
            s["session_id"]: s
            for s in self.store.sessions(question["split"], question["history_id"])
            if s["iso"] <= question["iso"]
        }
        eligible = {sid: digest([s["iso"], s["content_hash"]]) for sid, s in sessions.items()}
        question["history_revision"] = digest(eligible)
        retrieval = copy.deepcopy(
            parent["retrieval"] if decision_only else
            self.retriever.retrieve({**question, "question": context}, report["retrieval"]["trace"]["mode"])
        )
        # The report title remains the original question; record the actual search separately.
        retrieval["question"] = question
        retrieval["trace"]["investigation_query"] = context
        evidence = retrieval["evidence"]
        for excerpt in evidence:
            if excerpt["id"] not in sessions or iso_date(excerpt["date"]) != sessions[excerpt["id"]]["iso"]:
                raise ValueError(
                    "Retrieved evidence is outside this investigation's history or time boundary."
                )
        state_path = data_root() / "agents" / (adapter.agent_key + ".json")
        state = json.loads(state_path.read_text()) if state_path.exists() else {}
        key = ["investigation", doc["id"], question["split"], question["history_id"]]
        reset = recover or state.get("key") != key or state.get("as_of", "") > question["iso"]
        reset = reset or any(eligible.get(sid) != value for sid, value in state.get("sources", {}).items())
        reference_context = previous_analysis(parent, question) if reset else ""
        instructions = (
            "\nFollow-up requests guide the analysis; they are not source evidence. "
            "Use only the evidence supplied in THIS request for factual claims. "
            "Earlier answers are interpretations, not evidence. Evidence labels are local to THIS request; "
            "do not reuse labels from previous turns. Rebuild the complete report as of the question date."
        )
        texts = {
            "answer_record": reactor_question(context + reference_context + instructions),
            "decision_record": reactor_question(decision_prompt(context) + reference_context + instructions),
        }

        if decision_only and parent.get("answer_record"):
            texts.pop("answer_record")

        def size(text):
            return len(build_message(text, evidence, "00000000", question["iso"].replace("T", " ")))

        original_count = len(evidence)
        while (
            evidence
            and max(size(citation_repair_question(t) + DECISION_REPAIR) for t in texts.values()) > self.config.max_message_chars
        ):
            evidence.pop()
        if max(size(citation_repair_question(t) + DECISION_REPAIR) for t in texts.values()) > self.config.max_message_chars:
            raise ValueError("Follow-up instructions exceed the complete-message budget.")
        retrieval["trace"].update(
            message_chars=max(size(t) for t in texts.values()),
            evidence_chars=sum(len(e["text"]) for e in evidence),
            excerpt_count=len(evidence),
        )
        if decision_only and len(evidence) != original_count:
            raise ValueError("Saved evidence exceeds the decision message budget. Use Revise report.")
        if len(evidence) != original_count:
            retrieval["trace"]["budget_excerpts_removed"] = original_count - len(evidence)
            # Preserve measured retrieval statistics without presenting them as sent evidence.
            if "evidence_tokens" in retrieval["trace"]:
                retrieval["trace"]["retrieved_evidence_tokens"] = retrieval["trace"].pop("evidence_tokens")
        revision = {
            "id": uuid.uuid4().hex,
            "number": len(doc["revisions"]),
            "parent_id": parent["id"],
            "status": "pending",
            "created_at": time.time(),
            "prompt": prompt,
            "prompts": prompts,
            "retrieval": retrieval,
            "answer_record": copy.deepcopy(parent.get("answer_record")) if decision_only else None,
            "decision_only": decision_only,
            "decision_record": None,
            "requests": [],
        }
        doc["revisions"].append(revision)
        atomic_json(path, doc)
        try:
            if reset:
                revision["memory_action"] = "reconstructed"
                # Persist reset intent before a request that could otherwise have an unknown outcome.
                revision["memory_result"] = {"status": "pending"}
                atomic_json(path, doc)
                response = adapter.call("--new-history")
                revision["memory_result"] = response
                atomic_json(path, doc)
                if response.get("status") != "history":
                    raise InvestigationError("Reactor could not start an investigation history.")
                state = {"key": key, "reactor_history": response["history_id"]}
            else:
                revision["memory_action"] = "continued"
            state.update(as_of=question["iso"], sources=eligible)
            atomic_json(state_path, state)
            revision["reactor_history"] = state["reactor_history"]
            evidence_path = path.parent / "requests" / (revision["id"] + ".evidence.json")
            atomic_json(evidence_path, evidence)
            for field, text in texts.items():
                request_question = {
                    **question,
                    "question_id": f"{doc['id']}_{revision['id']}_{field}",
                }
                record = {
                    "retrieval": {
                        **copy.deepcopy(retrieval),
                        "question": request_question,
                    },
                    "reactor_history": state["reactor_history"],
                }
                revision[field] = record

                def transmit(
                    body,
                    kind,
                    field=field,
                    request_question=request_question,
                    record=record,
                ):
                    request = {
                        "section": field,
                        "kind": kind,
                        "question": body,
                        "message_chars": size(body),
                        "started_at": time.time(),
                        "result": {"status": "pending"},
                    }
                    revision["requests"].append(request)
                    atomic_json(path, doc)
                    args = [
                        "--history",
                        state["reactor_history"],
                        "--question",
                        body,
                        "--question-date",
                        question["question_date"],
                        "--question-id",
                        request_question["question_id"],
                        "--max-chars",
                        str(self.config.max_message_chars),
                    ]
                    if evidence:
                        args += ["--evidence", str(evidence_path)]
                    result = adapter.call(*args)
                    request.update(result=result, finished_at=time.time())
                    record["result"] = checked_result(result, request_question, evidence, self.store)
                    atomic_json(path, doc)

                transmit(text, "initial")
                # A completed but invalid response gets ONE correction, shared by
                # citation and schema validation. Never resend an uncertain request.
                for correction in range(2):
                    result = record["result"]
                    error = None
                    if result.get("status") == "answered" and field == "decision_record" and not result.get("abstained"):
                        _, error = validate_decision(result["answer"], evidence)
                    uncited = result.get("error") == "Factual answer has no source citations."
                    if correction == 0 and (error or uncited):
                        transmit(citation_repair_question(text) + (DECISION_REPAIR if field == "decision_record" else ""),
                                 "decision_repair" if error else "citation_repair")
                        continue
                    if result.get("status") != "answered":
                        raise InvestigationError(
                            f"{field.replace('_record', '').capitalize()} generation did not complete with valid citations."
                        )
                    if error:
                        record["validation_error"] = error
                        raise InvestigationError(error)
                    break
            old_sources = {e["id"] for e in parent["retrieval"]["evidence"]}
            new_sources = {e["id"] for e in evidence}

            def answer(rev, field):
                return (rev.get(field) or {}).get("result", {}).get("answer")

            revision["changes"] = {
                "answer_changed": answer(parent, "answer_record") != answer(revision, "answer_record"),
                "decision_changed": answer(parent, "decision_record") != answer(revision, "decision_record"),
                "sources_added": sorted(new_sources - old_sources),
                "sources_removed": sorted(old_sources - new_sources),
            }
            revision.update(status="complete", finished_at=time.time())
            doc["current_revision"] = revision["id"]
            atomic_json(path, doc)
        except Exception as error:
            revision.update(status="failed", error=str(error), finished_at=time.time())
            atomic_json(path, doc)
            # A failed/unknown response cannot be used as a base for continuation.
            atomic_json(state_path, {})
            raise InvestigationError(
                f"Revision saved as incomplete; the previous version is intact. {error}"
            ) from error
        return revision_report(report, doc, revision)
