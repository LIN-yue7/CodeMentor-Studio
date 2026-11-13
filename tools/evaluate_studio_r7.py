"""One explicitly authorized synthetic R7 request; final output captured, no secrets."""
import argparse, asyncio, json, os
from pathlib import Path
from time import perf_counter

async def run(args):
    from app.core.llm_client import get_llm_client,close_llm_clients
    from app.services.workbench_tutor import Tutor
    from app.services.project_review import bundle,review
    from app.api.workbench_projects import ReviewInput
    from app.services.project_diagnostics import inspect_python
    files={'main.py':'from helper import first\nprint(first([]) + 1)', 'helper.py':'def first(values):\n    if values:\n        return values[0]\n    return None'}
    if args.fixed: files['helper.py']=files['helper.py'].replace('return None','return 0')
    payload=ReviewInput(files=files,path='main.py',revision=0,request='请解释空列表调用的跨文件影响，区分推断和实际执行。需求是空列表按0处理。只建议必要修改。')
    context={**inspect_python('main.py',files['main.py']),'context':{'related_files':['helper.py']}}
    from app.services.project_retrieval import retrieve_project
    context['retrieval']=retrieve_project(files,'main.py',request=payload.request)
    capture={}
    class Capture:
        async def chat(self,messages,**kwargs):
            response=await get_llm_client().chat(messages,**kwargs)
            capture.update(final_output=response.content,finish_reason=response.finish_reason,truncated=response.truncated,attempts=response.attempts)
            return response
    tutor=Tutor(model=Capture());tutor.mode='live'
    started=perf_counter()
    try:
        result=await review(tutor,'synthetic-r7',bundle(payload,context),'collaborate')
        data={'files':files,'result':result,'capture':capture,'elapsed_ms':round((perf_counter()-started)*1000),'kind':'real-model-synthetic','fixed':args.fixed,'preview':bundle(payload,context)}
        args.output.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
        print(result['status'],result.get('failure_kind'),data['elapsed_ms'])
    finally: await close_llm_clients()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--allow-paid',action='store_true');p.add_argument('--env-file',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--fixed',action='store_true');a=p.parse_args()
    if not a.allow_paid:p.error('explicit authorization required')
    from dotenv import load_dotenv
    load_dotenv(a.env_file,override=True);os.environ['LLM__MAX_RETRIES']='0'
    asyncio.run(run(a))
