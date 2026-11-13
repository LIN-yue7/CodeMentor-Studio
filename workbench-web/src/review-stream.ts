export type WorkflowEvent={event:string;data:Record<string,unknown>}
export async function readReviewStream<T>(response:Response,onEvent:(event:WorkflowEvent)=>void):Promise<T>{
 if(!response.ok){const error=await response.json().catch(()=>null);throw Error(typeof error?.detail==='string'?error.detail:`请求失败（${response.status}）。`)}
 if(!response.body)throw Error('未收到分析事件流。')
 const reader=response.body.getReader(),decoder=new TextDecoder();let pending='',result:T|undefined
 function consume(line:string){if(!line.trim())return;const event=JSON.parse(line) as WorkflowEvent;if(event.event==='heartbeat')return;if(event.event==='error')throw Error(String(event.data?.message??event.data?.reason??'模型分析失败'));onEvent(event);if(event.event==='completed')result=event.data as T}
 try{while(true){const {done,value}=await reader.read();pending+=decoder.decode(value,{stream:!done});const lines=pending.split('\n');pending=lines.pop()!;lines.forEach(consume);if(done){consume(pending);break}}}finally{await reader.cancel().catch(()=>{});reader.releaseLock()}
 if(result===undefined)throw Error('分析连接已中断，未收到完成结果；请手动重试。')
 return result
}
export async function streamReview<T>(id:string,body:object,signal:AbortSignal,onEvent:(event:WorkflowEvent)=>void):Promise<T>{
 const response=await fetch('/api/projects/'+id+'/review-stream',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify(body),signal})
 return readReviewStream<T>(response,onEvent)
}
