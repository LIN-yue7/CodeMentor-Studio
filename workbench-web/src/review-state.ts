export type ReviewPayload={files:Record<string,string>;revision:number;path:string;cursor_line:number;language?:'auto'|'python'|'text';request?:string}
export type Patch={path:string;line:number;before:string;after:string;reason?:string}
export type AppliedPatch={before:Record<string,string>;after:Record<string,string>}
export function requestFingerprint(body:object):string{
 function stable(value:unknown):unknown{return value&&typeof value==='object'&&!Array.isArray(value)?Object.fromEntries(Object.entries(value).sort(([a],[b])=>a.localeCompare(b)).map(([k,v])=>[k,stable(v)])):Array.isArray(value)?value.map(stable):value}
 return JSON.stringify(stable(body))
}
export function applyReviewedPatches(files:Record<string,string>,patches:Patch[]):Record<string,string>{
 const next={...files},seen=new Set<string>()
 for(const patch of patches){const key=patch.path+':'+patch.line;if(seen.has(key)||!Number.isInteger(patch.line)||patch.line<1||files[patch.path]?.split('\n')[patch.line-1]!==patch.before)throw Error('源代码已变化或补丁冲突，请重新分析。');seen.add(key)}
 for(const p of [...patches].sort((a,b)=>b.line-a.line)){const lines=next[p.path].split('\n');lines.splice(p.line-1,1,p.after);next[p.path]=lines.join('\n')}
 return next
}
export function undoReviewedPatch(files:Record<string,string>,patch:AppliedPatch):Record<string,string>{
 if(requestFingerprint(files)!==requestFingerprint(patch.after))throw Error('应用后存在手动编辑或其他文件变化，已阻止撤回以保留你的改动。')
 return {...patch.before}
}
