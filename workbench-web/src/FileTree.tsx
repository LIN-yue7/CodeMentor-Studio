import {useState} from 'react'
type Node={files:string[];folders:Record<string,Node>}
export function FileTree({paths,active,onSelect,onAction,dirty=[],issues={}}:{paths:string[];active:string;onSelect:(path:string)=>void;onAction?:(action:string,path:string)=>void;dirty?:string[];issues?:Record<string,unknown[]>}){
 const [context,setContext]=useState<string|null>(null)
 const root:Node={files:[],folders:Object.create(null)}
 for(const path of [...paths].sort()){
  const parts=path.split('/');let node=root
  for(const part of parts.slice(0,-1))node=node.folders[part]??=( {files:[],folders:Object.create(null)} )
  node.files.push(path)
 }
 function render(node:Node,prefix=''):React.ReactNode{return <>
  {Object.entries(node.folders).map(([name,child])=><details className="tree-folder" key={prefix+name} open><summary onContextMenu={e=>{e.preventDefault();e.stopPropagation();setContext(prefix+name+'/')}}>▱ {name}</summary>{render(child,prefix+name+'/')}</details>)}
  {node.files.map(path=><button title={path} aria-label={path} className={path===active?'file-active':''} key={path} onContextMenu={e=>{e.preventDefault();setContext(path)}} onClick={()=>{setContext(null);onSelect(path)}} aria-current={path===active?'page':undefined}><span aria-hidden="true" className="file-icon">{path.endsWith('.py')?'Py':'◇'}</span><span>{path.split('/').pop()}</span>{dirty.includes(path)&&<span aria-label="未保存">●</span>}{!!issues[path]?.length&&<span className="issue-badge">{issues[path].length}</span>}</button>)}
 </>}
 return <nav className="file-tree" aria-label="项目文件">{render(root)}{context&&<div role="menu" className="file-context" onKeyDown={e=>{if(e.key==='Escape')setContext(null)}}>{['新建文件',context.endsWith('/')?'重命名文件夹':'重命名文件',context.endsWith('/')?'删除文件夹':'删除文件'].map(action=><button key={action} role="menuitem" onClick={()=>{onAction?.(action,context);setContext(null)}}>{action}</button>)}<button role="menuitem" onClick={()=>setContext(null)}>关闭菜单</button></div>}</nav>
}
