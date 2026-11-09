import { expect, test } from '@playwright/test'

// Break caught: removing the mobile section navigation makes the answer form hard to reach.
test('section navigation reaches practice and evidence link returns to editable code', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: '开始诊断' }).click()
  const navigation = page.getByRole('navigation', { name: '工作区导航' })
  await navigation.getByRole('link', { name: '复测', exact: true }).click()
  await expect(page.getByRole('textbox', { name: '填写答案' })).toBeInViewport()
  await navigation.getByRole('link', { name: '诊断', exact: true }).click()
  await page.getByRole('button', { name: '第 3 行', exact: true }).click()
  await expect(page.getByRole('textbox', { name: 'Python 代码' })).toBeFocused()
  await expect(page.getByRole('textbox', { name: 'Python 代码' })).toBeInViewport()
  await page.getByRole('textbox', { name: 'Python 代码' }).press('End')
  await page.getByRole('textbox', { name: 'Python 代码' }).press('Space')
  await expect(page.getByText('当前代码已改动，以下证据属于上次提交。')).toBeVisible()
  await expect(page.getByRole('button', { name: '第 3 行', exact: true })).toBeDisabled()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
})

test('keyboard moves from submitted code to its evidence before practice', async ({ page }) => {
  await page.goto('/')
  const start = page.getByRole('button', { name: '开始诊断' })
  await start.click()
  await expect(page.getByRole('button', { name: '第 3 行' })).toBeVisible()
  await start.focus()
  await page.keyboard.press('Tab')
  await expect(page.getByRole('button', { name: '第 3 行' })).toBeFocused()
})

test('a model citation opens the actual retrieved source card', async ({ page }) => {
  // Only the unavailable model explanation is a fixture; source cards come from the real API.
  let content = ''
  await page.route('**/api/diagnoses', async route => {
    const response = await route.fetch()
    const result = await response.json()
    content = result.cards[0].content
    result.annotation = { explanation: '测试模型引用交互。', citations: [result.cards[0].id] }
    await route.fulfill({ response, json: result })
  })
  await page.goto('/')
  await page.getByRole('button', { name: '开始诊断' }).click()
  await page.getByRole('link', { name: '证据 1', exact: true }).click()
  await expect(page.getByText(content, { exact: true })).toBeVisible()
})

test('profile failure stays unknown until a successful retry', async ({ page }) => {
  let failed = false
  await page.route('**/api/profile', async route => {
    if (!failed) { failed = true; await route.fulfill({ status: 503, json: { detail: 'test outage' } }) }
    else await route.continue()
  })
  await page.goto('/')
  const profile = page.getByRole('region', { name: '学习记录', exact: true })
  await expect(profile.getByText('学习记录暂时无法刷新。')).toBeVisible()
  await expect(profile.locator('.profile-overview')).toHaveCount(0)
  await profile.getByRole('button', { name: '重试加载' }).click()
  await expect(profile.getByText('还没有学习记录。完成诊断和复测后，这里会显示你的掌握证据。')).toBeVisible()
  await expect(profile.locator('.profile-overview')).toBeVisible()
})

test('a previously exposed answer is assisted without claiming a hint was used', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: '开始诊断' }).click()
  // Complete the three current variants, then revisit the first one without hints.
  // The initial template is boundary-a-v2, not the legacy exposed boundary-a-v1.
  for (const answer of ['6', '7', '11']) {
    await page.getByRole('textbox', { name: '填写答案' }).fill(answer)
    await page.getByRole('button', { name: '提交答案' }).click()
    await expect(page.getByText('独立通过', { exact: true })).toBeVisible()
    await page.getByRole('button', { name: '重新挑战' }).click()
  }
  await page.getByRole('textbox', { name: '填写答案' }).fill('6')
  await page.getByRole('button', { name: '提交答案' }).click()
  const practice = page.getByRole('region', { name: '变式复测', exact: true })
  await expect(practice.getByText('辅助通过', { exact: true })).toBeVisible()
  await expect(practice.getByText('提示后通过', { exact: true })).toHaveCount(0)
  await expect(page.getByText('1 次辅助通过', { exact: true })).toBeVisible()
})

test('narrow phone layout fits the usable width including scrollbar space', async ({ page }) => {
  await page.setViewportSize({ width: 305, height: 740 })
  await page.goto('/')
  await expect(page.getByRole('textbox', { name: 'Python 代码' })).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true)
})

