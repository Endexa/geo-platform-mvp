# Phase 11: End-to-End Testing with Playwright - Research

**Researched:** 2026-02-23
**Domain:** End-to-end browser testing for a full-stack GEO platform (Nuxt 3 + FastAPI + PostgreSQL + Redis + Celery)
**Confidence:** HIGH

## Summary

The GEO platform already has a partial Playwright setup: `@playwright/test` v1.58.2 is installed, a basic `playwright.config.ts` exists pointing at `./tests/e2e`, and two spec files exist (`auth-and-audit.spec.ts` with 3 tests, `dashboard-phase9.spec.ts` with 10 tests using route mocking). However, the current setup lacks several critical elements for production-grade E2E testing: no authentication state reuse (each test re-registers or mocks auth), no Page Object Model structure, no webServer configuration for automatic server startup, no CI integration, no coverage of 8 of 11 pages, and no test isolation strategy.

The platform has 11 Vue pages (login, audit, dashboard, recommendations, competitors, brands, analyze, brand-voice, optimization, settings, index), 22 components, 2 composables (useApiFetch, useAuth), and an auth middleware. The backend has 12 API route files across auth, audit, dashboard, recommendations, competitors, brands, and more. All protected routes require JWT authentication via cookie-based tokens. The audit pipeline is asynchronous (Celery), requiring polling-aware test strategies.

**Primary recommendation:** Use Playwright's project dependencies pattern with a `setup` project for authentication, Page Object Model for page abstractions, route mocking for deterministic data (following the pattern already established in dashboard-phase9.spec.ts), and webServer configuration for automatic frontend/backend startup. Organize tests by user journey (auth, audit lifecycle, dashboard, recommendations, competitors, brands) rather than by page.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| @playwright/test | 1.58.2 | E2E test runner + assertions + browser automation | Already installed. Industry standard. Auto-waiting, multi-browser, built-in assertions |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| @playwright/test (built-in fixtures) | 1.58.2 | Authentication state reuse via storageState | Every test that needs auth (all except login page) |
| @playwright/test (built-in route mocking) | 1.58.2 | API response mocking via page.route() | Tests needing deterministic data without full backend |
| dotenv | (existing) | Environment variable loading for test config | Load test-specific env vars (API URLs, test credentials) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| @playwright/test | @nuxt/test-utils with Playwright | Nuxt test-utils adds a layer of abstraction but is primarily for component/integration testing. Direct Playwright is more flexible for full-stack E2E, and the project already uses it directly |
| Route mocking (page.route) | HAR file recording/playback | HAR files capture real traffic for replay but are brittle when APIs change. Route mocking is more maintainable for this project since mock data patterns are already established |
| Manual test data setup | Database seeding scripts | DB seeding gives real data but requires DB access in tests. Route mocking is simpler and already proven in the codebase |

**Installation:**
No new packages needed. `@playwright/test` v1.58.2 is already installed. Only need to run `npx playwright install` to ensure browser binaries are available.

## Architecture Patterns

### Recommended Project Structure
```
frontend/
├── playwright.config.ts              # Enhanced config with webServer, projects, auth
├── playwright/.auth/                  # Auth state files (gitignored)
│   └── user.json                     # Stored auth state
├── tests/
│   └── e2e/
│       ├── fixtures/                 # Shared test fixtures and mock data
│       │   ├── auth.setup.ts         # Auth setup project (register + save state)
│       │   ├── mock-data.ts          # Centralized mock data (extracted from existing tests)
│       │   └── test-helpers.ts       # Shared utilities (setupMocks, etc.)
│       ├── pages/                    # Page Object Models
│       │   ├── login.page.ts         # LoginPage POM
│       │   ├── audit.page.ts         # AuditPage POM
│       │   ├── dashboard.page.ts     # DashboardPage POM
│       │   ├── recommendations.page.ts
│       │   ├── competitors.page.ts
│       │   └── brands.page.ts        # BrandsPage POM
│       ├── auth.spec.ts              # Auth flow tests (login, register, guard)
│       ├── audit-lifecycle.spec.ts   # Full audit lifecycle (start, progress, results)
│       ├── dashboard.spec.ts         # Dashboard rendering + interactions
│       ├── recommendations.spec.ts   # Recommendations page (tabs, filters, status updates)
│       ├── competitors.spec.ts       # Competitor discovery page
│       ├── brands.spec.ts            # Multi-brand management (Phase 10)
│       └── navigation.spec.ts        # Cross-page navigation, sidebar, auth guards
```

