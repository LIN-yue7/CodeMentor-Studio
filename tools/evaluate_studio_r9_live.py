"""R9 authorized synthetic live evaluation with a separate, fail-closed budget.

Requires --allow-paid and an explicit private env path. Never uses R8 allowances.
A fresh evidence directory is required. All HTTP attempts reserve worst-case cost.
"""
import argparse
import asyncio
from dataclasses import asdict
import json
import math
import hashlib
import httpx
from pathlib import Path
from time import perf_counter

from app.core.llm_client import GenericLLMClient, LLMClientConfig, LLMError

class BudgetStop(LLMError):
    pass


class CountedClient:
    def __init__(self, client, output, ledger_path=None):
        self.client = client
        self.output = output
        self.ledger_path = ledger_path or output / 'budget.json'
        previous = json.loads(self.ledger_path.read_text(encoding='utf-8')) if self.ledger_path.exists() else {}
        if self.ledger_path.exists():
            if (type(previous.get('used')) is not int or not 0 <= previous['used'] <= 28
                    or type(previous.get('reserved_cny')) not in (int, float)
                    or not math.isfinite(previous['reserved_cny'])
                    or not 0 <= previous['reserved_cny'] <= 5):
                raise ValueError('Invalid authorization ledger; reconcile before resuming')
        self.used = previous.get('used', 0)
        self.reserved_cny = previous.get('reserved_cny', 0.0)
        self.last_error = None

    async def request(self, method, messages, **kwargs):
        kwargs.pop('model', None)
        kwargs['max_tokens'] = 2400
        kwargs['temperature'] = 0
        payload = [m.to_payload() if hasattr(m, 'to_payload') else m for m in messages]
        # UTF-8 bytes plus envelope allowance conservatively bound input tokens.
        input_bound = len(json.dumps({'messages': payload, **kwargs}, ensure_ascii=False).encode()) + 2048
        reserve = (input_bound * 0.30 + 2400 * 1.20) / 1_000_000 * 10
        if self.used >= 28 or self.reserved_cny + reserve > 5:
            raise BudgetStop('R9 authorized request or cost limit reached')
        self.used += 1
        self.reserved_cny += reserve
        ledger = {'authorization':'User explicitly approved 28 new HTTP requests, CNY5, deepseek-flash non-thinking, 2400 output tokens, retries0',
                  'used': self.used, 'reserved_cny': self.reserved_cny, 'cap_cny':5,
                  'pricing':'USD0.30/M input, USD1.20/M output; conservative CNY10/USD allowance; failures retain full reservation'}
        temporary = self.ledger_path.with_suffix('.tmp')
        temporary.write_text(json.dumps(ledger,indent=2),encoding='utf-8')
        temporary.replace(self.ledger_path)
        (self.output/'budget.json').write_text(json.dumps(ledger,indent=2),encoding='utf-8')
        target=self.output/f'request-{self.used:03}.json'
        record={'request_index':self.used,'method':method,'messages':payload,'kwargs':kwargs,'status':'started','model':'deepseek-flash','thinking':'disabled','reserved_cny':reserve}
        target.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
        started=perf_counter()
        try:
            response=await getattr(self.client,method)(messages,**kwargs)
            record.update(status='returned',content=response.content,usage=asdict(response.usage),model=response.model,finish_reason=response.finish_reason)
            if method=='chat_tools':
                record.update(tool_calls=response.tool_calls,assistant_message=response.assistant_message)
            return response
        except BaseException as exc:
            self.last_error = type(exc).__name__
            record.update(status='failed',error_type=self.last_error)
            raise
        finally:
            record['elapsed_ms']=round((perf_counter()-started)*1000)
            target.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')

    async def chat_once(self,messages,**kwargs):
        return await self.request('chat_once',messages,**kwargs)

    async def chat(self,messages,**kwargs):
        return await self.chat_once(messages,**kwargs)

    async def chat_tools(self,messages,tools,**kwargs):
        return await self.request('chat_tools',messages,tools=tools,**kwargs)


