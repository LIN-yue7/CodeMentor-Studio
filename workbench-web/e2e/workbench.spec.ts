
import { expect, test } from '@playwright/test'

test('diagnose, request hint, grade, and pass a new variant', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('heading', { name: '编程复测工作台' })).toBeVisible()
  await expect(page.getByText('本地证据模式')).toBeVisible()
  await page.getByRole('button', { name: '开始诊断' }).click()
  await expect(page.getByText('第 3 行', { exact: true })).toBeVisible()
  await expect(page.getByText('range 的停止位置')).toBeVisible()
  await page.getByRole('button', { name: '查看下一条提示' }).click()
  await expect(page.getByText('先写出列表包含的两个下标。')).toBeVisible()
  await page.getByRole('textbox', { name: '填写答案' }).fill('6')
  await page.getByRole('button', { name: '提交答案' }).click()
  await expect(page.getByText('提示后通过', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: '重新挑战' }).click()
  await page.getByRole('textbox', { name: '填写答案' }).fill('7')
  await page.getByRole('button', { name: '提交答案' }).click()
  await expect(page.getByText('独立通过', { exact: true })).toBeVisible()
  await expect(page.getByText('接下来做一道不同题面的复测。')).toBeVisible()
  await page.reload()
  await expect(page.getByText('1 次独立通过')).toBeVisible()
})

test('cancel a pending request and retry the same submission', async ({ page }) => {
  await page.goto('/')
  let calls = 0
  const ids: string[] = []
  await page.route('**/api/diagnoses', async route => {
    calls += 1
    ids.push(route.request().postDataJSON().request_id)
    if (calls === 1) await new Promise(resolve => setTimeout(resolve, 1400))
    await route.continue().catch(() => undefined)
  })
  await page.getByRole('button', { name: '开始诊断' }).click()
  await expect.poll(() => calls).toBe(1)
  await page.getByRole('button', { name: '取消等待' }).click()
  await expect(page.getByText('已停止等待，代码仍在编辑器中。')).toBeVisible()
  await page.getByRole('button', { name: '重试诊断' }).click()
  await expect(page.getByText('第 3 行', { exact: true })).toBeVisible()
  expect(ids[0]).toBe(ids[1])
})

test('a diagnosis during slow initial session creation keeps its exercise owner', async ({ page }) => {
  let sessions = 0
  await page.route('**/api/session', async route => {
    sessions += 1
    await new Promise(resolve => setTimeout(resolve, 400))
    await route.continue()
  })
  await page.goto('/')
  await page.getByRole('button', { name: '开始诊断' }).click()
  await expect(page.getByText('第 3 行', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: '查看下一条提示' }).click()
  await expect(page.getByText('先写出列表包含的两个下标。')).toBeVisible()
  expect(sessions).toBe(1)
})

test('model output is rendered as text even if it contains markup', async ({ page }) => {
  await page.route('**/api/diagnoses', async route => {
    const response = await route.fetch()
    const result = await response.json()
    result.annotation = { explanation: '<img src=x onerror="document.title=\'injected\'">', citations: [] }
    await route.fulfill({ response, json: result })
  })
  await page.goto('/')
  await page.getByRole('button', { name: '开始诊断' }).click()
  await expect(page.getByText('<img src=x', { exact: false })).toBeVisible()
  await expect(page.locator('.model-note img')).toHaveCount(0)
})
