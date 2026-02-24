import { type Locator, type Page, expect } from '@playwright/test'

export class DashboardPage {
  readonly page: Page
  readonly heading: Locator
  readonly subtitle: Locator
  readonly auditSelector: Locator
  readonly combinedScore: Locator
  readonly visibilityScore: Locator
  readonly optimizationScore: Locator
  readonly topIssues: Locator
  readonly engineBreakdown: Locator
  readonly competitivePosition: Locator
  readonly trendChart: Locator
  readonly recommendationProgress: Locator
  readonly exportPdfButton: Locator
  readonly exportCsvButton: Locator
  readonly emptyState: Locator
  readonly startAuditLink: Locator

  constructor(page: Page) {
    this.page = page
    this.heading = page.getByRole('heading', { name: 'Dashboard' })
    this.subtitle = page.locator('text=GEO performance overview')
    this.auditSelector = page.locator('select')
    this.combinedScore = page.locator('text=Combined GEO Score')
    this.visibilityScore = page.locator('text=AI Visibility')
    this.optimizationScore = page.locator('text=Site Optimization')
    this.topIssues = page.locator('text=Top Issues to Fix')
    this.engineBreakdown = page.locator('text=AI Engine Breakdown')
    this.competitivePosition = page.locator('text=Competitive Position')
    this.trendChart = page.locator('text=Score Trends')
    this.recommendationProgress = page.locator(
      'text=Recommendation Progress'
    )
    this.exportPdfButton = page.locator('button:has-text("Export PDF")')
    this.exportCsvButton = page.locator('button:has-text("Export CSV")')
    this.emptyState = page.locator('text=No completed audits yet')
    this.startAuditLink = page.getByRole('link', { name: 'Start an Audit' })
  }

  async goto() {
    await this.page.goto('/dashboard')
  }

  async expectScoresVisible() {
    await expect(this.combinedScore).toBeVisible({ timeout: 10000 })
    await expect(this.visibilityScore).toBeVisible()
    await expect(this.optimizationScore).toBeVisible()
  }

  async expectEmptyState() {
    await expect(this.emptyState).toBeVisible({ timeout: 10000 })
    await expect(this.startAuditLink).toBeVisible()
  }

  async selectAudit(index: number) {
    const options = this.auditSelector.locator('option')
    const value = await options.nth(index).getAttribute('value')
    if (value) {
      await this.auditSelector.selectOption(value)
    }
  }

  async exportPdf() {
    await this.exportPdfButton.click()
  }

  async exportCsv() {
    await this.exportCsvButton.click()
  }
}
