// 各パターンのトップを撮影  node tools/render_variants.js <siteRoot> <outDir>
const { chromium } = require('playwright'); const path = require('path'); const fs = require('fs');
(async () => {
  const root = path.resolve(process.argv[2] || '.'); const out = path.resolve(process.argv[3] || 'shots-variants'); fs.mkdirSync(out, { recursive: true });
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM || undefined });
  for (const v of ['v1', 'v2', 'v3', 'v4', 'v5']) {
    for (const vp of [{ w: 1280, h: 800, name: 'pc' }, { w: 390, h: 844, name: 'sp' }]) {
      const ctx = await browser.newContext({ deviceScaleFactor: 1 }); const p = await ctx.newPage();
      await p.setViewportSize({ width: vp.w, height: vp.h });
      await p.goto('file://' + path.join(root, 'variants', v, 'index.html')); await p.waitForTimeout(1500);
      await p.evaluate(() => document.querySelectorAll('img[loading="lazy"]').forEach(i => { i.loading = 'eager'; }));
      await p.evaluate(() => Promise.all(Array.from(document.images).map(i => i.complete ? 1 : new Promise(r => { i.onload = i.onerror = r; }))));
      await p.screenshot({ path: path.join(out, `${v}-${vp.name}-fv.png`) });
      await p.evaluate(async () => { for (let y = 0; y < document.body.scrollHeight; y += 600) { window.scrollTo(0, y); await new Promise(r => setTimeout(r, 50)); } window.scrollTo(0, 0); });
      await p.evaluate(() => document.querySelectorAll('.rv').forEach(e => { e.style.transition = 'none'; e.classList.add('in'); }));
      await p.waitForTimeout(400);
      await p.screenshot({ path: path.join(out, `${v}-${vp.name}-full.png`), fullPage: true });
      if (vp.name === 'pc') { await p.setViewportSize({ width: 1280, height: 960 }); await p.evaluate(() => window.scrollTo(0, 0)); await p.waitForTimeout(300); await p.screenshot({ path: path.join(root, 'variants', v, 'shot-pc.png') }); }
      await ctx.close();
    }
    console.log('rendered', v);
  }
  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
