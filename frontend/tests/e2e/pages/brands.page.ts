import { type Locator, type Page, expect } from '@playwright/test'

export class BrandsPage {
  readonly page: Page
  readonly heading: Locator
  readonly subtitle: Locator
  readonly createButton: Locator
  readonly brandNameInput: Locator
  readonly brandUrlInput: Locator
  readonly brandDescInput: Locator
  readonly submitButton: Locator
  readonly cancelButton: Locator
  readonly comparisonChart: Locator
  readonly emptyState: Locator
  readonly formError: Locator

  constructor(page: Page) {
    this.page = page
    this.heading = page.getByRole('heading', { name: 'Brands' })
    this.subtitle = page.locator(
      'text=Manage brands and compare GEO performance'
    )
    this.createButton = page.getByRole('button', { name: 'Create Brand' })
    this.brandNameInput = page.locator('#brand-name')
    this.brandUrlInput = page.locator('#brand-url')
    this.brandDescInput = page.locator('#brand-desc')
    this.submitButton = page
      .locator('form')
      .getByRole('button', { name: /Create Brand|Update Brand/ })
    this.cancelButton = page.getByRole('button', { name: 'Cancel' })
    this.comparisonChart = page.locator('canvas')
    this.emptyState = page.locator('text=No brands yet')
    this.formError = page.locator('.text-red-600')
  }

  async goto() {
    await this.page.goto('/brands')
    await this.page.waitForLoadState('networkidle')
  }

  async openCreateForm() {
    await this.createButton.first().click()
  }

  async fillBrandForm(name: string, url: string, description?: string) {
    await this.brandNameInput.fill(name)
    await this.brandUrlInput.fill(url)
    if (description) {
      await this.brandDescInput.fill(description)
    }
  }

  async submitForm() {
    await this.submitButton.click()
  }

  async expectBrandVisible(name: string) {
    // Use heading role to avoid strict mode violations (brand name appears in h3 + domain text)
    await expect(
      this.page.locator('h3', { hasText: name }).first()
    ).toBeVisible({ timeout: 10000 })
  }

  async expectEmptyState() {
    await expect(this.emptyState).toBeVisible({ timeout: 10000 })
  }

  async expectFormVisible() {
    await expect(this.brandNameInput).toBeVisible()
    await expect(this.brandUrlInput).toBeVisible()
  }
}
