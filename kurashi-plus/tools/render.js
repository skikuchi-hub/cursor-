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
  const fonts = '<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700&family=Shippori+Mincho+B1:wght@600;700&family=Outfit:wght@300;500&display=swap" rel="stylesheet">';

  // アイコン類
  for (const [name, size] of [['favicon.png', 64], ['icon-180.png', 180], ['icon-192.png', 192], ['icon-512.png', 512]]) {
    await page.setViewportSize({ width: size, height: size });
    await page.setContent(`<html><body style="margin:0;background:transparent">${mark.replace('width="120" height="120"', `width="${size}" height="${size}"`)}</body></html>`);
    await page.screenshot({ path: path.join(img, name), omitBackground: true, clip: { x: 0, y: 0, width: size, height: size }, scale: 'css' });
  }

  // 横ロゴ PNG（透過）
  await page.setViewportSize({ width: 420, height: 120 });
  await page.setContent(`<html><head>${fonts}</head><body style="margin:0;background:transparent">
    <div style="display:flex;align-items:center;gap:14px;height:120px;font-family:'Shippori Mincho B1','Noto Sans JP',serif">
      ${mark.replace('width="120" height="120"', 'width="96" height="96"')}
      <div style="line-height:1"><div style="font-size:42px;font-weight:700;color:#141D1C;letter-spacing:.08em">くらしプラス</div>
      <div style="font-family:'Outfit',sans-serif;font-size:13px;font-weight:500;color:#A8873A;letter-spacing:.42em;margin-top:8px">KURASHI+</div></div>
    </div></body></html>`);
  await page.waitForTimeout(1200);
  await page.screenshot({ path: path.join(img, 'logo.png'), omitBackground: true, clip: { x: 0, y: 0, width: 420, height: 120 }, scale: 'css' });

  // OG 画像 1200x630
  await page.setViewportSize({ width: 1200, height: 630 });
  await page.setContent(`<html><head>${fonts}</head><body style="margin:0">
    <div style="width:1200px;height:630px;background:linear-gradient(135deg,#F5F1E8 0%,#DCE8E4 100%);display:flex;align-items:center;justify-content:center;font-family:'Shippori Mincho B1','Noto Sans JP',serif;position:relative;overflow:hidden">
      <div style="position:absolute;right:-120px;top:-120px;width:520px;height:520px;border-radius:50%;background:#F1E7CF"></div>
      <div style="position:relative;display:flex;align-items:center;gap:40px">
        ${mark.replace('width="120" height="120"', 'width="220" height="220"')}
        <div style="line-height:1.2">
          <div style="font-size:84px;font-weight:700;color:#141D1C;letter-spacing:.08em">くらしプラス</div>
          <div style="font-family:'Outfit',sans-serif;font-size:22px;font-weight:500;color:#A8873A;letter-spacing:.5em;margin:6px 0 22px">KURASHI+</div>
          <div style="font-family:'Noto Sans JP',sans-serif;font-size:28px;color:#3B4746;letter-spacing:.06em">毎日の「もしも」に、ひとつ足す安心。</div>
        </div>
      </div>
    </div></body></html>`);
  await page.waitForTimeout(1200);
  await page.screenshot({ path: path.join(img, 'og.png'), clip: { x: 0, y: 0, width: 1200, height: 630 }, scale: 'css' });

  // ページのスクリーンショット（確認用）
  const pages = ['index.html', 'services/okihai.html', 'services/kumamori.html', 'terms/okihai.html', 'contact.html', 'login.html', 'mypage.html', 'legal.html', 'privacy.html'];
  for (const vp of [{ w: 1280, name: 'pc' }, { w: 390, name: 'sp' }]) {
    const p = await ctx.newPage();
    await p.setViewportSize({ width: vp.w, height: 900 });
    for (const f of pages) {
      if (f === 'mypage.html') {
        await p.goto('file://' + path.join(root, 'login.html'));
        await p.evaluate(() => sessionStorage.setItem('kp_user', JSON.stringify({ email: 'demo@example.com', name: 'デモ 太郎 様' })));
      }
      await p.goto('file://' + path.join(root, f));
      await p.waitForTimeout(900);
      await p.evaluate(() => document.querySelectorAll('.rv').forEach(e => { e.style.transition = 'none'; e.classList.add('in'); }));
      await p.waitForTimeout(300);
      await p.screenshot({ path: path.join(out, `${vp.name}-${f.replace(/[\/]/g, '_')}.png`), fullPage: true });
    }
    await p.close();
  }
  await browser.close();
  console.log('rendered');
})().catch(e => { console.error(e); process.exit(1); });
