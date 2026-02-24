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
      command: 'cd ../backend && . venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000',
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
