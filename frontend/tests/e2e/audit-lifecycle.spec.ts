import { test, expect, type Route } from '@playwright/test'
import { AuditPage } from './pages/audit.page'
import {
  setupAuthMock,
  setupAuditListMock,
  setupAuditPageMocks,
} from './fixtures/test-helpers'
import { MOCK_AUDIT_ID, MOCK_AUDIT_DETAIL } from './fixtures/mock-data'

test.describe('Audit Lifecycle', () => {
  test('audit page shows URL input and start button', async ({ page }) => {
    await setupAuthMock(page)
    await setupAuditListMock(page, [])

    const auditPage = new AuditPage(page)
    await auditPage.goto()
    await auditPage.expectFormVisible()

    await expect(auditPage.startButton).toHaveText('Start AI Audit')
  })

  test('starting audit shows progress indicator', async ({ page }) => {
    await setupAuthMock(page)
    await setupAuditListMock(page, [])

    // Mock POST to start audit
    await page.route('**/api/v1/audit/', async (route: Route) => {
      if (route.request().method() === 'POST') {
        await route.fulfill({
          json: { id: MOCK_AUDIT_ID, status: 'pending' },
        })
      } else {
        await route.fallback()
      }
    })

    // Mock polling -- return progressive statuses using a counter
    let pollCount = 0
    await page.route(
      `**/api/v1/audit/${MOCK_AUDIT_ID}`,
      async (route: Route) => {
        pollCount++
        const statuses = ['crawling', 'generating_queries', 'dispatching', 'dispatching']
        const status = statuses[Math.min(pollCount - 1, statuses.length - 1)]

        await route.fulfill({
          json: {
            id: MOCK_AUDIT_ID,
            url: 'https://stripe.com',
            domain: 'stripe.com',
            status,
            error_message: null,
            visibility_score: null,
            optimization_score: null,
            queries: [],
            dispatch_summary: null,
            page_scores: [],
          },
        })
      }
    )

    const auditPage = new AuditPage(page)
    await auditPage.goto()
    await auditPage.startAudit('https://stripe.com')
    await auditPage.expectProgressVisible()
  })

  test('completed audit displays visibility and optimization scores', async ({
    page,
  }) => {
    await setupAuditPageMocks(page)

    // Override audit list to include a completed audit
    // The audit page shows results if the audit is completed
    // We need to simulate navigating to a completed audit
    await page.route('**/api/v1/audit/', async (route: Route) => {
      if (route.request().method() === 'POST') {
        await route.fulfill({
          json: { id: MOCK_AUDIT_ID, status: 'pending' },
        })
      } else if (route.request().method() === 'GET') {
        await route.fulfill({
          json: [
            {
              id: MOCK_AUDIT_ID,
              domain: 'stripe.com',
              url: 'https://stripe.com',
              status: 'completed',
              created_at: '2026-02-20T10:00:00Z',
              completed_at: '2026-02-20T10:04:00Z',
            },
          ],
        })
      } else {
        await route.fallback()
      }
    })

    // Mock polling to return completed immediately
    let pollCount = 0
    await page.route(
      `**/api/v1/audit/${MOCK_AUDIT_ID}`,
      async (route: Route) => {
        pollCount++
        // First call: pending to trigger polling, second: completed
        if (pollCount <= 1) {
          await route.fulfill({
            json: {
              ...MOCK_AUDIT_DETAIL,
              status: 'pending',
              visibility_score: null,
              optimization_score: null,
            },
          })
        } else {
          await route.fulfill({ json: MOCK_AUDIT_DETAIL })
        }
      }
    )

    const auditPage = new AuditPage(page)
    await auditPage.goto()
    await auditPage.startAudit('https://stripe.com')

    // Wait for the results to appear
    await expect(page.locator('text=Visibility Score')).toBeVisible({
      timeout: 15000,
    })
    await expect(page.locator('text=Optimization Score')).toBeVisible()
  })

  test('audit results show query list with mention indicators', async ({
    page,
  }) => {
    await setupAuditPageMocks(page)

    // Override audit detail to return completed with queries
    await page.route(
      `**/api/v1/audit/${MOCK_AUDIT_ID}`,
      async (route: Route) => {
        await route.fulfill({ json: MOCK_AUDIT_DETAIL })
      }
    )

    // Simulate a completed audit by starting one and having it complete immediately
    await page.route('**/api/v1/audit/', async (route: Route) => {
      if (route.request().method() === 'POST') {
        await route.fulfill({
          json: { id: MOCK_AUDIT_ID, status: 'pending' },
        })
      } else if (route.request().method() === 'GET') {
        await route.fulfill({
          json: [
            {
              id: MOCK_AUDIT_ID,
              domain: 'stripe.com',
              url: 'https://stripe.com',
              status: 'completed',
            },
          ],
        })
      } else {
        await route.fallback()
      }
    })

    const auditPage = new AuditPage(page)
    await auditPage.goto()
    await auditPage.startAudit('https://stripe.com')

    // Wait for queries to appear (from MOCK_AUDIT_DETAIL.queries)
    // Use .first() because query text appears in both AuditResults (QueryDetail) and QueryEditor
    await expect(
      page.locator('text=best payment processing platform').first()
    ).toBeVisible({ timeout: 15000 })
    await expect(
      page.locator('text=Stripe vs PayPal comparison').first()
    ).toBeVisible()
  })

  test('empty state shows URL input form when no audits exist', async ({
    page,
  }) => {
    await setupAuthMock(page)
    await setupAuditListMock(page, [])

    const auditPage = new AuditPage(page)
    await auditPage.goto()

    // Should show the form for starting a new audit
    await auditPage.expectFormVisible()
    await expect(auditPage.urlInput).toBeEditable()
  })
})