### Pattern 1: Project Dependencies for Authentication
**What:** Use Playwright's project dependencies to authenticate once, save state, and reuse across all test projects.
**When to use:** Every test except login page tests.
**Example:**
```typescript
// Source: https://playwright.dev/docs/auth
// playwright.config.ts
import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 30000,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: process.env.CI
    ? [['html', { open: 'never' }], ['github']]
    : [['html', { open: 'on-failure' }]],
  use: {
    baseURL: 'http://localhost:3000',
    headless: true,
    screenshot: 'only-on-failure',
    trace: 'on-first-retry',
  },
  webServer: [
    {
      command: 'cd ../backend && uvicorn app.main:app --host 0.0.0.0 --port 8000',
      url: 'http://localhost:8000/health',
      name: 'Backend',
      timeout: 120000,
      reuseExistingServer: !process.env.CI,
    },
    {
      command: 'npm run dev',
      url: 'http://localhost:3000',
      name: 'Frontend',
      timeout: 120000,
      reuseExistingServer: !process.env.CI,
    },
  ],
  projects: [
    { name: 'setup', testMatch: /.*\.setup\.ts/ },
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        storageState: 'playwright/.auth/user.json',
      },
      dependencies: ['setup'],
    },
  ],
})
```

### Pattern 2: Page Object Model
**What:** Encapsulate page interactions into reusable classes with locators and methods.
**When to use:** For every page that has more than one test accessing it.
**Example:**
```typescript
// Source: https://playwright.dev/docs/pom
// tests/e2e/pages/audit.page.ts
import { type Locator, type Page, expect } from '@playwright/test'

export class AuditPage {
  readonly page: Page
  readonly heading: Locator
  readonly urlInput: Locator
  readonly startButton: Locator
  readonly progressIndicator: Locator
  readonly visibilityScore: Locator
  readonly optimizationScore: Locator

  constructor(page: Page) {
    this.page = page
    this.heading = page.getByRole('heading', { name: 'AI Brand Visibility Audit' })
    this.urlInput = page.locator('input[type="url"]')
    this.startButton = page.getByRole('button', { name: 'Start AI Audit' })
    this.progressIndicator = page.locator('text=Audit in Progress')
    this.visibilityScore = page.locator('text=Visibility Score')
    this.optimizationScore = page.locator('text=Optimization Score')
  }

  async goto() {
    await this.page.goto('/audit')
  }

  async startAudit(url: string) {
    await this.urlInput.fill(url)
    await this.startButton.click()
  }

  async expectProgressVisible() {
    await expect(this.progressIndicator).toBeVisible({ timeout: 10000 })
  }
}
```

### Pattern 3: Centralized Mock Data with Route Interception
**What:** Extract mock data into shared fixtures and apply route mocking consistently.
**When to use:** For all tests that need deterministic data without relying on the full backend pipeline.
**Example:**
```typescript
// Source: https://playwright.dev/docs/mock
// tests/e2e/fixtures/mock-data.ts
export const MOCK_AUDIT_ID = '11111111-1111-1111-1111-111111111111'

export const MOCK_AUDIT_LIST = [
  {
    id: MOCK_AUDIT_ID,
    domain: 'stripe.com',
    url: 'https://stripe.com',
    status: 'completed',
    created_at: '2026-02-20T10:00:00Z',
    completed_at: '2026-02-20T10:04:00Z',
  },
]

// ... more mock data

// tests/e2e/fixtures/test-helpers.ts
import type { Page, Route } from '@playwright/test'
import { MOCK_AUDIT_LIST, MOCK_OVERVIEW, MOCK_HISTORY } from './mock-data'

export async function setupDashboardMocks(page: Page) {
  await page.route('**/api/v1/audit', async (route: Route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({ json: MOCK_AUDIT_LIST })
    } else {
      await route.continue()
    }
  })
  // ... more mocks
}
```

