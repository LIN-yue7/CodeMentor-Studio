from fastapi.testclient import TestClient
from app.workbench import create_workbench


def test_saved_modification_is_observable_without_exporting_source(sqlite_path):
    with TestClient(create_workbench()) as client:
        client.post('/api/session')
        project = client.post('/api/projects', json={'name': 'trial'}).json()
        route = '/api/projects/' + project['id']
        client.post(route, json={'revision': 0, 'files': {'main.py': 'print(1)'}})
        client.post(route, json={'revision': 1, 'files': {'main.py': 'print(2)'}})
        events = client.get(route + '/learning').json()['items']
        modifications = [e for e in events if e['kind'] == 'saved-modification']
        assert len(modifications) == 1
        assert modifications[0]['revision'] == 2
        assert 'print(2)' not in str(modifications)
        client.post(route, json={'revision': 2, 'files': {'main.py': 'print(2)'}})
        events = client.get(route + '/learning').json()['items']
        assert len([e for e in events if e['kind'] == 'saved-modification']) == 1
