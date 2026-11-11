import json
from fastapi.testclient import TestClient
from app.workbench import create_workbench
from app.core.llm_client import LLMResponse
class Model:
    def __init__(self): self.calls=0
    async def chat(self,messages,**kwargs):
        self.calls+=1
        data=json.loads(messages[-1].content)
        return LLMResponse(content=json.dumps({'explanation':'检查返回值约定，问题待验证。','hints':['预期返回什么？'],'citations':[data['snippets'][0]]}),model='stub')

def test_project_review_requires_revocable_permission_and_valid_evidence():
    model=Model()
    with TestClient(create_workbench(model=model)) as a:
        a.post('/api/session')
        p=a.post('/api/projects',json={'name':'review'}).json(); base='/api/projects/'+p['id']
        body={'files':{'main.py':'value = 3\n'},'revision':0,'path':'main.py','cursor_line':1,'mode':'mentor'}
        assert a.post(base+'/review',json=body).status_code==403 and model.calls==0
        assert a.post(base+'/review-preview',json=body).json()['snippets'][0]['quote']=='value = 3'
        assert model.calls==0
        a.post(base+'/privacy',json={'allow_external':True})
        r=a.post(base+'/review',json=body).json()
        assert r['status']=='accepted' and r['mode']=='simulated' and r['claim_status']=='unverified'
        a.post(base+'/privacy',json={'allow_external':False})
        assert a.post(base+'/review',json=body).status_code==403 and model.calls==1

class BadModel(Model):
    async def chat(self,messages,**kwargs):
        return LLMResponse(content=json.dumps({'explanation':'bad','hints':['hint'],'citations':[{'path':'private.py','line':1,'quote':'invented'}]}),model='stub')

def test_model_cannot_invent_project_citations():
    with TestClient(create_workbench(model=BadModel())) as a:
        a.post('/api/session'); p=a.post('/api/projects',json={'name':'bad'}).json(); base='/api/projects/'+p['id']
        a.post(base+'/privacy',json={'allow_external':True})
        r=a.post(base+'/review',json={'files':{'main.py':'x = 1'},'revision':0,'path':'main.py','cursor_line':1}).json()
        assert r['status']=='failed' and r['review'] is None