### Pattern 4: Auth Setup Project
**What:** Authenticate once per worker and reuse the state via storageState.
**When to use:** As a project dependency for all non-login tests.
**Example:**
```typescript
// tests/e2e/fixtures/auth.setup.ts
import { test as setup, expect } from '@playwright/test'

const authFile = 'playwright/.auth/user.json'

setup('authenticate', async ({ page }) => {
  const email = `e2e-${Date.now()}@test.com`
  const password = 'MyPassword123@'

  // Register via API (faster than UI)
  const response = await page.request.post('http://localhost:8000/api/v1/auth/register', {
    data: { email, password },
  })
  expect(response.ok()).toBeTruthy()
  const { access_token } = await response.json()

  // Set cookie in the browser context
  await page.context().addCookies([{
    name: 'access_token',
    value: access_token,
    domain: 'localhost',
    path: '/',
  }])

  // Verify by visiting a protected page
  await page.goto('http://localhost:3000/audit')
  await expect(page.getByRole('heading', { name: 'AI Brand Visibility Audit' })).toBeVisible()

  // Save storage state
  await page.context().storageState({ path: authFile })
})
```

### Anti-Patterns to Avoid
- **Re-authenticating in every test:** Use storageState to share auth across tests. The existing tests register a new user per test, which is slow and creates DB pollution.
- **Hardcoded waits (waitForTimeout):** The existing dashboard-phase9.spec.ts uses `waitForTimeout(2000-3000)` extensively. Use `waitForSelector`, `waitForResponse`, or Playwright's auto-waiting instead. `waitForTimeout` is flaky and slow.
- **Overly broad route matchers:** `**/api/v1/**` can mask unexpected API calls. Match specific endpoints.
- **Duplicate mock data across test files:** The existing tests define mock data inline. Centralize in fixtures.
- **Testing CSS classes for assertions:** `page.locator('.bg-green-500.h-2\\.5')` (from existing tests) is fragile. Prefer `getByRole`, `getByText`, or `data-testid` attributes.
- **Missing error scenario tests:** Current tests only cover happy paths. Include network errors, auth failures, empty states, and timeout handling.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Browser automation | Custom Puppeteer/Selenium wrappers | @playwright/test built-in | Auto-waiting, assertions, fixtures, parallelism all built in |
| Authentication sharing | Custom cookie-setting helpers | storageState + project dependencies | Official pattern, handles cookies + localStorage + session storage |
| API mocking | Custom fetch interceptors | page.route() / routeFromHAR | Built into Playwright, handles all HTTP methods, supports response modification |
| Test reporting | Custom HTML reporters | playwright-report (built-in HTML) | Generates rich HTML reports with traces, screenshots, and video |
| Waiting for elements | Custom polling/retry logic | Playwright auto-waiting + expect assertions | Auto-retrying assertions with configurable timeouts |
| CI browser setup | Manual Chrome/Firefox installs | `npx playwright install --with-deps` | Installs exact browser versions Playwright was tested against |

**Key insight:** Playwright 1.58 includes everything needed for robust E2E testing out of the box. No additional testing libraries, assertion frameworks, or utilities are required.

## Common Pitfalls

