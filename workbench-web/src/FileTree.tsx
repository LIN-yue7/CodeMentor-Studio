type Node={files:string[];folders:Record<string,Node>}
export function FileTree({paths,active,onSelect}:{paths:string[];active:string;onSelect:(path:string)=>void}){
 const root:Node={files:[],folders:Object.create(null)}
 for(const path of [...paths].sort()){
  const parts=path.split('/');let node=root
  for(const part of parts.slice(0,-1))node=node.folders[part]??=( {files:[],folders:Object.create(null)} )
  node.files.push(path)
 }
 function render(node:Node,prefix=''):React.ReactNode{return <>
  {Object.entries(node.folders).map(([name,child])=><details className="tree-folder" key={prefix+name} open><summary>▱ {name}</summary>{render(child,prefix+name+'/')}</details>)}
  {node.files.map(path=><button title={path} aria-label={path} className={path===active?'file-active':''} key={path} onClick={()=>onSelect(path)} aria-current={path===active?'page':undefined}><span aria-hidden="true" className="file-icon">{path.endsWith('.py')?'Py':'◇'}</span><span>{path.split('/').pop()}</span></button>)}
 </>}
 return <nav className="file-tree" aria-label="项目文件">{render(root)}</nav>
}
