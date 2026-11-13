export type Issue={path:string;line:number;column:number;message:string;title:string;why:string;fix:string;example:string;concept:string;intent:string;observed:string;prevention:string}
export type Inspection={project_issues?:Record<string,Issue[]>;learning?:{items:{path:string;message:string}[];summary?:{recommendations:string[];boundary:string}};context?:{function:string|null;related_files:string[];unsaved:boolean};status:string;summary:string;issues:Issue[]}

export function DiagnosticCard({issue,onJump}:{issue:Issue;onJump:()=>void}){
 return <article className="diagnostic-card">
  <div className="diagnostic-title"><span aria-hidden="true">!</span><h3>{issue.title}</h3></div>
  <button className="diagnostic-location" onClick={onJump}>⌖ {issue.path} · 第 {issue.line} 行，第 {issue.column} 列 <span>定位 ↗</span></button>
  <dl><dt>为什么出错</dt><dd>{issue.why}</dd><dt>怎样修改</dt><dd>{issue.fix}</dd></dl>
  <details><summary>解析器原始证据</summary><code>{issue.message}</code><p>{issue.observed}</p></details>
 </article>
}

export function TeachingPanel({tab,inspection,events,selection,file,onJump}:{tab:string;inspection:Inspection|null;events:string[];selection:string;file:string;onJump:(line:number)=>void}){
 const issue=inspection?.issues[0]
 if(tab==='学习记录')return <><p className="subtle">记录实际解析器观察、查看提示及保存后的复查。语法通过不表示运行正确或已掌握。</p>{inspection?.learning?.summary&&<details><summary>基于真实记录的学习建议</summary>{inspection.learning.summary.recommendations.map((text,i)=><p key={i}>{text}</p>)}<p className="subtle">{inspection.learning.summary.boundary}</p></details>}{events.length?<ol className="learning-events">{events.map((e,i)=><li key={i}>{e}</li>)}</ol>:<p>尚无检查状态变化。修改代码后，观察与复查会显示在这里。</p>}</>
 if(tab==='易错点')return issue?<div className="teaching-grid"><article><h3>以后怎样避免</h3><p>{issue.prevention}</p></article><article><h3>修改示例与适用条件</h3>{issue.example?<><pre>{issue.example}</pre><p className="subtle">结构示意；请保留你原有的业务代码。</p></>:<p>当前证据不足以给出唯一代码补丁，先确认目标语言和需求。</p>}</article></div>:<p>当前没有已确认的语法问题。下一步可用普通输入、空输入和边界输入核对你的预期。</p>
 if(tab==='代码解析')return <div className="teaching-grid"><article><h3>代码可能想实现什么</h3><p>{issue?.intent??'尚未调用模型分析业务意图。请说明预期输入、输出和边界条件，避免根据变量名猜测需求。'}</p><h3>实际发生了什么</h3><p>{issue?.observed??'这里只进行了静态语法检查，未执行项目代码，没有运行结果。'}</p></article><article><h3>当前项目证据</h3><p>文件：{file} · 函数：{inspection?.context?.function??'未定位'}</p><p>直接引用：{inspection?.context?.related_files.join('、')||'未定位到支持的项目内引用'}</p>{selection&&<pre>{selection.slice(0,1000)}</pre>}</article></div>
 return issue?<div className="problem-row"><button onClick={()=>onJump(issue.line)}>{file}:{issue.line}:{issue.column}</button><span>{issue.title}</span><span className="subtle">本地解析器 · 未执行代码</span></div>:<p>{inspection?.status==='syntax-ok'?'当前未列出语法问题；请继续验证运行行为和边界输入。':inspection?.status==='unsupported'?'当前语言仅支持编辑和保存，不能据此判断无错误。':'等待当前文件的检查结果。'}</p>
}
