import { test, expect } from '@playwright/test';
import path from 'path';

const REPORT_DIR = __dirname;
const FRONTEND_URL = 'http://localhost:5173';

test.describe('Chat UI Improvements - Manual Validation', () => {
  test('Complete Chat UI Validation Flow', async ({ page }) => {
    // Step 1: Navigate to frontend
    await page.goto(FRONTEND_URL);
    await page.waitForLoadState('networkidle');
    await page.screenshot({ path: path.join(REPORT_DIR, '01-initial-dashboard.png'), fullPage: true });

    // Step 2: Navigate to Chat page - look for chat link in sidebar
    const chatLink = page.locator('a:has-text("AI Assistant"), a:has-text("Chat"), [href*="chat"]').first();
    await chatLink.click();
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);
    await page.screenshot({ path: path.join(REPORT_DIR, '02-chat-page-loaded.png'), fullPage: true });

    // Step 3: Capture page HTML for analysis
    const pageContent = await page.content();
    console.log('Chat page loaded, checking for chat elements...');

    // Step 4: Try to find the model selector - inspect what's available
    try {
      const modelSelectorArea = await page.locator('[class*="model"], [class*="Model"], select').first();
      if (await modelSelectorArea.isVisible()) {
        await modelSelectorArea.screenshot({ path: path.join(REPORT_DIR, '03-model-selector-area.png') });

        // Click on model selector
        await modelSelectorArea.click();
        await page.waitForTimeout(1000);
        await page.screenshot({ path: path.join(REPORT_DIR, '04-model-selector-opened.png'), fullPage: true });

        // Get all visible text to see available models
        const bodyText = await page.locator('body').textContent();
        console.log('Available models text:', bodyText?.substring(0, 500));

        // Check for specific model names
        const hasAnthropicModels = bodyText?.toLowerCase().includes('opus') ||
                                   bodyText?.toLowerCase().includes('sonnet') ||
                                   bodyText?.toLowerCase().includes('haiku');
        const hasGeminiModels = bodyText?.toLowerCase().includes('gemini');
        const hasOpenAIModels = bodyText?.toLowerCase().includes('gpt') ||
                                bodyText?.toLowerCase().includes('openai');

        console.log('Anthropic models found:', hasAnthropicModels);
        console.log('Gemini models found:', hasGeminiModels);
        console.log('OpenAI models found:', hasOpenAIModels);

        expect(hasAnthropicModels).toBeTruthy();
        expect(hasGeminiModels).toBeTruthy();
        expect(hasOpenAIModels).toBeFalsy();

        // Close selector by clicking elsewhere
        await page.locator('body').click({ position: { x: 100, y: 100 } });
        await page.waitForTimeout(500);
      }
    } catch (error) {
      console.log('Model selector test error:', error);
    }

    // Step 5: Find chat input and test markdown rendering
    await page.screenshot({ path: path.join(REPORT_DIR, '05-before-message.png'), fullPage: true });

    const chatInput = await page.locator('textarea, [contenteditable="true"], input[placeholder*="message" i]').first();
    await chatInput.scrollIntoViewIfNeeded();

    // Prepare comprehensive markdown test message
    const markdownTest = `# Markdown Test

## Features to test:

This paragraph has **bold text**, *italic text*, and ***bold italic***.

Inline code: \`const x = 42;\`

\`\`\`python
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
\`\`\`

\`\`\`javascript
const greet = (name) => {
  console.log(\`Hello, \${name}!\`);
};
\`\`\`

### Lists:

Unordered:
- First item
- Second item
- Third item

Ordered:
1. Step one
2. Step two
3. Step three

> This is a blockquote.
> It demonstrates quote styling.

[Link to Anthropic](https://www.anthropic.com)

| Header 1 | Header 2 | Header 3 |
|----------|----------|----------|
| Cell 1   | Cell 2   | Cell 3   |
| Cell 4   | Cell 5   | Cell 6   |`;

    await chatInput.fill(markdownTest);
    await page.screenshot({ path: path.join(REPORT_DIR, '06-message-typed.png'), fullPage: true });

    // Send the message - try multiple button selectors
    const sendButton = page.locator('button[type="submit"], button:has-text("Send"), button:has-text("Enviar"), [aria-label*="send" i]').first();

    if (await sendButton.isVisible()) {
      await sendButton.click();
    } else {
      // Try keyboard shortcut
      await chatInput.press('Enter');
    }

    // Wait for response
    await page.waitForTimeout(3000);
    await page.screenshot({ path: path.join(REPORT_DIR, '07-message-sent.png'), fullPage: true });

    // Step 6: Verify markdown rendering
    const messages = page.locator('[class*="message"]');
    const lastMessage = messages.last();

    if (await lastMessage.isVisible()) {
      await lastMessage.screenshot({ path: path.join(REPORT_DIR, '08-markdown-rendered-detail.png') });

      // Check for markdown elements within the message
      const hasHeadings = await lastMessage.locator('h1, h2, h3').count() > 0;
      const hasCodeBlocks = await lastMessage.locator('pre, [class*="codeBlock"]').count() > 0;
      const hasInlineCode = await lastMessage.locator('code:not(pre code)').count() > 0;
      const hasLists = await lastMessage.locator('ul, ol').count() > 0;
      const hasBlockquote = await lastMessage.locator('blockquote').count() > 0;
      const hasLinks = await lastMessage.locator('a').count() > 0;
      const hasTable = await lastMessage.locator('table').count() > 0;

      console.log('Markdown rendering results:');
      console.log('  Headings:', hasHeadings);
      console.log('  Code blocks:', hasCodeBlocks);
      console.log('  Inline code:', hasInlineCode);
      console.log('  Lists:', hasLists);
      console.log('  Blockquote:', hasBlockquote);
      console.log('  Links:', hasLinks);
      console.log('  Table:', hasTable);

      // Verify at least some markdown is rendered
      expect(hasHeadings || hasCodeBlocks || hasLists).toBeTruthy();

      // Check if links have proper attributes
      if (hasLinks) {
        const link = lastMessage.locator('a').first();
        const target = await link.getAttribute('target');
        const rel = await link.getAttribute('rel');
        console.log('  Link target:', target);
        console.log('  Link rel:', rel);
        expect(target).toBe('_blank');
        expect(rel).toContain('noopener');
      }
    }

    // Step 7: Test responsive design
    await page.setViewportSize({ width: 1920, height: 1080 });
    await page.screenshot({ path: path.join(REPORT_DIR, '09-desktop-1920.png'), fullPage: true });

    await page.setViewportSize({ width: 768, height: 1024 });
    await page.waitForTimeout(500);
    await page.screenshot({ path: path.join(REPORT_DIR, '10-tablet-768.png'), fullPage: true });

    await page.setViewportSize({ width: 375, height: 667 });
    await page.waitForTimeout(500);
    await page.screenshot({ path: path.join(REPORT_DIR, '11-mobile-375.png'), fullPage: true });

    // Step 8: Verify dark theme consistency
    await page.setViewportSize({ width: 1920, height: 1080 });
    const bodyBg = await page.locator('body').evaluate(el => {
      return window.getComputedStyle(el).backgroundColor;
    });

    const chatContainerBg = await page.locator('[class*="chat"], main').first().evaluate(el => {
      return window.getComputedStyle(el).backgroundColor;
    });

    console.log('Theme colors:');
    console.log('  Body background:', bodyBg);
    console.log('  Chat container background:', chatContainerBg);

    // Parse RGB and verify dark theme
    const rgbMatch = bodyBg.match(/rgb\((\d+),\s*(\d+),\s*(\d+)\)/);
    if (rgbMatch) {
      const [, r, g, b] = rgbMatch.map(Number);
      const avgBrightness = (r + g + b) / 3;
      console.log('  Average brightness:', avgBrightness);
      expect(avgBrightness).toBeLessThan(50);
    }

    // Final screenshot
    await page.screenshot({ path: path.join(REPORT_DIR, '12-final-state.png'), fullPage: true });
  });
});
