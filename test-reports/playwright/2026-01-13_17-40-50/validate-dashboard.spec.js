const { test, expect } = require('@playwright/test');
const path = require('path');

const REPORT_DIR = __dirname;
const BASE_URL = 'http://localhost:5173';

test.describe('Dashboard Visual Improvements Validation', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(BASE_URL);
    // Wait for the page to be fully loaded
    await page.waitForLoadState('networkidle');
  });

  test('01 - Initial page load and hero section', async ({ page }) => {
    // Take initial screenshot
    await page.screenshot({
      path: path.join(REPORT_DIR, '01-initial-page.png'),
      fullPage: true
    });

    // Check hero section exists
    const hero = await page.locator('[class*="hero"]').first();
    await expect(hero).toBeVisible();

    // Check for glassmorphism effects (backdrop-filter)
    const heroStyles = await hero.evaluate((el) => {
      const styles = window.getComputedStyle(el);
      return {
        backdropFilter: styles.backdropFilter,
        background: styles.background,
        border: styles.border,
        borderRadius: styles.borderRadius
      };
    });

    console.log('Hero Section Styles:', heroStyles);
  });

  test('02 - Mesh gradient background animation', async ({ page }) => {
    // Check for background effects
    const backgroundEffects = await page.locator('[class*="backgroundEffects"], [class*="meshGradient"]').first();

    if (await backgroundEffects.isVisible()) {
      const bgStyles = await backgroundEffects.evaluate((el) => {
        const styles = window.getComputedStyle(el);
        return {
          background: styles.background,
          opacity: styles.opacity,
          animation: styles.animation
        };
      });
      console.log('Background Effects:', bgStyles);
    } else {
      console.log('Background effects not found - may be fixed positioned or styled differently');
    }

    await page.screenshot({
      path: path.join(REPORT_DIR, '02-background-effects.png'),
      fullPage: true
    });
  });

  test('03 - Metrics grid layout and spacing', async ({ page }) => {
    // Find metrics grid
    const metricsGrid = await page.locator('[class*="metricsGrid"], [class*="metrics"]').first();
    await expect(metricsGrid).toBeVisible();

    // Check grid properties
    const gridStyles = await metricsGrid.evaluate((el) => {
      const styles = window.getComputedStyle(el);
      return {
        display: styles.display,
        gap: styles.gap,
        gridTemplateColumns: styles.gridTemplateColumns
      };
    });

    console.log('Metrics Grid Styles:', gridStyles);

    await page.screenshot({
      path: path.join(REPORT_DIR, '03-metrics-grid.png'),
      fullPage: true
    });
  });

  test('04 - Metric cards styling and hover effects', async ({ page }) => {
    // Find all metric cards
    const metricCards = await page.locator('[class*="metricCard"]').all();
    console.log(`Found ${metricCards.length} metric cards`);

    if (metricCards.length > 0) {
      const firstCard = metricCards[0];

      // Get initial styles
      const initialStyles = await firstCard.evaluate((el) => {
        const styles = window.getComputedStyle(el);
        return {
          background: styles.background,
          border: styles.border,
          borderRadius: styles.borderRadius,
          boxShadow: styles.boxShadow,
          transform: styles.transform
        };
      });
      console.log('Card Initial Styles:', initialStyles);

      // Take screenshot before hover
      await page.screenshot({
        path: path.join(REPORT_DIR, '04-metric-cards-normal.png'),
        fullPage: true
      });

      // Hover over first card
      await firstCard.hover();
      await page.waitForTimeout(500); // Wait for hover animation

      // Get hover styles
      const hoverStyles = await firstCard.evaluate((el) => {
        const styles = window.getComputedStyle(el);
        return {
          transform: styles.transform,
          boxShadow: styles.boxShadow
        };
      });
      console.log('Card Hover Styles:', hoverStyles);

      // Take screenshot after hover
      await page.screenshot({
        path: path.join(REPORT_DIR, '04-metric-cards-hover.png'),
        fullPage: true
      });
    }
  });

  test('05 - Activity feed timeline and animations', async ({ page }) => {
    // Look for activity feed
    const activityFeed = await page.locator('[class*="activityFeed"], [class*="timeline"]').first();

    if (await activityFeed.isVisible()) {
      // Check for timeline line (pseudo-element)
      const timelineStyles = await activityFeed.evaluate((el) => {
        const styles = window.getComputedStyle(el, '::before');
        return {
          content: styles.content,
          background: styles.background,
          width: styles.width
        };
      });
      console.log('Timeline Styles:', timelineStyles);
    }

    await page.screenshot({
      path: path.join(REPORT_DIR, '05-activity-feed.png'),
      fullPage: true
    });
  });

  test('06 - Dark theme consistency', async ({ page }) => {
    // Check root CSS variables
    const cssVars = await page.evaluate(() => {
      const root = document.documentElement;
      const styles = window.getComputedStyle(root);
      return {
        bgPrimary: styles.getPropertyValue('--bg-primary'),
        bgSecondary: styles.getPropertyValue('--bg-secondary'),
        textPrimary: styles.getPropertyValue('--text-primary'),
        accentCyan: styles.getPropertyValue('--accent-cyan'),
        accentPurple: styles.getPropertyValue('--accent-purple')
      };
    });
    console.log('CSS Variables:', cssVars);

    // Check body background
    const bodyBg = await page.evaluate(() => {
      return window.getComputedStyle(document.body).background;
    });
    console.log('Body Background:', bodyBg);
  });

  test('07 - Check for console errors', async ({ page }) => {
    const errors = [];
    const warnings = [];

    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      } else if (msg.type() === 'warning') {
        warnings.push(msg.text());
      }
    });

    // Navigate and wait
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    console.log('Console Errors:', errors.length > 0 ? errors : 'None');
    console.log('Console Warnings:', warnings.length > 0 ? warnings : 'None');

    // Fail test if there are critical CSS errors
    const cssErrors = errors.filter(e => e.toLowerCase().includes('css') || e.toLowerCase().includes('style'));
    expect(cssErrors.length).toBe(0);
  });

  test('08 - Mobile responsive view (640px)', async ({ page }) => {
    await page.setViewportSize({ width: 640, height: 1000 });
    await page.waitForTimeout(500);

    await page.screenshot({
      path: path.join(REPORT_DIR, '08-mobile-640px.png'),
      fullPage: true
    });

    // Check grid changes to 1 column
    const metricsGrid = await page.locator('[class*="metricsGrid"], [class*="metrics"]').first();
    if (await metricsGrid.isVisible()) {
      const gridCols = await metricsGrid.evaluate((el) => {
        return window.getComputedStyle(el).gridTemplateColumns;
      });
      console.log('Mobile Grid Columns:', gridCols);
    }
  });

  test('09 - Tablet responsive view (1024px)', async ({ page }) => {
    await page.setViewportSize({ width: 1024, height: 768 });
    await page.waitForTimeout(500);

    await page.screenshot({
      path: path.join(REPORT_DIR, '09-tablet-1024px.png'),
      fullPage: true
    });

    // Check grid changes to 2 columns
    const metricsGrid = await page.locator('[class*="metricsGrid"], [class*="metrics"]').first();
    if (await metricsGrid.isVisible()) {
      const gridCols = await metricsGrid.evaluate((el) => {
        return window.getComputedStyle(el).gridTemplateColumns;
      });
      console.log('Tablet Grid Columns:', gridCols);
    }
  });

  test('10 - Desktop responsive view (1440px)', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.waitForTimeout(500);

    await page.screenshot({
      path: path.join(REPORT_DIR, '10-desktop-1440px.png'),
      fullPage: true
    });

    // Check grid changes to 3 columns
    const metricsGrid = await page.locator('[class*="metricsGrid"], [class*="metrics"]').first();
    if (await metricsGrid.isVisible()) {
      const gridCols = await metricsGrid.evaluate((el) => {
        return window.getComputedStyle(el).gridTemplateColumns;
      });
      console.log('Desktop Grid Columns:', gridCols);
    }
  });

  test('11 - Icon glow effects', async ({ page }) => {
    // Find icon wrappers in metric cards
    const icons = await page.locator('[class*="iconWrapper"], [class*="icon"]').all();
    console.log(`Found ${icons.length} icons`);

    if (icons.length > 0) {
      const iconStyles = await icons[0].evaluate((el) => {
        const styles = window.getComputedStyle(el);
        return {
          background: styles.background,
          boxShadow: styles.boxShadow,
          filter: styles.filter
        };
      });
      console.log('Icon Styles:', iconStyles);
    }

    await page.screenshot({
      path: path.join(REPORT_DIR, '11-icon-glow-effects.png'),
      fullPage: true
    });
  });

  test('12 - Animation smoothness check', async ({ page }) => {
    // Measure animation performance
    const animationMetrics = await page.evaluate(() => {
      return new Promise((resolve) => {
        const observer = new PerformanceObserver((list) => {
          const entries = list.getEntries();
          resolve({
            animationCount: entries.length,
            entries: entries.map(e => ({ name: e.name, duration: e.duration }))
          });
        });
        observer.observe({ entryTypes: ['measure'] });

        // Trigger animations by scrolling
        window.scrollTo(0, 100);
        window.scrollTo(0, 0);

        setTimeout(() => resolve({ animationCount: 0, entries: [] }), 1000);
      });
    });

    console.log('Animation Metrics:', animationMetrics);

    await page.screenshot({
      path: path.join(REPORT_DIR, '12-animations-check.png'),
      fullPage: true
    });
  });

  test('13 - Vibrant accent colors validation', async ({ page }) => {
    // Check for new vibrant accent color variables
    const vibrantColors = await page.evaluate(() => {
      const root = document.documentElement;
      const styles = window.getComputedStyle(root);
      return {
        cyanVibrant: styles.getPropertyValue('--accent-cyan-vibrant'),
        purpleVibrant: styles.getPropertyValue('--accent-purple-vibrant'),
        successVibrant: styles.getPropertyValue('--accent-success-vibrant'),
        warningVibrant: styles.getPropertyValue('--accent-warning-vibrant'),
        infoVibrant: styles.getPropertyValue('--accent-info-vibrant'),
        dangerVibrant: styles.getPropertyValue('--accent-danger-vibrant')
      };
    });

    console.log('Vibrant Accent Colors:', vibrantColors);
  });

  test('14 - Glass blur variables check', async ({ page }) => {
    const glassVars = await page.evaluate(() => {
      const root = document.documentElement;
      const styles = window.getComputedStyle(root);
      return {
        glassBlur: styles.getPropertyValue('--glass-blur'),
        glassBlurHeavy: styles.getPropertyValue('--glass-blur-heavy'),
        glassBlurLight: styles.getPropertyValue('--glass-blur-light'),
        glassBorder: styles.getPropertyValue('--glass-border')
      };
    });

    console.log('Glass Effect Variables:', glassVars);
  });

  test('15 - Accessibility color contrast check', async ({ page }) => {
    // Get text and background color pairs
    const contrastChecks = await page.evaluate(() => {
      const checks = [];
      const textElements = document.querySelectorAll('p, h1, h2, h3, h4, h5, h6, span, div');

      for (let i = 0; i < Math.min(10, textElements.length); i++) {
        const el = textElements[i];
        const styles = window.getComputedStyle(el);
        const text = el.textContent.trim();

        if (text.length > 0) {
          checks.push({
            text: text.substring(0, 50),
            color: styles.color,
            backgroundColor: styles.backgroundColor,
            fontSize: styles.fontSize
          });
        }
      }

      return checks;
    });

    console.log('Contrast Checks (sample):', contrastChecks.slice(0, 5));
  });
});
