import json
from pathlib import Path
import pytest
from app.services.project_retrieval import retrieve_project

CASES = json.loads((Path(__file__).parents[1] / 'evaluation/studio-r8/retrieval-cases.json').read_text(encoding='utf-8'))['cases']

@pytest.mark.parametrize('case', CASES, ids=lambda c: c['id'])
def test_relevant_lines_and_bound_imports(case):
    result = retrieve_project(**{k: case[k] for k in ['files','path','cursor_line','request','language','issues']})
    actual = {(s['path'],s['line']) for s in result['snippets']}
    assert {(s['path'],s['line']) for s in case['relevant_lines']} <= actual
    if case['theme'] in ['duplicate symbols and aliases','relative imports','large unrelated context']:
        assert not any(s['path'].startswith(('decoy','noise','other')) for s in result['snippets'])
    for s in result['snippets']:
        assert s['quote'] == case['files'][s['path']].splitlines()[s['line']-1]

def test_cursor_scope_does_not_pull_unrelated_function_import():
    files = {'main.py':'from a import relevant\nfrom b import unused\ndef focus():\n    return relevant()\n\ndef elsewhere():\n    return unused()\n', 'a.py':'def relevant():\n    return 1\n','b.py':'def unused():\n    return 2\n'}
    result=retrieve_project(files,'main.py',4)
    assert any(s['path']=='a.py' for s in result['snippets'])
    assert not any(s['path']=='b.py' for s in result['snippets'])

def test_error_line_precedes_cursor_under_budget_and_remains_exact():
    files={'main.py':'# pad\n'*40+'if True\n    pass\n'}
    result=retrieve_project(files,'main.py',1,issues=[{'line':41}],max_chars=7)
    assert result['snippets'][0]=={'path':'main.py','line':41,'quote':'if True'}
    assert sum(len(s['quote']) for s in result['snippets'])<=7

def test_bounds_and_determinism():
    case=CASES[-1]
    args={k:case[k] for k in ['files','path','cursor_line','request','language','issues']}
    first=retrieve_project(**args,max_chars=60,max_candidates=2)
    assert first==retrieve_project(**args,max_chars=60,max_candidates=2)
    assert len(first['candidates'])<=2
    assert sum(len(s['quote']) for s in first['snippets'])<=60
    assert len(first['snippets'])<=160
    assert all(len(s['quote'])<=500 for s in first['snippets'])
