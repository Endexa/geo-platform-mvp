import { test, expect, type Route } from '@playwright/test'
import { RecommendationsPage } from './pages/recommendations.page'
import {
  setupRecommendationMocks,
  setupAuthMock,
  setupAuditListMock,
} from './fixtures/test-helpers'

test.describe('Recommendations', () => {
  test('page loads with heading and recommendations list', async ({
    page,
  }) => {
    await setupRecommendationMocks(page)
    const recsPage = new RecommendationsPage(page)
    await recsPage.goto()
    await recsPage.expectLoaded()

    // Recommendation cards should be rendered
    await expect(
      page.locator('text=Add FAQPage schema markup')
    ).toBeVisible({ timeout: 10000 })

    // Priority labels visible
    await expect(page.locator('text=High Priority')).toBeVisible()
    await expect(page.locator('text=Medium Priority')).toBeVisible()
  })

  test('tab navigation switches between views', async ({ page }) => {
    await setupRecommendationMocks(page)
    const recsPage = new RecommendationsPage(page)
    await recsPage.goto()
    await recsPage.expectLoaded()

    // Default tab is "By Priority"
    await expect(recsPage.tabPriority).toBeVisible()

    // Switch to "By Page" tab
    await recsPage.selectTab('By Page')
    // Page groups should appear (site-wide recommendations have null page_url)
    await expect(page.getByRole('button', { name: /Site-wide/ })).toBeVisible({
      timeout: 5000,
    })

    // Switch to "Content Gaps" tab
    await recsPage.selectTab('Content Gaps')
    await expect(
      page.locator('text=best payment processing for startups')
    ).toBeVisible({ timeout: 5000 })

    // Switch to "Sentiment" tab
    await recsPage.selectTab('Sentiment')
    // Sentiment data should render
    await expect(page.locator('text=chatgpt')).toBeVisible({ timeout: 5000 })
  })

  test('recommendation card shows evidence and impact', async ({ page }) => {
    await setupRecommendationMocks(page)
    const recsPage = new RecommendationsPage(page)
    await recsPage.goto()
    await recsPage.expectLoaded()

    // Check that at least one card contains summary, criterion name, and impact
    await expect(
      page.locator('text=Add FAQPage schema markup')
    ).toBeVisible({ timeout: 10000 })
    await expect(page.locator('text=FAQPage Schema').first()).toBeVisible()
    await expect(page.locator('text=High Impact').first()).toBeVisible()
  })

  test('export fix plan button is visible', async ({ page }) => {
    await setupRecommendationMocks(page)
    const recsPage = new RecommendationsPage(page)
    await recsPage.goto()
    await recsPage.expectLoaded()

    await expect(recsPage.exportButton).toBeVisible({ timeout: 10000 })
    await expect(recsPage.exportButton).toBeEnabled()
  })

  test('empty state when no audit selected', async ({ page }) => {
    await setupAuthMock(page)
    // Return empty audit list so no audit is auto-selected
    await setupAuditListMock(page, [])

    const recsPage = new RecommendationsPage(page)
    await recsPage.goto()
    await recsPage.expectEmptyState()
    await expect(recsPage.startAuditLink).toBeVisible()
  })

  test('sentiment tab renders engine sentiment data', async ({ page }) => {
    await setupRecommendationMocks(page)
    const recsPage = new RecommendationsPage(page)
    await recsPage.goto()
    await recsPage.expectLoaded()

    await recsPage.selectTab('Sentiment')
    // Sentiment breakdown should show engine names
    await expect(page.locator('text=chatgpt')).toBeVisible({ timeout: 5000 })
    await expect(page.locator('text=perplexity')).toBeVisible()
  })
})
