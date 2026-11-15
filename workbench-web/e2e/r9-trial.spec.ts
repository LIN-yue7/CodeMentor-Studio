import {test,expect} from '@playwright/test'
import {readFile} from 'node:fs/promises'
import {resolve} from 'node:path'
import {editCode} from './editor-input'

for(const level of ['beginner','advanced']){
 test(`R9 ${level} imported project and anonymous export`,async({page},testInfo)=>{
  if(testInfo.project.name==='desktop')await page.setViewportSize({width:1440,height:900})
  const panel=async(name:string)=>{const button=page.getByRole('button',{name:name+'面板',exact:true});if(await button.isVisible())await button.click()}
  await page.goto('/')
  await page.getByRole('button',{name:'导入项目 JSON',exact:true}).click()
  await page.getByLabel('选择 JSON 文件').setInputFiles(resolve('../examples/studio-r9/'+level+'.json'))
  await page.getByRole('button',{name:'导入项目',exact:true}).click()
  await expect(page.getByRole('heading',{name:'R9 '+level,exact:true})).toBeVisible()
  const helper=level==='beginner'?'helper.py':'numbers_local.py'
  await panel('文件')
  await page.getByRole('button',{name:helper,exact:true}).click()
  await editCode(page,'def first(values):\n    if values:\n        return values[0]\n    return 0\n')
  await page.getByRole('button',{name:'保存项目',exact:true}).click()
  await expect(page.getByText('已保存到服务端 · 版本 2',{exact:true})).toBeVisible()
  await page.getByRole('tab',{name:'main.py',exact:true}).click()
  await page.getByRole('button',{name:'验证当前入口',exact:true}).click()
  await panel('诊断')
  await expect(page.getByText('当前输入验证通过',{exact:true})).toBeVisible()
  await page.screenshot({path:resolve('../docs/evidence/studio-r9/'+level+'-'+testInfo.project.name+'.png')})
  await panel('文件')
  await page.getByText('存储与备份',{exact:true}).click()
  const downloaded=page.waitForEvent('download')
  await page.getByRole('button',{name:'导出匿名试用记录',exact:true}).click()
  const download=await downloaded
  const log=JSON.parse(await readFile((await download.path())!,'utf8'))
  expect(log.events.some((e:{kind:string})=>e.kind==='saved-modification')).toBeTruthy()
  expect(log.events.some((e:{kind:string})=>e.kind==='execution-passed')).toBeTruthy()
  expect(JSON.stringify(log)).not.toContain('first(values)')
  expect(JSON.stringify(log)).not.toContain('main.py')
  await page.reload()
  await expect(page.getByRole('heading',{name:'R9 '+level,exact:true})).toBeVisible()
 })
}
