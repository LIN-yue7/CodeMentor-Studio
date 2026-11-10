import {test,expect} from '@playwright/test'
test('self-check records first response and changes next diagnosis advice',async({page})=>{
 await page.goto('/?view=lessons')
 await page.getByRole('button',{name:'开始诊断'}).click()
 await page.getByText('用一道自查核对理解',{exact:true}).click()
 await page.getByRole('radio',{name:'2, 3, 4, 5',exact:true}).check()
 await page.getByRole('button',{name:'提交概念自查'}).click()
 await expect(page.getByText('讲解后自查未通过，',{exact:false})).toBeVisible()
 await expect(page.getByRole('radio',{name:'2, 3, 4',exact:true})).toBeDisabled()
 await page.getByRole('button',{name:'开始诊断'}).click()
 await expect(page.getByText('最近一次讲解后自查未通过：',{exact:false})).toBeVisible()
})
