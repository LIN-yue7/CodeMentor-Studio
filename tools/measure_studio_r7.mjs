import {chromium} from '../workbench-web/node_modules/playwright/index.mjs'
import {writeFileSync} from 'node:fs'
const browser=await chromium.launch({channel:'msedge',headless:true})
try{
const page=await browser.newPage({viewport:{width:1440,height:900}})
await page.goto('http://127.0.0.1:8788');await page.getByRole('button',{name:'体验示例',exact:true}).click()
const samples=[]
for(let i=0;i<8;i++){
 const editor=page.getByRole('textbox',{name:'Python 代码'});await editor.click();await editor.press('ControlOrMeta+a')
 const response=page.waitForResponse(r=>r.url().endsWith('/context')&&r.request().postDataJSON().files['main.py'].includes('sample_'+i))
 const start=performance.now();await page.keyboard.insertText('def sample_'+i+'()\n    return 1')
 await response;await page.getByRole('heading',{name:'代码块头部缺少冒号'}).waitFor({state:'visible'})
 samples.push(Math.round(performance.now()-start))
}
const sorted=[...samples].sort((a,b)=>a-b)
writeFileSync('../docs/evidence/studio-r7/performance.json',JSON.stringify({kind:'local-browser-input-to-visible-diagnostic',samples_ms:samples,p50_ms:sorted[3],p95_ms:sorted[7],viewport:'1440x900',includes:'650ms debounce, HTTP context retrieval and UI display',boundary:'8 local synthetic inputs; not production SLA or pure parser speed'},null,2))
console.log(JSON.stringify({samples_ms:samples}))
}finally{await browser.close()}
