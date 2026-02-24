import { type Locator, type Page, expect } from '@playwright/test'

export class CompetitorsPage {
  readonly page: Page
  readonly heading: Locator
  readonly subtitle: Locator
  readonly emptyState: Locator
  readonly noCompetitors: Locator
  readonly startAuditLink: Locator
  readonly loadingState: Locator

  constructor(page: Page) {
    this.page = page
    this.heading = page.getByRole('heading', {
      name: 'Competitor Discovery',
    })
    this.subtitle = page.locator(
      'text=See which brands AI engines mention alongside yours'
    )
    this.emptyState = page.locator(
      'text=Run an audit first to discover competitors.'
    )
    this.noCompetitors = page.locator(
      'text=No competitors found in AI responses.'
    )
    this.startAuditLink = page.getByRole('link', {
      name: 'Start an Audit',
    })
    this.loadingState = page.locator('text=Loading competitor data...')
  }

  async goto() {
    await this.page.goto('/competitors')
    await this.page.waitForLoadState('networkidle')
  }

  async expectLeaderboardVisible() {
    await expect(this.heading).toBeVisible({ timeout: 10000 })
    await expect(this.subtitle).toBeVisible()
  }

  async expectEmptyState() {
    await expect(this.emptyState).toBeVisible({ timeout: 10000 })
    await expect(this.startAuditLink).toBeVisible()
  }

  async expectNoCompetitorsState() {
    await expect(this.noCompetitors).toBeVisible({ timeout: 10000 })
  }
}
