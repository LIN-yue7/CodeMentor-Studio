import {test,expect} from '@playwright/test'
import {readFileSync,mkdirSync} from 'node:fs'
import {editCode} from './editor-input'
import {simulatedStream} from './stream-fixture'

test('render archived real model response with visible replay disclosure, no paid request',async({page})=>{
 const record=JSON.parse(readFileSync('../docs/evidence/studio-r8/live-pilot/results.json','utf8'))[0]
 await page.setViewportSize({width:1440,height:900});await page.goto('/')
 await page.getByRole('button',{name:'新建项目',exact:true}).click()
 await page.getByLabel('项目名称',{exact:true}).fill('真实模型记录回放 · 语法讲解')
 await page.getByRole('button',{name:'创建项目',exact:true}).click()
 await editCode(page,record.files['main.py'])
 await expect(page.getByRole('heading',{name:'代码块头部缺少冒号'})).toBeVisible()
 await page.route('**/api/projects/*/review-stream',route=>simulatedStream(route,record.result))
 await page.getByText('模型权限与自动分析',{exact:false}).click()
 await page.getByLabel('允许本项目向已配置模型发送所选上下文').click()
 await expect(page.getByLabel('允许本项目向已配置模型发送所选上下文')).toBeChecked()
 await page.getByRole('button',{name:'预览审查上下文'}).click()
 await page.getByRole('button',{name:'确认发送并请求 AI 指导'}).click()
 await page.getByText('详细解释：为什么这样修改',{exact:true}).click()
 await page.evaluate(()=>{
  const banner=document.createElement('div');banner.textContent='真实 API 第 1 次响应回放 · 当前页面不产生模型调用 · 本地检查仍实时运行';
  Object.assign(banner.style,{position:'fixed',bottom:'0',left:'0',right:'0',background:'#302743',color:'#fff',padding:'10px',zIndex:'9999',textAlign:'center',fontSize:'14px'});document.body.append(banner)
 })
 await page.locator('.privacy-settings').evaluate((el:HTMLDetailsElement)=>el.open=false)
 await page.getByText('详细解释：为什么这样修改',{exact:true}).evaluate(el=>el.scrollIntoView({block:'start'}))
 mkdirSync('../docs/evidence/studio-r8/recorded',{recursive:true})
 await page.screenshot({scale:'css',path:'../docs/evidence/studio-r8/recorded/1440-real-response-replay.png'})
 await expect(page.getByText('语言机制',{exact:true})).toBeVisible()
})
