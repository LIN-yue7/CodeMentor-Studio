import {simulatedStream} from './stream-fixture'
import {editCode} from './editor-input'
import {test,expect} from '@playwright/test'

test.beforeEach(async({page})=>{
 await page.setViewportSize({width:1440,height:900})
 await page.goto('/')
 await page.getByRole('button',{name:'新建项目',exact:true}).click()
 await page.getByLabel('项目名称',{exact:true}).fill('实时反馈验收')
 await page.getByRole('button',{name:'创建项目',exact:true}).click()
})

test('root cause is visible immediately and editor stays primary',async({page})=>{
 await editCode(page,'def total(scores)\n    return sum(scores)')
 await expect(page.getByRole('heading',{name:'实时代码反馈',exact:true})).toBeVisible()
 await expect(page.getByRole('heading',{name:'代码块头部缺少冒号'})).toBeVisible()
 await expect(page.getByText('为什么出错',{exact:true})).toBeVisible()
 await expect(page.getByLabel('指导模式')).toHaveCount(0)
 await expect(page.getByLabel('项目名称',{exact:true})).toBeHidden()
 await expect(page.getByRole('separator',{name:'调整教学区高度'})).toBeVisible()
 const code=await page.locator('.station-code').boundingBox()
 const files=await page.locator('.station-files').boundingBox()
 expect(code!.width).toBeGreaterThan(files!.width*2)
})

test('automatic analysis needs opt in, debounces edits, and discards late responses',async({page})=>{
 let calls=0
 await page.route('**/api/projects/*/review-stream',async route=>{
   calls++
   await new Promise(r=>setTimeout(r,1200))
   await simulatedStream(route,{status:'accepted',mode:'simulated',review:{explanation:'旧版本的模拟分析',hints:['模拟提示'],citations:[]}})
 })
 const editor=page.getByRole('textbox',{name:'Python 代码'})
 await editCode(page,'value = 1')
 await expect(page.getByText('Python 语法检查通过。',{exact:false})).toBeVisible()
 expect(calls).toBe(0)
 await page.getByText('模型权限与自动分析',{exact:false}).click()
 await page.getByLabel('允许本项目向已配置模型发送所选上下文').click()
 await expect(page.getByLabel('允许本项目向已配置模型发送所选上下文')).toBeChecked()
 await page.getByLabel('代码稳定后自动分析（本次打开）').check()
 await editCode(page,'value = 2')
 await editCode(page,'value = 3')
 await expect.poll(()=>calls).toBe(1)
 await editCode(page,'value = 4')
 await page.waitForTimeout(1600)
 await expect(page.getByText('旧版本的模拟分析',{exact:true})).toHaveCount(0)
 await page.getByLabel('允许本项目向已配置模型发送所选上下文').click()
 await expect(page.getByLabel('允许本项目向已配置模型发送所选上下文')).not.toBeChecked()
 await expect(page.getByLabel('代码稳定后自动分析（本次打开）')).not.toBeChecked()
 expect(calls).toBe(1)
})

test('failed automatic analysis stops until deliberate retry',async({page})=>{
 let calls=0
 await page.route('**/api/projects/*/review-stream',async route=>{calls++;await simulatedStream(route,{status:'timeout',mode:'simulated',review:null})})
 await editCode(page,'value = 1')
 await page.getByText('模型权限与自动分析',{exact:false}).click()
 await page.getByLabel('允许本项目向已配置模型发送所选上下文').click()
 await expect(page.getByLabel('允许本项目向已配置模型发送所选上下文')).toBeChecked()
 await page.getByLabel('代码稳定后自动分析（本次打开）').check()
 await expect(page.getByText('模型响应超时',{exact:false})).toBeVisible()
 await expect(page.getByLabel('代码稳定后自动分析（本次打开）')).not.toBeChecked()
 await editCode(page,'value = 2')
 await page.waitForTimeout(2100)
 expect(calls).toBe(1)
})

test('phone uses panel switching without document scrolling',async({page})=>{
 await page.setViewportSize({width:390,height:844})
 await editCode(page,'if True\n    print(1)')
 await page.getByRole('button',{name:'诊断面板',exact:true}).click()
 await expect(page.getByRole('heading',{name:'代码块头部缺少冒号'})).toBeVisible()
 expect(await page.evaluate(()=>document.documentElement.scrollHeight<=innerHeight)).toBe(true)
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true)
 await page.getByRole('button',{name:'代码面板',exact:true}).click()
 await expect(page.getByRole('textbox',{name:'Python 代码'})).toBeVisible()
})

test('valid directory names matching object properties cannot crash the editor',async({page})=>{
 for(const name of ['constructor','__proto__','toString']){
  await page.getByRole('button',{name:'新建文件',exact:true}).click()
  await page.getByLabel('文件路径').fill(name+'/main.py')
  await page.getByRole('button',{name:'创建文件',exact:true}).click()
  await expect(page.getByRole('textbox',{name:'Python 代码'})).toBeVisible()
  await editCode(page,'value = 1')
 }
 await expect(page.getByRole('button',{name:'constructor/main.py',exact:true})).toBeVisible()
})
