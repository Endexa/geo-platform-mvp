import { test, expect } from '@playwright/test'
import { LoginPage } from './pages/login.page'

// Auth tests run without storageState -- they test the auth flow itself
test.use({ storageState: { cookies: [], origins: [] } })

test.describe('Authentication', () => {
  test('register new account and redirect to audit', async ({ page }) => {
    const loginPage = new LoginPage(page)
    await loginPage.goto()
    await loginPage.expectHeadingVisible()

    const email = `e2e-auth-${Date.now()}@test.com`
    await loginPage.register(email, 'MyPassword123@')
    await loginPage.expectRedirectToAudit()
  })

  test('login with existing account redirects to audit', async ({ page }) => {
    const email = `e2e-login-${Date.now()}@test.com`
    const password = 'MyPassword123@'

    // Register via API first
    const regResponse = await page.request.post(
      'http://localhost:8000/api/v1/auth/register',
      { data: { email, password } }
    )
    expect(regResponse.ok()).toBeTruthy()

    const loginPage = new LoginPage(page)
    await loginPage.goto()
    await loginPage.login(email, password)
    await loginPage.expectRedirectToAudit()
  })

  test('invalid credentials show error message', async ({ page }) => {
    const loginPage = new LoginPage(page)
    await loginPage.goto()
    await loginPage.login('nonexistent@test.com', 'WrongPassword123@')
    await loginPage.expectErrorVisible()
  })

  test('unauthenticated user is redirected to login', async ({ page }) => {
    await page.context().clearCookies()
    await page.goto('/audit')
    await expect(page).toHaveURL(/\/login/, { timeout: 10000 })
  })
})
