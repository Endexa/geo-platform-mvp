import { defineConfig, devices } from '@playwright/test'

const isCI = !!process.env.CI

// In CI, only start the frontend — all API calls are mocked via Playwright route interception.
// Locally, also start the backend for convenience (reuses existing if already running).
const webServers = isCI
  ? [
      {
        command: 'npm run dev -- --port 3000',
        url: 'http://localhost:3000',
        name: 'Frontend',
        timeout: 120000,
        reuseExistingServer: false,
      },
    ]
  : [
      {
        command: 'cd ../backend && . venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000',
        url: 'http://localhost:8000/health',
        name: 'Backend',
        timeout: 120000,
        reuseExistingServer: true,
      },
      {
        command: 'npm run dev -- --port 3000',
        url: 'http://localhost:3000',
        name: 'Frontend',
        timeout: 120000,
        reuseExistingServer: true,
      },
    ]

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: true,
  forbidOnly: isCI,
  retries: isCI ? 2 : 0,
  workers: isCI ? 1 : undefined,
  reporter: [
    ['html', { open: isCI ? 'never' : 'on-failure' }],
    ...(isCI ? [['github' as const]] : []),
  ],
  use: {
    baseURL: 'http://localhost:3000',
    headless: true,
    screenshot: 'only-on-failure',
    trace: 'on-first-retry',
    actionTimeout: 10000,
  },
  webServer: webServers,
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
