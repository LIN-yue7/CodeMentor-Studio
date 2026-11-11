"""Opt-in smoke evaluation: three synthetic cases, no existing project data.

The flag is a local guard, not evidence of user authorization. Obtain authorization
before running. Never print credentials or provider URLs. No automatic retry.
"""
import argparse
import asyncio
import json
import os
from pathlib import Path
from time import perf_counter


async def evaluate(output):
    from app.api.workbench_projects import ReviewInput
    from app.core.llm_client import close_llm_clients
    from app.services.project_diagnostics import inspect_python
    from app.services.project_review import bundle, review
    from app.services.workbench_tutor import Tutor
    cases = [
        ('missing-colon', {'main.py':'def total(scores)\n    return sum(scores)'}, '请解释为什么报错，保持原有求和需求。'),
        ('cross-file-contract', {'main.py':'from helper import first\nprint(first([]) + 1)', 'helper.py':'def first(values):\n    if values:\n        return values[0]\n    return None'}, '请分析空列表时跨文件调用的潜在问题，区分推断和执行。'),
        ('correct-control', {'main.py':'def total(scores):\n    return sum(scores)'}, '请审查这段代码；没有证据时不要编造错误。'),
    ]
    rows=[]
    try:
        for name,files,question in cases:
            payload=ReviewInput(files=files,revision=0,path='main.py',request=question)
            context={**inspect_python(payload.path,files[payload.path]),'context':{'related_files':[p for p in files if p!='main.py']}}
            started=perf_counter()
            result=await review(Tutor(live=True),'synthetic-evaluation',bundle(payload,context),'collaborate')
            rows.append({'case':name,'input':files,'request':question,'elapsed_ms':round((perf_counter()-started)*1000),'result':result})
            output.write_text(json.dumps({'scope':'3 synthetic samples; smoke test, not an accuracy or teaching-effect estimate','results':rows},ensure_ascii=False,indent=2),encoding='utf-8')
            print(name,result['status'],rows[-1]['elapsed_ms'])
    finally:
        await close_llm_clients()


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--allow-paid',action='store_true')
    parser.add_argument('--env-file',type=Path,required=True)
    parser.add_argument('--output',type=Path,default=Path('evaluation/live-studio-r6.json'))
    args=parser.parse_args()
    if not args.allow_paid:
        parser.error('Explicit user authorization required before --allow-paid. No configuration was read.')
    from dotenv import load_dotenv
    load_dotenv(args.env_file,override=True)
    os.environ['LLM__MAX_RETRIES']='0'
    os.environ['CODEMENTOR_AI_MODE']='live'
    args.output.parent.mkdir(parents=True,exist_ok=True)
    asyncio.run(evaluate(args.output))
