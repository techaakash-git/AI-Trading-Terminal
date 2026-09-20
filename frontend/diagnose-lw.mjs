import { chromium } from 'playwright';

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const events = [];

  page.on('pageerror', e => events.push(`PAGEERROR: ${e.message}`));
  page.on('console', msg => events.push(`CONSOLE[${msg.type()}]: ${msg.text().slice(0, 300)}`));

  // Capture chart config response
  page.on('response', async resp => {
    if (resp.url().includes('/api/chart/config')) {
      events.push(`CHART_CONFIG: ${resp.status()}`);
      try {
        const body = await resp.json();
        const cfg = body.config?.[0];
        if (cfg) {
          const series = cfg.series ?? [];
          events.push(`SERIES: ${series.length} items, types=${series.map(s => s.type).join(',')}`);
          // Check if Histogram exists
          const hasHistogram = series.some(s => s.type === 'Histogram');
          events.push(`HAS_HISTOGRAM: ${hasHistogram}`);
        }
      } catch (e) {
        events.push(`CONFIG_PARSE_FAIL: ${e.message}`);
      }
    }
  });

  await page.goto('http://localhost:3000', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(2000);

  // Switch to Lightweight charts
  await page.locator('button:has-text("Lightweight")').click();
  await page.waitForTimeout(5000);

  // Take a screenshot of the chart area
  const chartFrame = page.locator('.chart-frame, .market-chart, [class*="chart"]').first();
  if (await chartFrame.count() > 0) {
    await chartFrame.screenshot({ path: 'screenshot-lw-after-fix.png' });
    events.push('SCREENSHOT_SAVED: screenshot-lw-after-fix.png');
  } else {
    events.push('NO_CHART_FRAME_FOUND');
  }

  // Check if canvas exists
  const html = await page.content();
  events.push(`PAGE_HAS_CANVAS: ${html.includes('canvas')}`);
  events.push(`PAGE_HAS_SVG: ${html.includes('svg')}`);
  events.push(`PAGE_LENGTH: ${html.length}`);

  // Check for lightweight-charts data
  events.push(`LW_CHART_SCRIPT: ${html.includes('lightweight-charts')}`);

  console.log('\n=== EVENTS ===');
  events.forEach(e => console.log(e));
  await browser.close();
})();
