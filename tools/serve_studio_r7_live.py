"""One live synthetic browser call, loopback only. Refuses a second call across restarts."""
import argparse,json,os,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--allow-paid',action='store_true');p.add_argument('--env-file',required=True);a=p.parse_args()
if not a.allow_paid:p.error('Explicit authorization required')
from dotenv import load_dotenv
load_dotenv(a.env_file,override=True)
os.environ['LLM__MAX_RETRIES']='0';os.environ['DATABASE__SQLITE_PATH']='data/studio-r7-synthetic-live.db'
from app.workbench import create_workbench
from app.core.llm_client import get_llm_client,LLMError
out=Path('docs/evidence/studio-r7/live-04-browser.json')
class Capture:
    async def chat(self,messages,**kw):
        # Creation is atomic, including across concurrent requests and restarts.
        try:
            with out.open('x',encoding='utf-8') as f:f.write('{"status":"started","authorization":"R7 call 4 of 4"}')
        except FileExistsError:raise LLMError('Synthetic call budget exhausted')
        body=json.loads(messages[-1].content)
        r=await get_llm_client().chat(messages,**kw)
        out.write_text(json.dumps({'kind':'real-model-synthetic-browser','preview':body,'capture':{'final_output':r.content,'finish_reason':r.finish_reason,'truncated':r.truncated,'attempts':r.attempts}},ensure_ascii=False,indent=2),encoding='utf-8')
        return r
app=create_workbench(model=Capture());app.state.tutor.mode='live'
if __name__=='__main__':
    import uvicorn
    uvicorn.run(app,host='127.0.0.1',port=8787,access_log=False)
