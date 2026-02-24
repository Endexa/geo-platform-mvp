import { test, expect } from '@playwright/test'
import {
  setupDashboardMocks,
  setupAuthMock,
  setupAuditListMock,
  setupRecommendationMocks,
  setupCompetitorMocks,
  setupBrandMocks,
  setupAuditPageMocks,
} from './fixtures/test-helpers'

test.describe('Sidebar Navigation', () => {
  test('sidebar shows all navigation links', async ({ page }) => {
    await setupDashboardMocks(page)
    await page.goto('/dashboard')
    await page.waitForResponse('**/api/v1/dashboard/overview/**')

    // Verify sidebar navigation links exist
    const sidebar = page.locator('aside')
    await expect(sidebar.getByText('Dashboard')).toBeVisible()
    await expect(sidebar.getByText('AI Audit')).toBeVisible()
    await expect(sidebar.getByText('Recommendations')).toBeVisible()
    await expect(sidebar.getByText('Competitors')).toBeVisible()
    await expect(sidebar.getByText('Brands')).toBeVisible()
  })

  test('navigation links route to correct pages', async ({ page }) => {
    // Setup comprehensive mocks for all pages
    await setupDashboardMocks(page)
    await setupRecommendationMocks(page)
    await setupCompetitorMocks(page)
    await setupBrandMocks(page)
    await setupAuditPageMocks(page)

    await page.goto('/dashboard')
    await page.waitForResponse('**/api/v1/dashboard/overview/**')

    const sidebar = page.locator('aside')

    // Navigate to Audit
    await sidebar.getByText('AI Audit').click()
    await page.waitForURL(/\/audit/)
    await expect(page).toHaveURL(/\/audit/)

    // Navigate to Dashboard
    await sidebar.getByText('Dashboard').click()
    await page.waitForURL(/\/dashboard/)
    await expect(page).toHaveURL(/\/dashboard/)

    // Navigate to Recommendations
    await sidebar.getByText('Recommendations').click()
    await page.waitForURL(/\/recommendations/)
    await expect(page).toHaveURL(/\/recommendations/)

    // Navigate to Competitors
    await sidebar.getByText('Competitors').click()
    await page.waitForURL(/\/competitors/)
    await expect(page).toHaveURL(/\/competitors/)

    // Navigate to Brands
    await sidebar.getByText('Brands').click()
    await page.waitForURL(/\/brands/)
    await expect(page).toHaveURL(/\/brands/)
  })
})

test.describe('Auth Guards', () => {
  test.use({ storageState: { cookies: [], origins: [] } })

  const protectedRoutes = [
    '/audit',
    '/dashboard',
    '/recommendations',
    '/competitors',
    '/brands',
  ]

  for (const route of protectedRoutes) {
    test(`unauthenticated user visiting ${route} is redirected to login`, async ({
      page,
    }) => {
      await page.goto(route)
      await expect(page).toHaveURL(/\/login/, { timeout: 10000 })
    })
  }
})
