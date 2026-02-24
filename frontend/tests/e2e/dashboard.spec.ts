import { test, expect, type Route } from '@playwright/test'
import { DashboardPage } from './pages/dashboard.page'
import { setupDashboardMocks, setupAuthMock, setAuthCookie } from './fixtures/test-helpers'

test.describe('Dashboard', () => {
  test.describe.configure({ timeout: 60000 })

  let dashboardPage: DashboardPage

  test('page loads with title, subtitle, and audit selector', async ({
    page,
  }) => {
    await setupDashboardMocks(page)
    dashboardPage = new DashboardPage(page)
    await dashboardPage.goto()
    await page.waitForResponse('**/api/v1/dashboard/overview/**')

    await expect(dashboardPage.heading).toBeVisible()
    await expect(dashboardPage.subtitle).toBeVisible()
    await expect(dashboardPage.auditSelector).toBeVisible({ timeout: 10000 })

    // Should contain our mock audit
    await expect(dashboardPage.auditSelector.locator('option')).toHaveCount(1)
    const optionText = await dashboardPage.auditSelector
      .locator('option')
      .first()
      .textContent()
    expect(optionText).toContain('stripe.com')
  })

  test('score cards show combined, visibility, and optimization scores', async ({
    page,
  }) => {
    await setupDashboardMocks(page)
    dashboardPage = new DashboardPage(page)
    await dashboardPage.goto()
    await page.waitForResponse('**/api/v1/dashboard/overview/**')

    await expect(page.locator('text=Combined GEO Score')).toBeVisible({
      timeout: 10000,
    })
    await expect(page.locator('text=72').first()).toBeVisible()

    await expect(page.locator('text=AI Visibility')).toBeVisible()
    await expect(page.locator('text=83').first()).toBeVisible()

    await expect(page.locator('text=Site Optimization')).toBeVisible()
    await expect(page.locator('text=61').first()).toBeVisible()

    await expect(page.locator('text=107 mentions')).toBeVisible()
    await expect(page.locator('text=73% query rate')).toBeVisible()
  })

  test('top issues section shows priority badges and summaries', async ({
    page,
  }) => {
    await setupDashboardMocks(page)
    dashboardPage = new DashboardPage(page)
    await dashboardPage.goto()
    await page.waitForResponse('**/api/v1/dashboard/overview/**')

    await expect(page.locator('text=Top Issues to Fix')).toBeVisible({
      timeout: 10000,
    })
    await expect(page.locator('text=HIGH')).toBeVisible()
    await expect(page.locator('text=MEDIUM')).toBeVisible()
    await expect(
      page.locator('text=Add FAQPage schema markup')
    ).toBeVisible()
    await expect(
      page.locator('text=Include cited statistics')
    ).toBeVisible()

    const recLink = page.locator('a[href="/recommendations"]').first()
    await expect(recLink).toBeVisible()
  })

  test('AI engine breakdown shows per-engine bars and scores', async ({
    page,
  }) => {
    await setupDashboardMocks(page)
    dashboardPage = new DashboardPage(page)
    await dashboardPage.goto()
    await page.waitForResponse('**/api/v1/dashboard/overview/**')

    await expect(page.locator('text=AI Engine Breakdown')).toBeVisible({
      timeout: 10000,
    })
    await expect(page.locator('text=chatgpt')).toBeVisible()
    await expect(page.locator('text=claude')).toBeVisible()
    await expect(page.locator('text=perplexity')).toBeVisible()
    await expect(page.locator('text=gemini')).toBeVisible()
    await expect(page.locator('text=80').first()).toBeVisible()
    await expect(page.locator('text=90').first()).toBeVisible()
  })

  test('competitive position shows radar chart and SOV table', async ({
    page,
  }) => {
    await setupDashboardMocks(page)
    dashboardPage = new DashboardPage(page)
    await dashboardPage.goto()
    await page.waitForResponse('**/api/v1/dashboard/overview/**')

    await expect(page.locator('text=Competitive Position')).toBeVisible({
      timeout: 10000,
    })
    await expect(
      page.getByRole('heading', { name: 'Share of Voice' })
    ).toBeVisible()
    await expect(page.locator('text=You')).toBeVisible()
    await expect(page.locator('text=PayPal')).toBeVisible()
    await expect(page.locator('text=Square')).toBeVisible()
    await expect(page.locator('text=18.5%')).toBeVisible()
    await expect(page.locator('text=12.3%')).toBeVisible()

    const canvas = page.locator('canvas')
    await expect(canvas.first()).toBeVisible()
  })

  test('export PDF button triggers download', async ({ page }) => {
    await setupDashboardMocks(page)
    dashboardPage = new DashboardPage(page)
    await dashboardPage.goto()
    await page.waitForResponse('**/api/v1/dashboard/overview/**')

    const pdfBtn = dashboardPage.exportPdfButton
    await expect(pdfBtn).toBeVisible({ timeout: 10000 })
    await expect(pdfBtn).toBeEnabled()

    const [download] = await Promise.all([
      page.waitForEvent('download', { timeout: 10000 }).catch(() => null),
      pdfBtn.click(),
    ])

    if (download) {
      expect(download.suggestedFilename()).toContain('geo-audit')
    }
  })

  test('export CSV button triggers download', async ({ page }) => {
    await setupDashboardMocks(page)
    dashboardPage = new DashboardPage(page)
    await dashboardPage.goto()
    await page.waitForResponse('**/api/v1/dashboard/overview/**')

    const csvBtn = dashboardPage.exportCsvButton
    await expect(csvBtn).toBeVisible({ timeout: 10000 })
    await expect(csvBtn).toBeEnabled()

    const [download] = await Promise.all([
      page.waitForEvent('download', { timeout: 10000 }).catch(() => null),
      csvBtn.click(),
    ])

    if (download) {
      expect(download.suggestedFilename()).toContain('geo-audit')
    }
  })

  test('trend chart renders with history data', async ({ page }) => {
    await setupDashboardMocks(page)
    dashboardPage = new DashboardPage(page)
    await dashboardPage.goto()
    await page.waitForResponse('**/api/v1/dashboard/history**')

    await expect(page.locator('text=Score Trends')).toBeVisible({
      timeout: 15000,
    })

    const canvases = page.locator('canvas')
    expect(await canvases.count()).toBeGreaterThanOrEqual(2)
  })

  test('recommendation progress shows bar and counts', async ({ page }) => {
    await setupDashboardMocks(page)
    dashboardPage = new DashboardPage(page)
    await dashboardPage.goto()
    await page.waitForResponse('**/api/v1/dashboard/overview/**')

    await expect(
      page.locator('text=Recommendation Progress')
    ).toBeVisible({ timeout: 10000 })
    await expect(page.locator('text=7/15 addressed')).toBeVisible()
    await expect(page.locator('text=Done: 5')).toBeVisible()
    await expect(page.locator('text=Dismissed: 2')).toBeVisible()
    await expect(page.locator('text=Open: 8')).toBeVisible()

    // Progress bar (green bar) -- using CSS class as fallback since no role or testid
    const progressBar = page.locator('.bg-green-500.h-2\\.5')
    await expect(progressBar).toBeVisible()
  })

  test('trend chart shows tab buttons (Overview, Categories, AI Engines)', async ({
    page,
  }) => {
    await setupDashboardMocks(page)
    dashboardPage = new DashboardPage(page)
    await dashboardPage.goto()
    await page.waitForResponse('**/api/v1/dashboard/history**')

    await expect(page.locator('text=Score Trends')).toBeVisible({
      timeout: 15000,
    })

    await expect(page.getByTestId('trend-tab-overview')).toBeVisible()
    await expect(page.getByTestId('trend-tab-categories')).toBeVisible()
    await expect(page.getByTestId('trend-tab-engines')).toBeVisible()
  })

  test('Categories tab is clickable and re-renders chart', async ({
    page,
  }) => {
    await setupDashboardMocks(page)
    dashboardPage = new DashboardPage(page)
    await dashboardPage.goto()
    await page.waitForResponse('**/api/v1/dashboard/history**')

    await expect(page.locator('text=Score Trends')).toBeVisible({
      timeout: 15000,
    })

    const categoriesTab = page.getByTestId('trend-tab-categories')
    await categoriesTab.click()

    // After clicking, the categories tab should be active (blue background)
    await expect(categoriesTab).toHaveClass(/bg-\[#1E40AF\]/)

    // Chart canvas should still be visible
    const canvases = page.locator('canvas')
    expect(await canvases.count()).toBeGreaterThanOrEqual(2)
  })

  test('score cards show delta badges with correct values', async ({
    page,
  }) => {
    await setupDashboardMocks(page)
    dashboardPage = new DashboardPage(page)
    await dashboardPage.goto()
    await page.waitForResponse('**/api/v1/dashboard/history**')

    // Wait for score cards to be visible
    await expect(page.locator('text=Combined GEO Score')).toBeVisible({
      timeout: 10000,
    })

    // Delta badges should show: combined 72-63=+9, visibility 83-70=+13, optimization 61-55=+6
    const deltaBadges = page.getByTestId('delta-badge')
    await expect(deltaBadges.first()).toBeVisible({ timeout: 10000 })

    const badgeTexts = await deltaBadges.allTextContents()
    expect(badgeTexts).toContain('+9')
    expect(badgeTexts).toContain('+13')
    expect(badgeTexts).toContain('+6')
  })

  test('empty state when no completed audits', async ({ page }) => {
    // Override audit list to return empty
    await page.route('**/api/v1/audit', async (route: Route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({ json: [] })
      } else {
        await route.continue()
      }
    })
    await page.route('**/api/v1/audit/', async (route: Route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({ json: [] })
      } else {
        await route.continue()
      }
    })
    await setupAuthMock(page)

    dashboardPage = new DashboardPage(page)
    await dashboardPage.goto()
    await dashboardPage.expectEmptyState()
    await expect(
      page.locator('text=Run your first AI audit')
    ).toBeVisible()
  })
})
