"""Package complete Reactor predictions and an explicit allowlist of runnable source."""
from __future__ import annotations

import argparse
import shutil
import tarfile
from pathlib import Path

from decision_memory.reactor import export_predictions
from decision_memory.store import Store

ROOT = Path(__file__).resolve().parents[1]


def package(run_id, output):
    output = Path(output)
    store = Store()
    try:
        report = export_predictions(store, run_id, output / "predictions.jsonl")
    finally:
        store.close()
    if not report["submission_ready"]:
        raise RuntimeError("Only a complete test run can be packaged for submission.")
    files = [ROOT / name for name in (
        "README.md", "PRESENTATION.md", "NOTICE.md", "pyproject.toml", "uv.lock",
        "models.lock.json", ".env.example", "app.py", "ui.css",
    )]
    for directory in ("src", "tests", "scripts"):
        files.extend(sorted((ROOT / directory).rglob("*.py")))
    files.append(ROOT / "scripts/setup.sh")
    temporary = output / "code.tar.gz.tmp"
    with tarfile.open(temporary, "w:gz") as archive:
        for path in files:
            if path.is_symlink():
                raise RuntimeError(f"Refusing source symlink: {path}")
            archive.add(path, arcname=str(Path("decision-memory") / path.relative_to(ROOT)), recursive=False)
    temporary.replace(output / "code.tar.gz")
    shutil.copyfile(ROOT / "PRESENTATION.md", output / "PRESENTATION.md")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--out", type=Path, default=ROOT / ".data/submission")
    args = parser.parse_args()
    report = package(args.run_id, args.out)
    print(f"Packaged {report['written']} predictions, code.tar.gz and PRESENTATION.md in {args.out}")


if __name__ == "__main__":
    main()
