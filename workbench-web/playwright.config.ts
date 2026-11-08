
import { defineConfig, devices } from '@playwright/test'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { randomUUID } from 'node:crypto'

const port = 8766
const python = process.env.CODEMENTOR_TEST_PYTHON || 'python'
const url = `http://127.0.0.1:${port}`
export default defineConfig({
  testDir: './e2e',
  webServer: {
    command: `"${python}" -m uvicorn app.workbench:app --host 127.0.0.1 --port ${port}`,
    cwd: '..',
    url: `${url}/api/health`,
    reuseExistingServer: false,
    env: {
      CODEMENTOR_AI_MODE: 'local',
      DATABASE__SQLITE_PATH: join(tmpdir(), `codementor-${randomUUID()}.db`),
    },
  },
  use: { baseURL: url, channel: process.env.PLAYWRIGHT_CHANNEL || 'msedge' },
  projects: [
    { name: 'desktop', use: { ...devices['Desktop Edge'] } },
    { name: 'mobile', use: { ...devices['Pixel 7'], defaultBrowserType: 'chromium' } },
  ],
})
