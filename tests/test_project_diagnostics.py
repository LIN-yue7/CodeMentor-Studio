import pytest
from fastapi.testclient import TestClient
from app.workbench import create_workbench


@pytest.mark.parametrize('code,concept,word', [
    ('def total(scores)\n    return sum(scores)', 'python-suite', '冒号'),
    ('if True:\nprint(1)', 'python-indentation', '缩进'),
    ('values = [1, 2', 'python-delimiter', '配对'),
    ('typedef int (*calc)(int, int);', 'language-mismatch', 'C'),
    ('return 1', 'python-scope', '函数'),
    ('x = "abc', 'python-string', '引号'),
    ('await foo()', 'python-async', 'async def'),
])
def test_diagnostic_explains_evidence_without_execution(code, concept, word):
    with TestClient(create_workbench()) as client:
        client.post('/api/session')
        result = client.post('/api/code-inspection', json={'path':'main.py','code':code}).json()
        assert result['status'] == 'syntax-error'
        issue = result['issues'][0]
        assert issue.get('concept') == concept
        assert word in issue['why']
        assert issue['column'] >= 1
        assert issue['path'] == 'main.py'
        assert issue['fix'] and issue['prevention']
        assert '未执行' in issue['observed']
        assert '无法' in issue['intent'] or '可能' in issue['intent']


def test_c_text_in_a_valid_python_string_is_not_a_language_mismatch():
    with TestClient(create_workbench()) as client:
        client.post('/api/session')
        result = client.post('/api/code-inspection', json={
            'path':'main.py','code':'text = "typedef int foo;"\nraise RuntimeError("never run")'}).json()
        assert result['status'] == 'syntax-ok'
        assert result['issues'] == []


def test_project_can_inspect_full_allowed_file_size():
    with TestClient(create_workbench()) as client:
        client.post('/api/session')
        project = client.post('/api/projects', json={'name':'large'}).json()
        response = client.post('/api/projects/'+project['id']+'/context', json={
            'revision':0, 'path':'main.py', 'files':{'main.py':'# comment\n'*2000}})
        assert response.status_code == 200
        assert response.json()['status'] == 'syntax-ok'
