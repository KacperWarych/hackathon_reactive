"""Install the verified report entry change, preserving originals for rollback."""
from pathlib import Path
import hashlib
import shutil
import tempfile

project = Path('/Users/kacperwarych/Desktop/hackathon reactive ai')
staged = Path(__file__).resolve().parent
expected = {'src/decision_memory/report_entry_ui.py': None, 'src/decision_memory/investigation_ui.py': 'de5242f8d24acd3992e6af9d6c2ff9f329dbf3b644c932bd08fa5aa58a540c61', 'tests/test_report_entry_ui.py': None, 'INVESTIGATIONS.md': 'b71f548661f3046fa19b8073307239f68e65c45e33c176b439711bf4216f1e8e'}
for name, checksum in expected.items():
    target = project / name
    actual = hashlib.sha256(target.read_bytes()).hexdigest() if target.exists() else None
    if actual != checksum:
        raise RuntimeError(f'{name} changed; rebase before installing')
backup = Path(tempfile.mkdtemp(prefix='reactive-report-entry-before-'))
for name in expected:
    target = project / name
    if target.exists():
        saved = backup / name
        saved.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(target, saved)
for name in expected:
    target = project / name
    temporary = target.with_suffix(target.suffix + '.report-entry.tmp')
    shutil.copy2(staged / name, temporary)
    temporary.replace(target)
print(f'Installed report entry capture and refresh. Original files: {backup}')
