from pathlib import Path
import hashlib, shutil, tempfile
base=Path('/Users/kacperwarych/Desktop/hackathon reactive ai')
stage=Path(__file__).resolve().parent/'report-entry-implementation'
expected={'app.py': 'cd2d521c36d57e9e4a8f642cbb1bc77d09e45e8394f9161aac8a4b03c11f9d6d', 'src/decision_memory/decision.py': '1e12e850cf14887b1bc1d15bcfb5603c62fe89c7a5b821bc02683e9f5515ef81', 'src/decision_memory/investigations.py': '0d4df91eb3a23cdb3fb8d79b73a990b5f3fd687a8c712ca04c91dbac7f5fa3e5', 'src/decision_memory/investigation_ui.py': '38b0aca160f2282c26e6a94f217fe6dd28744a6f981b36936acde3eb9c660b3f', 'tests/test_investigations.py': '4d7ed782b057598ca38896db073a17550372ce360ed5a283caaa7a5899b495dd', 'tests/test_investigation_ui.py': '1e91b2c1de8118da585b2bc534df9c1069e3c548f507d8fe0debdbca74581d2f', 'INVESTIGATIONS.md': '79bd0f9b778fe0cb88b3081629d28fad30b3bbff7867d9a039492cdeb1b159a9'}
for name, checksum in expected.items():
    if hashlib.sha256((base/name).read_bytes()).hexdigest()!=checksum:
        raise RuntimeError(f'{name} changed; rebase before installing')
backup=Path(tempfile.mkdtemp(prefix='decision-view-before-'))
for name in expected:
    saved=backup/name
    saved.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(base/name,saved)
for name in expected:
    target=base/name
    temporary=target.with_suffix(target.suffix+'.decision-fix.tmp')
    shutil.copy2(stage/name,temporary)
    temporary.replace(target)
print(f'Installed {len(expected)} files. Backup: {backup}')
