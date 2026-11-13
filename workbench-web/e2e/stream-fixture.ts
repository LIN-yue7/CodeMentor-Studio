import type {Route} from '@playwright/test'
// Explicit simulated protocol fixture; never counted as live model evidence.
export function simulatedStream(route:Route,result:unknown){
 return route.fulfill({contentType:'application/x-ndjson',body:JSON.stringify({event:'model-turn',data:{turn:1}})+'\n'+JSON.stringify({event:'completed',data:result})+'\n'})
}
