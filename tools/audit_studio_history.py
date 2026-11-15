"""Read-only full reachable Git object audit. Findings never include matched secrets."""
import hashlib
import importlib.metadata
import json
import re
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parents[1]
def git(*args):
    return subprocess.check_output(['git', *args], cwd=root)

objects = git('rev-list', '--objects', '--all').decode().splitlines()
patterns = {
    'private-key': re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
    'provider-key': re.compile(rb'\b(?:sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{30,})'),
    'assigned-credential': re.compile(rb'(?im)^\s*(?:LLM__API_KEY|API_KEY|CODEMENTOR_SESSION_SECRET|PASSWORD)\s*=\s*[^\s#][^\r\n]{7,}'),
    'sqlite': re.compile(rb'^SQLite format 3\x00'),
}
findings = []
blobs = 0
for entry in objects:
    oid, _, path = entry.partition(' ')
    if git('cat-file', '-t', oid).strip() != b'blob':
        continue
    blobs += 1
    content = git('cat-file', 'blob', oid)
    for rule, pattern in patterns.items():
        if pattern.search(content):
            findings.append({'object': oid, 'path': path, 'rule': rule, 'sha256': hashlib.sha256(content).hexdigest()})
report = {'scope': 'All objects reachable from all local refs, including historical blobs',
          'commits': int(git('rev-list', '--count', '--all')), 'blobs': blobs,
          'findings': findings,
          'limits': 'Pattern scan does not establish absence of all secrets or personal data. Findings need source review. Unreachable Git objects and private working files excluded.'}
Path('docs/evidence/studio-r9/history-audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
licenses = []
for dist in importlib.metadata.distributions():
    meta=dist.metadata
    licenses.append({'name': meta['Name'], 'version': dist.version, 'license': meta.get('License-Expression') or meta.get('License') or 'UNDECLARED',
                     'classifiers':[x for x in meta.get_all('Classifier',[]) if x.startswith('License ::')]})
Path('docs/evidence/studio-r9/python-dependencies.json').write_text(json.dumps(sorted(licenses,key=lambda x:x['name'].lower()),ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'commits': report['commits'], 'blobs': blobs, 'findings':len(findings)}))
