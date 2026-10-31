"""Resume live validation, then wait for offline preparation and complete the test run."""
import argparse
import json
import time

from decision_memory.cli import selected_mode
from decision_memory.config import Config, atomic_json, data_root, load_env
from decision_memory.evaluation import evaluate_answers
from decision_memory.models import Models
from decision_memory.reactor import credentials, export_predictions, run_questions
from decision_memory.retrieval import Retriever
from decision_memory.store import Store


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wait-hours", type=float, default=8,
                        help="Maximum time to wait for indexing or an idle agent (default: 8)")
    args = parser.parse_args()
    if args.wait_hours <= 0:
        parser.error("--wait-hours must be positive")
    load_env()
    credentials()
    config = Config()
    mode = selected_mode("selected", config)
    store = Store()
    retriever = Retriever(store, Models(config), config)
    deadline = time.monotonic() + args.wait_hours * 3600

    def run(questions, run_id):
        waiting = False
        while True:
            try:
                return run_questions(store, retriever, questions, run_id, mode)
            except RuntimeError as error:
                # Lock refusal happens before sending anything. All other failures require review.
                if str(error) != "This Reactor agent is in use by another run. Wait until it finishes.":
                    raise
                if time.monotonic() >= deadline:
                    raise TimeoutError("Timed out waiting for the Reactor agent to become idle.") from error
                if not waiting:
                    print("Waiting for the Reactor agent to become idle.", flush=True)
                    waiting = True
                time.sleep(10)

    try:
        manifest = json.loads((data_root()/"manifests"/"validation.json").read_text())
        print("Starting live validation with", mode, flush=True)
        validation = run(store.questions("dev", manifest["question_ids"]), "validation-live")
        print(evaluate_answers(store, "validation-live"), flush=True)
        export_predictions(store, "validation-live", data_root()/"runs"/"validation-live"/"predictions.jsonl")
        print("Validation complete. Waiting for offline stress evaluation and test indexing.", flush=True)
        summary_path = data_root()/"evaluation"/"offline-summary.json"
        while True:
            summary = json.loads(summary_path.read_text()) if summary_path.exists() else {}
            if summary.get("config") == config.fingerprint:
                break
            if time.monotonic() >= deadline:
                raise TimeoutError("Offline preparation did not finish within the wait window. Resume this script later.")
            time.sleep(30)
        if selected_mode("selected", config) != mode:
            raise RuntimeError("Frozen method changed during live validation. Review the selection before continuing.")
        questions = store.questions("test")
        if len(questions) != 146:
            raise RuntimeError("Expected all 146 official test questions before starting the final run.")
        print("Starting the complete 146-question test run.", flush=True)
        test = run(questions, "test-final")
        exported = export_predictions(store, "test-final", data_root()/"submission"/"predictions.jsonl")
        atomic_json(data_root()/"runs"/"benchmark-summary.json", {
            "config": config.fingerprint, "mode": mode,
            "validation": validation, "test": test, "export": exported})
        print(exported, flush=True)
    finally:
        store.close()


if __name__ == "__main__":
    main()
