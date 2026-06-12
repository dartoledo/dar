import { test, expect } from '@playwright/test';

// We define a test that runs continuously in a loop to generate traffic.
test('Continuous synthetic traffic generator', async ({ page, request }) => {
  const baseUrl = 'http://localhost:8080';
  console.log(`Starting synthetic traffic generator against ${baseUrl}`);
  
  // We'll run a large number of iterations so it generates sustained metrics
  // over a long period. To run truly forever, use while(true)
  for (let i = 0; i < 5000; i++) {
    try {
      // 1. Successful Login Hit (200 & 302 Redirect)
      await page.goto(`${baseUrl}/login`);
      await page.fill('input[name="username"]', 'admin');
      await page.fill('input[name="password"]', 'password123');
      await page.click('button[type="submit"]');
      
      // Wait for dashboard and verify it loads
      await expect(page.locator('h2')).toContainText('Dashboard', { timeout: 5000 });
      await page.waitForTimeout(60000);
      
      // 2. Failed Login Hit (401 Unauthorized)
      await page.goto(`${baseUrl}/login`);
      await page.fill('input[name="username"]', 'admin');
      await page.fill('input[name="password"]', 'wrongpass');
      await page.click('button[type="submit"]');
      await expect(page.locator('p')).toContainText('Invalid username', { timeout: 5000 });
      await page.waitForTimeout(60000);
      
      // 3. 404 Hit (Not Found)
      await request.get(`${baseUrl}/non-existent-page-for-404-${i}`);
      await page.waitForTimeout(60000);
      
      // 4. Bad method (405 Method Not Allowed)
      // Sending a PUT to the login page which only expects GET/POST
      await request.put(`${baseUrl}/login`, { data: { dummy: 'data' } });
      await page.waitForTimeout(60000);

      // 5. Trigger 500 Internal Server Error (The injected bug)
      await page.goto(`${baseUrl}/login`);
      await page.fill('input[name="username"]', 'admin');
      await page.fill('input[name="password"]', '!admin');
      await page.click('button[type="submit"]');
      // Wait for the 500 response
      await expect(page.locator('body')).toContainText('Internal Server Error', { timeout: 5000 });
      
      // Final delay for this loop iteration
      await page.waitForTimeout(60000);
      
      if (i % 50 === 0) {
        console.log(`Completed ${i} traffic iterations.`);
      }
    } catch (e: any) {
      console.log('Iteration error (server might be down):', e.message);
      // Wait a bit longer if there's an error before retrying
      await page.waitForTimeout(2000);
    }
  }
});
