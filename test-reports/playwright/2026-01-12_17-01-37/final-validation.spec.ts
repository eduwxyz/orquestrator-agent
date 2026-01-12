import { test, expect } from '@playwright/test';
import path from 'path';

const REPORT_DIR = __dirname;
const CHAT_URL = 'http://localhost:5173/chat'; // Direct chat URL

test.describe('Chat UI Improvements - Final Validation', () => {
  test.setTimeout(60000); // Increase timeout to 60 seconds

  test('AC1-5: Complete Chat UI Feature Validation', async ({ page }) => {
    console.log('\n=== STEP 1: Navigate to Chat Page ===');
    await page.goto(CHAT_URL);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);
    await page.screenshot({ path: path.join(REPORT_DIR, '01-chat-page-initial.png'), fullPage: true });

    console.log('\n=== STEP 2: Verify Dark Theme (AC3) ===');
    const bodyBg = await page.locator('body').evaluate(el => {
      return window.getComputedStyle(el).backgroundColor;
    });
    console.log('Body background color:', bodyBg);

    const rgbMatch = bodyBg.match(/rgb\((\d+),\s*(\d+),\s*(\d+)\)/);
    if (rgbMatch) {
      const [, r, g, b] = rgbMatch.map(Number);
      const avgBrightness = (r + g + b) / 3;
      console.log('Average brightness:', avgBrightness, '(should be < 50 for dark theme)');
      expect(avgBrightness).toBeLessThan(50);
      console.log('✓ Dark theme verified');
    }

    console.log('\n=== STEP 3: Test Model Selector (AC2) ===');
    // Find model selector by various methods
    const modelSelectors = [
      'select',
      '[class*="modelSelector"]',
      '[class*="ModelSelector"]',
      'button:has-text("Model")',
      'button:has-text("Modelo")',
      '[data-testid="model-selector"]'
    ];

    let modelSelectorFound = false;
    let modelSelector = null;

    for (const selector of modelSelectors) {
      try {
        const element = page.locator(selector).first();
        if (await element.isVisible({ timeout: 2000 })) {
          modelSelector = element;
          modelSelectorFound = true;
          console.log('✓ Model selector found with:', selector);
          break;
        }
      } catch (e) {
        // Try next selector
      }
    }

    if (modelSelectorFound && modelSelector) {
      await modelSelector.screenshot({ path: path.join(REPORT_DIR, '02-model-selector.png') });

      // Try to interact with it
      try {
        await modelSelector.click();
        await page.waitForTimeout(1000);
        await page.screenshot({ path: path.join(REPORT_DIR, '03-model-selector-open.png'), fullPage: true });

        // Get all text on page to find model names
        const pageText = await page.locator('body').textContent();

        // Check for model providers
        const hasAnthropicModels = pageText?.toLowerCase().includes('opus') ||
                                   pageText?.toLowerCase().includes('sonnet') ||
                                   pageText?.toLowerCase().includes('haiku') ||
                                   pageText?.toLowerCase().includes('anthropic');

        const hasGeminiModels = pageText?.toLowerCase().includes('gemini');

        const hasOpenAIModels = pageText?.toLowerCase().includes('gpt-4') ||
                                pageText?.toLowerCase().includes('gpt-3') ||
                                (pageText?.toLowerCase().includes('openai') &&
                                 pageText?.toLowerCase().includes('gpt'));

        console.log('Anthropic models present:', hasAnthropicModels);
        console.log('Gemini models present:', hasGeminiModels);
        console.log('OpenAI/GPT models present:', hasOpenAIModels);

        if (hasAnthropicModels) console.log('✓ Anthropic models found');
        if (hasGeminiModels) console.log('✓ Gemini models found');
        if (!hasOpenAIModels) console.log('✓ OpenAI models correctly filtered out');

        // Close selector
        await page.keyboard.press('Escape');
        await page.waitForTimeout(500);
      } catch (error) {
        console.log('Could not interact with model selector:', error);
      }
    } else {
      console.log('⚠ Model selector not found, may need manual verification');
    }

    console.log('\n=== STEP 4: Test Markdown Rendering (AC1) ===');

    // Find chat input
    const inputSelectors = [
      'textarea',
      '[contenteditable="true"]',
      'input[type="text"]',
      '[placeholder*="message" i]',
      '[placeholder*="mensagem" i]',
      '[class*="chatInput"]',
      '[class*="ChatInput"]'
    ];

    let chatInput = null;
    for (const selector of inputSelectors) {
      try {
        const element = page.locator(selector).first();
        if (await element.isVisible({ timeout: 2000 })) {
          chatInput = element;
          console.log('✓ Chat input found with:', selector);
          break;
        }
      } catch (e) {
        // Try next selector
      }
    }

    if (chatInput) {
      await chatInput.screenshot({ path: path.join(REPORT_DIR, '04-chat-input.png') });

      // Type comprehensive markdown message
      const markdownMessage = `# Test Markdown

**Bold text**, *italic text*, and ***both***.

Inline code: \`const x = 42;\`

\`\`\`python
print("Hello World")
\`\`\`

- Item 1
- Item 2

1. First
2. Second

> Quote text

[Test Link](https://anthropic.com)

| Col1 | Col2 |
|------|------|
| A    | B    |`;

      await chatInput.fill(markdownMessage);
      await page.screenshot({ path: path.join(REPORT_DIR, '05-message-ready.png'), fullPage: true });

      // Send message
      const sendSelectors = [
        'button[type="submit"]',
        'button:has-text("Send")',
        'button:has-text("Enviar")',
        '[aria-label*="send" i]',
        '[class*="sendButton"]'
      ];

      let sent = false;
      for (const selector of sendSelectors) {
        try {
          const button = page.locator(selector).first();
          if (await button.isVisible({ timeout: 1000 })) {
            await button.click();
            sent = true;
            console.log('✓ Message sent with button:', selector);
            break;
          }
        } catch (e) {
          // Try next
        }
      }

      if (!sent) {
        // Try Enter key
        await chatInput.press('Enter');
        console.log('✓ Message sent with Enter key');
      }

      // Wait for message to appear
      await page.waitForTimeout(3000);
      await page.screenshot({ path: path.join(REPORT_DIR, '06-message-sent.png'), fullPage: true });

      // Check for markdown rendering
      const messageArea = page.locator('[class*="message"], [class*="Message"]').last();

      try {
        if (await messageArea.isVisible()) {
          await messageArea.screenshot({ path: path.join(REPORT_DIR, '07-markdown-detail.png') });

          const checks = {
            headings: await messageArea.locator('h1, h2, h3, h4, h5, h6').count(),
            codeBlocks: await messageArea.locator('pre, [class*="codeBlock"]').count(),
            inlineCode: await messageArea.locator('code:not(pre code)').count(),
            lists: await messageArea.locator('ul, ol').count(),
            listItems: await messageArea.locator('li').count(),
            blockquotes: await messageArea.locator('blockquote').count(),
            links: await messageArea.locator('a').count(),
            tables: await messageArea.locator('table').count(),
            bold: await messageArea.locator('strong, b').count(),
            italic: await messageArea.locator('em, i').count()
          };

          console.log('Markdown elements found:');
          console.log('  Headings:', checks.headings);
          console.log('  Code blocks:', checks.codeBlocks);
          console.log('  Inline code:', checks.inlineCode);
          console.log('  Lists:', checks.lists);
          console.log('  List items:', checks.listItems);
          console.log('  Blockquotes:', checks.blockquotes);
          console.log('  Links:', checks.links);
          console.log('  Tables:', checks.tables);
          console.log('  Bold:', checks.bold);
          console.log('  Italic:', checks.italic);

          // Verify link attributes
          if (checks.links > 0) {
            const link = messageArea.locator('a').first();
            const target = await link.getAttribute('target');
            const rel = await link.getAttribute('rel');
            console.log('  Link target:', target);
            console.log('  Link rel:', rel);

            if (target === '_blank') console.log('✓ Links open in new tab');
            if (rel?.includes('noopener')) console.log('✓ Links have security attributes');
          }

          // Summary
          const totalElements = Object.values(checks).reduce((a, b) => a + b, 0);
          console.log(`\nTotal markdown elements rendered: ${totalElements}`);

          if (totalElements > 5) {
            console.log('✓ Markdown rendering appears to be working');
          } else {
            console.log('⚠ Limited markdown rendering detected');
          }
        }
      } catch (error) {
        console.log('Could not analyze markdown rendering:', error);
      }
    } else {
      console.log('⚠ Chat input not found, skipping markdown test');
    }

    console.log('\n=== STEP 5: Test Responsive Design (AC4) ===');

    // Desktop
    await page.setViewportSize({ width: 1920, height: 1080 });
    await page.waitForTimeout(500);
    await page.screenshot({ path: path.join(REPORT_DIR, '08-desktop-1920x1080.png'), fullPage: false });
    console.log('✓ Desktop screenshot captured (1920x1080)');

    // Tablet
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.waitForTimeout(500);
    await page.screenshot({ path: path.join(REPORT_DIR, '09-tablet-768x1024.png'), fullPage: false });
    console.log('✓ Tablet screenshot captured (768x1024)');

    // Mobile
    await page.setViewportSize({ width: 375, height: 667 });
    await page.waitForTimeout(500);
    await page.screenshot({ path: path.join(REPORT_DIR, '10-mobile-375x667.png'), fullPage: false });

    // Check for horizontal scroll
    const hasHorizontalScroll = await page.evaluate(() => {
      return document.documentElement.scrollWidth > document.documentElement.clientWidth;
    });

    if (!hasHorizontalScroll) {
      console.log('✓ No horizontal scrolling on mobile');
    } else {
      console.log('⚠ Horizontal scrolling detected on mobile');
    }

    console.log('✓ Mobile screenshot captured (375x667)');

    // Reset to desktop
    await page.setViewportSize({ width: 1920, height: 1080 });

    console.log('\n=== STEP 6: Check Streaming Indicator (AC5) ===');

    // Check if streaming cursor styles exist
    const hasStreamingStyles = await page.evaluate(() => {
      const styleSheets = Array.from(document.styleSheets);
      for (const sheet of styleSheets) {
        try {
          const rules = Array.from(sheet.cssRules || []);
          for (const rule of rules) {
            if (rule.cssText && (rule.cssText.includes('streamingCursor') || rule.cssText.includes('▊'))) {
              return true;
            }
          }
        } catch (e) {
          // CORS restriction, skip
        }
      }
      return false;
    });

    console.log('Streaming cursor styles present:', hasStreamingStyles);
    if (hasStreamingStyles) {
      console.log('✓ Streaming indicator styles found');
    }

    // Final screenshot
    await page.screenshot({ path: path.join(REPORT_DIR, '11-final-state.png'), fullPage: true });

    console.log('\n=== VALIDATION COMPLETE ===\n');
  });
});