### Pitfall 1: Flaky Tests from Hardcoded Waits
**What goes wrong:** Tests pass locally but fail in CI, or fail intermittently, because `waitForTimeout(2000)` is not enough time on slow machines.
**Why it happens:** The existing tests use `page.waitForTimeout()` extensively (8 occurrences across 2 files). Network speed and render timing vary between environments.
**How to avoid:** Replace `waitForTimeout` with event-based waits: `page.waitForResponse()` for API calls, `expect(locator).toBeVisible()` for UI elements (auto-retries), `page.waitForLoadState('networkidle')` for navigation.
**Warning signs:** Tests that pass with `timeout: 60000` but fail with default timeout. Tests that need repeated retries.

### Pitfall 2: Test Isolation Failure
**What goes wrong:** Test A creates data that test B depends on (or conflicts with). Reordering tests breaks the suite.
**Why it happens:** Tests share state via the database or browser context without explicit cleanup.
**How to avoid:** Each test should set up its own mocks via `page.route()`. For tests against a real backend, use unique identifiers (email with timestamp) and treat each test as independent. Use `test.describe.configure({ mode: 'serial' })` only when tests genuinely depend on each other.
**Warning signs:** Tests pass individually but fail when run together. Tests fail when run in a different order.

### Pitfall 3: Auth Cookie Domain Mismatch
**What goes wrong:** storageState saved with one domain does not work when the app runs on a different domain/port.
**Why it happens:** Cookies are domain-scoped. If auth.setup.ts sets cookies for `localhost` but the test accesses `127.0.0.1`, cookies will not be sent.
**How to avoid:** Always use consistent URLs. Configure `baseURL` in playwright.config.ts and use relative paths in tests (`page.goto('/audit')` not `page.goto('http://localhost:3000/audit')`).
**Warning signs:** Tests pass with explicit URLs but fail with relative URLs, or vice versa.

### Pitfall 4: Missing API Mocks Lead to Flaky Network Calls
**What goes wrong:** A test expects mocked data but some API calls fall through to the real backend, causing unpredictable results.
**Why it happens:** Route mocking is set up for some endpoints but not all. The app may make requests the test did not anticipate (e.g., `/auth/me` on page load).
**How to avoid:** Mock ALL API calls in mock-based tests. Use a helper function that intercepts the common endpoints (auth/me, audit list) and add test-specific mocks on top. Consider `page.route('**/api/**', route => route.abort())` as a catch-all to detect unmocked calls.
**Warning signs:** Tests that work with route mocking sometimes make real API calls (visible in Playwright trace).

### Pitfall 5: webServer Startup Race Conditions
**What goes wrong:** Tests start before the backend or frontend is fully ready, causing connection refused errors.
**Why it happens:** The webServer `url` check passes (HTTP 200) but the server is not fully initialized (e.g., database migrations not complete, Nuxt hydration not done).
**How to avoid:** Use the `wait` option (new in Playwright 1.58) to match specific stdout patterns, or set generous `timeout` values. For the backend, use the `/health` endpoint. For Nuxt, wait for the dev server URL to respond. Set `reuseExistingServer: !process.env.CI` so local development is fast.
**Warning signs:** Tests fail with "Connection refused" or "Navigation timeout" on first run but pass on retry.

### Pitfall 6: Celery/Async Pipeline Cannot Be E2E Tested Without Full Stack
**What goes wrong:** Audit lifecycle tests require Celery, Redis, and PostgreSQL all running, which is complex to set up in CI.
**Why it happens:** The audit pipeline is asynchronous: POST /audit triggers a Celery task that crawls, generates queries, dispatches to AI engines, and scores.
**How to avoid:** Two strategies: (1) Mock the entire API for UI-only tests (already proven in dashboard-phase9.spec.ts). (2) For true E2E tests, use docker-compose to run the full stack and test the real pipeline (slower, but validates the integration). Keep these in separate test projects/tags.
**Warning signs:** Audit lifecycle tests hang waiting for status changes that never come because Celery is not running.

## Code Examples

Verified patterns from official sources:

