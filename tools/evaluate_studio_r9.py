"""Evaluate repository-owned synthetic fixtures, never arbitrary uploaded projects.

Reference CPython runs are test-only and separate from the product interpreter.
This command has no model client, credentials, or paid request path.
"""
import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def evaluate(output):
    source = ROOT / 'evaluation/studio-r9/holdout.json'
    dataset = json.loads(source.read_text(encoding='utf-8'))
    output.mkdir(parents=True, exist_ok=False)
    results = []
    for case in dataset['cases']:
        with tempfile.TemporaryDirectory(prefix='codementor-reference-') as folder:
            directory = Path(folder)
            for name, code in case['files'].items():
                target = (directory / name).resolve()
                if not target.is_relative_to(directory.resolve()):
                    raise ValueError('fixture path escaped temporary directory')
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(code, encoding='utf-8')
            completed = subprocess.run([sys.executable, '-B', case['path']], cwd=directory,
                                       capture_output=True, text=True, timeout=5)
            expected = case['expected']
            passed = (completed.returncode == 0 and completed.stdout == expected['stdout']) if 'stdout' in expected else (
                completed.returncode != 0 and expected['error'] + ':' in completed.stderr)
            results.append({'case_id': case['id'], 'provenance': 'deterministic-reference-cpython',
                            'reference_matches': passed, 'returncode': completed.returncode,
                            'stdout': completed.stdout, 'stderr': completed.stderr,
                            'model_status': 'not-run'})
    (output / 'raw-results.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    summary = {'dataset_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
               'cases': len(results), 'reference_matches': sum(r['reference_matches'] for r in results),
               'real_model_requests': 0, 'protocol_acceptance': None, 'location_accuracy': None,
               'root_cause_correctness': None, 'repair_effectiveness': None, 'bad_repair_fraction': None,
               'cross_file_completion': None, 'model_failure_reasons': {},
               'boundary': 'CPython fixture checks establish expected behavior only. Model semantic metrics await raw live outputs and human judgments.'}
    (output / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False))
    return all(r['reference_matches'] for r in results)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='New evidence directory; existing output is never overwritten')
    args = parser.parse_args()
    raise SystemExit(0 if evaluate(args.output) else 1)
