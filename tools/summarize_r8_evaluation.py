"""Reproducible accounting plus explicitly authored, non-blind semantic review."""
import json
import statistics
from pathlib import Path
from app.services.project_review import validate_review

ROOT=Path('docs/evidence/studio-r8')
NOTES={
 'scope-shadow':('pass','fail','首条建议和补丁把求和改成固定返回0；第二条删除遮蔽赋值才保留求和。禁止把这一案例记为有效修复。'),
 'return-none':('partial','pass','正确讲出隐式None及反例，但缺完整文件标记导致过度保留“后面可能还有return”的不确定性。'),
 'correct-scope':('partial','pass','正确判断没有已确认错误，但附带声称字符串元素会拼接不正确：整数0加字符串会TypeError。'),
 'recheck-boundary':('pass','partial','正确保留空输入修复，但建议再加None分支多余：当前if not values已经处理None。'),
}

def main():
    jobs=[]; requests=[]; rows=[]; replay=[]
    for folder in ['live-pilot','live-main','live-recheck']:
        run=ROOT/folder
        for path in sorted(run.glob('request-*.json')):
            requests.append(json.loads(path.read_text(encoding='utf-8')))
        for r in json.loads((run/'results.json').read_text(encoding='utf-8')):
            jobs.append({**r,'run':folder})
            if r['result']['status']!='accepted' and r['result'].get('failure_kind')=='invalid-output':
                raw=json.loads((run/f"request-{r['request_indices'][-1]:03}.json").read_text(encoding='utf-8'))
                sent=[]
                for message in raw['messages']:
                    if message.get('role') in ['user','tool']:
                        try:sent.extend(json.loads(message['content']).get('snippets',[]))
                        except (ValueError,TypeError):pass
                try:value,failure=validate_review(raw.get('content',''),{'snippets':sent});status='accepted-offline' if not failure else failure
                except ValueError:status='invalid-output'
                replay.append({'run':folder,'case_id':r['case_id'],'variant':r['context_variant'],'tools':r['use_tools'],'current_validator':status,'boundary':'原始真实结果仍为失败；这里只重放原响应，没有再调用模型。'})
            if r['context_variant']!='C' or r['use_tools']:continue
            v=r['result'].get('review');root,fix,note=NOTES.get(r['case_id'],('pass','pass','对照合成源码，核心根因及条件化建议一致；未把静态推断冒充执行。'))
            if not v:root=fix='unavailable';note='原始请求未产生可交付结果：'+r['result'].get('failure_kind','unknown')
            expected={(a['path'],a['line']) for a in r['expected'].get('location',[])}
            cited={(a['path'],a['line']) for a in v['citations']} if v else set()
            rows.append({'id':r['case_id'],'category':r['category'],'status':r['result']['status'],'location_coverage':len(expected&cited)/len(expected) if expected and v else None,'citations_exact':all(r['files'][a['path']].splitlines()[a['line']-1]==a['quote'] for a in v['citations']) if v else None,'root_cause':root,'repair':fix,'false_positive':False if v and r['expected'].get('valid_code') else None,'note':note,'source':f"{folder}/results.json"})
    latency=[r['elapsed_ms'] for r in requests if 'elapsed_ms' in r]
    totals={key:sum(r.get('usage',{}).get(key,0) for r in requests) for key in ['prompt_tokens','completion_tokens','total_tokens']}
    summary={'requests':len(requests),'global_indices':sorted(r['global_request_index'] for r in requests),'returned':sum(r['status']=='returned' for r in requests),'distinct_source_cases':len(rows),'direct_protocol_accepted':sum(r['status']=='accepted' for r in rows),'jobs':len(jobs),'job_protocol_accepted':sum(r['result']['status']=='accepted' for r in jobs),'tokens_recorded':totals,'latency_returned_ms':{'median':statistics.median(latency),'p95':sorted(latency)[int(.95*(len(latency)-1))]},'billing':'无服务商账单，不估算实际人民币费用；失败请求可能产生费用。'}
    report={'summary':summary,'review_boundary':'逐项评审由开发助手对照源码、explanation、hints及关键patch进行，非独立盲评、非教师实验，不代表所有教学文本已核验。位置覆盖只测期望行是否在引用中，不等于语义正确。','source_cases':rows,'postfix_offline_replay':replay,'native_tool_runs':[{'run':r['run'],'case_id':r['case_id'],'status':r['result']['status'],'failure':r['result'].get('failure_kind'),'executed_tool_calls':len(r['result'].get('tool_trace',[]))} for r in jobs if r['use_tools']]}
    (ROOT/'evaluation-summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    md=['# R8 真实模型评测账','',f"实际请求 **{len(requests)}/42**；24个不同源码案例，直接结构校验接受 **{summary['direct_protocol_accepted']}/24**。另有6组A/B检索对照、3个原生工具场景以及1次工具修复复验。",'',report['review_boundary'],'','## 核心质量检查','','| 案例 | 原始状态 | 根因 | 修复 | 审阅意见 |','|---|---|---|---|---|']
    md += [f"| {r['id']} | {r['status']} | {r['root_cause']} | {r['repair']} | {r['note']} |" for r in rows]
    md += ['','## 必须保留的限制','','- 工具场景确实发生模型自主tool_calls，并保存每轮请求、参数、工具响应及最终文本。初测仅cross-arity完整接受；cross-alias被建议条数拒绝；cross-relative超轮次。限制末轮tool_choice=none后，cross-relative用3次真实请求复验通过。','- cross-alias等建议条数失败以当前校验器离线重放可恢复，不能改写成新的真实模型通过。对象数组等类型错误继续拒绝。','- scope-shadow错误补丁、correct-scope附加错误说明、return-none过度不确定均影响教学质量。已补充完整片段标记和提示约束；额度用尽后没有再做真实验证，不能宣称彻底解决。','- 正确源码样本仅3例，其中1例服务失败；另外3例修改后复查。可用回复没有将正确源码断言为确定错误，但附加解释仍有错误，不能推出误报率为零。','- A只给调用片段时会明确缺少实现；B/C能识别别名返回整数和相对导入空输入风险。这3组小样本不足以证明C比B诊断更准确。','- 检索24例是开发集；C标注行召回100%，B为87.5%，A为46.875%。非标注上下文不必然有害。没有向量数据库，不称为语义检索。','',f"已返回请求延迟中位数 {summary['latency_returned_ms']['median']} ms，P95 {summary['latency_returned_ms']['p95']} ms。记录token：{totals}。失败请求缺失usage，不能当作零费用。",'','原始证据：live-pilot、live-main、live-recheck；汇总：evaluation-summary.json；检索：retrieval-evaluation.json。所有源码为合成，不含本机密钥。']
    (ROOT/'evaluation-report.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