### Enhanced Playwright Config with webServer and Auth
```typescript
// Source: https://playwright.dev/docs/test-webserver + https://playwright.dev/docs/auth
// playwright.config.ts
import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [
    ['html', { open: process.env.CI ? 'never' : 'on-failure' }],
    ...(process.env.CI ? [['github' as const]] : []),
  ],
  use: {
    baseURL: 'http://localhost:3000',
    headless: true,
    screenshot: 'only-on-failure',
    trace: 'on-first-retry',
    actionTimeout: 10000,
  },
  webServer: [
    {
      command: 'cd ../backend && uvicorn app.main:app --host 0.0.0.0 --port 8000',
      url: 'http://localhost:8000/health',
      name: 'Backend',
      timeout: 120000,
      reuseExistingServer: !process.env.CI,
    },
    {
      command: 'npm run dev -- --port 3000',
      url: 'http://localhost:3000',
      name: 'Frontend',
      timeout: 120000,
      reuseExistingServer: !process.env.CI,
    },
  ],
  projects: [
    {
      name: 'setup',
      testMatch: /.*\.setup\.ts/,
    },
    {
      name: 'e2e-mocked',
      testMatch: /.*\.spec\.ts/,
      testIgnore: /.*\.live\.spec\.ts/,
      use: {
        ...devices['Desktop Chrome'],
        storageState: 'playwright/.auth/user.json',
      },
      dependencies: ['setup'],
    },
  ],
})
```

### Page Object Model for LoginPage
```typescript
// Source: https://playwright.dev/docs/pom
// tests/e2e/pages/login.page.ts
import { type Locator, type Page, expect } from '@playwright/test'

export class LoginPage {
  readonly page: Page
  readonly heading: Locator
  readonly emailInput: Locator
  readonly passwordInput: Locator
  readonly signInButton: Locator
  readonly createAccountButton: Locator
  readonly toggleModeButton: Locator
  readonly errorMessage: Locator

  constructor(page: Page) {
    this.page = page
    this.heading = page.locator('h1', { hasText: 'GEO Platform' })
    this.emailInput = page.locator('input[type="email"]')
    this.passwordInput = page.locator('input[type="password"]')
    this.signInButton = page.getByRole('button', { name: 'Sign In' })
    this.createAccountButton = page.getByRole('button', { name: 'Create Account' })
    this.toggleModeButton = page.locator('text=Don\'t have an account? Sign up')
    this.errorMessage = page.locator('.text-red-700')
  }

  async goto() {
    await this.page.goto('/login')
  }

  async login(email: string, password: string) {
    await this.emailInput.fill(email)
    await this.passwordInput.fill(password)
    await this.signInButton.click()
  }

  async switchToRegister() {
    await this.toggleModeButton.click()
  }

  async register(email: string, password: string) {
    await this.switchToRegister()
    await this.emailInput.fill(email)
    await this.passwordInput.fill(password)
    await this.createAccountButton.click()
  }

  async expectRedirectToAudit() {
    await expect(this.page).toHaveURL(/\/audit/, { timeout: 10000 })
  }
}
```

### Route Mocking with Centralized Data
```typescript
// Source: https://playwright.dev/docs/mock
// tests/e2e/fixtures/test-helpers.ts
import type { Page, Route } from '@playwright/test'
import * as mockData from './mock-data'

export async function setupAuthMock(page: Page) {
  await page.route('**/api/v1/auth/me', async (route: Route) => {
    await route.fulfill({
      json: { id: 'user-123', email: 'test@test.com', full_name: null, role: 'user' },
    })
  })
}

export async function setupAuditListMock(page: Page, audits = mockData.MOCK_AUDIT_LIST) {
  await page.route('**/api/v1/audit', async (route: Route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({ json: audits })
    } else {
      await route.continue()
    }
  })
}

export async function setupDashboardMocks(page: Page) {
  await setupAuthMock(page)
  await setupAuditListMock(page)

  await page.route(`**/api/v1/dashboard/overview/${mockData.MOCK_AUDIT_ID}`, async (route: Route) => {
    await route.fulfill({ json: mockData.MOCK_OVERVIEW })
  })

  await page.route('**/api/v1/dashboard/history**', async (route: Route) => {
    await route.fulfill({ json: mockData.MOCK_HISTORY })
  })
}
```

