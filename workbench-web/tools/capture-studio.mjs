import { chromium, expect } from '@playwright/test'
import {mkdir, writeFile} from 'node:fs/promises'
import {resolve} from 'node:path'
const output=resolve('../docs/evidence/studio-r6')
await mkdir(output,{recursive:true})
const browser=await chromium.launch({channel:'msedge',headless:true})
const page=await browser.newPage({viewport:{width:1440,height:900},deviceScaleFactor:1})
const errors=[];page.on('pageerror',e=>errors.push(e.message))
const started=Date.now()
await page.goto('http://127.0.0.1:8780/')
await page.getByLabel('项目名称',{exact:true}).fill('课程成绩分析 · Python')
await page.getByRole('button',{name:'新建项目',exact:true}).click()
await page.locator('.new-file summary').click()
await page.getByLabel('新文件路径').fill('src/formatting.py')
await page.getByRole('button',{name:'添加文件',exact:true}).click()
await page.getByRole('textbox',{name:'Python 代码'}).fill('def format_score(value):\n    return f"{value:.1f}"\n')
await page.getByRole('button',{name:'main.py',exact:true}).click()
const code=`from src.formatting import format_score

# 目标：按课程统计分数，并输出结果
# 先修复语法，再用空列表等边界输入验证行为

def summarize(scores)
    total = sum(scores)
    average = total / len(scores)
    return {
        "total": total,
        "average": average,
        "count": len(scores),
    }

scores = [78, 92, 85, 96]
result = summarize(scores)
print("平均成绩：", format_score(result["average"]))
`
await page.getByRole('textbox',{name:'Python 代码'}).fill(code)
await expect(page.getByRole('heading',{name:'代码块头部缺少冒号'})).toBeVisible()
await page.getByRole('textbox',{name:'Python 代码'}).press('Control+Home')
await page.locator('.new-file summary').click()
await page.getByRole('tab',{name:'易错点',exact:true}).click()
await page.screenshot({path:resolve(output,'desktop-diagnosis-final.png')})
await page.setViewportSize({width:1920,height:1080})
await page.screenshot({path:resolve(output,'desktop-1080p.png')})
await page.setViewportSize({width:390,height:844})
await page.getByRole('button',{name:'诊断面板',exact:true}).click()
await page.screenshot({path:resolve(output,'mobile-diagnosis.png')})
await page.getByRole('button',{name:'代码面板',exact:true}).click()
await page.screenshot({path:resolve(output,'mobile-editor.png')})
const latency=[]
await page.setViewportSize({width:1440,height:900})
for(let i=0;i<8;i++){
 const time=Date.now()
 await page.getByRole('textbox',{name:'Python 代码'}).fill(code.replace('summarize(scores)','summarize(scores):')+'\n# sample '+i)
 await expect(page.locator('.inspection-summary')).toContainText('Python 语法检查通过。')
 latency.push(Date.now()-time)
}
await page.getByRole('button',{name:'保存项目',exact:true}).click()
await expect(page.getByText('已保存到服务端 · 版本 1')).toBeVisible()
await page.getByRole('tab',{name:'学习记录',exact:true}).click()
await page.screenshot({path:resolve(output,'desktop-recheck.png')})
const navigation=await page.evaluate(()=>performance.getEntriesByType('navigation')[0].toJSON())
const sorted=[...latency].sort((a,b)=>a-b)
await writeFile(resolve(output,'browser-measurements-final.json'),JSON.stringify({mode:'local; no external model calls',browser:'headless Microsoft Edge',viewport:[1440,900],samples:latency,p50_ms:sorted[3],p95_ms:sorted[7],includes:'UI fill + 650ms debounce + HTTP local parse + visible result',navigation,page_errors:errors,elapsed_ms:Date.now()-started},null,2))
await browser.close()
console.log(JSON.stringify({screenshots:5,samples:latency,pageErrors:errors}))
