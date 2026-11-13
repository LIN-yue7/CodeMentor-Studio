import httpx
from app.core.llm_client import GenericLLMClient,LLMClientConfig
from app.services.project_review import review
from app.services.workbench_tutor import Tutor

async def test_project_text_fallback_has_one_attempt_despite_legacy_retry_config():
    requests=[]
    def handler(request):
        requests.append(request)
        return httpx.Response(429,json={'error':{'message':'rate limited'}})
    model=GenericLLMClient(LLMClientConfig(model_name='fixture',base_url='https://example.test/v1',api_key='fixture',max_retries=4,retry_backoff_seconds=0),transport=httpx.MockTransport(handler))
    try:
        tutor=Tutor(model=model)
        result=await review(tutor,'owner',{'snippets':[],'buffer_hash':'fixture'},'collaborate',use_tools=False)
        assert result['status']=='failed'
        assert len(requests)==1
        assert model._config.max_retries==4
    finally:await model.aclose()