### Replacing waitForTimeout with Proper Waits
```typescript
// BAD (existing pattern in dashboard-phase9.spec.ts)
await page.goto(`${BASE_URL}/dashboard`)
await page.waitForLoadState('networkidle')
await page.waitForTimeout(2000)  // Flaky!
await expect(page.locator('text=Combined GEO Score')).toBeVisible()

// GOOD (event-based waiting)
await page.goto('/dashboard')
await page.waitForResponse('**/api/v1/dashboard/overview/**')
await expect(page.locator('text=Combined GEO Score')).toBeVisible({ timeout: 10000 })
```

## Test Coverage Matrix

### Pages Requiring E2E Tests

| Page | Route | Auth Required | Existing Tests | Priority | Test Strategy |
|------|-------|---------------|---------------|----------|---------------|
| Login | /login | No | 3 tests (auth-and-audit.spec.ts) | HIGH | Real backend (auth flow) |
| Audit | /audit | Yes | 1 test (auth-and-audit.spec.ts) | HIGH | Mocked (complex pipeline) |
| Dashboard | /dashboard | Yes | 10 tests (dashboard-phase9.spec.ts) | HIGH | Mocked (already done) |
| Recommendations | /recommendations | Yes | 0 tests | HIGH | Mocked (tabs, filters, status) |
| Competitors | /competitors | Yes | 0 tests | MEDIUM | Mocked (leaderboard, comparison) |
| Brands | /brands | Yes | 0 tests | MEDIUM | Mocked (CRUD, comparison) |
| Settings | /settings | Yes | 0 tests | LOW | Mocked (if features exist) |
| Index | / | No | 0 tests | LOW | Navigation only |

### Critical User Journeys to Test

| Journey | Pages Involved | What to Verify |
|---------|---------------|----------------|
| Auth flow | login -> audit | Register, login, redirect, auth guard |
| Audit lifecycle | audit | Start audit, see progress, see results |
| Results exploration | audit -> recommendations, audit -> competitors | Drill-down navigation, data display |
| Dashboard overview | dashboard | Score cards, charts, exports, history |
| Recommendation workflow | recommendations | Tabs, filters, status updates, export |
| Competitor analysis | competitors | Leaderboard, comparison, crawl trigger |
| Multi-brand management | brands | Create, edit, delete, comparison chart |
| Cross-page navigation | all | Sidebar nav, auth guards, deep linking |

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| globalSetup file for auth | Project dependencies (setup project) | Playwright 1.31+ | Better integration with HTML report, traces, fixtures |
| Chromium-based headless | Chrome for Testing builds | Playwright 1.57+ | More accurate browser behavior, same headed/headless |
| Manual browser install | `npx playwright install --with-deps` | Stable since 1.20+ | Exact pinned versions, system deps included |
| waitForTimeout hacks | Auto-waiting + expect retries | Stable since 1.0 | Eliminates flakiness from timing |
| Custom test CLI wrappers | Playwright Agents (LLM-guided test generation) | Playwright 1.58 | AI-assisted test plan -> test file -> self-healing |
| Separate webServer scripts | webServer `wait` field with regex | Playwright 1.58 | Can wait for specific stdout before starting tests |

**Deprecated/outdated:**
- `globalSetup` for auth: Still works but project dependencies are preferred (better reporting, trace support)
- `page.waitForTimeout()`: Not deprecated but considered an anti-pattern. Auto-waiting is always better.
- `networkidle` waitUntil: Still works but can be unreliable. Prefer waiting for specific responses.

## Open Questions

