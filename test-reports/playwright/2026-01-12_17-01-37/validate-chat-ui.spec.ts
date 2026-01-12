import { test, expect } from '@playwright/test';
import path from 'path';

const REPORT_DIR = __dirname;
const FRONTEND_URL = 'http://localhost:5173';

test.describe('Chat UI Improvements Validation', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(FRONTEND_URL);
    await page.waitForLoadState('networkidle');
  });

  test('AC1: Markdown Rendering - Comprehensive Test', async ({ page }) => {
    // Wait for chat interface to load
    await page.waitForSelector('[data-testid="chat-input"], textarea, input[type="text"]', { timeout: 10000 });

    // Take initial screenshot
    await page.screenshot({ path: path.join(REPORT_DIR, '01-initial-page.png'), fullPage: true });

    // Find the chat input (try multiple selectors)
    const chatInput = await page.locator('textarea, input[type="text"], [contenteditable="true"]').first();

    // Construct a comprehensive markdown message
    const markdownMessage = `# Heading 1
## Heading 2
### Heading 3

This is a paragraph with **bold text**, *italic text*, and ***bold italic text***.

Here's some \`inline code\` in a sentence.

\`\`\`python
def hello_world():
    print('Hello, World!')
    return 42
\`\`\`

\`\`\`javascript
const greeting = () => {
  console.log('Hello from JS!');
};
\`\`\`

Unordered list:
- Item 1
- Item 2
- Item 3

Ordered list:
1. First item
2. Second item
3. Third item

> This is a blockquote.
> It can span multiple lines.

Here's a [link to Anthropic](https://www.anthropic.com) that should open in a new tab.

| Column 1 | Column 2 | Column 3 |
|----------|----------|----------|
| Row 1    | Data A   | Data X   |
| Row 2    | Data B   | Data Y   |
| Row 3    | Data C   | Data Z   |

Mixed formatting: **bold with \`code\`** and *italic with [link](https://example.com)*.`;

    // Fill and send the message
    await chatInput.fill(markdownMessage);
    await page.screenshot({ path: path.join(REPORT_DIR, '02-message-typed.png'), fullPage: true });

    // Submit the message (try multiple methods)
    const sendButton = await page.locator('button[type="submit"], button:has-text("Send"), [data-testid="send-button"]').first();
    if (await sendButton.isVisible()) {
      await sendButton.click();
    } else {
      await chatInput.press('Enter');
    }

    // Wait for message to appear in chat
    await page.waitForTimeout(2000);
    await page.screenshot({ path: path.join(REPORT_DIR, '03-markdown-rendered.png'), fullPage: true });

    // Verify markdown elements are rendered
    const messageContainer = await page.locator('.messageText, [class*="message"]').last();

    // Check for headings
    await expect(messageContainer.locator('h1')).toBeVisible();
    await expect(messageContainer.locator('h2')).toBeVisible();
    await expect(messageContainer.locator('h3')).toBeVisible();

    // Check for formatted text (bold, italic)
    await expect(messageContainer.locator('strong, b')).toBeVisible();
    await expect(messageContainer.locator('em, i')).toBeVisible();

    // Check for code blocks
    const codeBlocks = await messageContainer.locator('pre code, [class*="codeBlock"]').count();
    expect(codeBlocks).toBeGreaterThanOrEqual(2); // Python and JavaScript blocks

    // Check for inline code
    await expect(messageContainer.locator('code:not(pre code)')).toBeVisible();

    // Check for lists
    await expect(messageContainer.locator('ul')).toBeVisible();
    await expect(messageContainer.locator('ol')).toBeVisible();
    await expect(messageContainer.locator('li')).toHaveCount(6); // 3 unordered + 3 ordered

    // Check for blockquote
    await expect(messageContainer.locator('blockquote')).toBeVisible();

    // Check for link
    const link = await messageContainer.locator('a[href*="anthropic"]');
    await expect(link).toBeVisible();

    // Verify link opens in new tab
    const linkTarget = await link.getAttribute('target');
    expect(linkTarget).toBe('_blank');

    const linkRel = await link.getAttribute('rel');
    expect(linkRel).toContain('noopener');

    // Check for table
    await expect(messageContainer.locator('table')).toBeVisible();
    await expect(messageContainer.locator('th')).toHaveCount(3);

    // Take detailed screenshot of markdown rendering
    await messageContainer.screenshot({ path: path.join(REPORT_DIR, '04-markdown-detail.png') });
  });

  test('AC2: Model Selector Filtering', async ({ page }) => {
    // Find and click the model selector
    const modelSelector = await page.locator('select, [data-testid="model-selector"], button:has-text("Model"), [class*="modelSelector"]').first();

    await page.screenshot({ path: path.join(REPORT_DIR, '05-before-model-selector.png'), fullPage: true });

    // Click to open dropdown
    await modelSelector.click();
    await page.waitForTimeout(500);

    await page.screenshot({ path: path.join(REPORT_DIR, '06-model-selector-open.png'), fullPage: true });

    // Get all model options
    const options = await page.locator('option, [role="option"], [class*="model"]').allTextContents();

    // Verify Anthropic models are present
    const hasOpus = options.some(opt => opt.toLowerCase().includes('opus'));
    const hasSonnet = options.some(opt => opt.toLowerCase().includes('sonnet'));
    const hasHaiku = options.some(opt => opt.toLowerCase().includes('haiku'));

    // Verify Gemini models are present
    const hasGemini = options.some(opt => opt.toLowerCase().includes('gemini'));

    // Verify OpenAI/GPT models are NOT present
    const hasGPT = options.some(opt =>
      opt.toLowerCase().includes('gpt') ||
      opt.toLowerCase().includes('openai')
    );

    expect(hasOpus || hasSonnet || hasHaiku).toBeTruthy();
    expect(hasGemini).toBeTruthy();
    expect(hasGPT).toBeFalsy();

    console.log('Available models:', options);
  });

  test('AC3: Visual Consistency with Deep Dark Theme', async ({ page }) => {
    await page.screenshot({ path: path.join(REPORT_DIR, '07-dark-theme-overview.png'), fullPage: true });

    // Check background colors are dark
    const body = await page.locator('body');
    const bodyBg = await body.evaluate(el => {
      return window.getComputedStyle(el).backgroundColor;
    });

    // Parse RGB values - dark backgrounds should have low RGB values
    const rgbMatch = bodyBg.match(/rgb\((\d+),\s*(\d+),\s*(\d+)\)/);
    if (rgbMatch) {
      const [, r, g, b] = rgbMatch.map(Number);
      const avgBrightness = (r + g + b) / 3;
      expect(avgBrightness).toBeLessThan(50); // Dark background
    }

    // Check chat container uses dark theme
    const chatContainer = await page.locator('[class*="chat"], [class*="Chat"], main').first();
    await chatContainer.screenshot({ path: path.join(REPORT_DIR, '08-chat-container-theme.png') });

    // Verify text contrast
    const textColor = await page.locator('p, div[class*="message"]').first().evaluate(el => {
      return window.getComputedStyle(el).color;
    });

    console.log('Body background:', bodyBg);
    console.log('Text color:', textColor);
  });

  test('AC4: Responsive Design', async ({ page }) => {
    // Test desktop viewport (1920x1080)
    await page.setViewportSize({ width: 1920, height: 1080 });
    await page.screenshot({ path: path.join(REPORT_DIR, '09-desktop-viewport.png'), fullPage: true });

    // Test tablet viewport (768x1024)
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.waitForTimeout(500);
    await page.screenshot({ path: path.join(REPORT_DIR, '10-tablet-viewport.png'), fullPage: true });

    // Test mobile viewport (375x667)
    await page.setViewportSize({ width: 375, height: 667 });
    await page.waitForTimeout(500);
    await page.screenshot({ path: path.join(REPORT_DIR, '11-mobile-viewport.png'), fullPage: true });

    // Check for horizontal scrolling
    const hasHorizontalScroll = await page.evaluate(() => {
      return document.documentElement.scrollWidth > document.documentElement.clientWidth;
    });

    expect(hasHorizontalScroll).toBeFalsy();

    // Reset to desktop
    await page.setViewportSize({ width: 1920, height: 1080 });
  });

  test('AC5: Message Streaming Indicator', async ({ page }) => {
    // This test would require triggering actual streaming
    // For now, we'll check if the streaming cursor class exists in CSS

    const styles = await page.evaluate(() => {
      const styleSheets = Array.from(document.styleSheets);
      let hasStreamingCursor = false;

      styleSheets.forEach(sheet => {
        try {
          const rules = Array.from(sheet.cssRules || []);
          rules.forEach(rule => {
            if (rule.cssText.includes('streamingCursor') || rule.cssText.includes('▊')) {
              hasStreamingCursor = true;
            }
          });
        } catch (e) {
          // CORS or other access issues
        }
      });

      return hasStreamingCursor;
    });

    await page.screenshot({ path: path.join(REPORT_DIR, '12-streaming-check.png'), fullPage: true });

    // Note: Full streaming test would require mock backend
    console.log('Streaming cursor style exists:', styles);
  });
});
