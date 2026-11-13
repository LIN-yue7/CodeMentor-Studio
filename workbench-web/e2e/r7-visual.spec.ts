import {editCode} from './editor-input'
import {test,expect} from '@playwright/test'
import {mkdirSync,writeFileSync} from 'node:fs'
const out=process.env.STUDIO_EVIDENCE_ROOT||'../docs/evidence/studio-r7'
const round=process.env.STUDIO_VISUAL_ROUND||'final'
for(const [width,height] of [[1440,900],[1366,768],[900,700],[390,844]]){
 test(`visual and interaction ${width}`,async({page})=>{
  mkdirSync(`${out}/${round}`,{recursive:true})
  await page.setViewportSize({width,height});await page.goto('/')
  await page.getByRole('button',{name:'体验示例',exact:true}).click()
  const editor=page.getByRole('textbox',{name:'Python 代码'})
  await expect(editor).toContainText('helper.first([])')
  await page.screenshot({scale:'css',path:`${out}/${round}/${width}-workspace.png`})
  const panel=async(name:string)=>{const b=page.getByRole('button',{name:name+'面板',exact:true});if(await b.isVisible())await b.click()}
  await panel('文件')
  await expect(page.getByRole('button',{name:'helper.py',exact:true})).toBeVisible()
  await page.screenshot({scale:'css',path:`${out}/${round}/${width}-navigation.png`})
  await page.getByRole('button',{name:'helper.py',exact:true}).click()
  await editCode(page,'def first(values)\n    if values:\n        return values[0]\n    return None')
  await panel('诊断')
  await expect(page.getByRole('heading',{name:'代码块头部缺少冒号'})).toBeVisible()
  await page.screenshot({scale:'css',path:`${out}/${round}/${width}-feedback.png`})
  await panel('代码');await editCode(page,'def first(values):\n    if values:\n        return values[0]\n    return None')
  await page.getByRole('tab',{name:'main.py',exact:true}).click()
  const failed=page.waitForResponse(r=>r.url().endsWith('/verify'))
  await page.getByRole('button',{name:'验证当前入口'}).click()
  expect((await (await failed).json()).status).toBe('runtime-error')
  await panel('诊断');await expect(page.getByText('运行发现问题',{exact:true})).toBeVisible()
  await panel('代码');await page.getByRole('tab',{name:'helper.py',exact:true}).click()
  await editCode(page,'def first(values):\n    if values:\n        return values[0]\n    return 0')
  await page.getByRole('tab',{name:'main.py',exact:true}).click()
  const passed=page.waitForResponse(r=>r.url().endsWith('/verify'))
  await page.getByRole('button',{name:'验证当前入口'}).click()
  const result=await (await passed).json();expect(result.status).toBe('passed');expect(result.stdout).toBe('1\n')
  writeFileSync(`${out}/${round}/${width}-execution.json`,JSON.stringify(result,null,2))
  await panel('诊断');await expect(page.getByText('当前输入验证通过',{exact:true})).toBeVisible()
  await page.screenshot({scale:'css',path:`${out}/${round}/${width}-verified.png`})
  await panel('学习');await page.getByRole('tab',{name:'学习记录',exact:true}).click()
  await expect(page.getByText('受限 Python 执行：passed',{exact:false})).toBeVisible()
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true)
  expect(await page.evaluate(()=>document.documentElement.scrollHeight<=innerHeight)).toBe(true)
  if(width>1100){await page.getByRole('button',{name:'折叠文件区'}).click();await expect(page.locator('.station-files')).toBeHidden();await page.getByRole('button',{name:'展开文件区'}).click()}
 })
}
