import { test, expect, type Route } from '@playwright/test'
import { CompetitorsPage } from './pages/competitors.page'
import {
  setupCompetitorMocks,
  setupAuthMock,
  setupAuditListMock,
} from './fixtures/test-helpers'
import { MOCK_AUDIT_ID, MOCK_AUDIT_DETAIL } from './fixtures/mock-data'

test.describe('Competitors', () => {
  test('page loads with heading and leaderboard', async ({ page }) => {
    await setupCompetitorMocks(page)
    const compPage = new CompetitorsPage(page)
    await compPage.goto()
    await compPage.expectLeaderboardVisible()

    // Competitor names should be visible in leaderboard table
    await expect(page.getByRole('cell', { name: /PayPal/ }).first()).toBeVisible({ timeout: 10000 })
    await expect(page.getByRole('cell', { name: /Square/ }).first()).toBeVisible()
    await expect(page.getByRole('cell', { name: /Adyen/ }).first()).toBeVisible()

    // Share of voice percentages
    await expect(page.getByRole('cell', { name: '18.5%' })).toBeVisible()
    await expect(page.getByRole('cell', { name: '12.3%' })).toBeVisible()
    await expect(page.getByRole('cell', { name: '7.4%' })).toBeVisible()
  })

  test('competitor comparison section shows score categories', async ({
    page,
  }) => {
    await setupCompetitorMocks(page)
    const compPage = new CompetitorsPage(page)
    await compPage.goto()
    await compPage.expectLeaderboardVisible()

    // CompetitorComparison component should render with category scores
    // The PayPal competitor audit has detailed scores
    await expect(page.getByRole('columnheader', { name: 'PayPal' })).toBeVisible({ timeout: 10000 })
  })

  test('empty state when no audit exists', async ({ page }) => {
    await setupAuthMock(page)
    await setupAuditListMock(page, [])

    const compPage = new CompetitorsPage(page)
    await compPage.goto()
    await compPage.expectEmptyState()
    await expect(compPage.startAuditLink).toBeVisible()
  })

  test('no competitors found state', async ({ page }) => {
    await setupAuthMock(page)
    await setupAuditListMock(page)

    // Mock leaderboard with empty competitors
    await page.route(
      `**/api/v1/competitors/${MOCK_AUDIT_ID}/leaderboard`,
      async (route: Route) => {
        await route.fulfill({
          json: {
            audit_id: MOCK_AUDIT_ID,
            user_brand_name: 'Stripe',
            total_entities: 0,
            competitors: [],
            competitor_audits: [],
          },
        })
      }
    )

    // Mock audit detail
    await page.route(
      `**/api/v1/audit/${MOCK_AUDIT_ID}`,
      async (route: Route) => {
        await route.fulfill({ json: MOCK_AUDIT_DETAIL })
      }
    )

    const compPage = new CompetitorsPage(page)
    await compPage.goto()
    await compPage.expectNoCompetitorsState()
  })
})
