import { test } from '@playwright/test';
import * as path from 'path';

const REPORT_DIR = '/Users/eduardo/Documents/youtube/orquestrator-agent/.worktrees/card-ddeb49a0/test-reports/playwright/2026-01-14_08-39-14';

test('Investigate dropdown visibility', async ({ page }) => {
  // Navigate to dashboard
  await page.goto('http://localhost:5173');
  await page.waitForLoadState('networkidle');

  // Click AI Assistant button
  const chatButton = page.locator('button:has-text("AI Assistant")').first();
  await chatButton.click();
  await page.waitForTimeout(1500);

  // Click model selector to open dropdown
  const modelSelector = page.locator('button:has-text("AI MODEL:")').first();
  await modelSelector.click();
  await page.waitForTimeout(1000);

  // Take screenshot of full page
  await page.screenshot({
    path: path.join(REPORT_DIR, 'investigate-dropdown-full.png'),
    fullPage: true
  });

  // Get the dropdown element
  const dropdown = page.locator('[role="listbox"], .dropdown, [class*="dropdown"]').first();

  // Check if dropdown exists
  const dropdownExists = await dropdown.count() > 0;
  console.log('Dropdown exists:', dropdownExists);

  if (dropdownExists) {
    // Take screenshot of just the dropdown
    await dropdown.screenshot({
      path: path.join(REPORT_DIR, 'investigate-dropdown-element.png')
    });

    // Get all model cards
    const modelCards = page.locator('[role="option"], button:has-text("Opus"), button:has-text("Sonnet"), button:has-text("Haiku"), button:has-text("Gemini")');
    const count = await modelCards.count();
    console.log('Number of model options found:', count);

    // Print text of each model card
    for (let i = 0; i < count; i++) {
      const text = await modelCards.nth(i).textContent();
      console.log(`Model ${i + 1}:`, text);
    }

    // Try scrolling within the dropdown
    await dropdown.evaluate(el => {
      el.scrollTop = el.scrollHeight;
    }).catch(() => console.log('Could not scroll dropdown'));

    await page.waitForTimeout(500);

    await page.screenshot({
      path: path.join(REPORT_DIR, 'investigate-dropdown-scrolled.png'),
      fullPage: true
    });

    // Get HTML of dropdown for inspection
    const dropdownHTML = await dropdown.innerHTML();
    console.log('Dropdown HTML:', dropdownHTML.substring(0, 500));
  }

  // Get full page HTML and search for model names
  const pageContent = await page.content();
  console.log('Page contains "Opus 4.5":', pageContent.includes('Opus 4.5'));
  console.log('Page contains "Haiku 4.5":', pageContent.includes('Haiku 4.5'));
  console.log('Page contains "Sonnet 4.5":', pageContent.includes('Sonnet 4.5'));
  console.log('Page contains "Gemini 3 Pro":', pageContent.includes('Gemini 3 Pro'));
  console.log('Page contains "Gemini 3 Flash":', pageContent.includes('Gemini 3 Flash'));
});
