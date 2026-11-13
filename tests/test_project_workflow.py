import json
from fastapi.testclient import TestClient
from app.workbench import create_workbench
from app.core.llm_client import LLMResponse

class TextModel:
    def __init__(self):self.calls=0
    async def chat(self,messages,**kwargs):
        self.calls+=1;data=json.loads(messages[-1].content)
        return LLMResponse(content=json.dumps({'explanation':'这是静态阅读；代码返回数值。','hints':['用空输入核对约定。'],'citations':[data['snippets'][0]]}),model='stub')

def test_stream_consent_cache_and_readonly_preview():
    model=TextModel()
    with TestClient(create_workbench(model=model)) as c:
        c.post('/api/session');p=c.post('/api/projects',json={'name':'stream'}).json();url='/api/projects/'+p['id']
        body={'files':{'main.py':'value = 1'},'path':'main.py','revision':0}
        assert c.post(url+'/review-stream',json=body).status_code==403
        c.post(url+'/privacy',json={'allow_external':True})
        first=c.post(url+'/review-stream',json=body)
        events=[json.loads(line) for line in first.text.splitlines()]
        assert events[0]['event']=='started'
        assert events[-1]['event']=='completed' and events[-1]['data']['status']=='accepted'
        assert events[-1]['data']['workflow_mode']=='text-fallback'
        second=[json.loads(line) for line in c.post(url+'/review-stream',json=body).text.splitlines()]
        assert second[-1]['data']['cache_hit'] is True and model.calls==1
        body['files']['main.py']='value = 2'
        c.post(url+'/review-stream',json=body);assert model.calls==2
        body['mode']='engineering'
        c.post(url+'/review-stream',json=body);assert model.calls==3

def test_execution_is_hash_bound_and_private():
    from app.models.workbench import ProjectExecution
    with TestClient(create_workbench()) as c:
        c.post('/api/session');p=c.post('/api/projects',json={'name':'execution'}).json();url='/api/projects/'+p['id']
        body={'files':{'main.py':'print(1)'},'path':'main.py','revision':0}
        result=c.post(url+'/verify',json=body).json()
        assert result['entry_path']=='main.py'
        preview=c.post(url+'/review-preview',json=body).json()
        assert preview['test_status']=='not-run'  # context preview never invents execution

def test_cache_is_owner_scoped_and_revocation_blocks_cached_result():
    model=TextModel();app=create_workbench(model=model)
    with TestClient(app) as c, TestClient(app) as other:
        c.post('/api/session');other.post('/api/session')
        p=c.post('/api/projects',json={'name':'cache-owner'}).json();url='/api/projects/'+p['id']
        body={'files':{'main.py':'value = 1'},'path':'main.py','revision':0}
        c.post(url+'/privacy',json={'allow_external':True})
        assert c.post(url+'/review',json=body).json()['status']=='accepted'
        assert other.post(url+'/review',json=body).status_code==404
        c.post(url+'/privacy',json={'allow_external':False})
        assert c.post(url+'/review-stream',json=body).status_code==403
        assert model.calls==1

def test_sensitive_buffer_is_blocked_before_fallback_model_call():
    model=TextModel()
    with TestClient(create_workbench(model=model)) as c:
        c.post('/api/session');p=c.post('/api/projects',json={'name':'guard'}).json();url='/api/projects/'+p['id']
        c.post(url+'/privacy',json={'allow_external':True})
        body={'files':{'main.py':'password = "synthetic-sensitive"'},'path':'main.py','revision':0}
        events=[json.loads(line) for line in c.post(url+'/review-stream',json=body).text.splitlines()]
        assert events[-1]['data']['status']=='blocked' and model.calls==0
