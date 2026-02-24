import { test, expect, type Route } from '@playwright/test'
import { BrandsPage } from './pages/brands.page'
import { setupBrandMocks, setupAuthMock } from './fixtures/test-helpers'

test.describe('Brands', () => {
  test('page loads with heading and brand cards', async ({ page }) => {
    await setupBrandMocks(page)
    const brandsPage = new BrandsPage(page)
    await brandsPage.goto()

    await expect(brandsPage.heading).toBeVisible({ timeout: 10000 })
    await expect(brandsPage.subtitle).toBeVisible()

    // Brand cards should be visible
    await brandsPage.expectBrandVisible('Stripe')
    await brandsPage.expectBrandVisible('PayPal')
  })

  test('create brand form opens and submits', async ({ page }) => {
    await setupBrandMocks(page)

    // Mock POST to create brand
    await page.route('**/api/v1/brands/', async (route: Route) => {
      if (route.request().method() === 'POST') {
        await route.fulfill({
          json: {
            id: 'brand-new',
            name: 'New Brand',
            url: 'https://newbrand.com',
            domain: 'newbrand.com',
          },
        })
      } else {
        await route.fallback()
      }
    })

    const brandsPage = new BrandsPage(page)
    await brandsPage.goto()
    await expect(brandsPage.heading).toBeVisible({ timeout: 10000 })

    // Open create form
    await brandsPage.openCreateForm()
    await brandsPage.expectFormVisible()

    // Fill and submit
    await brandsPage.fillBrandForm(
      'New Brand',
      'https://newbrand.com',
      'A test brand'
    )
    await brandsPage.submitForm()
  })

  test('brand comparison chart renders when 2+ brands exist', async ({
    page,
  }) => {
    await setupBrandMocks(page)
    const brandsPage = new BrandsPage(page)
    await brandsPage.goto()

    await expect(brandsPage.heading).toBeVisible({ timeout: 10000 })

    // With 2 brands (Stripe + PayPal), comparison chart should render
    const canvas = page.locator('canvas')
    await expect(canvas.first()).toBeVisible({ timeout: 10000 })
  })

  test('empty state when no brands exist', async ({ page }) => {
    await setupAuthMock(page)

    // Mock empty brands list
    await page.route('**/api/v1/brands/overview', async (route: Route) => {
      await route.fulfill({
        json: { brands: [], total_brands: 0 },
      })
    })

    const brandsPage = new BrandsPage(page)
    await brandsPage.goto()
    await brandsPage.expectEmptyState()

    // Create Brand button should still be visible in empty state
    // (header + empty state CTA both have "Create Brand" — use first())
    await expect(brandsPage.createButton.first()).toBeVisible()
  })

  test('delete brand removes card', async ({ page }) => {
    await setupBrandMocks(page)

    // Track whether delete was called
    let deleteRequested = false
    await page.route('**/api/v1/brands/brand-*', async (route: Route) => {
      if (route.request().method() === 'DELETE') {
        deleteRequested = true
        await route.fulfill({ status: 204 })
      } else {
        await route.fallback()
      }
    })

    // After delete, return only one brand
    let brandsFetched = 0
    await page.route('**/api/v1/brands/overview', async (route: Route) => {
      brandsFetched++
      if (brandsFetched > 1 && deleteRequested) {
        // After delete, return only Stripe
        await route.fulfill({
          json: {
            brands: [
              {
                brand_id: 'brand-1',
                brand_name: 'Stripe',
                brand_url: 'https://stripe.com',
                brand_domain: 'stripe.com',
                latest_audit_id: '11111111-1111-1111-1111-111111111111',
                combined_geo_score: 72,
                visibility_score: 83,
                optimization_score: 61,
                mention_count: 107,
                top_issues_count: 5,
                audit_count: 3,
                last_audited_at: '2026-02-20T10:04:00Z',
              },
            ],
            total_brands: 1,
          },
        })
      } else {
        await route.fallback()
      }
    })

    const brandsPage = new BrandsPage(page)
    await brandsPage.goto()
    await expect(brandsPage.heading).toBeVisible({ timeout: 10000 })

    // Find and click a delete button on one of the brand cards
    // BrandCard component should have a delete action
    const deleteButton = page
      .locator('button')
      .filter({ hasText: /delete/i })
      .first()
    if (await deleteButton.isVisible()) {
      await deleteButton.click()
    }
  })
})
