"""Offline A/B/C development-set retrieval measurements, no model calls."""
import importlib.util
import json
from pathlib import Path
from time import perf_counter
from app.services.project_retrieval import retrieve_project

def main():
    root=Path('evaluation/studio-r8')
    spec=importlib.util.spec_from_file_location('r7',root/'r7_project_retrieval.py')
    baseline=importlib.util.module_from_spec(spec);spec.loader.exec_module(baseline)
    source=json.loads((root/'retrieval-cases.json').read_text(encoding='utf-8'))
    rows=[]
    for case in source['cases']:
        kwargs={k:case[k] for k in ['files','path','cursor_line','request','language','issues']}
        expected={(s['path'],s['line']) for s in case['relevant_lines']}
        for variant in ['A','B','C']:
            start=perf_counter()
            if variant=='A':
                snippets=[{'path':case['path'],'line':i+1,'quote':line} for i,line in enumerate(case['files'][case['path']].splitlines()) if max(0,case['cursor_line']-8)<=i<case['cursor_line']+16 and len(line)<=500]
            else:snippets=(baseline.retrieve_project if variant=='B' else retrieve_project)(**kwargs)['snippets']
            actual={(s['path'],s['line']) for s in snippets if s['quote'].strip()}
            rows.append({'case_id':case['id'],'theme':case['theme'],'variant':variant,'required_lines':len(expected),'hit_lines':len(expected&actual),'returned_nonblank_lines':len(actual),'excess_nonblank_lines':len(actual-expected),'exact_citations':all(case['files'][s['path']].splitlines()[s['line']-1]==s['quote'] for s in snippets),'source_characters':sum(len(s['quote']) for s in snippets),'elapsed_ms':round((perf_counter()-start)*1000,3)})
    summary={}
    for variant in ['A','B','C']:
        group=[r for r in rows if r['variant']==variant]
        summary[variant]={'cases':len(group),'line_recall':sum(r['hit_lines'] for r in group)/sum(r['required_lines'] for r in group),'full_hit_cases':sum(r['hit_lines']==r['required_lines'] for r in group),'excess_context_fraction':sum(r['excess_nonblank_lines'] for r in group)/sum(r['returned_nonblank_lines'] for r in group),'mean_source_characters':sum(r['source_characters'] for r in group)/len(group),'mean_ms':sum(r['elapsed_ms'] for r in group)/len(group)}
    out=Path('docs/evidence/studio-r8/retrieval-evaluation.json')
    out.write_text(json.dumps({'boundary':source['label_policy']+' Excess lines may still be helpful. This is not a held-out set or model accuracy.', 'summary':summary,'rows':rows},ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
