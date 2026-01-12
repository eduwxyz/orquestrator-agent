const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const REPORT_DIR = '/Users/eduardo/Documents/youtube/orquestrator-agent/.worktrees/card-ba8aa45b/test-reports/playwright/2026-01-12_16-43-10';
const BASE_URL = 'http://localhost:5173';

async function validateZenflow() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 }
  });
  const page = await context.newPage();

  const results = [];
  let stepNumber = 1;

  try {
    console.log('Starting Zenflow validation...');

    // Step 1: Navigate to the application
    console.log(`Step ${stepNumber}: Navigating to ${BASE_URL}`);
    await page.goto(BASE_URL, { waitUntil: 'networkidle' });
    await page.screenshot({ path: path.join(REPORT_DIR, `0${stepNumber}-initial-page.png`), fullPage: true });
    results.push({
      step: stepNumber++,
      action: `Navigate to ${BASE_URL}`,
      status: 'success',
      screenshot: `0${stepNumber - 1}-initial-page.png`
    });

    // Step 2: Validate browser tab title
    console.log(`Step ${stepNumber}: Checking browser tab title`);
    const title = await page.title();
    const titleExpected = 'Zenflow - Workflow Inteligente';
    const titleMatch = title === titleExpected;
    results.push({
      step: stepNumber++,
      action: 'Validate browser tab title',
      criterion: 'Browser tab title should show "Zenflow - Workflow Inteligente"',
      expected: titleExpected,
      actual: title,
      status: titleMatch ? 'success' : 'failure',
      screenshot: `0${stepNumber - 1}-tab-title.png`
    });
    console.log(`  Expected: "${titleExpected}"`);
    console.log(`  Actual: "${title}"`);
    console.log(`  Result: ${titleMatch ? '✅ PASS' : '❌ FAIL'}`);

    // Step 3: Check sidebar logo/name
    console.log(`Step ${stepNumber}: Checking sidebar logo/name`);
    await page.screenshot({ path: path.join(REPORT_DIR, `0${stepNumber}-sidebar-logo.png`), fullPage: true });

    let sidebarLogoText = null;
    let sidebarLogoMatch = false;
    try {
      // Try to find the Zenflow text in the sidebar header
      const logoElement = await page.locator('h2:has-text("Zenflow")').first();
      sidebarLogoText = await logoElement.textContent();
      sidebarLogoMatch = sidebarLogoText && sidebarLogoText.includes('Zenflow');
    } catch (e) {
      sidebarLogoText = 'Not found';
    }

    results.push({
      step: stepNumber++,
      action: 'Validate sidebar logo/name',
      criterion: 'The sidebar logo/name should display "Zenflow"',
      expected: 'Zenflow',
      actual: sidebarLogoText,
      status: sidebarLogoMatch ? 'success' : 'failure',
      screenshot: `0${stepNumber - 1}-sidebar-logo.png`
    });
    console.log(`  Expected: "Zenflow"`);
    console.log(`  Actual: "${sidebarLogoText}"`);
    console.log(`  Result: ${sidebarLogoMatch ? '✅ PASS' : '❌ FAIL'}`);

    // Step 4: Check breadcrumbs
    console.log(`Step ${stepNumber}: Checking breadcrumbs`);
    await page.screenshot({ path: path.join(REPORT_DIR, `0${stepNumber}-breadcrumbs.png`), fullPage: true });

    let breadcrumbText = null;
    let breadcrumbMatch = false;
    try {
      const breadcrumbElement = await page.locator('span:has-text("Zenflow")').first();
      breadcrumbText = await breadcrumbElement.textContent();
      breadcrumbMatch = breadcrumbText && breadcrumbText.includes('Zenflow');
    } catch (e) {
      breadcrumbText = 'Not found';
    }

    results.push({
      step: stepNumber++,
      action: 'Validate breadcrumbs',
      criterion: 'Breadcrumbs should show "Zenflow / [Module Name]"',
      expected: 'Zenflow / ...',
      actual: breadcrumbText,
      status: breadcrumbMatch ? 'success' : 'failure',
      screenshot: `0${stepNumber - 1}-breadcrumbs.png`
    });
    console.log(`  Expected: "Zenflow / ..."`);
    console.log(`  Actual: "${breadcrumbText}"`);
    console.log(`  Result: ${breadcrumbMatch ? '✅ PASS' : '❌ FAIL'}`);

    // Step 5: Navigate to Workflow Board and check title
    console.log(`Step ${stepNumber}: Navigating to Workflow Board`);
    try {
      // Look for the navigation item with "Workflow Board" text
      const workflowBoardNav = await page.locator('text=Workflow Board').first();
      await workflowBoardNav.click();
      await page.waitForTimeout(1000);
      await page.screenshot({ path: path.join(REPORT_DIR, `0${stepNumber}-workflow-board-page.png`), fullPage: true });

      // Check if the page title is "Workflow Board"
      let pageTitleText = null;
      let pageTitleMatch = false;
      try {
        const pageTitle = await page.locator('h1:has-text("Workflow Board")').first();
        pageTitleText = await pageTitle.textContent();
        pageTitleMatch = pageTitleText && pageTitleText.includes('Workflow Board');
      } catch (e) {
        pageTitleText = 'Not found';
      }

      results.push({
        step: stepNumber++,
        action: 'Navigate to Workflow Board and validate title',
        criterion: 'The Kanban page title should be "Workflow Board"',
        expected: 'Workflow Board',
        actual: pageTitleText,
        status: pageTitleMatch ? 'success' : 'failure',
        screenshot: `0${stepNumber - 1}-workflow-board-page.png`
      });
      console.log(`  Expected: "Workflow Board"`);
      console.log(`  Actual: "${pageTitleText}"`);
      console.log(`  Result: ${pageTitleMatch ? '✅ PASS' : '❌ FAIL'}`);
    } catch (e) {
      results.push({
        step: stepNumber++,
        action: 'Navigate to Workflow Board',
        criterion: 'The Kanban page title should be "Workflow Board"',
        status: 'failure',
        error: e.message,
        screenshot: `0${stepNumber - 1}-workflow-board-page.png`
      });
      console.log(`  Result: ❌ FAIL - ${e.message}`);
    }

    // Step 6: Check sidebar footer version
    console.log(`Step ${stepNumber}: Checking sidebar footer`);
    await page.screenshot({ path: path.join(REPORT_DIR, `0${stepNumber}-sidebar-footer.png`), fullPage: true });

    let footerText = null;
    let footerMatch = false;
    try {
      // Look for Zenflow in footer
      const footerElement = await page.locator('span:has-text("Zenflow")').last();
      footerText = await footerElement.textContent();
      footerMatch = footerText && footerText.includes('Zenflow');

      // Also check for version
      const versionText = await page.locator('text=/v?\\d+\\.\\d+\\.\\d+/').textContent().catch(() => 'No version found');
      footerText = `${footerText} (Version info: ${versionText})`;
    } catch (e) {
      footerText = 'Not found';
    }

    results.push({
      step: stepNumber++,
      action: 'Validate sidebar footer',
      criterion: 'The sidebar footer should show "Zenflow v1.0.0"',
      expected: 'Zenflow v1.0.0',
      actual: footerText,
      status: footerMatch ? 'success' : 'failure',
      screenshot: `0${stepNumber - 1}-sidebar-footer.png`
    });
    console.log(`  Expected: "Zenflow v1.0.0"`);
    console.log(`  Actual: "${footerText}"`);
    console.log(`  Result: ${footerMatch ? '✅ PASS' : '❌ FAIL'}`);

    // Step 7: Navigate to Settings page
    console.log(`Step ${stepNumber}: Navigating to Settings page`);
    try {
      const settingsNav = await page.locator('text=Settings').first();
      await settingsNav.click();
      await page.waitForTimeout(1000);
      await page.screenshot({ path: path.join(REPORT_DIR, `0${stepNumber}-settings-page.png`), fullPage: true });

      // Check settings page description
      let settingsDescMatch = false;
      let settingsDescText = null;
      try {
        const settingsDesc = await page.locator('p:has-text("Zenflow")').first();
        settingsDescText = await settingsDesc.textContent();
        settingsDescMatch = settingsDescText && settingsDescText.includes('Zenflow');
      } catch (e) {
        settingsDescText = 'Not found';
      }

      results.push({
        step: stepNumber++,
        action: 'Validate Settings page description',
        criterion: 'Settings page description should mention "Zenflow"',
        expected: 'Text containing "Zenflow"',
        actual: settingsDescText,
        status: settingsDescMatch ? 'success' : 'failure',
        screenshot: `0${stepNumber - 1}-settings-page.png`
      });
      console.log(`  Expected: Text containing "Zenflow"`);
      console.log(`  Actual: "${settingsDescText}"`);
      console.log(`  Result: ${settingsDescMatch ? '✅ PASS' : '❌ FAIL'}`);

      // Check settings page placeholder
      let placeholderMatch = false;
      let placeholderText = null;
      try {
        const inputWithPlaceholder = await page.locator('input[placeholder*="Zenflow"]').first();
        placeholderText = await inputWithPlaceholder.getAttribute('placeholder');
        placeholderMatch = placeholderText && placeholderText.includes('Zenflow');
      } catch (e) {
        placeholderText = 'Not found';
      }

      results.push({
        step: stepNumber++,
        action: 'Validate Settings page input placeholder',
        criterion: 'Settings page project name input placeholder should show "Zenflow"',
        expected: 'Zenflow',
        actual: placeholderText,
        status: placeholderMatch ? 'success' : 'failure',
        screenshot: `0${stepNumber}-settings-placeholder.png`
      });
      console.log(`  Expected: "Zenflow"`);
      console.log(`  Actual: "${placeholderText}"`);
      console.log(`  Result: ${placeholderMatch ? '✅ PASS' : '❌ FAIL'}`);

      await page.screenshot({ path: path.join(REPORT_DIR, `${stepNumber}-settings-placeholder.png`), fullPage: true });
      stepNumber++;
    } catch (e) {
      results.push({
        step: stepNumber++,
        action: 'Navigate to Settings',
        status: 'failure',
        error: e.message
      });
      console.log(`  Result: ❌ FAIL - ${e.message}`);
    }

    // Step 8: Check navigation labels
    console.log(`Step ${stepNumber}: Checking navigation labels`);
    await page.screenshot({ path: path.join(REPORT_DIR, `${stepNumber}-navigation-labels.png`), fullPage: true });

    let navLabelsFound = [];
    try {
      const workflowBoardLabel = await page.locator('text=Workflow Board').count();
      if (workflowBoardLabel > 0) {
        navLabelsFound.push('Workflow Board');
      }

      const navLabelsMatch = workflowBoardLabel > 0;
      results.push({
        step: stepNumber++,
        action: 'Validate navigation labels',
        criterion: 'The navigation item labels should be updated (e.g., "Workflow Board" instead of "Kanban")',
        expected: 'Navigation showing "Workflow Board"',
        actual: `Found labels: ${navLabelsFound.join(', ') || 'None'}`,
        status: navLabelsMatch ? 'success' : 'failure',
        screenshot: `${stepNumber - 1}-navigation-labels.png`
      });
      console.log(`  Expected: Navigation showing "Workflow Board"`);
      console.log(`  Actual: Found labels: ${navLabelsFound.join(', ') || 'None'}`);
      console.log(`  Result: ${navLabelsMatch ? '✅ PASS' : '❌ FAIL'}`);
    } catch (e) {
      results.push({
        step: stepNumber++,
        action: 'Validate navigation labels',
        status: 'failure',
        error: e.message,
        screenshot: `${stepNumber - 1}-navigation-labels.png`
      });
      console.log(`  Result: ❌ FAIL - ${e.message}`);
    }

    // Take final screenshot
    await page.screenshot({ path: path.join(REPORT_DIR, `${stepNumber}-final-state.png`), fullPage: true });

  } catch (error) {
    console.error('Error during validation:', error);
    results.push({
      step: stepNumber++,
      action: 'Validation error',
      status: 'failure',
      error: error.message
    });
  } finally {
    await browser.close();
  }

  return results;
}

// Run validation and output results
validateZenflow().then(results => {
  console.log('\n' + '='.repeat(80));
  console.log('VALIDATION COMPLETE');
  console.log('='.repeat(80));

  // Write results to JSON file
  const resultsPath = path.join(REPORT_DIR, 'validation-results.json');
  fs.writeFileSync(resultsPath, JSON.stringify(results, null, 2));
  console.log(`\nResults saved to: ${resultsPath}`);

  // Count successes and failures
  const successes = results.filter(r => r.status === 'success').length;
  const failures = results.filter(r => r.status === 'failure').length;

  console.log(`\nSummary: ${successes} passed, ${failures} failed out of ${results.length} total checks`);

  // Exit with appropriate code
  process.exit(failures > 0 ? 1 : 0);
}).catch(error => {
  console.error('Fatal error:', error);
  process.exit(1);
});
