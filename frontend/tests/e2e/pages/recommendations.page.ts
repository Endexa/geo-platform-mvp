import { type Locator, type Page, expect } from '@playwright/test'

export class RecommendationsPage {
  readonly page: Page
  readonly heading: Locator
  readonly subtitle: Locator
  readonly exportButton: Locator
  readonly tabPriority: Locator
  readonly tabPage: Locator
  readonly tabGaps: Locator
  readonly tabSentiment: Locator
  readonly filterCategory: Locator
  readonly filterStatus: Locator
  readonly emptyState: Locator
  readonly loadingState: Locator
  readonly startAuditLink: Locator

  constructor(page: Page) {
    this.page = page
    this.heading = page.getByRole('heading', { name: 'Recommendations' })
    this.subtitle = page.locator('text=Evidence-based fixes')
    this.exportButton = page.getByRole('button', { name: 'Export Fix Plan' })
    this.tabPriority = page.getByRole('button', { name: 'By Priority' })
    this.tabPage = page.getByRole('button', { name: 'By Page' })
    this.tabGaps = page.getByRole('button', { name: 'Content Gaps' })
    this.tabSentiment = page.getByRole('button', { name: 'Sentiment' })
    this.filterCategory = page.locator('select').first()
    this.filterStatus = page.locator('select').last()
    this.emptyState = page.locator(
      'text=No recommendations generated. Run an audit to get started.'
    )
    this.loadingState = page.locator('text=Loading recommendations...')
    this.startAuditLink = page.getByRole('link', { name: 'Start an Audit' })
  }

  async goto() {
    await this.page.goto('/recommendations')
    await this.page.waitForLoadState('networkidle')
  }

  async expectLoaded() {
    await expect(this.heading).toBeVisible({ timeout: 10000 })
    await expect(this.subtitle).toBeVisible()
  }

  async selectTab(tabName: 'By Priority' | 'By Page' | 'Content Gaps' | 'Sentiment') {
    await this.page.getByRole('button', { name: tabName }).click()
  }

  async expectEmptyState() {
    await expect(this.emptyState).toBeVisible({ timeout: 10000 })
  }
}
