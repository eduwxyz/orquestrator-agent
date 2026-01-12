import { test } from '@playwright/test';
import path from 'path';

const REPORT_DIR = __dirname;
const FRONTEND_URL = 'http://localhost:5173';

test('Inspect Model Selector Dropdown', async ({ page }) => {
  test.setTimeout(60000);

  await page.goto(FRONTEND_URL);
  await page.waitForLoadState('networkidle');

  // Open chat
  const chatButton = page.locator('button:has-text("Abrir Chat AI"), a:has-text("Abrir Chat AI")').first();
  await chatButton.click();
  await page.waitForTimeout(2000);

  // Click on the dropdown arrow next to the model selector
  const dropdown = page.locator('button:has-text("ANTHROPIC") ~ button, [class*="dropdown"], button[aria-label*="model"]').first();

  // Try clicking the entire model selector area
  const modelArea = page.locator('text=AI MODEL:').locator('xpath=..').first();
  await modelArea.screenshot({ path: path.join(REPORT_DIR, 'model-selector-area.png') });

  // Click the dropdown
  const dropdownBtn = page.locator('button', { has: page.locator('text=Sonnet 4.5') }).locator('..').locator('button').last();
  await dropdownBtn.click();
  await page.waitForTimeout(1500);
  await page.screenshot({ path: path.join(REPORT_DIR, 'dropdown-opened-detailed.png'), fullPage: true });

  // Get all visible text
  const allText = await page.locator('body').innerText();
  console.log('\n=== ALL VISIBLE TEXT ===');
  console.log(allText);
  console.log('\n=== MODEL ANALYSIS ===');

  // Search for specific model names
  const models = {
    'Opus 4.5': allText.includes('Opus 4.5'),
    'Sonnet 4.5': allText.includes('Sonnet 4.5'),
    'Sonnet 3.5': allText.includes('Sonnet 3.5'),
    'Haiku': allText.includes('Haiku'),
    'Gemini': allText.includes('Gemini'),
    'GPT-4': allText.includes('GPT-4'),
    'GPT-3.5': allText.includes('GPT-3.5'),
    'GPT-4o': allText.includes('GPT-4o'),
    'o1': allText.includes(' o1'),
  };

  console.log('\nModel presence check:');
  for (const [model, present] of Object.entries(models)) {
    console.log(`  ${model}: ${present ? 'FOUND' : 'NOT FOUND'}`);
  }

  // Take screenshot of dropdown
  await page.screenshot({ path: path.join(REPORT_DIR, 'final-dropdown-view.png'), fullPage: true });
});
