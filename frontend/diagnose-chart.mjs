import { chromium } from 'playwright';
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const events = [];
  page.on('pageerror', e => events.push(`PAGEERROR: ${e.message}`));
  page.on('console', msg => events.push(`CONSOLE[${msg.type()}]: ${msg.text().slice(0, 500)}`));
  page.on('response', resp => {
    if (resp.url().includes('/api/chart/config')) {
      events.push(`CHART_CONFIG: ${resp.status()} ${resp.url()}`);
      resp.text().then(t => {
        try {
          const j = JSON.parse(t);
          const cfg = j.config?.[0];
          if (cfg) {
            events.push(`CONFIG_SHAPE: chart=${!!cfg.chart}, series=${cfg.series?.length}, types=${cfg.series?.map(s => s.type).join(',')}`);
            cfg.series?.forEach((s, i) => events.push(`SERIES ${i}: type=${s.type}, data=${Array.isArray(s.data) ? s.data.length : 'NOT_ARRAY'}, options=${!!s.options}`));
          } else {
            events.push(`CONFIG_NULL_OR_EMPTY: ${t.slice(0, 300)}`);
          }
        } catch (e) {
          events.push(`CONFIG_PARSE_FAIL: ${e.message}`);
        }
      });
    }
  });
  await page.goto('http://localhost:3000', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(3000);
  await page.locator('button:has-text("Lightweight")').click();
  await page.waitForTimeout(5000);
  const html = await page.locator('.chart-frame').innerHTML();
  console.log(`LW frame has canvas: ${html.includes('canvas')}`);
  console.log(`LW frame has svg: ${html.includes('svg')}`);
  console.log(`LW frame html length: ${html.length}`);
  console.log(`LW frame first 500 chars: ${html.slice(0, 500)}`);
  console.log('\n=== EVENTS ===');
  events.forEach(e => console.log(e));
  await page.screenshot({ path: 'screenshot-lw-diagnose.png' });
  await browser.close();
})();
