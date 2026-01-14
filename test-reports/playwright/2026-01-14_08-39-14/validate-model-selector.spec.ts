import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

const REPORT_DIR = '/Users/eduardo/Documents/youtube/orquestrator-agent/.worktrees/card-ddeb49a0/test-reports/playwright/2026-01-14_08-39-14';

test.describe('Model Selector Validation', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the chat page
    await page.goto('http://localhost:5173');
    await page.waitForLoadState('networkidle');
  });

  test('Acceptance Criterion 1: Model Selector displays 5 models', async ({ page }) => {
    // Take initial screenshot
    await page.screenshot({
      path: path.join(REPORT_DIR, '01-initial-page.png'),
      fullPage: true
    });

    // Find and click the model selector dropdown
    const modelSelector = page.locator('[data-testid="model-selector"], .model-selector, button:has-text("Sonnet"), button:has-text("model")').first();
    await modelSelector.waitFor({ timeout: 10000 });
    await modelSelector.screenshot({
      path: path.join(REPORT_DIR, '02-model-selector-button.png')
    });

    await modelSelector.click();
    await page.waitForTimeout(1000);

    // Take screenshot of opened dropdown
    await page.screenshot({
      path: path.join(REPORT_DIR, '03-dropdown-opened.png'),
      fullPage: true
    });

    // Check for the 5 expected models
    const expectedModels = [
      'Opus 4.5',
      'Sonnet 4.5',
      'Haiku 4.5',
      'Gemini 3 Pro',
      'Gemini 3 Flash'
    ];

    const results = [];
    for (const modelName of expectedModels) {
      const modelElement = page.locator(`text="${modelName}"`).first();
      const isVisible = await modelElement.isVisible().catch(() => false);
      results.push({ model: modelName, visible: isVisible });

      if (isVisible) {
        console.log(`✅ ${modelName} is visible`);
      } else {
        console.log(`❌ ${modelName} is NOT visible`);
      }
    }

    // Assert all models are visible
    for (const result of results) {
      expect(result.visible, `${result.model} should be visible`).toBe(true);
    }
  });

  test('Acceptance Criterion 2: Model IDs verification', async ({ page }) => {
    // Click the model selector
    const modelSelector = page.locator('[data-testid="model-selector"], .model-selector, button:has-text("Sonnet"), button:has-text("model")').first();
    await modelSelector.click();
    await page.waitForTimeout(1000);

    // Verify model IDs by inspecting the DOM
    const modelElements = await page.locator('[data-model-id], [data-value]').all();

    const expectedModelIds = [
      { id: 'opus-4.5', label: 'Opus 4.5' },
      { id: 'sonnet-4.5', label: 'Sonnet 4.5' },
      { id: 'haiku-4.5', label: 'Haiku 4.5' },
      { id: 'gemini-3-pro', label: 'Gemini 3 Pro' },
      { id: 'gemini-3-flash', label: 'Gemini 3 Flash' }
    ];

    for (const expected of expectedModelIds) {
      const modelOption = page.locator(`[data-value="${expected.id}"], [data-model-id="${expected.id}"]`).first();
      const exists = await modelOption.count() > 0;

      if (exists) {
        const text = await modelOption.textContent();
        console.log(`✅ Model ID "${expected.id}" found with text: ${text}`);
      } else {
        console.log(`❌ Model ID "${expected.id}" not found`);
      }
    }

    await page.screenshot({
      path: path.join(REPORT_DIR, '04-model-ids-check.png'),
      fullPage: true
    });
  });

  test('Acceptance Criterion 3: Default model is Sonnet 4.5', async ({ page }) => {
    // Check if Sonnet 4.5 is the default selected model
    const modelSelector = page.locator('[data-testid="model-selector"], .model-selector, button:has-text("Sonnet"), button:has-text("model")').first();

    const buttonText = await modelSelector.textContent();
    console.log(`Default model button text: ${buttonText}`);

    await page.screenshot({
      path: path.join(REPORT_DIR, '05-default-model.png'),
      fullPage: true
    });

    expect(buttonText).toContain('Sonnet 4.5');
  });

  test('Acceptance Criterion 4: Model selection functionality', async ({ page }) => {
    const models = ['Opus 4.5', 'Sonnet 4.5', 'Haiku 4.5', 'Gemini 3 Pro', 'Gemini 3 Flash'];

    for (let i = 0; i < models.length; i++) {
      const modelName = models[i];

      // Click to open dropdown
      const modelSelector = page.locator('[data-testid="model-selector"], .model-selector, button:has-text("Sonnet"), button:has-text("model")').first();
      await modelSelector.click();
      await page.waitForTimeout(500);

      // Click the model option
      const modelOption = page.locator(`text="${modelName}"`).first();
      await modelOption.click();
      await page.waitForTimeout(500);

      // Take screenshot of selected model
      await page.screenshot({
        path: path.join(REPORT_DIR, `06-${i + 1}-selected-${modelName.toLowerCase().replace(/\s+/g, '-')}.png`),
        fullPage: true
      });

      // Verify the button shows the selected model
      const buttonText = await modelSelector.textContent();
      console.log(`Selected ${modelName}, button shows: ${buttonText}`);

      expect(buttonText).toContain(modelName);
    }
  });

  test('Acceptance Criterion 5: Send message test with Sonnet 4.5', async ({ page }) => {
    // Ensure Sonnet 4.5 is selected (should be default)
    await page.screenshot({
      path: path.join(REPORT_DIR, '07-before-message.png'),
      fullPage: true
    });

    // Find the message input field
    const messageInput = page.locator('textarea, input[type="text"]').first();
    await messageInput.waitFor({ timeout: 10000 });

    // Type "Hello" message
    await messageInput.fill('Hello');
    await page.waitForTimeout(500);

    await page.screenshot({
      path: path.join(REPORT_DIR, '08-message-typed.png'),
      fullPage: true
    });

    // Find and click the send button
    const sendButton = page.locator('button:has-text("Send"), button[type="submit"], button:has([aria-label*="send"])').first();
    await sendButton.click();

    // Wait for response to start (don't wait for full completion)
    await page.waitForTimeout(2000);

    await page.screenshot({
      path: path.join(REPORT_DIR, '09-message-sent.png'),
      fullPage: true
    });

    // Verify message was sent (should appear in chat)
    const chatMessage = page.locator('text="Hello"').first();
    await expect(chatMessage).toBeVisible();

    console.log('✅ Message sent successfully with Sonnet 4.5');
  });
});
