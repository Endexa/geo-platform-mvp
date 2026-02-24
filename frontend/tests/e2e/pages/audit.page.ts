import { type Locator, type Page, expect } from '@playwright/test'

export class AuditPage {
  readonly page: Page
  readonly heading: Locator
  readonly urlInput: Locator
  readonly startButton: Locator
  readonly progressIndicator: Locator
  readonly visibilityScore: Locator
  readonly optimizationScore: Locator
  readonly queryList: Locator
  readonly errorState: Locator

  constructor(page: Page) {
    this.page = page
    this.heading = page.getByRole('heading', {
      name: 'AI Brand Visibility Audit',
    })
    this.urlInput = page.locator('input[type="url"]')
    this.startButton = page.getByRole('button', { name: 'Start AI Audit' })
    this.progressIndicator = page.locator('text=Audit in Progress')
    this.visibilityScore = page.locator('text=Visibility Score')
    this.optimizationScore = page.locator('text=Optimization Score')
    this.queryList = page.locator('[data-testid="query-list"]')
    this.errorState = page.locator('text=Audit failed')
  }

  async goto() {
    await this.page.goto('/audit')
    await this.page.waitForLoadState('networkidle')
  }

  async startAudit(url: string) {
    // Ensure form is fully rendered before interacting
    await expect(this.urlInput).toBeVisible({ timeout: 10000 })
    await this.urlInput.fill(url)
    // Wait for Vue reactivity to enable button after URL validation
    await expect(this.startButton).toBeEnabled({ timeout: 5000 })
    await this.startButton.click()
  }

  async expectHeadingVisible() {
    await expect(this.heading).toBeVisible({ timeout: 10000 })
  }

  async expectFormVisible() {
    await expect(this.heading).toBeVisible({ timeout: 10000 })
    await expect(this.urlInput).toBeVisible()
    await expect(this.startButton).toBeVisible()
  }

  async expectProgressVisible() {
    await expect(this.progressIndicator).toBeVisible({ timeout: 10000 })
  }

  async expectResultsVisible() {
    await expect(this.visibilityScore).toBeVisible({ timeout: 10000 })
    await expect(this.optimizationScore).toBeVisible({ timeout: 10000 })
  }
}
