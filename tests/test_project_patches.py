import json
from fastapi.testclient import TestClient
from app.workbench import create_workbench
from app.core.llm_client import LLMResponse

class PatchModel:
    def __init__(self,before='    return None'):self.before=before
    async def chat(self,messages,**kw):
        data=json.loads(messages[-1].content)
        return LLMResponse(content=json.dumps({'explanation':'空列表返回None，调用方进行加法。','hints':['若需求为空列表返回0，修改返回值并验证。'],'citations':[s for s in data['snippets'] if s['path']=='helper.py'][:1], 'patches':[{'path':'helper.py','line':2,'before':self.before,'after':'    return 0','reason':'满足空输入按0处理的需求'}]}),model='stub')

def call(model):
    with TestClient(create_workbench(model=model)) as c:
        c.post('/api/session');p=c.post('/api/projects',json={'name':'patch'}).json();base='/api/projects/'+p['id']
        c.post(base+'/privacy',json={'allow_external':True})
        return c.post(base+'/review',json={'revision':0,'path':'main.py','files':{'main.py':'from helper import first\nprint(first([])+1)','helper.py':'def first(values):\n    return None'}}).json()

def test_grounded_patch_is_returned_for_approval_not_applied():
    result=call(PatchModel());assert result['status']=='accepted'
    assert result['review']['patches'][0]['before']=='    return None'
    assert result['claim_status']=='unverified'

def test_patch_cannot_replace_unprovided_source():
    result=call(PatchModel('    return secret'))
    assert result.get('failure_kind')=='invalid-patch'


def test_real_six_citation_response_is_valid_after_contract_alignment():
    from pathlib import Path
    from app.services.project_review import Review
    evidence=json.loads(Path('docs/evidence/studio-r7/live-03-fixed.json').read_text(encoding='utf-8'))
    value=Review.model_validate_json(evidence['capture']['final_output'])
    assert len(value.citations)==6
    available={(s['path'],s['line'],s['quote']) for s in evidence['preview']['snippets']}
    assert all((c.path,c.line,c.quote) in available for c in value.citations)
