import { test, expect } from '@playwright/test';
import path from 'path';

const REPORT_DIR = __dirname;
const FRONTEND_URL = 'http://localhost:5173';

test('Markdown Rendering Comprehensive Test', async ({ page }) => {
  test.setTimeout(90000);

  console.log('\n=== Opening Chat Interface ===');
  await page.goto(FRONTEND_URL);
  await page.waitForLoadState('networkidle');

  const chatButton = page.locator('button:has-text("Abrir Chat AI")').first();
  await chatButton.click();
  await page.waitForTimeout(2000);
  await page.screenshot({ path: path.join(REPORT_DIR, 'markdown-01-chat-ready.png'), fullPage: true });

  console.log('\n=== Entering Markdown Message ===');
  const chatInput = page.locator('textarea').first();

  const markdownContent = `# Level 1 Heading
## Level 2 Heading
### Level 3 Heading

This is a paragraph with **bold text**, *italic text*, and ***bold italic text***.

Here's some inline code: \`const x = 42;\`

Python code block with syntax highlighting:
\`\`\`python
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

print(fibonacci(10))
\`\`\`

JavaScript code block:
\`\`\`javascript
const greet = (name) => {
  console.log(\`Hello, \${name}!\`);
  return true;
};
\`\`\`

Unordered list:
- First item
- Second item with **bold**
- Third item with \`code\`

Ordered list:
1. Step one
2. Step two
3. Step three

> This is a blockquote.
> It can span multiple lines.
> And demonstrate proper styling.

Here's a link: [Anthropic Website](https://www.anthropic.com)

Table example:

| Feature | Status | Priority |
|---------|--------|----------|
| Markdown | Done | High |
| Syntax | Done | High |
| Tables | Testing | Medium |

Mixed formatting: **Bold with \`code\`** and *italic with [link](https://example.com)*.`;

  await chatInput.fill(markdownContent);
  await page.screenshot({ path: path.join(REPORT_DIR, 'markdown-02-content-entered.png'), fullPage: true });

  console.log('✓ Markdown content entered');

  console.log('\n=== Sending Message ===');
  await page.keyboard.press('Enter');
  await page.waitForTimeout(5000); // Wait for message to appear and render

  await page.screenshot({ path: path.join(REPORT_DIR, 'markdown-03-message-sent.png'), fullPage: true });

  console.log('\n=== Analyzing Rendered Markdown ===');
  const messageContainers = page.locator('[class*="message"]');
  const userMessage = messageContainers.last();

  if (await userMessage.isVisible({ timeout: 5000 }).catch(() => false)) {
    await userMessage.screenshot({ path: path.join(REPORT_DIR, 'markdown-04-closeup.png') });

    const elements = {
      h1: await userMessage.locator('h1').count(),
      h2: await userMessage.locator('h2').count(),
      h3: await userMessage.locator('h3').count(),
      strong: await userMessage.locator('strong, b').count(),
      em: await userMessage.locator('em, i').count(),
      codeBlocks: await userMessage.locator('pre').count(),
      inlineCode: await userMessage.locator('code:not(pre code)').count(),
      ul: await userMessage.locator('ul').count(),
      ol: await userMessage.locator('ol').count(),
      li: await userMessage.locator('li').count(),
      blockquote: await userMessage.locator('blockquote').count(),
      links: await userMessage.locator('a').count(),
      tables: await userMessage.locator('table').count(),
      tableHeaders: await userMessage.locator('th').count(),
      tableRows: await userMessage.locator('tr').count()
    };

    console.log('\n=== Markdown Element Count ===');
    console.log('Headings:');
    console.log('  H1:', elements.h1, elements.h1 >= 1 ? '✓' : '✗');
    console.log('  H2:', elements.h2, elements.h2 >= 1 ? '✓' : '✗');
    console.log('  H3:', elements.h3, elements.h3 >= 1 ? '✓' : '✗');
    console.log('Text formatting:');
    console.log('  Bold:', elements.strong, elements.strong >= 1 ? '✓' : '✗');
    console.log('  Italic:', elements.em, elements.em >= 1 ? '✓' : '✗');
    console.log('Code:');
    console.log('  Code blocks:', elements.codeBlocks, elements.codeBlocks >= 2 ? '✓' : '✗');
    console.log('  Inline code:', elements.inlineCode, elements.inlineCode >= 1 ? '✓' : '✗');
    console.log('Lists:');
    console.log('  Unordered (ul):', elements.ul, elements.ul >= 1 ? '✓' : '✗');
    console.log('  Ordered (ol):', elements.ol, elements.ol >= 1 ? '✓' : '✗');
    console.log('  List items:', elements.li, elements.li >= 6 ? '✓' : '✗');
    console.log('Other:');
    console.log('  Blockquotes:', elements.blockquote, elements.blockquote >= 1 ? '✓' : '✗');
    console.log('  Links:', elements.links, elements.links >= 1 ? '✓' : '✗');
    console.log('  Tables:', elements.tables, elements.tables >= 1 ? '✓' : '✗');
    console.log('  Table headers:', elements.tableHeaders, elements.tableHeaders >= 3 ? '✓' : '✗');

    // Test assertions
    expect(elements.h1).toBeGreaterThanOrEqual(1);
    expect(elements.h2).toBeGreaterThanOrEqual(1);
    expect(elements.h3).toBeGreaterThanOrEqual(1);
    expect(elements.strong).toBeGreaterThanOrEqual(1);
    expect(elements.codeBlocks).toBeGreaterThanOrEqual(2);
    expect(elements.ul).toBeGreaterThanOrEqual(1);
    expect(elements.ol).toBeGreaterThanOrEqual(1);
    expect(elements.blockquote).toBeGreaterThanOrEqual(1);
    expect(elements.links).toBeGreaterThanOrEqual(1);
    expect(elements.tables).toBeGreaterThanOrEqual(1);

    console.log('\n=== Link Attributes Test ===');
    if (elements.links > 0) {
      const firstLink = userMessage.locator('a').first();
      const target = await firstLink.getAttribute('target');
      const rel = await firstLink.getAttribute('rel');

      console.log('Link target:', target);
      console.log('Link rel:', rel);

      expect(target).toBe('_blank');
      expect(rel).toContain('noopener');
      console.log('✓ Links open in new tab with security attributes');
    }

    console.log('\n=== Code Block Styling Test ===');
    if (elements.codeBlocks > 0) {
      const codeBlock = userMessage.locator('pre').first();
      const bgColor = await codeBlock.evaluate(el => window.getComputedStyle(el).backgroundColor);
      const hasContent = await codeBlock.locator('code').count() > 0;

      console.log('Code block background:', bgColor);
      console.log('Has code element inside:', hasContent);

      // Check if it's a dark background
      const rgbMatch = bgColor.match(/rgb\((\d+),\s*(\d+),\s*(\d+)\)/);
      if (rgbMatch) {
        const [, r, g, b] = rgbMatch.map(Number);
        const brightness = (r + g + b) / 3;
        console.log('Code block brightness:', brightness);

        if (brightness < 80) {
          console.log('✓ Code block has dark background for syntax highlighting');
        }
      }
    }

    console.log('\n=== List Styling Test ===');
    if (elements.li > 0) {
      const listItem = userMessage.locator('li').first();
      const color = await listItem.evaluate(el => {
        const style = window.getComputedStyle(el, '::marker');
        return style.color;
      });
      console.log('List marker color:', color);
    }

    const totalElements = Object.values(elements).reduce((a, b) => a + b, 0);
    console.log('\n=== Summary ===');
    console.log('Total markdown elements rendered:', totalElements);
    console.log(totalElements >= 20 ? '✓ PASS: Comprehensive markdown rendering' : '⚠ WARNING: Limited markdown support');

  } else {
    console.log('✗ FAIL: Could not find rendered message');
    throw new Error('Message not rendered');
  }

  await page.screenshot({ path: path.join(REPORT_DIR, 'markdown-05-final.png'), fullPage: true });
  console.log('\n=== Test Complete ===\n');
});
