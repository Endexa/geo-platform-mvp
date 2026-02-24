import type { Page, Route } from '@playwright/test'
import {
  MOCK_AUDIT_ID,
  MOCK_AUDIT_LIST,
  MOCK_AUDIT_DETAIL,
  MOCK_OVERVIEW,
  MOCK_HISTORY,
  MOCK_USER,
  MOCK_RECOMMENDATION_LIST_RESPONSE,
  MOCK_SENTIMENT,
  MOCK_CONTENT_GAPS,
  MOCK_LEADERBOARD,
  MOCK_BRANDS_OVERVIEW,
  MOCK_BRAND_DETAIL,
} from './mock-data'

/** Mock the /auth/me endpoint to return a valid user */
export async function setupAuthMock(page: Page) {
  await page.route('**/api/v1/auth/me', async (route: Route) => {
    await route.fulfill({ json: MOCK_USER })
  })
}

/** Mock the audit list endpoint (matches with or without query params) */
export async function setupAuditListMock(
  page: Page,
  audits = MOCK_AUDIT_LIST
) {
  // Use regex to match /audit or /audit/ with optional query params
  await page.route(/\/api\/v1\/audit\/?(\?.*)?$/, async (route: Route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({ json: audits })
    } else {
      await route.fallback()
    }
  })
}

/** Mock all dashboard endpoints (auth + audit list + overview + history + exports) */
export async function setupDashboardMocks(page: Page) {
  await setupAuthMock(page)
  await setupAuditListMock(page)

  await page.route(
    `**/api/v1/dashboard/overview/${MOCK_AUDIT_ID}`,
    async (route: Route) => {
      await route.fulfill({ json: MOCK_OVERVIEW })
    }
  )

  await page.route('**/api/v1/dashboard/history**', async (route: Route) => {
    await route.fulfill({ json: MOCK_HISTORY })
  })

  await page.route(
    `**/api/v1/dashboard/${MOCK_AUDIT_ID}/export/pdf`,
    async (route: Route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/pdf',
        body: Buffer.from('%PDF-1.4 mock pdf content'),
        headers: {
          'Content-Disposition':
            'attachment; filename="geo-audit-stripe.com.pdf"',
        },
      })
    }
  )

  await page.route(
    `**/api/v1/dashboard/${MOCK_AUDIT_ID}/export/csv`,
    async (route: Route) => {
      await route.fulfill({
        status: 200,
        contentType: 'text/csv',
        body: 'Score Type,Value\nCombined GEO,72\nVisibility,83\nOptimization,61',
        headers: {
          'Content-Disposition':
            'attachment; filename="geo-audit-stripe.com.csv"',
        },
      })
    }
  )
}

/** Mock recommendation endpoints (auth + audit list + recs + sentiment + gaps) */
export async function setupRecommendationMocks(page: Page) {
  await setupAuthMock(page)
  await setupAuditListMock(page)

  await page.route(
    `**/api/v1/recommendations/${MOCK_AUDIT_ID}`,
    async (route: Route) => {
      await route.fulfill({ json: MOCK_RECOMMENDATION_LIST_RESPONSE })
    }
  )

  await page.route(
    `**/api/v1/recommendations/${MOCK_AUDIT_ID}/sentiment`,
    async (route: Route) => {
      await route.fulfill({ json: MOCK_SENTIMENT })
    }
  )

  await page.route(
    `**/api/v1/recommendations/${MOCK_AUDIT_ID}/content-gaps`,
    async (route: Route) => {
      await route.fulfill({ json: MOCK_CONTENT_GAPS })
    }
  )

  await page.route(
    `**/api/v1/recommendations/${MOCK_AUDIT_ID}/export/markdown`,
    async (route: Route) => {
      await route.fulfill({
        status: 200,
        contentType: 'text/markdown',
        body: '# Fix Plan\n\n## High Priority\n- Add FAQPage schema',
        headers: {
          'Content-Disposition': 'attachment; filename="fix-plan.md"',
        },
      })
    }
  )
}

/** Mock competitor endpoints (auth + audit list + leaderboard + audit detail) */
export async function setupCompetitorMocks(page: Page) {
  await setupAuthMock(page)
  await setupAuditListMock(page)

  await page.route(
    `**/api/v1/competitors/${MOCK_AUDIT_ID}/leaderboard`,
    async (route: Route) => {
      await route.fulfill({ json: MOCK_LEADERBOARD })
    }
  )

  await page.route(
    `**/api/v1/audit/${MOCK_AUDIT_ID}`,
    async (route: Route) => {
      await route.fulfill({ json: MOCK_AUDIT_DETAIL })
    }
  )
}

/** Mock brand endpoints (auth + brands overview + CRUD) */
export async function setupBrandMocks(page: Page) {
  await setupAuthMock(page)

  await page.route('**/api/v1/brands/overview', async (route: Route) => {
    await route.fulfill({ json: MOCK_BRANDS_OVERVIEW })
  })

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

  await page.route('**/api/v1/brands/brand-*', async (route: Route) => {
    if (route.request().method() === 'DELETE') {
      await route.fulfill({ status: 204 })
    } else if (route.request().method() === 'PUT') {
      await route.fulfill({ json: MOCK_BRAND_DETAIL })
    } else if (route.request().method() === 'GET') {
      await route.fulfill({ json: MOCK_BRAND_DETAIL })
    } else {
      await route.fallback()
    }
  })
}

/** Mock audit page endpoints (auth + audit list + audit detail with results) */
export async function setupAuditPageMocks(page: Page) {
  await setupAuthMock(page)
  await setupAuditListMock(page)

  await page.route(
    `**/api/v1/audit/${MOCK_AUDIT_ID}`,
    async (route: Route) => {
      await route.fulfill({ json: MOCK_AUDIT_DETAIL })
    }
  )

  // Mock competitor leaderboard for audit results page
  await page.route(
    `**/api/v1/competitors/${MOCK_AUDIT_ID}/leaderboard`,
    async (route: Route) => {
      await route.fulfill({ json: MOCK_LEADERBOARD })
    }
  )

  // Mock recommendations for audit results page
  await page.route(
    `**/api/v1/recommendations/${MOCK_AUDIT_ID}`,
    async (route: Route) => {
      await route.fulfill({ json: MOCK_RECOMMENDATION_LIST_RESPONSE })
    }
  )
}

/** Set an auth cookie on the page context */
export async function setAuthCookie(page: Page, token = 'mock-token') {
  await page.context().addCookies([
    {
      name: 'access_token',
      value: token,
      domain: 'localhost',
      path: '/',
    },
  ])
}
