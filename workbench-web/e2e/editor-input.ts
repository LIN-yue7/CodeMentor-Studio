import {expect,type Page} from '@playwright/test'
// Use the editor's own keyboard selection rather than DOM Range replacement.
export async function editCode(page:Page,code:string){
 const editor=page.getByRole('textbox',{name:'Python 代码'})
 await editor.click();await editor.press('ControlOrMeta+a');await page.keyboard.insertText(code)
 await expect(editor).toHaveText(code)
}