1. **Docker Compose for CI E2E Tests**
   - What we know: The project has a `docker-compose.yml` with all services. Playwright has official Docker images (`mcr.microsoft.com/playwright:v1.58.0-noble`).
   - What's unclear: Whether to use docker-compose for the full stack in CI or just the webServer approach (backend + frontend started by Playwright). Docker-compose gives true integration testing but is slower and requires more CI resources.
   - Recommendation: Start with webServer approach for UI tests (mocked APIs). Add docker-compose-based integration tests as a separate CI job if needed later. This keeps the test suite fast (< 2 min) while allowing real integration tests when desired.

2. **Test Database Management**
   - What we know: Auth tests currently register real users via the API. The backend uses PostgreSQL with Alembic migrations.
   - What's unclear: How to handle test database cleanup between runs. Whether to use a separate test database.
   - Recommendation: For mocked tests (majority), no DB needed. For auth setup, use timestamp-based unique emails to avoid conflicts. For future live tests, configure a `TEST_DATABASE_URL` env var and run migrations before tests.

3. **Celery Worker in Tests**
   - What we know: The audit pipeline requires Celery for async processing. Without Celery, POST /audit creates the record but nothing happens.
   - What's unclear: Whether to test the full async pipeline E2E or rely on mocked data.
   - Recommendation: Mock the pipeline for UI tests (faster, deterministic). Document how to run full-stack E2E tests with docker-compose for manual validation before releases.

4. **Visual Regression Testing**
   - What we know: Playwright supports screenshot comparison via `expect(page).toHaveScreenshot()`. The platform uses Tailwind CSS with custom design tokens.
   - What's unclear: Whether visual regression testing is worth the maintenance cost for this project size.
   - Recommendation: Defer visual regression testing to a future phase. Focus on functional correctness first. If needed, add screenshot baselines for the dashboard and audit results pages.

## Sources

### Primary (HIGH confidence)
- [Playwright Official Docs - Authentication](https://playwright.dev/docs/auth) - storageState, project dependencies, setup project pattern
- [Playwright Official Docs - Mock APIs](https://playwright.dev/docs/mock) - page.route(), route.fulfill(), HAR recording
- [Playwright Official Docs - Page Object Model](https://playwright.dev/docs/pom) - POM pattern with TypeScript
- [Playwright Official Docs - WebServer](https://playwright.dev/docs/test-webserver) - Multiple server configuration, wait patterns
- [Playwright Official Docs - Docker](https://playwright.dev/docs/docker) - Docker images, CI setup
- [Playwright Release Notes](https://playwright.dev/docs/release-notes) - v1.58 features (Agents, wait field, CLI mode)

### Secondary (MEDIUM confidence)
- [BrowserStack - Playwright Best Practices 2026](https://www.browserstack.com/guide/playwright-best-practices) - 15 best practices compilation
- [BrowserStack - How to Mock APIs with Playwright 2026](https://www.browserstack.com/guide/how-to-mock-api-with-playwright) - Mocking patterns guide
- [DeepWiki - Nuxt Test Utils Playwright Integration](https://deepwiki.com/nuxt/test-utils/6.2-playwright-integration) - Nuxt-specific Playwright patterns
- [Nuxt Testing Docs](https://nuxt.com/docs/3.x/getting-started/testing) - Nuxt 3 testing framework overview

### Tertiary (LOW confidence)
- [GitHub story2Dev/playwright-nuxt3-e2e](https://github.com/story2Dev/playwright-nuxt3-e2e) - Community example repo (not verified for quality)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Playwright 1.58.2 is already installed and partially configured. No new dependencies needed.
- Architecture: HIGH - POM pattern, project dependencies, and route mocking are well-documented Playwright patterns with official examples. The existing codebase already demonstrates route mocking.
- Pitfalls: HIGH - Identified from existing code patterns (waitForTimeout, inline mock data, per-test auth) and official documentation warnings.

**Research date:** 2026-02-23
**Valid until:** 2026-03-23 (Playwright has monthly releases but patterns are stable)
