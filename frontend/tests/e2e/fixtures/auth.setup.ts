import { test as setup, expect } from '@playwright/test'

const authFile = 'playwright/.auth/user.json'

setup('authenticate', async ({ page }) => {
  const email = `e2e-${Date.now()}@test.com`
  const password = 'MyPassword123@'

  // Register via API (faster than UI)
  const response = await page.request.post('http://localhost:8000/api/v1/auth/register', {
    data: { email, password },
  })
  expect(response.ok()).toBeTruthy()
  const body = await response.json()
  const accessToken = body.access_token

  // Set cookie in the browser context
  await page.context().addCookies([
    {
      name: 'access_token',
      value: accessToken,
      domain: 'localhost',
      path: '/',
    },
  ])

  // Verify by visiting a protected page
  await page.goto('http://localhost:3000/audit')
  await expect(
    page.getByRole('heading', { name: 'AI Brand Visibility Audit' })
  ).toBeVisible({ timeout: 10000 })

  // Save storage state
  await page.context().storageState({ path: authFile })
})
