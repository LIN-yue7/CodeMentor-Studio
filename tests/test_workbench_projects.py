from fastapi.testclient import TestClient
from app.workbench import create_workbench


def test_projects_isolate_and_detect_stale_save():
    with TestClient(create_workbench()) as a, TestClient(create_workbench()) as b:
        a.post('/api/session'); b.post('/api/session')
        p = a.post('/api/projects',json={'name':'My project'}).json()
        assert 'id' in p
        assert b.get('/api/projects/'+p['id']).status_code == 404
        body={'revision':0,'files':{'main.py':'x = 1\n','lib/helper.py':'def f():\n    return 2\n'}}
        r=a.post('/api/projects/'+p['id'],json=body)
        assert r.status_code==200 and r.json()['revision']==1
        assert a.post('/api/projects/'+p['id'],json=body).status_code==409
        assert a.get('/api/projects/'+p['id']).json()['files']==body['files']
        assert b.get('/api/projects').json()['items']==[]
        body['revision']=1; body['files']={'../secret.py':'x'}
        assert a.post('/api/projects/'+p['id'],json=body).status_code==422


def test_live_analysis_reports_arbitrary_python_without_execution():
    with TestClient(create_workbench()) as a:
        a.post('/api/session')
        r=a.post('/api/code-inspection',json={'path':'any.py','code':'def custom(:\n pass'}).json()
        assert r['status']=='syntax-error' and r['issues'][0]['line']==1
        r=a.post('/api/code-inspection',json={'path':'any.py','code':'raise RuntimeError("must not execute")'}).json()
        assert r['status']=='syntax-ok'
        assert a.post('/api/code-inspection',json={'path':'style.css','code':'body {}'}).json()['status']=='unsupported'
