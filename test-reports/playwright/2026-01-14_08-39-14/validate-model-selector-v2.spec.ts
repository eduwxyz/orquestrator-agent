import { test, expect } from '@playwright/test';
import * as path from 'path';

const REPORT_DIR = '/Users/eduardo/Documents/youtube/orquestrator-agent/.worktrees/card-ddeb49a0/test-reports/playwright/2026-01-14_08-39-14';

test.describe('Model Selector Validation', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the main page
    await page.goto('http://localhost:5173');
    await page.waitForLoadState('networkidle');

    // Take initial screenshot
    await page.screenshot({
      path: path.join(REPORT_DIR, '01-initial-dashboard.png'),
      fullPage: true
    });

    // Navigate to Chat page by clicking the sidebar button
    // Looking for "AI Assistant" button in the sidebar
    const chatButton = page.locator('button:has-text("AI Assistant")').first();

    const chatButtonExists = await chatButton.count() > 0;
    if (chatButtonExists) {
      console.log('✅ Found AI Assistant button, clicking...');
      await chatButton.click();
      await page.waitForTimeout(1500);
    } else {
      console.log('⚠️ Could not find AI Assistant button in sidebar');
      throw new Error('AI Assistant navigation button not found');
    }

    await page.screenshot({
      path: path.join(REPORT_DIR, '02-chat-page-loaded.png'),
      fullPage: true
    });
  });

  test('Complete Model Selector Validation - All Acceptance Criteria', async ({ page }) => {
    const results = {
      criterion1: { name: 'Model Selector displays 5 models', passed: false, details: [] },
      criterion2: { name: 'Model IDs verification', passed: false, details: [] },
      criterion3: { name: 'Default model is Sonnet 4.5', passed: false, details: [] },
      criterion4: { name: 'Model selection functionality', passed: false, details: [] },
      criterion5: { name: 'Send message test', passed: false, details: [] }
    };

    // ============================================================
    // CRITERION 1: Model Selector displays 5 models
    // ============================================================
    console.log('\n========== Testing Criterion 1: Model Selector displays 5 models ==========');

    try {
      // Find the model selector button - look for "AI MODEL:" label or model names
      const possibleSelectors = [
        'button:has-text("AI MODEL:")',
        'button:has-text("Sonnet")',
        'button:has-text("Opus")',
        '[aria-label="Select AI Model"]',
        'button:has-text("anthropic")',
        '.modelSelector button',
        '[class*="modelSelector"] button',
        '[class*="trigger"]'
      ];

      let modelSelector = null;
      for (const selector of possibleSelectors) {
        const element = page.locator(selector).first();
        if (await element.count() > 0) {
          modelSelector = element;
          console.log(`✅ Found model selector using: ${selector}`);
          break;
        }
      }

      if (!modelSelector) {
        throw new Error('Could not find model selector button');
      }

      // Take screenshot of the selector button
      await modelSelector.screenshot({
        path: path.join(REPORT_DIR, '03-model-selector-button.png')
      });

      // Click to open dropdown
      await modelSelector.click();
      await page.waitForTimeout(1000);

      // Take screenshot of opened dropdown
      await page.screenshot({
        path: path.join(REPORT_DIR, '04-dropdown-opened.png'),
        fullPage: true
      });

      // Check for the 5 expected models
      const expectedModels = [
        { name: 'Opus 4.5', provider: 'Claude' },
        { name: 'Sonnet 4.5', provider: 'Claude' },
        { name: 'Haiku 4.5', provider: 'Claude' },
        { name: 'Gemini 3 Pro', provider: 'Google' },
        { name: 'Gemini 3 Flash', provider: 'Google' }
      ];

      for (const model of expectedModels) {
        const modelElement = page.locator(`text="${model.name}"`).first();
        const isVisible = await modelElement.isVisible().catch(() => false);

        results.criterion1.details.push({
          model: model.name,
          visible: isVisible,
          provider: model.provider
        });

        if (isVisible) {
          console.log(`✅ ${model.name} (${model.provider}) is visible`);
        } else {
          console.log(`❌ ${model.name} (${model.provider}) is NOT visible`);
        }
      }

      const allVisible = results.criterion1.details.every(d => d.visible);
      results.criterion1.passed = allVisible;

      if (allVisible) {
        console.log('✅ CRITERION 1 PASSED: All 5 models are visible');
      } else {
        console.log('❌ CRITERION 1 FAILED: Not all models are visible');
      }

      // Close dropdown for next test
      await page.keyboard.press('Escape');
      await page.waitForTimeout(500);

    } catch (error) {
      console.log(`❌ CRITERION 1 FAILED: ${error.message}`);
      results.criterion1.details.push({ error: error.message });
    }

    // ============================================================
    // CRITERION 2: Model IDs verification
    // ============================================================
    console.log('\n========== Testing Criterion 2: Model IDs verification ==========');

    try {
      // Open dropdown again
      const modelSelector = page.locator('button:has-text("AI MODEL:"), button:has-text("Sonnet"), button:has-text("Opus")').first();
      await modelSelector.click();
      await page.waitForTimeout(1000);

      const expectedModelIds = [
        { id: 'opus-4.5', label: 'Opus 4.5' },
        { id: 'sonnet-4.5', label: 'Sonnet 4.5' },
        { id: 'haiku-4.5', label: 'Haiku 4.5' },
        { id: 'gemini-3-pro', label: 'Gemini 3 Pro' },
        { id: 'gemini-3-flash', label: 'Gemini 3 Flash' }
      ];

      // Check the page content for model IDs
      const pageContent = await page.content();

      for (const expected of expectedModelIds) {
        const hasId = pageContent.includes(expected.id);
        const hasLabel = pageContent.includes(expected.label);

        results.criterion2.details.push({
          id: expected.id,
          label: expected.label,
          idFound: hasId,
          labelFound: hasLabel
        });

        if (hasId && hasLabel) {
          console.log(`✅ Model ID "${expected.id}" with label "${expected.label}" found`);
        } else {
          console.log(`❌ Model ID "${expected.id}" or label "${expected.label}" not found`);
        }
      }

      await page.screenshot({
        path: path.join(REPORT_DIR, '05-model-ids-check.png'),
        fullPage: true
      });

      const allIdsFound = results.criterion2.details.every(d => d.idFound && d.labelFound);
      results.criterion2.passed = allIdsFound;

      if (allIdsFound) {
        console.log('✅ CRITERION 2 PASSED: All model IDs are correct');
      } else {
        console.log('❌ CRITERION 2 FAILED: Some model IDs are incorrect');
      }

      // Close dropdown
      await page.keyboard.press('Escape');
      await page.waitForTimeout(500);

    } catch (error) {
      console.log(`❌ CRITERION 2 FAILED: ${error.message}`);
      results.criterion2.details.push({ error: error.message });
    }

    // ============================================================
    // CRITERION 3: Default model is Sonnet 4.5
    // ============================================================
    console.log('\n========== Testing Criterion 3: Default model is Sonnet 4.5 ==========');

    try {
      const modelSelector = page.locator('button:has-text("AI MODEL:"), button:has-text("Sonnet"), button:has-text("Opus")').first();
      const buttonText = await modelSelector.textContent();

      console.log(`Default model button text: "${buttonText}"`);

      const hasSonnet = buttonText?.includes('Sonnet 4.5') || buttonText?.includes('sonnet-4.5');
      results.criterion3.passed = hasSonnet;
      results.criterion3.details.push({ buttonText, hasSonnet });

      await page.screenshot({
        path: path.join(REPORT_DIR, '06-default-model.png'),
        fullPage: true
      });

      if (hasSonnet) {
        console.log('✅ CRITERION 3 PASSED: Default model is Sonnet 4.5');
      } else {
        console.log('❌ CRITERION 3 FAILED: Default model is not Sonnet 4.5');
      }

    } catch (error) {
      console.log(`❌ CRITERION 3 FAILED: ${error.message}`);
      results.criterion3.details.push({ error: error.message });
    }

    // ============================================================
    // CRITERION 4: Model selection functionality
    // ============================================================
    console.log('\n========== Testing Criterion 4: Model selection functionality ==========');

    try {
      const models = ['Opus 4.5', 'Haiku 4.5', 'Gemini 3 Pro', 'Gemini 3 Flash', 'Sonnet 4.5'];

      for (let i = 0; i < models.length; i++) {
        const modelName = models[i];
        console.log(`\nTesting selection of: ${modelName}`);

        // Open dropdown
        const modelSelector = page.locator('button:has-text("AI MODEL:"), button:has-text("Sonnet"), button:has-text("Opus")').first();
        await modelSelector.click();
        await page.waitForTimeout(500);

        // Click the model option
        const modelOption = page.locator(`button:has-text("${modelName}"), [role="option"]:has-text("${modelName}")`).first();
        const optionExists = await modelOption.count() > 0;

        if (!optionExists) {
          console.log(`❌ Model option "${modelName}" not found`);
          results.criterion4.details.push({ model: modelName, selected: false, reason: 'Option not found' });
          continue;
        }

        await modelOption.click();
        await page.waitForTimeout(500);

        // Take screenshot of selected model
        await page.screenshot({
          path: path.join(REPORT_DIR, `07-${i + 1}-selected-${modelName.toLowerCase().replace(/\s+/g, '-')}.png`),
          fullPage: true
        });

        // Verify the button shows the selected model
        const buttonText = await modelSelector.textContent();
        const isSelected = buttonText?.includes(modelName);

        results.criterion4.details.push({
          model: modelName,
          selected: isSelected,
          buttonText: buttonText
        });

        if (isSelected) {
          console.log(`✅ ${modelName} selected successfully`);
        } else {
          console.log(`❌ ${modelName} NOT selected (button shows: ${buttonText})`);
        }

        await page.waitForTimeout(300);
      }

      const allSelected = results.criterion4.details.every(d => d.selected);
      results.criterion4.passed = allSelected;

      if (allSelected) {
        console.log('✅ CRITERION 4 PASSED: All models can be selected');
      } else {
        console.log('❌ CRITERION 4 FAILED: Some models could not be selected');
      }

    } catch (error) {
      console.log(`❌ CRITERION 4 FAILED: ${error.message}`);
      results.criterion4.details.push({ error: error.message });
    }

    // ============================================================
    // CRITERION 5: Send message test with Sonnet 4.5
    // ============================================================
    console.log('\n========== Testing Criterion 5: Send message test with Sonnet 4.5 ==========');

    try {
      // Make sure Sonnet 4.5 is selected
      const modelSelector = page.locator('button:has-text("AI MODEL:"), button:has-text("Sonnet"), button:has-text("Opus")').first();
      const currentModel = await modelSelector.textContent();

      if (!currentModel?.includes('Sonnet 4.5')) {
        console.log('Selecting Sonnet 4.5...');
        await modelSelector.click();
        await page.waitForTimeout(500);
        const sonnetOption = page.locator('button:has-text("Sonnet 4.5"), [role="option"]:has-text("Sonnet 4.5")').first();
        await sonnetOption.click();
        await page.waitForTimeout(500);
      }

      await page.screenshot({
        path: path.join(REPORT_DIR, '08-before-message.png'),
        fullPage: true
      });

      // Find the message input field
      const possibleInputSelectors = [
        'textarea',
        'input[type="text"]',
        '[contenteditable="true"]',
        '[placeholder*="message"]',
        '[placeholder*="Message"]',
        '[placeholder*="type"]'
      ];

      let messageInput = null;
      for (const selector of possibleInputSelectors) {
        const element = page.locator(selector).first();
        if (await element.count() > 0 && await element.isVisible()) {
          messageInput = element;
          console.log(`✅ Found message input using: ${selector}`);
          break;
        }
      }

      if (!messageInput) {
        throw new Error('Could not find message input field');
      }

      // Type "Hello" message
      await messageInput.fill('Hello');
      await page.waitForTimeout(500);

      await page.screenshot({
        path: path.join(REPORT_DIR, '09-message-typed.png'),
        fullPage: true
      });

      // Find and click the send button
      const possibleSendButtons = [
        'button:has-text("Send")',
        'button:has-text("Enviar")',
        'button[type="submit"]',
        'button[aria-label*="send"]',
        'button[aria-label*="Send"]'
      ];

      let sendButton = null;
      for (const selector of possibleSendButtons) {
        const element = page.locator(selector).first();
        if (await element.count() > 0 && await element.isVisible()) {
          sendButton = element;
          console.log(`✅ Found send button using: ${selector}`);
          break;
        }
      }

      if (!sendButton) {
        // Try pressing Enter instead
        console.log('⚠️ Send button not found, trying Enter key');
        await messageInput.press('Enter');
      } else {
        await sendButton.click();
      }

      // Wait for response to start (don't wait for full completion)
      await page.waitForTimeout(3000);

      await page.screenshot({
        path: path.join(REPORT_DIR, '10-message-sent.png'),
        fullPage: true
      });

      // Verify message was sent (should appear in chat)
      const pageContent = await page.content();
      const messageAppeared = pageContent.includes('Hello');

      results.criterion5.passed = messageAppeared;
      results.criterion5.details.push({
        messageSent: messageAppeared,
        model: 'Sonnet 4.5'
      });

      if (messageAppeared) {
        console.log('✅ CRITERION 5 PASSED: Message sent successfully with Sonnet 4.5');
      } else {
        console.log('❌ CRITERION 5 FAILED: Message not sent or not visible');
      }

    } catch (error) {
      console.log(`❌ CRITERION 5 FAILED: ${error.message}`);
      results.criterion5.details.push({ error: error.message });
    }

    // ============================================================
    // SUMMARY
    // ============================================================
    console.log('\n========== VALIDATION SUMMARY ==========');
    console.log('Criterion 1 (5 models displayed):', results.criterion1.passed ? '✅ PASSED' : '❌ FAILED');
    console.log('Criterion 2 (Model IDs correct):', results.criterion2.passed ? '✅ PASSED' : '❌ FAILED');
    console.log('Criterion 3 (Default Sonnet 4.5):', results.criterion3.passed ? '✅ PASSED' : '❌ FAILED');
    console.log('Criterion 4 (Selection works):', results.criterion4.passed ? '✅ PASSED' : '❌ FAILED');
    console.log('Criterion 5 (Send message):', results.criterion5.passed ? '✅ PASSED' : '❌ FAILED');

    const allPassed = Object.values(results).every(r => r.passed);
    console.log('\n' + (allPassed ? '✅ ALL TESTS PASSED' : '❌ SOME TESTS FAILED'));

    // Write results to JSON file for report generation
    const fs = require('fs');
    fs.writeFileSync(
      path.join(REPORT_DIR, 'validation-results.json'),
      JSON.stringify(results, null, 2)
    );

    // Assert that all criteria passed
    expect(results.criterion1.passed, 'Criterion 1: All 5 models should be displayed').toBe(true);
    expect(results.criterion2.passed, 'Criterion 2: All model IDs should be correct').toBe(true);
    expect(results.criterion3.passed, 'Criterion 3: Default model should be Sonnet 4.5').toBe(true);
    expect(results.criterion4.passed, 'Criterion 4: All models should be selectable').toBe(true);
    expect(results.criterion5.passed, 'Criterion 5: Should be able to send message').toBe(true);
  });
});
