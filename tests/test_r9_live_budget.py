import pytest
from app.core.llm_client import LLMResponse
from tools.evaluate_studio_r9_live import CountedClient, BudgetStop

class LocalResponse:
    calls=0
    async def chat_once(self,messages,**kwargs):
        self.calls+=1
        return LLMResponse(content='{}',model='simulated')

@pytest.mark.asyncio
async def test_r9_budget_counts_each_actual_request_and_stops_at_28(tmp_path):
    local=LocalResponse();client=CountedClient(local,tmp_path)
    for _ in range(28):await client.chat_once([],max_tokens=2400)
    with pytest.raises(BudgetStop):await client.chat_once([],max_tokens=2400)
    assert local.calls==28
    assert len(list(tmp_path.glob('request-*.json')))==28

@pytest.mark.asyncio
async def test_r9_budget_reserves_full_input_before_request(tmp_path):
    local=LocalResponse();client=CountedClient(local,tmp_path)
    with pytest.raises(BudgetStop):await client.chat_once([{'role':'user','content':'x'*2000000}])
    assert local.calls==0

@pytest.mark.asyncio
async def test_r9_budget_reloaded_across_output_directories(tmp_path):
    one=tmp_path/'one';two=tmp_path/'two';one.mkdir();two.mkdir()
    ledger=tmp_path/'shared.json';local=LocalResponse()
    first=CountedClient(local,one,ledger)
    for _ in range(28):await first.chat_once([])
    resumed=CountedClient(local,two,ledger)
    with pytest.raises(BudgetStop):await resumed.chat_once([])
    assert local.calls==28

@pytest.mark.asyncio
async def test_explicit_transport_does_not_follow_provider_redirect():
    import httpx
    from app.core.llm_client import GenericLLMClient, LLMClientConfig, LLMError
    requests=[]
    def redirect(request):
        requests.append(str(request.url))
        return httpx.Response(307,headers={'location':'https://unexpected.example/completions'})
    model=GenericLLMClient(LLMClientConfig(model_name='deepseek-flash',base_url='https://api.deepseek.com/v1',api_key='synthetic',max_retries=0),transport=httpx.MockTransport(redirect))
    try:
        with pytest.raises(LLMError):await model.chat_once([])
        assert requests==['https://api.deepseek.com/v1/chat/completions']
    finally:await model.aclose()

@pytest.mark.parametrize('content',['{}','{"used":0,"reserved_cny":NaN}','{"used":-1,"reserved_cny":0}'])
def test_invalid_persistent_ledger_cannot_reset_authorization(tmp_path,content):
    ledger=tmp_path/'budget.json';ledger.write_text(content)
    with pytest.raises(ValueError):CountedClient(LocalResponse(),tmp_path,ledger)
