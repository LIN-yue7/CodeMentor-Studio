import {test} from 'node:test'
import assert from 'node:assert/strict'
const api=await import('../src/review-stream.ts').catch(()=>({}))
test('stream emits real events split across network chunks and requires completed',async()=>{
 assert.equal(typeof api.readReviewStream,'function')
 const chunks=['{"event":"tool-start","data":{"name":"inspect"}}\n{"event":"com','pleted","data":{"status":"accepted"}}\n']
 const response=new Response(new ReadableStream({start(c){for(const s of chunks)c.enqueue(new TextEncoder().encode(s));c.close()}}))
 const events=[]
 assert.deepEqual(await api.readReviewStream(response,e=>events.push(e)),{status:'accepted'})
 assert.equal(events[0].event,'tool-start')
 await assert.rejects(()=>api.readReviewStream(new Response('{"event":"started","data":{}}\n'),()=>{}),/中断/)
})
