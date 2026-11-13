"""R8 synthetic live evaluation. No private config is read without --allow-paid.

Counts actual HTTP model requests (including tool rounds), never just user cases.
Append-only request evidence; use a fresh run directory to avoid accidental reuse.
"""
import argparse
import asyncio
import json
import os
from dataclasses import asdict
from pathlib import Path
from time import perf_counter

class BudgetExceeded(Exception):pass

async def run(args,cases):
    from app.core.llm_client import get_llm_client,close_llm_clients
    from app.services.workbench_tutor import Tutor
    from app.services.project_review import bundle,review
    from app.services.project_retrieval import retrieve_project
    from app.services.project_verification import verify
    from app.api.workbench_projects import ReviewInput,inspect_project
    args.output.mkdir(parents=True,exist_ok=False)
    used=0;captures=[]
    ledger=args.budget_ledger
    ledger.parent.mkdir(parents=True,exist_ok=True)
    lock=ledger.with_suffix('.lock')
    lock_handle=lock.open('x')
    budget=json.loads(ledger.read_text(encoding='utf-8')) if ledger.exists() else {'authorized_cap':42,'used':0,'authorization':'R8 user approved up to42 synthetic requests; max2400 output tokens; no retries'}
    class Counted:
        async def request(self,method,messages,**kwargs):
            nonlocal used
            if used>=args.max_requests or budget['used']>=42:raise BudgetExceeded('authorized request cap reached')
            used+=1;budget['used']+=1
            ledger.write_text(json.dumps(budget,ensure_ascii=False,indent=2),encoding='utf-8')
            record={'request_index':used,'global_request_index':budget['used'],'method':method,'messages':[m.to_payload() if hasattr(m,'to_payload') else m for m in messages],
                    'kwargs':kwargs,'status':'started'}
            target=args.output/f'request-{used:03}.json'
            target.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
            started=perf_counter()
            try:
                response=await getattr(get_llm_client(),method)(messages,**kwargs)
                record.update(status='returned',elapsed_ms=round((perf_counter()-started)*1000),content=response.content,
                              usage=asdict(response.usage),truncated=response.truncated)
                if method=='chat_tools':record.update(assistant_message=response.assistant_message,tool_calls=response.tool_calls)
                else:record.update(finish_reason=response.finish_reason,attempts=response.attempts)
                return response
            except Exception as exc:
                record.update(status='failed',error_type=type(exc).__name__)
                raise
            finally:
                target.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8');captures.append(record)
        async def chat(self,messages,**kwargs):return await self.request('chat',messages,**kwargs)
        async def chat_tools(self,messages,tools,**kwargs):return await self.request('chat_tools',messages,tools=tools,**kwargs)
    results=[]
    selected=[c for c in cases if (not args.case_ids or c['id'] in args.case_ids.split(',')) and c['id'] not in args.exclude_case_ids.split(',')][:args.case_limit]
    # 24 direct cases + up to 3 native tool workflows; later A/B runs can be explicit.
    jobs=[] if args.only_tools else [(case,False,'C') for case in selected]
    if args.tools_cases:
        chosen=[c for c in cases if c['id'] in ('cross-arity','cross-alias','cross-relative') and (not args.only_tools or not args.case_ids or c['id'] in args.case_ids.split(','))][:args.tools_cases]
        jobs.extend((case,True,'C') for case in chosen)
        if not args.only_tools:jobs.extend((case,False,variant) for case in chosen for variant in ('A','B'))
    try:
        for case,use_tools,variant in jobs:
            files=case['files'];path=case.get('path','main.py')
            payload=ReviewInput(files=files,path=path,revision=0,cursor_line=case.get('cursor_line',1),request=case.get('request','请定位并解释有证据的问题；正确代码不编造错误。'),use_tools=use_tools)
            local=inspect_project(files,path,'auto');retrieval=retrieve_project(files,path,payload.cursor_line,payload.request,issues=local[path]['issues'])
            context={**local[path],'context':{'related_files':retrieval['related_files']},'retrieval':retrieval}
            data=bundle(payload,context)
            if variant=='A':
                data['snippets']=[{'path':path,'line':i+1,'quote':line} for i,line in enumerate(files[path].splitlines()) if max(0,payload.cursor_line-8)<=i<payload.cursor_line+16 and len(line)<=500]
            elif variant=='B':
                import importlib.util
                spec=importlib.util.spec_from_file_location('r7_retrieval',Path('evaluation/studio-r8/r7_project_retrieval.py'))
                baseline=importlib.util.module_from_spec(spec);spec.loader.exec_module(baseline)
                data['snippets']=baseline.retrieve_project(files,path,payload.cursor_line,payload.request,issues=local[path]['issues'])['snippets']
            execution={**verify(files,path),'entry_path':path}
            snapshot={'files':files,'path':path,'buffer_hash':data['buffer_hash'],'diagnostics':[i for v in local.values() for i in v['issues']],
                      'learning_history':[],'execution_result':execution}
            tutor=Tutor(model=Counted());tutor.mode='live';started=perf_counter();before=used
            try:result=await review(tutor,'synthetic-r8',data,'collaborate',snapshot=snapshot,use_tools=use_tools)
            except BudgetExceeded:break
            item={'case_id':case['id'],'category':case.get('category',case.get('theme')),'use_tools':use_tools,'context_variant':variant,'files':files,'request':payload.request,
                  'expected':case.get('expected',{}),'result':result,'execution':execution,'request_indices':list(range(before+1,used+1)),
                  'elapsed_ms':round((perf_counter()-started)*1000),'semantic_review':'pending-human-review'}
            results.append(item)
            (args.output/'results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
            print(case['id'],'tools' if use_tools else 'direct',result['status'],result.get('failure_kind',''),flush=True)
            if used>=args.max_requests:break
    finally:
        summary={'kind':'real-model-synthetic','completed_cases':len(results),'actual_requests':used,'global_requests_used':budget['used'],'authorized_cap':args.max_requests,
                 'accepted':sum(r['result']['status']=='accepted' for r in results),'note':'Protocol acceptance is not semantic accuracy; tokens recorded, monetary cost requires provider billing data.'}
        (args.output/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
        await close_llm_clients()
        lock_handle.close();lock.unlink()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--cases',type=Path,default=Path('evaluation/studio-r8/model-cases.json'));p.add_argument('--output',type=Path,default=Path('docs/evidence/studio-r8/live-run'))
    p.add_argument('--case-ids',default='');p.add_argument('--exclude-case-ids',default='');p.add_argument('--budget-ledger',type=Path,default=Path('docs/evidence/studio-r8/live-budget.json'));p.add_argument('--case-limit',type=int,default=24);p.add_argument('--tools-cases',type=int,default=3);p.add_argument('--max-requests',type=int,default=42)
    p.add_argument('--only-tools',action='store_true');p.add_argument('--allow-paid',action='store_true');p.add_argument('--env-file',type=Path);a=p.parse_args()
    data=json.loads(a.cases.read_text(encoding='utf-8-sig'));cases=data['cases'] if isinstance(data,dict) else data
    if not a.allow_paid:
        print(json.dumps({'dry_run':True,'available_cases':len(cases),'case_limit':a.case_limit,'tool_scenarios':a.tools_cases,'additional_AB_comparisons':a.tools_cases*2,'request_cap':a.max_requests,'max_output_tokens_per_request':2400},ensure_ascii=False));raise SystemExit(0)
    if not a.env_file:p.error('--env-file required for explicitly authorized live run')
    if not 1<=a.max_requests<=42 or not 0<=a.tools_cases<=3 or not 1<=a.case_limit<=30:p.error('evaluation bounds exceeded')
    from dotenv import load_dotenv
    load_dotenv(a.env_file,override=True);os.environ['LLM__MAX_RETRIES']='0'
    asyncio.run(run(a,cases))
