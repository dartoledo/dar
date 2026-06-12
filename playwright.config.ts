import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './',
  testMatch: 'synthetic-traffic.spec.ts',
  timeout: 0, // Disable timeout for continuous running
  workers: 1, // Only need 1 worker to generate a steady stream of traffic
  use: {
    headless: true,
  },
});
