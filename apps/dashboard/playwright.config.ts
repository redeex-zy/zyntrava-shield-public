import { defineConfig } from '@playwright/test';
export default defineConfig({ testDir: './e2e', testMatch: 'console.spec.ts', timeout: 180000, workers: 1,
  globalSetup: './e2e/setup.ts', reporter: [['list'], ['json', { outputFile: '../../artifacts/browser-results.json' }]],
  use: { actionTimeout: 10000, baseURL: 'http://127.0.0.1:8876', viewport: { width: 1440, height: 1100 }, trace: 'off', video: 'off', screenshot: 'only-on-failure' } });
