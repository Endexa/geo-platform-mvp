import { test as setup, expect } from '@playwright/test'
import * as fs from 'fs'
import * as path from 'path'

const authFile = 'playwright/.auth/user.json'

setup('authenticate', async ({ page }) => {
  const isCI = !!process.env.CI

  if (isCI) {
    // In CI, no real backend — create a mock auth state with a fake cookie.
    // All API calls are intercepted via Playwright route mocks in test helpers.
    const authDir = path.dirname(authFile)
    if (!fs.existsSync(authDir)) {
      fs.mkdirSync(authDir, { recursive: true })
    }

    await page.context().addCookies([
      {
        name: 'access_token',
        value: 'ci-mock-token',
        domain: 'localhost',
        path: '/',
      },
    ])

    await page.context().storageState({ path: authFile })
    return
  }

  // Locally: register via real backend API
  const email = `e2e-${Date.now()}@test.com`
  const password = 'MyPassword123@'

  const response = await page.request.post('http://localhost:8000/api/v1/auth/register', {
    data: { email, password },
  })
  expect(response.ok()).toBeTruthy()
  const body = await response.json()
  const accessToken = body.access_token

  await page.context().addCookies([
    {
      name: 'access_token',
      value: accessToken,
      domain: 'localhost',
      path: '/',
    },
  ])

  await page.goto('http://localhost:3000/audit')
  await expect(
    page.getByRole('heading', { name: 'AI Brand Visibility Audit' })
  ).toBeVisible({ timeout: 10000 })

  await page.context().storageState({ path: authFile })
})
