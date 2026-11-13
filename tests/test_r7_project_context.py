from fastapi.testclient import TestClient
from app.workbench import create_workbench


def test_context_retrieves_relative_calls_docs_and_broken_imports():
    with TestClient(create_workbench()) as client:
        client.post('/api/session')
        p = client.post('/api/projects', json={'name':'rank'}).json()
        files = {'pkg/main.py':'from .helpers import calculate\nvalue = calculate(3)\nif True\n    pass\n',
                 'pkg/helpers.py':'# header\n' * 40 + 'def calculate(x):\n    return x + 1\n',
                 'README.md':'# Contract\ncalculate returns its argument plus one.\n',
                 'noise.py':'def irrelevant():\n    return 0\n',
                 'other.py':'def broken(:\n    pass\n'}
        data = client.post(f"/api/projects/{p['id']}/context", json={'revision':0, 'files':files, 'path':'pkg/main.py'}).json()
        assert data['context']['related_files'][0] == 'pkg/helpers.py'
        assert data['project_issues']['other.py'][0]['line'] == 1
        snippets = data['retrieval']['snippets']
        assert {'path':'pkg/helpers.py','line':41,'quote':'def calculate(x):'} in snippets
        assert any(s['path']=='README.md' for s in snippets)
        assert not any(s['path']=='noise.py' for s in snippets)
        assert data['retrieval']['candidates'][0]['reasons']


def test_text_override_and_explicit_python_are_respected():
    with TestClient(create_workbench()) as client:
        client.post('/api/session')
        p=client.post('/api/projects', json={'name':'language'}).json()
        base={'revision':0, 'files':{'main.py':'def broken(:'}, 'path':'main.py', 'language':'text'}
        data=client.post(f"/api/projects/{p['id']}/context", json=base).json()
        assert data['status']=='unsupported' and data['issues']==[]
        assert data['project_issues']['main.py']==[]
        base.update(files={'notes.txt':'def broken(:'}, path='notes.txt', language='python')
        data=client.post(f"/api/projects/{p['id']}/context", json=base).json()
        assert data['status']=='syntax-error'
        assert data['issues'][0]['path']=='notes.txt'


def test_saved_learning_is_deduped_ordered_persistent_and_owner_scoped():
    app=create_workbench()
    with TestClient(app) as client, TestClient(app) as other:
        client.post('/api/session'); other.post('/api/session')
        p=client.post('/api/projects', json={'name':'before'}).json()
        url=f"/api/projects/{p['id']}"
        broken={'revision':0, 'files':{'main.py':'def f()\n    pass\n'}}
        assert client.post(url, json={**broken,'name':'renamed'}).json()['name']=='renamed'
        ctx={**broken,'revision':1,'path':'main.py'}
        for _ in range(2): assert client.post(url+'/context',json=ctx).status_code==200
        items=client.get(url+'/learning').json()['items']
        assert len([x for x in items if x['kind']=='syntax-error'])==1
        assert client.post(url+'/learning-action',json={'path':'main.py','action':'hint-viewed'}).status_code==200
        assert client.post(url+'/learning-action',json={'path':'main.py','action':'hint-viewed'}).status_code==200
        assert client.post(url, json={'revision':1,'files':{'main.py':'def f():\n    pass\n'}}).status_code==200
        assert client.post(url+'/context',json=ctx).status_code==200  # stale drafts cannot reset saved state
        items=client.get(url+'/learning').json()['items']
        assert len([x for x in items if x['kind']=='syntax-rechecked'])==1
        assert len([x for x in items if x['kind']=='hint-viewed'])==1
        assert all(x['path']=='main.py' and x['concept'] and x['message'] for x in items)
        assert other.get(url+'/learning').status_code==404
        assert other.post(url+'/learning-action',json={'path':'main.py','action':'hint-viewed'}).status_code==404
        assert client.post(url+'/learning-action',json={'path':'missing.py','action':'hint-viewed'}).status_code==422


def test_review_preview_does_not_fabricate_learning_observations():
    with TestClient(create_workbench()) as client:
        client.post('/api/session')
        p=client.post('/api/projects', json={'name':'preview'}).json()
        url=f"/api/projects/{p['id']}"
        response=client.post(url+'/review-preview',json={'revision':0,'files':{'main.py':'def f(:'},'path':'main.py'})
        assert response.status_code==200
        assert client.get(url+'/learning').json()['items']==[]
        assert client.get(url+'/learning').json()['summary']['status']=='insufficient'
