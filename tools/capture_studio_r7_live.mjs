import {chromium} from '../workbench-web/node_modules/playwright/index.mjs'
import {writeFileSync} from 'node:fs'
const browser=await chromium.launch({channel:'msedge',headless:true})
try{
 const page=await browser.newPage({viewport:{width:1440,height:900}})
 await page.goto('http://127.0.0.1:8787')
 await page.getByRole('button',{name:'体验示例',exact:true}).click()
 const editor=page.getByRole('textbox',{name:'Python 代码'})
 await page.getByRole('button',{name:'helper.py',exact:true}).click()
 await editor.fill('def first(values):\n    if values:\n        return values[0]\n    return 0')
 await page.getByRole('tab',{name:'main.py',exact:true}).click()
 await editor.fill('from helper import first\nprint(first([]) + 1)')
 await page.getByRole('button',{name:'保存项目',exact:true}).click()
 await page.getByLabel('想进一步了解什么？').fill('请解释空列表调用的跨文件影响，区分推断和实际执行。需求是空列表按0处理。只建议必要修改。')
 await page.getByText('模型权限与自动分析',{exact:false}).click()
 const permission=page.waitForResponse(r=>r.url().endsWith('/privacy')&&r.request().method()==='POST')
 await page.getByLabel('允许本项目向已配置模型发送所选上下文').click()
 await permission
 await page.getByRole('button',{name:'预览审查上下文'}).click()
 const response=page.waitForResponse(r=>r.url().endsWith('/review'))
 await page.getByRole('button',{name:'确认发送并请求 AI 指导'}).click()
 const result=await (await response).json()
 writeFileSync('../docs/evidence/studio-r7/live-04-result.json',JSON.stringify(result,null,2))
 await page.locator('.model-result').scrollIntoViewIfNeeded()
 await page.screenshot({path:'../docs/evidence/studio-r7/live-04-browser.png'})
 await page.locator('.model-result').screenshot({path:'../docs/evidence/studio-r7/live-04-explanation.png'})
 console.log(JSON.stringify({status:result.status,failure:result.failure_kind}))
 // Independent execution remains separate from the model claim.
 const verified=page.waitForResponse(r=>r.url().endsWith('/verify'))
 await page.getByRole('button',{name:'验证当前入口'}).click()
 writeFileSync('../docs/evidence/studio-r7/live-04-execution.json',JSON.stringify(await (await verified).json(),null,2))
}finally{await browser.close()}
