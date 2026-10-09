// ロゴ PNG・OG 画像・確認用スクリーンショットを Playwright(Chromium) で生成する
//   node tools/render.js <siteRoot> <outDir>
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

(async () => {
  const root = path.resolve(process.argv[2] || '.');
  const out = path.resolve(process.argv[3] || 'shots');
  fs.mkdirSync(out, { recursive: true });
  const img = path.join(root, 'assets', 'img');
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM || undefined });
  const ctx = await browser.newContext({ deviceScaleFactor: 2 });
  const page = await ctx.newPage();

  const mark = fs.readFileSync(path.join(img, 'mark.svg'), 'utf8');
  const fonts = '<link href="https://fonts.googleapis.com/css2?family=Zen+Old+Mincho:wght@400;500&family=Zen+Kaku+Gothic+New:wght@400;500;700&family=Jost:wght@300;400&display=swap" rel="stylesheet">';

  // アイコン類
  for (const [name, size] of [['favicon.png', 64], ['icon-180.png', 180], ['icon-192.png', 192], ['icon-512.png', 512]]) {
    await page.setViewportSize({ width: size, height: size });
    await page.setContent(`<html><body style="margin:0;background:transparent">${mark.replace('width="120" height="120"', `width="${size}" height="${size}"`)}</body></html>`);
    await page.screenshot({ path: path.join(img, name), omitBackground: true, clip: { x: 0, y: 0, width: size, height: size }, scale: 'css' });
  }

  // 横ロゴ PNG（透過）
  await page.setViewportSize({ width: 420, height: 120 });
  await page.setContent(`<html><head>${fonts}</head><body style="margin:0;background:transparent">
    <div style="display:flex;align-items:center;gap:14px;height:120px;font-family:'Zen Kaku Gothic New',sans-serif">
      ${mark.replace('width="120" height="120"', 'width="72" height="72"')}
      <div style="line-height:1"><div style="font-family:'Zen Old Mincho',serif;font-size:40px;font-weight:500;color:#1B2430;letter-spacing:.2em">くらしプラス</div><div style="font-family:'Jost',sans-serif;font-size:11px;font-weight:400;color:#8A94A3;letter-spacing:.32em;margin-top:10px">KURASHI PLUS — LIFE SUPPORT MEMBERSHIP</div></div>
    </div></body></html>`);
  await page.waitForTimeout(1200);
  await page.screenshot({ path: path.join(img, 'logo.png'), omitBackground: true, clip: { x: 0, y: 0, width: 420, height: 120 }, scale: 'css' });

  // OG 画像 1200x630
  await page.setViewportSize({ width: 1200, height: 630 });
  await page.setContent(`<html><head>${fonts}</head><body style="margin:0">
    <div style="width:1200px;height:630px;background:#FFFFFF;display:flex;align-items:center;font-family:'Zen Kaku Gothic New',sans-serif;position:relative;overflow:hidden">
      <img src="file://${path.join(img,'photo','hero.jpg')}" style="position:absolute;right:0;top:0;width:560px;height:630px;object-fit:cover">
      <div style="position:relative;padding-left:88px;line-height:1.2">
        <div style="font-family:'Jost',sans-serif;font-size:13px;letter-spacing:.3em;color:#2A5BD7;margin-bottom:30px">LIFE SUPPORT MEMBERSHIP</div><div style="font-family:'Zen Old Mincho',serif;font-size:54px;font-weight:400;color:#1B2430;letter-spacing:.12em;line-height:1.6">毎日の「もしも」に、<br>ひとつ足す安心。</div><div style="font-size:16px;font-weight:500;color:#4A5563;margin-top:30px;letter-spacing:.14em">くらしプラス｜株式会社WST</div>
      </div>
    </div></body></html>`);
  await page.waitForTimeout(1200);
  await page.screenshot({ path: path.join(img, 'og.png'), clip: { x: 0, y: 0, width: 1200, height: 630 }, scale: 'css' });

  // ページのスクリーンショット（確認用）
  const pages = ['index.html', 'services/okihai.html', 'services/lifecost.html', 'terms/lifecost.html', 'signup.html', 'contact.html', 'login.html', 'mypage.html', 'legal.html', 'privacy.html'];
  for (const vp of [{ w: 1280, name: 'pc' }, { w: 390, name: 'sp' }]) {
    const p = await ctx.newPage();
    await p.setViewportSize({ width: vp.w, height: 900 });
    for (const f of pages) {
      if (f === 'mypage.html') {
        await p.goto('file://' + path.join(root, 'login.html'));
        await p.evaluate(() => sessionStorage.setItem('kp_user', JSON.stringify({ email: 'demo@example.com', name: 'デモ 太郎 様' })));
      }
      await p.goto('file://' + path.join(root, f));
      await p.evaluate(() => document.querySelectorAll('img[loading="lazy"]').forEach(i => { i.loading = 'eager'; }));
      await p.evaluate(() => Promise.all(Array.from(document.images).map(i => i.complete ? 1 : new Promise(r => { i.onload = i.onerror = r; }))));
      await p.waitForTimeout(1200);
      await p.evaluate(async () => { for (let y = 0; y < document.body.scrollHeight; y += 600) { window.scrollTo(0, y); await new Promise(r => setTimeout(r, 60)); } window.scrollTo(0, 0); });
      await p.waitForTimeout(900);
      await p.evaluate(() => document.querySelectorAll('.rv').forEach(e => { e.style.transition = 'none'; e.classList.add('in'); }));
      await p.waitForTimeout(300);
      await p.screenshot({ path: path.join(out, `${vp.name}-${f.replace(/[\/]/g, '_')}.png`), fullPage: true });
    }
    await p.close();
  }
  // ファーストビューのみ（iPhone 14 相当 390x844 / PC 1280x800）
  for (const vp of [{ w: 390, h: 844, name: 'sp-fv' }, { w: 1280, h: 800, name: 'pc-fv' }]) {
    const p = await ctx.newPage();
    await p.setViewportSize({ width: vp.w, height: vp.h });
    await p.goto('file://' + path.join(root, 'index.html'));
    await p.waitForTimeout(1500);
    await p.evaluate(() => document.querySelectorAll('.rv').forEach(e => { e.style.transition = 'none'; e.classList.add('in'); }));
    await p.screenshot({ path: path.join(out, vp.name + '.png') });
    if (vp.name === 'sp-fv') { await p.evaluate(() => window.scrollTo(0, 1400)); await p.waitForTimeout(800); await p.screenshot({ path: path.join(out, 'sp-scrolled.png') }); }
    await p.close();
  }
  await browser.close();
  console.log('rendered');
})().catch(e => { console.error(e); process.exit(1); });
