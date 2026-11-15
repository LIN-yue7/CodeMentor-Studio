"""Replay saved final provider responses through current review safeguards, offline."""
import asyncio
import argparse
import json
from pathlib import Path
from app.core.llm_client import LLMResponse
from app.services.workbench_tutor import Tutor
from app.services.project_review import bundle, review
from app.services.project_retrieval import retrieve_project, source_coverage
from app.api.workbench_projects import ReviewInput, inspect_project

class RecordedResponse:
    def __init__(self, content):self.content=content
    async def chat(self,messages,**kwargs):return LLMResponse(content=self.content,model='offline-replay')

async def main(output):
    if output.exists():raise SystemExit('Replay evidence already exists; keep it immutable')
    records=[]
    for run in ('live-01','live-02'):
        folder=Path('docs/evidence/studio-r9')/run
        for row in json.loads((folder/'results.json').read_text(encoding='utf-8')):
            if not row['request_indices']:continue
            raw=json.loads((folder/f"request-{row['request_indices'][-1]:03}.json").read_text(encoding='utf-8'))
            files=row['files'];path=next(iter(files))
            payload=ReviewInput(files=files,path=path,revision=0,request=row['request'])
            local=inspect_project(files,path,'auto')
            retrieval=retrieve_project(files,path,1,payload.request,issues=local[path]['issues'])
            data=bundle(payload,{**local[path],'context':{'related_files':retrieval['related_files']},'retrieval':retrieval})
            original = json.loads(raw['messages'][1]['content'])
            sent = list(original.get('snippets', []))
            for message in raw['messages']:
                if message.get('role') == 'tool':
                    sent.extend(json.loads(message['content']).get('snippets', []))
            data['snippets'] = sent
            data['source_coverage'] = source_coverage(files, sent)
            tutor=Tutor(model=RecordedResponse(raw['content']))
            result=await review(tutor,'offline-r9',data,'collaborate',snapshot={'files':files,'path':path,'cursor_line':1})
            records.append({'source_run':run,'case_id':row['case_id'],'group':row['group'],'provenance':'offline-final-response-replay','network_requests':0,'result':result})
    output.write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'replayed':len(records),'accepted':sum(r['result']['status']=='accepted' for r in records),'network_requests':0}))

if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('docs/evidence/studio-r9/final-offline-replay-with-tool-evidence.json'))
    asyncio.run(main(parser.parse_args().output))
