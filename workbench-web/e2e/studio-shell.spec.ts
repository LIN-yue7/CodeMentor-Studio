import {editCode} from './editor-input'
import {test,expect} from '@playwright/test'
test('desktop shell keeps editor and mentor inside one viewport',async({page})=>{
 await page.setViewportSize({width:1440,height:900});await page.goto('/')
 await expect(page.getByRole('separator',{name:'调整导师宽度'})).toBeVisible()
 expect(await page.evaluate(()=>document.documentElement.scrollHeight<=window.innerHeight)).toBe(true)
 await page.getByRole('button',{name:'新建项目',exact:true}).click()
 await page.getByLabel('项目名称',{exact:true}).fill('布局验收')
 await page.getByRole('button',{name:'创建项目',exact:true}).click()
 await editCode(page,'def demo(:\n    pass')
 await expect(page.getByText('发现 Python 语法错误；',{exact:false})).toBeVisible()
 await editCode(page,'def demo():\n    pass')
 await expect(page.getByText('本次语法问题已通过复查',{exact:false})).toBeVisible()
})