async def run(args):
    from dotenv import dotenv_values
    from app.services.workbench_tutor import Tutor
    from app.services.project_review import bundle,review
    from app.services.project_retrieval import retrieve_project
    from app.services.project_verification import verify
    from app.api.workbench_projects import ReviewInput,inspect_project
    values=dotenv_values(args.env_file)
    key=values.get('LLM__MODELS__DEEPSEEK__API_KEY') or values.get('LLM__API_KEY')
    if not key:raise SystemExit('No configured DeepSeek key; no requests sent')
    args.output.mkdir(parents=True,exist_ok=False)
    client=GenericLLMClient(LLMClientConfig(model_name='deepseek-flash',base_url='https://api.deepseek.com/v1',api_key=key,thinking_mode='disabled',max_retries=0,max_tokens=2400,temperature=0,timeout_seconds=24), transport=httpx.AsyncHTTPTransport(retries=0))
    counted=CountedClient(client,args.output,Path('docs/evidence/studio-r9/live-budget.json'))
    initial_used = counted.used
    old=json.loads(Path('evaluation/studio-r8/model-cases.json').read_text(encoding='utf-8-sig'))
    old=old['cases'] if isinstance(old,dict) else old
    regression=[c for c in old if c['id'] in {'scope-shadow','correct-scope','return-none'}]
    holdout=json.loads(Path('evaluation/studio-r9/holdout.json').read_text(encoding='utf-8'))['cases']
    jobs=[(c,False,'development-regression') for c in regression]+[(c,False,'holdout') for c in holdout]+[(c,True,'holdout-tools') for c in holdout if c['id'] in {'aliased-call','relative-call','wrong-arity'}]
    if args.regressions_only:
        jobs = jobs[:3]
    manifest = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(Path('app/services').glob('project_*.py'))}
    (args.output/'source-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    results=[]
    try:
        for case,tools,group in jobs:
            files=case['files'];path=case.get('path','main.py')
            payload=ReviewInput(files=files,path=path,revision=0,cursor_line=case.get('cursor_line',1),request=case.get('request','请定位并解释有证据的问题；正确代码不编造错误。'),use_tools=tools)
            local=inspect_project(files,path,'auto')
            retrieval=retrieve_project(files,path,payload.cursor_line,payload.request,issues=local[path]['issues'])
            data=bundle(payload,{**local[path],'context':{'related_files':retrieval['related_files']},'retrieval':retrieval})
            execution={**verify(files,path),'entry_path':path}
            snapshot={'files':files,'path':path,'cursor_line':payload.cursor_line,'buffer_hash':data['buffer_hash'],'diagnostics':[i for v in local.values() for i in v['issues']],'learning_history':[],'execution_result':execution}
            tutor=Tutor(model=counted);tutor.mode='live';before=counted.used
            result=await review(tutor,'r9-synthetic',data,'collaborate',snapshot=snapshot,use_tools=tools)
            results.append({'case_id':case['id'],'group':group,'provenance':'real-model' if counted.used > before else 'local-budget-gate','files':files,'request':payload.request,'expected':case.get('expected',{}),'result':result,'request_indices':list(range(before+1,counted.used+1)),'semantic_review':'pending'})
            (args.output/'results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
            print(case['id'],group,result['status'],result.get('failure_kind',''),flush=True)
            if counted.used>=28 or counted.used==before or counted.last_error=='LLMAuthError':break
    finally:
        await client.aclose()
        (args.output/'summary.json').write_text(json.dumps({'actual_requests':counted.used-initial_used,'cumulative_authorized_requests':counted.used,'reserved_cny':counted.reserved_cny,'completed_jobs':len(results),'protocol_accepted':sum(x['result']['status']=='accepted' for x in results),'semantic_metrics':'pending independent review'},indent=2),encoding='utf-8')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--allow-paid',action='store_true')
    parser.add_argument('--regressions-only',action='store_true')
    parser.add_argument('--env-file',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if not args.allow_paid or not args.env_file:parser.error('Explicit paid authorization and private env path required')
    lock_path = Path('docs/evidence/studio-r9/live-budget.lock')
    with lock_path.open('x') as lock:
        try:
            asyncio.run(run(args))
        finally:
            lock.close()
            lock_path.unlink()
