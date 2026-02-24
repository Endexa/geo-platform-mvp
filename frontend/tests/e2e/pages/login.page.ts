import { type Locator, type Page, expect } from '@playwright/test'

export class LoginPage {
  readonly page: Page
  readonly heading: Locator
  readonly emailInput: Locator
  readonly passwordInput: Locator
  readonly signInButton: Locator
  readonly createAccountButton: Locator
  readonly toggleToRegister: Locator
  readonly toggleToLogin: Locator
  readonly errorMessage: Locator

  constructor(page: Page) {
    this.page = page
    this.heading = page.locator('h1', { hasText: 'GEO Platform' })
    this.emailInput = page.locator('input[type="email"]')
    this.passwordInput = page.locator('input[type="password"]')
    this.signInButton = page.getByRole('button', { name: 'Sign In' })
    this.createAccountButton = page.getByRole('button', {
      name: 'Create Account',
    })
    this.toggleToRegister = page.locator(
      "text=Don't have an account? Sign up"
    )
    this.toggleToLogin = page.locator(
      'text=Already have an account? Sign in'
    )
    this.errorMessage = page.locator('.text-red-700')
  }

  async goto() {
    await this.page.goto('/login')
    await this.page.waitForLoadState('networkidle')
  }

  async login(email: string, password: string) {
    await expect(this.emailInput).toBeVisible({ timeout: 10000 })
    await this.emailInput.fill(email)
    await this.passwordInput.fill(password)
    await this.signInButton.click()
  }

  async switchToRegister() {
    await expect(this.toggleToRegister).toBeVisible({ timeout: 5000 })
    await this.toggleToRegister.click()
  }

  async register(email: string, password: string) {
    await this.switchToRegister()
    // Wait for register form to render after Vue reactivity toggle
    await expect(this.createAccountButton).toBeVisible({ timeout: 5000 })
    await this.emailInput.fill(email)
    await this.passwordInput.fill(password)
    await this.createAccountButton.click()
  }

  async expectRedirectToAudit() {
    await expect(this.page).toHaveURL(/\/audit/, { timeout: 10000 })
  }

  async expectHeadingVisible() {
    await expect(this.heading).toBeVisible()
  }

  async expectErrorVisible() {
    await expect(this.errorMessage).toBeVisible({ timeout: 5000 })
  }
}
