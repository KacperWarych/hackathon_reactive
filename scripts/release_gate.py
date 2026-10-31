"""Record an offline, fake-transport release gate against source and installed code.

Run with .venv/bin/python scripts/release_gate.py after frozen package reinstall.
Each invocation writes a fresh namespace and never reads old evaluation scores.
"""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    import decision_memory

    namespace = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8]
    output = ROOT / 'outputs' / 'hackathon-release' / namespace
    output.mkdir(parents=True)
    installed = Path(decision_memory.__file__).parent
    source = ROOT / 'src' / 'decision_memory'
    files = sorted(source.rglob('*.py'))
    parity = all((installed / p.relative_to(source)).exists()
                 and sha(p) == sha(installed / p.relative_to(source)) for p in files)
    report = {
        'namespace': namespace, 'python': sys.version, 'installed_path': str(installed),
        'source_package_parity': parity, 'live_service_tested': False,
        'data': 'Temporary synthetic fixtures; no production corpus or model-weight inference.',
        'model_lock': json.loads((ROOT / 'models.lock.json').read_text()),
        'fingerprints': {str(p.relative_to(ROOT)): sha(p) for p in files +
                         sorted((ROOT / 'tests').glob('*.py')) +
                         [ROOT / 'app.py', ROOT / 'uv.lock', ROOT / 'models.lock.json']},
        'packages': {d.metadata['Name']: d.version for d in importlib.metadata.distributions()},
        'checks': [],
    }
    base_env = {k: v for k, v in os.environ.items() if k != 'PYTHONPATH'}
    for name, cmd, env in [
        ('source', [sys.executable, '-m', 'pytest', '-q'], {**base_env, 'PYTHONPATH': str(ROOT / 'src')}),
        ('installed', [sys.executable, '-m', 'pytest', '-q'], base_env),
        ('lint', [sys.executable, '-m', 'ruff', 'check', '--no-cache', 'src/decision_memory', 'app.py',
                  '--exclude', 'vendor'], base_env),
    ]:
        started = time.monotonic()
        result = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True)
        (output / f'{name}.log').write_text(result.stdout + result.stderr)
        report['checks'].append({'name': name, 'exit_code': result.returncode,
                                 'seconds': round(time.monotonic() - started, 3)})
        print(name, result.returncode, flush=True)
    report['passed'] = parity and all(c['exit_code'] == 0 for c in report['checks'])
    (output / 'release.json').write_text(json.dumps(report, indent=2) + '\n')
    print(output / 'release.json')
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
