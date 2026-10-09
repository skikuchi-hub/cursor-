#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
くらしプラス 別パターン（5種）生成
  python3 tools/build_variants.py
variants/v1〜v5/ に、共通の文言・下層ページを使いつつ、配色・書体・トップの構成・写真を変えたサイトを書き出す。
"""
import os, sys, re, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build as b

MAIN = b.ROOT
BASE_CSS = open(os.path.join(MAIN, "assets", "css", "style.css"), encoding="utf-8").read()

def base_css(tokens):
    """現行 CSS の :root をパターンのトークンに差し替えたものを土台にする"""
    css = re.sub(r':root\{.*?\n\}', tokens, BASE_CSS, count=1, flags=re.S)
    return css

VARIANTS = {}

def variant(name):
    def deco(fn):
        VARIANTS[name] = fn
        return fn
    return deco

def common_footer(r, cls=""):
    svc_links = "".join(f'<a href="{r}services/{x["code"]}.html">{x["name"]}</a>' for x in b.SERVICES)
    return f"""<footer class="site-footer {cls}">
  <div class="wrap">
    <div class="top">
      <div>
        <a class="brand" href="{r}index.html">{b.mark_svg()}<span class="word">{b.SITE['name']}</span></a>
        <p class="tag">{b.SITE['tagline']}<small>{b.SITE['company']}が提供する、暮らしの会員サービス</small></p>
      </div>
      <a class="btn btn-terra" href="{r}signup.html">お申し込みはこちら</a>
    </div>
    <div class="links">
      {svc_links}<span class="sep"></span>
      <a href="{r}index.html#faq">よくある質問</a>
      <a href="{r}signup.html">お申し込みについて</a>
      <a href="{r}contact.html">お問い合わせ</a>
      <a href="{r}login.html">会員ログイン</a>
    </div>
    <div class="copy">
      <span>© {b.SITE['company']}</span>
      <span><a href="{b.SITE['company_url']}" target="_blank" rel="noopener">会社情報</a>　<a href="{r}terms/index.html">利用規約</a>　<a href="{r}privacy.html">プライバシーポリシー</a>　<a href="{r}legal.html">特定商取引法に基づく表示</a></span>
    </div>
  </div>
</footer>
<script src="{r}assets/js/main.js?v={b.ver('assets/js/main.js')}"></script>
</body>
</html>
"""

def common_header(r, extra_cls=""):
    return f"""<header class="site-header {extra_cls}">
  <div class="wrap">
    <a class="brand" href="{r}index.html" aria-label="{b.SITE['name']} トップへ">{b.mark_svg()}<span class="word">{b.SITE['name']}</span></a>
    <button class="menu-btn" aria-label="メニュー" aria-expanded="false"><span></span><span></span><span></span></button>
    <nav class="nav">
      <a href="{r}index.html#services">サービス</a>
      <a href="{r}index.html#faq">よくある質問</a>
      <a href="{r}contact.html">お問い合わせ</a>
      <a href="{r}login.html">会員ログイン</a>
      <a class="cta" href="{r}signup.html">お申し込み</a>
    </nav>
  </div>
</header>
"""

def faq_html():
    return "\n".join(f'<details><summary>{b.esc(q)}</summary><div class="a">{b.esc(a)}</div></details>' for q, a in b.FAQ)

def svc_index_html(prefix="#svc-"):
    return "".join(f'<li><a href="{prefix}{s["code"]}"><span class="no">{s["no"]}</span><span class="name">{s.get("name_br", b.esc(s["name"]))}</span><i>→</i></a></li>' for s in b.SERVICES)

LEAD = "置き配の盗難、固定費の見直し、スマホや家電の故障、わずらわしい広告。暮らしのちいさな不安や困りごとを、まとめて支える会員サービスです。"
NOTE = 'お申し込みには販売パートナーの紹介コードが必要です。お持ちでない方は<a href="contact.html?kind=1">お問い合わせ</a>ください。'
STICKY = '<div class="sticky-cta"><span>初月から最大2ヶ月無料</span><a class="btn btn-terra btn-sm" href="signup.html">お申し込み</a></div>'

# ============================================================
# v1 静か × 上品
# ============================================================
@variant("v1")
def v1():
    tokens = ''':root{
  --bg:#FFFFFF; --sand:#F6F4F0; --sand-2:#EBE7E0; --ink:#2B2A28; --ink-2:#5B5955; --mute:#8F8C86;
  --line:#E8E4DD; --line-2:#D5D0C7; --terra:#4C5B73; --terra-2:#3A4759; --tint:#EEF0F4;
  --font:"Zen Kaku Gothic New","Hiragino Kaku Gothic ProN","Hiragino Sans",sans-serif;
  --serif:"Shippori Mincho","Hiragino Mincho ProN","Yu Mincho",serif;
  --en:"Jost",sans-serif; --max:1120px; --gut:clamp(20px,5vw,56px); --ease:cubic-bezier(.22,1,.36,1);
}'''
    css = base_css(tokens) + '''
/* ===== v1 静か×上品 ===== */
body{font-weight:400;letter-spacing:.04em;line-height:2.1}
h1,h2,h3{font-weight:500;letter-spacing:.06em}
.page-head h1,.v1-hero h1,.v1-sh h2,.trust h2,.closing h2{font-family:var(--serif);font-weight:500}
.btn{border-radius:2px;letter-spacing:.16em;font-size:13px;padding:17px 34px}
.btn-terra{background:var(--ink)}.btn-terra:hover{background:#000}
.nav a.cta{background:var(--ink);border-radius:2px}
.brand .word{font-family:var(--serif);font-weight:500;letter-spacing:.2em;font-size:20px}
.stamp{border-radius:2px;background:transparent;border:1px solid var(--line-2);color:var(--ink-2);padding:8px 14px}
.stamp::before{background:var(--ink-2)}
.v1-hero{position:relative;overflow:hidden}
.v1-hero .media{height:min(62vh,640px);overflow:hidden;background:var(--sand)}
.v1-hero .media img{width:100%;height:100%;object-fit:cover;object-position:center 30%}
.v1-hero .wrap{display:grid;grid-template-columns:1fr 1fr;gap:clamp(32px,6vw,96px);padding-top:clamp(40px,6vw,80px);padding-bottom:clamp(40px,6vw,80px);align-items:start}
.v1-hero h1{font-size:clamp(32px,3.8vw,52px);line-height:1.6;letter-spacing:.1em;font-weight:500}
.v1-hero .lead{color:var(--ink-2);font-size:14.5px;max-width:30em}
.v1-hero .card{display:flex;flex-direction:column;gap:20px;align-items:flex-start;padding-top:12px;border-top:1px solid var(--line-2)}
.v1-hero .card .btns{display:flex;gap:24px;align-items:center;flex-wrap:wrap}
@media (max-width:860px){
  .v1-hero .media{height:min(110vw,58svh)}
  .v1-hero .wrap{grid-template-columns:1fr;gap:20px;padding-top:28px}
  .v1-hero h1{font-size:clamp(28px,8vw,34px)}
  .v1-hero .card .btn{width:100%}
}
.v1-sh{margin-bottom:40px}.v1-sh h2{font-size:clamp(24px,2.8vw,34px);line-height:1.6}
.v1-sh .lbl{margin-bottom:16px}
.v1-worry{padding:clamp(72px,9vw,120px) 0}
.v1-worry .grid{display:grid;grid-template-columns:1fr 1fr;gap:clamp(40px,7vw,110px);align-items:center}
.v1-worry .photo{aspect-ratio:1/1;overflow:hidden}
.v1-worry .photo img{width:100%;height:100%;object-fit:cover}
.v1-worry ul{list-style:none;border-top:1px solid var(--line-2);margin-top:28px}
.v1-worry li{padding:16px 0;border-bottom:1px solid var(--line);font-size:15px;color:var(--ink)}
@media (max-width:860px){.v1-worry .grid{grid-template-columns:1fr}.v1-worry .photo{aspect-ratio:4/3}}
.v1-svcs{background:var(--sand);padding:clamp(72px,9vw,120px) 0}
.v1-svcs .intro{max-width:560px;margin-bottom:48px}
.v1-list{display:grid;gap:0;border-top:1px solid var(--line-2)}
.v1-item{display:grid;grid-template-columns:120px 1fr 1fr;gap:32px;padding:40px 0;border-bottom:1px solid var(--line-2);align-items:center;text-decoration:none;color:inherit}
.v1-item .no{font-family:var(--en);font-weight:300;font-size:30px;color:var(--terra)}
.v1-item h3{font-family:var(--serif);font-size:clamp(20px,2vw,26px);line-height:1.6;margin-bottom:8px;font-weight:500}
.v1-item .name{font-size:12px;letter-spacing:.14em;color:var(--mute);margin-bottom:12px}
.v1-item p{font-size:14px;color:var(--ink-2)}
.v1-item .photo{aspect-ratio:3/2;overflow:hidden}
.v1-item .photo img{width:100%;height:100%;object-fit:cover;transition:transform 1.2s var(--ease)}
.v1-item:hover .photo img{transform:scale(1.03)}
.v1-item .more{margin-top:16px;display:inline-block;font-size:12.5px;letter-spacing:.14em;border-bottom:1px solid var(--ink)}
@media (max-width:860px){.v1-item{grid-template-columns:1fr;gap:16px;padding:28px 0}.v1-item .no{font-size:22px}.v1-item .photo{order:-1}}
.trust{padding:clamp(80px,10vw,140px) 0}
.trust .media::after{background:rgba(255,255,255,.08)}
.trust .box{background:rgba(255,255,255,.96);max-width:560px}
.v1-faq{padding:clamp(72px,9vw,120px) 0}
.v1-faq .faq{max-width:820px;margin:0 auto}
.v1-faq .faq summary{font-family:var(--font);font-weight:500;font-size:15.5px}
.closing .inner{border-top:1px solid var(--line-2)}
.site-footer{background:#fff;border-top:1px solid var(--line-2)}
.site-footer .top .tag{font-family:var(--serif)}
'''
    body = f"""
<section class="v1-hero">
  <div class="media"><picture><source media="(max-width:860px)" srcset="assets/img/photo/hero-sp.jpg"><img src="assets/img/photo/hero.jpg" alt="" width="1800" height="1200" fetchpriority="high"></picture></div>
  <div class="wrap">
    <div>
      <div class="stamp">初月から<b>最大2ヶ月無料</b></div>
      <h1 style="margin-top:22px">毎日の「もしも」に、<br>ひとつ足す安心。</h1>
    </div>
    <div class="card">
      <p class="lead">{LEAD}</p>
      <div class="btns"><a class="btn btn-terra" href="signup.html">お申し込みはこちら</a><a class="tlink" href="contact.html">まずは相談する <i>→</i></a></div>
    </div>
  </div>
</section>
{STICKY}
<section class="v1-worry" id="intro"><div class="wrap"><div class="grid">
  <div class="photo rv"><img src="assets/img/photo/worry.jpg" alt="" loading="lazy" width="1200" height="1200"></div>
  <div class="rv"><div class="v1-sh"><span class="lbl">暮らしの困りごと</span><h2>こんな不安、<br>ありませんか。</h2></div>
    <p style="color:var(--ink-2);font-size:14.5px">大きな保険は重い。でも、何もしないのも不安。暮らしの「よくある困りごと」に、ちょうどいい安心をご用意しました。</p>
    <ul>{"".join(f"<li>{b.esc(w)}</li>" for w in b.WORRIES)}</ul></div>
</div></div></section>
<section class="v1-svcs" id="services"><div class="wrap">
  <div class="intro rv"><div class="v1-sh"><span class="lbl">サービス</span><h2>暮らしを支える、<br>5つのサービス</h2></div><p style="color:var(--ink-2);font-size:14.5px">家族の毎日に起こりやすい“困りごと”を、広く・やさしくカバーします。</p></div>
  <div class="v1-list">{"".join(f'''<a class="v1-item rv" id="svc-{s['code']}" href="services/{s['code']}.html"><span class="no">{s['no']}</span><div><div class="name">{b.esc(s['name'])}</div><h3>{s.get('copy_br', b.esc(s['copy']))}</h3><p>{b.esc(s['short'])}</p><span class="more">詳しく見る</span></div><div class="photo"><img src="assets/img/photo/svc-{s['code']}.jpg" alt="" loading="lazy" width="1200" height="900"></div></a>''' for s in b.SERVICES)}</div>
</div></section>
<section class="trust">
  <div class="media"><picture><source media="(max-width:760px)" srcset="assets/img/photo/trust-sp.jpg"><img src="assets/img/photo/trust.jpg" alt="" loading="lazy" width="1600" height="900"></picture></div>
  <div class="wrap"><div class="box rv"><span class="lbl">わたしたちの約束</span><h2>守られている安心は、<br>想像以上に心地いい。</h2><p>保険会社との正式提携と、実績あるグループ会社による運営体制のもと、安心してご利用いただけるサービスを提供しています。</p><div class="cta"><a class="btn btn-terra" href="signup.html">お申し込みはこちら</a></div></div></div>
</section>
<section class="v1-faq" id="faq"><div class="wrap"><div class="v1-sh rv" style="text-align:center"><span class="lbl">Q&amp;A</span><h2>よくあるご質問</h2></div><div class="faq rv">{faq_html()}</div></div></section>
<section class="closing"><div class="wrap"><div class="inner rv"><div><h2>不安を残さず、安心して<br>お申し込みいただけるように。</h2><p>不明点など遠慮なくご質問ください。ヘルプデスク（{b.SITE['hours_short']}）がお答えします。</p></div><div class="btns"><a class="btn btn-terra" href="signup.html">お申し込みはこちら</a><a class="btn btn-outline" href="contact.html">お問い合わせはこちら</a></div></div></div></section>
"""
    return dict(title="静か × 上品", fonts="https://fonts.googleapis.com/css2?family=Shippori+Mincho:wght@500;600&family=Zen+Kaku+Gothic+New:wght@400;500;700&family=Jost:wght@300;400&display=swap", css=css, body=body)

# ============================================================
# v2 高品質 × 信頼
# ============================================================
@variant("v2")
def v2():
    tokens = ''':root{
  --bg:#FFFFFF; --sand:#F3F5F8; --sand-2:#E3E8EF; --ink:#0F2A4A; --ink-2:#44546A; --mute:#8391A5;
  --line:#E1E6EE; --line-2:#C9D2DF; --terra:#0F2A4A; --terra-2:#0B1F38; --tint:#EEF2F8; --gold:#C9A227;
  --font:"Noto Sans JP","Hiragino Kaku Gothic ProN","Hiragino Sans",sans-serif; --serif:var(--font);
  --en:"Jost",sans-serif; --max:1200px; --gut:clamp(20px,5vw,56px); --ease:cubic-bezier(.22,1,.36,1);
}'''
    css = base_css(tokens) + '''
/* ===== v2 高品質×信頼 ===== */
body{font-weight:400;letter-spacing:.02em}
h1,h2,h3{font-weight:700;letter-spacing:.02em}
.btn{border-radius:4px;font-weight:700}
.btn-terra{background:var(--gold);color:var(--ink)}.btn-terra:hover{background:#B8911F;color:var(--ink)}
.nav a.cta{background:var(--gold);color:var(--ink);border-radius:4px;font-weight:700}
.brand .word{font-weight:700;letter-spacing:.1em}
.lbl{color:var(--gold)}.lbl::before{background:var(--gold)}
.stamp{background:var(--ink);color:#fff;border-radius:4px}.stamp::before{background:var(--gold)}
.v2-hero{position:relative;color:#fff;background:var(--ink);overflow:hidden}
.v2-hero .media{position:absolute;inset:0}
.v2-hero .media img{width:100%;height:100%;object-fit:cover;object-position:center 40%;opacity:.55}
.v2-hero .media::after{content:"";position:absolute;inset:0;background:linear-gradient(to right,rgba(15,42,74,.92) 0%,rgba(15,42,74,.7) 50%,rgba(15,42,74,.3) 100%)}
.v2-hero .wrap{position:relative;padding:clamp(72px,10vw,140px) var(--gut) clamp(56px,8vw,110px);max-width:var(--max)}
.v2-hero h1{color:#fff;font-size:clamp(34px,4.4vw,62px);line-height:1.4;max-width:14em}
.v2-hero .lead{color:rgba(255,255,255,.85);margin-top:26px;max-width:34em;font-size:15px}
.v2-hero .btns{display:flex;gap:14px;flex-wrap:wrap;margin-top:36px}
.v2-hero .btn-outline{color:#fff;border-color:rgba(255,255,255,.6)}
.v2-stats{background:#fff;border-bottom:1px solid var(--line)}
.v2-stats .wrap{display:grid;grid-template-columns:repeat(4,1fr);gap:0}
.v2-stats div{padding:26px 24px;border-left:1px solid var(--line)}
.v2-stats div:first-child{border-left:0}
.v2-stats b{display:block;font-family:var(--en);font-weight:400;font-size:30px;color:var(--ink);letter-spacing:.02em;line-height:1.1}
.v2-stats b small{font-family:var(--font);font-size:13px;font-weight:700;margin-left:4px}
.v2-stats span{font-size:12.5px;color:var(--mute);letter-spacing:.06em}
@media (max-width:860px){.v2-hero .media img{object-position:center top}.v2-stats .wrap{grid-template-columns:1fr 1fr;padding:0}.v2-stats div{padding:18px var(--gut)}.v2-stats div:nth-child(odd){border-left:0}.v2-stats div:nth-child(n+3){border-top:1px solid var(--line)}.v2-hero .btns .btn{width:100%}}
.v2-sh{margin-bottom:40px}.v2-sh h2{font-size:clamp(26px,3vw,38px);line-height:1.45}.v2-sh p{color:var(--ink-2);margin-top:14px;max-width:38em}
.v2-worry{padding:clamp(72px,9vw,120px) 0}
.v2-worry .grid{display:grid;grid-template-columns:1fr 1fr;gap:clamp(36px,6vw,96px);align-items:center}
.v2-worry .photo{border-radius:6px;overflow:hidden;aspect-ratio:6/5}.v2-worry .photo img{width:100%;height:100%;object-fit:cover}
.v2-worry ul{list-style:none;display:grid;gap:10px;margin-top:24px}
.v2-worry li{background:var(--sand);border-left:3px solid var(--gold);padding:14px 18px;font-size:14.5px;font-weight:500}
@media (max-width:860px){.v2-worry .grid{grid-template-columns:1fr}}
.v2-svcs{background:var(--sand);padding:clamp(72px,9vw,120px) 0}
.v2-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:20px}
.v2-card{background:#fff;border-radius:6px;overflow:hidden;text-decoration:none;color:inherit;display:flex;flex-direction:column;box-shadow:0 1px 0 var(--line);transition:transform .4s var(--ease),box-shadow .4s}
.v2-card:hover{transform:translateY(-3px);box-shadow:0 14px 34px rgba(15,42,74,.12)}
.v2-card .photo{aspect-ratio:3/2;overflow:hidden}.v2-card .photo img{width:100%;height:100%;object-fit:cover}
.v2-card .body{padding:24px 24px 26px;display:flex;flex-direction:column;flex:1}
.v2-card .no{font-family:var(--en);font-size:12px;letter-spacing:.2em;color:var(--gold)}
.v2-card h3{font-size:18px;margin:8px 0 6px}
.v2-card .copy{font-weight:700;color:var(--ink-2);font-size:14px;margin-bottom:8px}
.v2-card p{font-size:13.5px;color:var(--ink-2);flex:1}
.v2-card .more{margin-top:14px;font-size:12.5px;font-weight:700;color:var(--ink)}
.v2-card:first-child{grid-column:span 2}.v2-card:first-child .photo{aspect-ratio:2/1}
@media (max-width:960px){.v2-grid{grid-template-columns:1fr 1fr}.v2-card:first-child{grid-column:span 2}}
@media (max-width:600px){.v2-grid{grid-template-columns:1fr}.v2-card:first-child{grid-column:span 1}.v2-card:first-child .photo{aspect-ratio:3/2}}
.v2-why{padding:clamp(72px,9vw,120px) 0}
.v2-why .grid{display:grid;grid-template-columns:repeat(3,1fr);gap:40px;border-top:1px solid var(--line-2);padding-top:40px}
.v2-why h3{font-size:17px;margin:14px 0 8px}.v2-why p{font-size:14px;color:var(--ink-2)}
.v2-why .num{font-family:var(--en);font-size:36px;font-weight:300;color:var(--gold)}
@media (max-width:760px){.v2-why .grid{grid-template-columns:1fr;gap:28px}}
.trust{padding:0}
.trust .media{position:relative;aspect-ratio:16/7}.trust .media img{object-position:center 45%}
.trust .media::after{background:rgba(15,42,74,.45)}
.trust .wrap{position:absolute;inset:0;display:flex;align-items:center}
.trust .box{background:transparent;color:#fff;max-width:620px;padding:0 var(--gut)}
.trust h2,.trust p{color:#fff}.trust .lbl{color:var(--gold)}.trust .lbl::before{background:var(--gold)}
.trust .tlink{color:#fff;border-color:#fff}
@media (max-width:760px){.trust .media{aspect-ratio:4/5}.trust .wrap{position:absolute;padding:0}.trust .box{margin:0;padding:0 var(--gut)}}
.v2-faq{padding:clamp(72px,9vw,120px) 0}
.v2-faq .faq{max-width:860px;margin:0 auto}
.site-footer{background:var(--ink);color:rgba(255,255,255,.75)}
@media (max-width:860px){body.home .site-header{position:sticky;background:rgba(255,255,255,.94);backdrop-filter:blur(12px)}}
.site-footer .brand .word,.site-footer .top .tag,.site-footer .links a,.site-footer .copy a{color:#fff}
.site-footer .top .tag small,.site-footer .copy{color:rgba(255,255,255,.6)}
.site-footer .top,.site-footer .links{border-color:rgba(255,255,255,.18)}.site-footer .links .sep{background:rgba(255,255,255,.18)}
.site-footer .links a{border-color:rgba(255,255,255,.12)}
'''
    cards = "".join(f'''<a class="v2-card rv" id="svc-{s['code']}" href="services/{s['code']}.html"><div class="photo"><img src="assets/img/photo/svc-{s['code']}.jpg" alt="" loading="lazy" width="1200" height="900"></div><div class="body"><span class="no">SERVICE {s['no']}</span><h3>{b.esc(s['name'])}</h3><div class="copy">{b.esc(s['copy'])}</div><p>{b.esc(s['short'])}</p><span class="more">詳しく見る →</span></div></a>''' for s in b.SERVICES)
    body = f"""
<section class="v2-hero">
  <div class="media"><picture><source media="(max-width:860px)" srcset="assets/img/photo/hero-sp.jpg"><img src="assets/img/photo/hero.jpg" alt="" width="2000" height="1250" fetchpriority="high"></picture></div>
  <div class="wrap">
    <div class="stamp">初月から<b>最大2ヶ月無料</b></div>
    <h1 style="margin-top:24px">毎日の「もしも」に、<br>ひとつ足す安心。</h1>
    <p class="lead">{LEAD}</p>
    <div class="btns"><a class="btn btn-terra" href="signup.html">お申し込みはこちら</a><a class="btn btn-outline" href="contact.html">お問い合わせはこちら</a></div>
  </div>
</section>
<div class="v2-stats"><div class="wrap">
  <div><b>5<small>つ</small></b><span>暮らしを支えるサービス</span></div>
  <div><b>2<small>ヶ月</small></b><span>初月から最大2ヶ月無料</span></div>
  <div><b>0<small>円</small></b><span>解約金・違約金</span></div>
  <div><b>正式提携</b><span>保険会社との正式提携</span></div>
</div></div>
{STICKY}
<section class="v2-worry" id="intro"><div class="wrap"><div class="grid">
  <div class="rv"><div class="v2-sh"><span class="lbl">暮らしの困りごと</span><h2>こんな不安、ありませんか？</h2><p>大きな保険は重い。でも、何もしないのも不安。暮らしの「よくある困りごと」に、ちょうどいい安心をご用意しました。</p></div><ul>{"".join(f"<li>{b.esc(w)}</li>" for w in b.WORRIES)}</ul></div>
  <div class="photo rv"><img src="assets/img/photo/worry.jpg" alt="" loading="lazy" width="1200" height="1000"></div>
</div></div></section>
<section class="v2-svcs" id="services"><div class="wrap">
  <div class="v2-sh rv"><span class="lbl">サービス</span><h2>暮らしを支える、5つのサービス</h2><p>家族の毎日に起こりやすい“困りごと”を、広く・やさしくカバーします。暮らしの中で起こる“ちょっとした不安や困りごと”を、まとめてサポートする会員サービスです。</p></div>
  <div class="v2-grid">{cards}</div>
</div></section>
<section class="v2-why"><div class="wrap">
  <div class="v2-sh rv"><span class="lbl">選ばれる理由</span><h2>安心してお申し込みいただくために。</h2></div>
  <div class="grid">
    <div class="rv"><span class="num">01</span><h3>保険会社との正式提携</h3><p>補償サービスは引受保険会社との正式な提携のもとで提供。請求手続きもヘルプデスクがご案内します。</p></div>
    <div class="rv"><span class="num">02</span><h3>解約金・違約金なし</h3><p>最低利用期間の定めはありません。解約はお問い合わせフォームから、いつでも。</p></div>
    <div class="rv"><span class="num">03</span><h3>人が応えるヘルプデスク</h3><p>{b.SITE['hours']}に、使い方や補償の請求方法のご相談を承ります。</p></div>
  </div>
</div></section>
<section class="trust">
  <div class="media"><picture><source media="(max-width:760px)" srcset="assets/img/photo/trust-sp.jpg"><img src="assets/img/photo/trust.jpg" alt="" loading="lazy" width="1600" height="900"></picture></div>
  <div class="wrap"><div class="box rv"><span class="lbl">わたしたちの約束</span><h2>守られている安心は、<br>想像以上に心地いい。</h2><p>保険会社との正式提携と、実績あるグループ会社による運営体制のもと、安心してご利用いただけるサービスを提供しています。</p><div class="cta"><a class="btn btn-terra" href="signup.html">お申し込みはこちら</a><a class="tlink" href="contact.html">相談する <i>→</i></a></div></div></div>
</section>
<section class="v2-faq" id="faq"><div class="wrap"><div class="v2-sh rv" style="text-align:center"><span class="lbl">Q&amp;A</span><h2>よくあるご質問</h2></div><div class="faq rv">{faq_html()}</div></div></section>
<section class="closing"><div class="wrap"><div class="inner rv"><div><h2>不安を残さず、安心して<br>お申し込みいただけるように。</h2><p>不明点など遠慮なくご質問ください。ヘルプデスク（{b.SITE['hours_short']}）がお答えします。</p></div><div class="btns"><a class="btn btn-terra" href="signup.html">お申し込みはこちら</a><a class="btn btn-outline" href="contact.html">お問い合わせはこちら</a></div></div></div></section>
"""
    return dict(title="高品質 × 信頼", fonts="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700&family=Jost:wght@300;400&display=swap", css=css, body=body)

# ============================================================
# v3 安心 × 生活
# ============================================================
@variant("v3")
def v3():
    tokens = ''':root{
  --bg:#FFFDF9; --sand:#FFF4E6; --sand-2:#FFE6C7; --ink:#3B3330; --ink-2:#6B615B; --mute:#9C928A;
  --line:#F0E4D6; --line-2:#E3D2BE; --terra:#F08A3C; --terra-2:#D9772C; --tint:#FFF1E2; --green:#6DBE8C;
  --font:"Zen Maru Gothic","Hiragino Maru Gothic ProN","Hiragino Kaku Gothic ProN",sans-serif; --serif:var(--font);
  --en:"Nunito","Jost",sans-serif; --max:1160px; --gut:clamp(20px,5vw,56px); --ease:cubic-bezier(.22,1,.36,1);
}'''
    css = base_css(tokens) + '''
/* ===== v3 安心×生活 ===== */
body{font-weight:500;letter-spacing:.02em}
h1,h2,h3{font-weight:700;letter-spacing:.02em}
.btn{border-radius:999px;font-weight:700;box-shadow:0 6px 18px rgba(240,138,60,.22)}
.btn-outline{box-shadow:none}
.nav a.cta{border-radius:999px;font-weight:700}
.brand .word{font-weight:700;letter-spacing:.08em}
.stamp{border-radius:999px;background:#fff;border:2px solid var(--terra);color:var(--terra);font-weight:700}
.stamp::before{background:var(--terra)}
.v3-hero{background:var(--sand);overflow:hidden;position:relative}
.v3-hero::before{content:"";position:absolute;right:-10vw;top:-20vw;width:60vw;height:60vw;border-radius:50%;background:#fff;opacity:.6}
.v3-hero .wrap{position:relative;display:grid;grid-template-columns:1.05fr .95fr;gap:clamp(28px,5vw,72px);align-items:center;padding-top:clamp(40px,6vw,80px);padding-bottom:clamp(40px,6vw,80px)}
.v3-hero h1{font-size:clamp(32px,4.2vw,56px);line-height:1.45;margin-top:22px}
.v3-hero h1 em{font-style:normal;color:var(--terra)}
.v3-hero .lead{color:var(--ink-2);margin-top:22px;font-size:15px;max-width:30em}
.v3-hero .btns{display:flex;gap:14px;align-items:center;flex-wrap:wrap;margin-top:32px}
.v3-hero .photo{border-radius:32px 32px 32px 120px;overflow:hidden;aspect-ratio:4/3;box-shadow:0 20px 50px rgba(240,138,60,.18)}
.v3-hero .photo img{width:100%;height:100%;object-fit:cover}
@media (max-width:860px){.v3-hero .wrap{grid-template-columns:1fr;gap:22px;padding-top:24px}.v3-hero .photo{order:-1;aspect-ratio:1/1;border-radius:28px 28px 28px 90px}.v3-hero h1{font-size:clamp(28px,8vw,36px)}.v3-hero .btns .btn{width:100%}}
.v3-sh{text-align:center;margin-bottom:40px}.v3-sh h2{font-size:clamp(26px,3vw,38px);line-height:1.45}.v3-sh p{color:var(--ink-2);margin-top:14px}
.v3-sh .lbl{justify-content:center}
.v3-worry{padding:clamp(72px,9vw,120px) 0}
.v3-bubbles{display:grid;grid-template-columns:repeat(3,1fr);gap:18px;max-width:980px;margin:0 auto}
.v3-bubble{background:#fff;border:2px solid var(--line-2);border-radius:24px;padding:22px 24px;font-size:15px;font-weight:700;position:relative;color:var(--ink)}
.v3-bubble::after{content:"";position:absolute;left:34px;bottom:-12px;width:20px;height:20px;background:#fff;border-right:2px solid var(--line-2);border-bottom:2px solid var(--line-2);transform:rotate(45deg)}
.v3-bubble:nth-child(2n){margin-top:26px}
.v3-worry .photo{max-width:560px;margin:48px auto 0;border-radius:28px;overflow:hidden;aspect-ratio:6/5}.v3-worry .photo img{width:100%;height:100%;object-fit:cover}
@media (max-width:760px){.v3-bubbles{grid-template-columns:1fr}.v3-bubble:nth-child(2n){margin:0 0 0 24px}}
.v3-svcs{background:var(--sand);padding:clamp(72px,9vw,120px) 0}
.v3-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:22px}
.v3-card{background:#fff;border-radius:28px;overflow:hidden;display:grid;grid-template-columns:44% 1fr;text-decoration:none;color:inherit;transition:transform .4s var(--ease)}
.v3-card:hover{transform:translateY(-4px)}
.v3-card .photo{overflow:hidden}.v3-card .photo img{width:100%;height:100%;object-fit:cover}
.v3-card .body{padding:26px 26px 26px 24px}
.v3-card .no{display:inline-block;background:var(--tint);color:var(--terra);font-family:var(--en);font-weight:700;font-size:12px;letter-spacing:.14em;padding:4px 12px;border-radius:999px}
.v3-card h3{font-size:18px;margin:12px 0 6px}
.v3-card .copy{color:var(--terra);font-weight:700;font-size:14px;margin-bottom:8px}
.v3-card p{font-size:13.5px;color:var(--ink-2)}
.v3-card .more{display:inline-block;margin-top:12px;font-size:12.5px;font-weight:700;color:var(--ink)}
.v3-card:last-child{grid-column:span 2;grid-template-columns:30% 1fr}
@media (max-width:860px){.v3-grid{grid-template-columns:1fr}.v3-card,.v3-card:last-child{grid-column:span 1;grid-template-columns:1fr}.v3-card .photo{aspect-ratio:16/9}}
.v3-flow{padding:clamp(72px,9vw,120px) 0}
.v3-steps{display:grid;grid-template-columns:repeat(4,1fr);gap:18px;counter-reset:s}
.v3-step{background:var(--tint);border-radius:24px;padding:28px 24px;position:relative}
.v3-step::before{counter-increment:s;content:counter(s);display:inline-grid;place-items:center;width:36px;height:36px;border-radius:50%;background:var(--terra);color:#fff;font-family:var(--en);font-weight:700;margin-bottom:14px}
.v3-step h3{font-size:16.5px;margin-bottom:6px}.v3-step p{font-size:13.5px;color:var(--ink-2)}
@media (max-width:860px){.v3-steps{grid-template-columns:1fr 1fr}}@media (max-width:520px){.v3-steps{grid-template-columns:1fr}}
.trust{padding:clamp(64px,8vw,110px) 0}
.trust .media::after{background:rgba(59,51,48,.28)}
.trust .box{background:rgba(255,253,249,.96);border-radius:28px;max-width:540px}
.v3-faq{padding:clamp(72px,9vw,120px) 0;background:#fff}
.v3-faq .faq{max-width:860px;margin:0 auto}
.v3-faq .faq summary::before{color:var(--terra)}
.closing .inner{border-top:0;background:var(--sand);border-radius:28px;padding:clamp(32px,5vw,56px)}
.site-footer{background:var(--sand)}
'''
    cards = "".join(f'''<a class="v3-card rv" id="svc-{s['code']}" href="services/{s['code']}.html"><div class="photo"><img src="assets/img/photo/svc-{s['code']}.jpg" alt="" loading="lazy" width="1200" height="900"></div><div class="body"><span class="no">{s['no']}</span><h3>{b.esc(s['name'])}</h3><div class="copy">{b.esc(s['copy'])}</div><p>{b.esc(s['short'])}</p><span class="more">詳しく見る →</span></div></a>''' for s in b.SERVICES)
    body = f"""
<section class="v3-hero">
  <div class="wrap">
    <div>
      <div class="stamp">初月から<b>最大2ヶ月無料</b></div>
      <h1>毎日の「もしも」に、<br><em>ひとつ足す</em>安心。</h1>
      <p class="lead">{LEAD}</p>
      <div class="btns"><a class="btn btn-terra" href="signup.html">お申し込みはこちら</a><a class="tlink" href="contact.html">まずは相談する <i>→</i></a></div>
    </div>
    <div class="photo"><picture><source media="(max-width:860px)" srcset="assets/img/photo/hero-sp.jpg"><img src="assets/img/photo/hero.jpg" alt="" width="1800" height="1200" fetchpriority="high"></picture></div>
  </div>
</section>
{STICKY}
<section class="v3-worry" id="intro"><div class="wrap">
  <div class="v3-sh rv"><span class="lbl">暮らしの困りごと</span><h2>こんな不安、ありませんか？</h2><p>大きな保険は重い。でも、何もしないのも不安。<br class="pc">暮らしの「よくある困りごと」に、ちょうどいい安心をご用意しました。</p></div>
  <div class="v3-bubbles">{"".join(f'<div class="v3-bubble rv">{b.esc(w)}</div>' for w in b.WORRIES)}</div>
  <div class="photo rv"><img src="assets/img/photo/worry.jpg" alt="" loading="lazy" width="1200" height="1000"></div>
</div></section>
<section class="v3-svcs" id="services"><div class="wrap">
  <div class="v3-sh rv"><span class="lbl">サービス</span><h2>暮らしを支える、5つのサービス</h2><p>家族の毎日に起こりやすい“困りごと”を、広く・やさしくカバーします。</p></div>
  <div class="v3-grid">{cards}</div>
</div></section>
<section class="v3-flow"><div class="wrap">
  <div class="v3-sh rv"><span class="lbl">ご利用の流れ</span><h2>お申し込みは、4ステップ。</h2></div>
  <div class="v3-steps">
    <div class="v3-step rv"><h3>紹介コードを確認</h3><p>販売パートナーからお渡しした紹介コードをご用意ください。</p></div>
    <div class="v3-step rv"><h3>お申し込み</h3><p>お申込み窓口で紹介コードとお客様情報をご登録いただきます。</p></div>
    <div class="v3-step rv"><h3>決済登録</h3><p>メールまたはSMSで届く決済登録URLから、お支払い方法をご登録。</p></div>
    <div class="v3-step rv"><h3>ご利用開始</h3><p>各サービスのご案内と利用規約の控えをお送りします。</p></div>
  </div>
</div></section>
<section class="trust">
  <div class="media"><picture><source media="(max-width:760px)" srcset="assets/img/photo/trust-sp.jpg"><img src="assets/img/photo/trust.jpg" alt="" loading="lazy" width="1600" height="900"></picture></div>
  <div class="wrap"><div class="box rv"><span class="lbl">わたしたちの約束</span><h2>守られている安心は、<br>想像以上に心地いい。</h2><p>保険会社との正式提携と、実績あるグループ会社による運営体制のもと、安心してご利用いただけるサービスを提供しています。</p><div class="cta"><a class="btn btn-terra" href="signup.html">お申し込みはこちら</a></div></div></div>
</section>
<section class="v3-faq" id="faq"><div class="wrap"><div class="v3-sh rv"><span class="lbl">Q&amp;A</span><h2>よくあるご質問</h2></div><div class="faq rv">{faq_html()}</div></div></section>
<section class="closing"><div class="wrap"><div class="inner rv"><div><h2>不安を残さず、安心して<br>お申し込みいただけるように。</h2><p>不明点など遠慮なくご質問ください。ヘルプデスク（{b.SITE['hours_short']}）がお答えします。</p></div><div class="btns"><a class="btn btn-terra" href="signup.html">お申し込みはこちら</a><a class="btn btn-outline" href="contact.html">お問い合わせはこちら</a></div></div></div></section>
"""
    return dict(title="安心 × 生活", fonts="https://fonts.googleapis.com/css2?family=Zen+Maru+Gothic:wght@500;700&family=Nunito:wght@700;800&display=swap", css=css, body=body)

# ============================================================
# v4 原色 × 市区町村
# ============================================================
@variant("v4")
def v4():
    tokens = ''':root{
  --bg:#FFFFFF; --sand:#F2F4F6; --sand-2:#E2E6EA; --ink:#1A1A1A; --ink-2:#444; --mute:#777;
  --line:#DDE1E5; --line-2:#C2C8CE; --terra:#D7000F; --terra-2:#B3000C; --tint:#FFF0F0;
  --red:#D7000F; --blue:#0066CC; --yellow:#F5C400; --green:#009944; --orange:#F39800;
  --font:"Noto Sans JP","Hiragino Kaku Gothic ProN","Hiragino Sans",Meiryo,sans-serif; --serif:var(--font);
  --en:"Noto Sans JP",sans-serif; --max:1160px; --gut:clamp(16px,4vw,40px); --ease:cubic-bezier(.22,1,.36,1);
}'''
    css = base_css(tokens) + '''
/* ===== v4 原色×市区町村 ===== */
body{font-weight:400;letter-spacing:0;line-height:1.8;font-size:16px}
h1,h2,h3{font-weight:700;letter-spacing:0;line-height:1.4}
.btn{border-radius:6px;font-weight:700;font-size:15px;letter-spacing:.04em}
.btn-terra{background:var(--red)}.btn-terra:hover{background:var(--terra-2)}
.btn-outline{border:2px solid var(--ink);font-weight:700}
.site-header{background:#fff;border-bottom:4px solid var(--red);backdrop-filter:none}
.site-header .wrap{height:72px}
.brand .word{font-weight:900;letter-spacing:.04em;font-size:22px}
.brand .mark circle{fill:var(--red)}
.nav a{font-weight:700;color:var(--ink);font-size:14px}
.nav a.cta{background:var(--red);border-radius:6px}
.lbl{color:var(--ink);font-weight:700;font-size:13px}.lbl::before{width:6px;height:18px;background:var(--red)}
.stamp{border-radius:4px;background:var(--yellow);color:var(--ink);font-weight:900}.stamp::before{display:none}
.v4-hero .bar{background:var(--red);color:#fff;font-weight:700;font-size:14px;padding:10px 0}
.v4-hero .bar .wrap{display:flex;gap:24px;flex-wrap:wrap}
.v4-hero .main{display:grid;grid-template-columns:1fr 1fr;gap:0;align-items:stretch}
.v4-hero .text{padding:clamp(32px,5vw,72px) var(--gut);display:flex;flex-direction:column;justify-content:center;gap:20px;background:#fff}
.v4-hero h1{font-size:clamp(30px,3.8vw,50px);line-height:1.35}
.v4-hero h1 span{background:linear-gradient(transparent 60%,var(--yellow) 60%)}
.v4-hero .lead{color:var(--ink-2);font-size:15px;max-width:32em}
.v4-hero .btns{display:flex;gap:12px;flex-wrap:wrap}
.v4-hero .photo{position:relative;min-height:360px}
.v4-hero .photo img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}
.v4-hero .photo .tag{position:absolute;left:0;bottom:0;background:var(--blue);color:#fff;font-weight:700;padding:10px 16px;font-size:13px}
@media (max-width:860px){.v4-hero .main{grid-template-columns:1fr}.v4-hero .photo{min-height:0;aspect-ratio:16/10;order:-1}.v4-hero .btns .btn{width:100%}}
.v4-tiles{padding:clamp(28px,4vw,48px) 0 0}
.v4-tiles .grid{display:grid;grid-template-columns:repeat(5,1fr);gap:12px}
.v4-tile{display:flex;flex-direction:column;justify-content:space-between;min-height:150px;padding:18px 16px;border-radius:8px;color:#fff;text-decoration:none;font-weight:700;font-size:17px;line-height:1.35;transition:transform .3s var(--ease)}
.v4-tile:hover{transform:translateY(-3px)}
.v4-tile small{display:block;font-size:11.5px;font-weight:700;opacity:.9;margin-bottom:10px;letter-spacing:.1em}
.v4-tile i{font-style:normal;align-self:flex-end;font-size:20px}
.v4-tile.c1{background:var(--red)}.v4-tile.c2{background:var(--blue)}.v4-tile.c3{background:var(--green)}.v4-tile.c4{background:var(--orange)}.v4-tile.c5{background:#7B3FA0}
@media (max-width:960px){.v4-tiles .grid{grid-template-columns:repeat(3,1fr)}}@media (max-width:600px){.v4-tiles .grid{grid-template-columns:1fr 1fr}.v4-tile{min-height:120px;font-size:15px}}
.v4-sec{padding:clamp(56px,7vw,96px) 0}
.v4-sec h2{font-size:clamp(24px,2.8vw,34px);padding-left:16px;border-left:8px solid var(--red);line-height:1.3;margin-bottom:28px}
.v4-worry .grid{display:grid;grid-template-columns:1fr 1fr;gap:40px;align-items:start}
.v4-worry ul{list-style:none;display:grid;gap:8px}
.v4-worry li{background:var(--sand);padding:14px 18px 14px 52px;position:relative;font-weight:700;border-radius:4px}
.v4-worry li::before{content:"!";position:absolute;left:16px;top:12px;width:24px;height:24px;border-radius:50%;background:var(--red);color:#fff;text-align:center;line-height:24px;font-weight:900;font-size:14px}
.v4-worry .photo{border-radius:8px;overflow:hidden;aspect-ratio:6/5}.v4-worry .photo img{width:100%;height:100%;object-fit:cover}
@media (max-width:860px){.v4-worry .grid{grid-template-columns:1fr}}
.v4-svcs{background:var(--sand)}
.v4-list{display:grid;gap:14px}
.v4-row{display:grid;grid-template-columns:260px 1fr auto;gap:24px;align-items:center;background:#fff;border-radius:8px;overflow:hidden;text-decoration:none;color:inherit;border-left:10px solid var(--c)}
.v4-row .photo{aspect-ratio:4/3;overflow:hidden}.v4-row .photo img{width:100%;height:100%;object-fit:cover}
.v4-row .body{padding:18px 0}
.v4-row .no{display:inline-block;background:var(--c);color:#fff;font-weight:900;font-size:12px;padding:3px 10px;border-radius:4px;letter-spacing:.1em}
.v4-row h3{font-size:20px;margin:8px 0 4px}.v4-row .copy{font-weight:700;color:var(--c);font-size:14.5px}.v4-row p{font-size:14px;color:var(--ink-2);margin-top:6px}
.v4-row .go{padding:0 24px;font-weight:700;white-space:nowrap}
.v4-row:nth-child(1){--c:var(--red)}.v4-row:nth-child(2){--c:var(--blue)}.v4-row:nth-child(3){--c:var(--green)}.v4-row:nth-child(4){--c:var(--orange)}.v4-row:nth-child(5){--c:#7B3FA0}
@media (max-width:860px){.v4-row{grid-template-columns:1fr;gap:0;border-left:0;border-top:10px solid var(--c)}.v4-row .body{padding:16px 18px}.v4-row .go{padding:0 18px 16px}}
.v4-info .grid{display:grid;grid-template-columns:1fr 1fr;gap:24px}
.v4-box{border:2px solid var(--line-2);border-radius:8px;padding:24px}
.v4-box h3{font-size:18px;margin-bottom:10px;padding-bottom:10px;border-bottom:2px solid var(--yellow)}
.v4-box table{width:100%;border-collapse:collapse;font-size:14px}
.v4-box th,.v4-box td{text-align:left;padding:10px 6px;border-bottom:1px solid var(--line);vertical-align:top}
.v4-box th{width:34%;font-weight:700;color:var(--ink)}
@media (max-width:760px){.v4-info .grid{grid-template-columns:1fr}}
.trust{padding:0}
.trust .media{position:relative;aspect-ratio:16/6}.trust .media::after{background:rgba(0,0,0,.35)}
.trust .wrap{position:absolute;inset:0;display:flex;align-items:center}
.trust .box{background:#fff;border-radius:8px;max-width:560px;border-left:10px solid var(--blue)}
@media (max-width:760px){.trust .media{aspect-ratio:4/3}.trust .wrap{position:absolute;padding:0 var(--gut)}.trust .box{margin:0;padding:22px}}
.v4-faq .faq summary{font-weight:700;padding-left:44px}
.v4-faq .faq summary::before{background:var(--blue);color:#fff;width:26px;height:26px;border-radius:4px;text-align:center;line-height:26px;font-size:13px;font-weight:900;top:21px}
.v4-faq .faq .a::before{background:var(--red);color:#fff;width:26px;height:26px;border-radius:4px;text-align:center;line-height:26px;font-size:13px;font-weight:900}
.v4-faq .faq .a{padding-left:44px}
.closing .inner{border:0;background:var(--yellow);border-radius:8px;padding:clamp(28px,5vw,48px)}
.closing .btn-outline{background:#fff}
.site-footer{background:#fff;border-top:4px solid var(--red)}
@media (max-width:860px){body.home .site-header{position:sticky;background:#fff}}
.sticky-cta .btn{background:var(--red)}
'''
    tiles = "".join(f'<a class="v4-tile c{i+1}" href="#svc-{s["code"]}"><span><small>SERVICE {s["no"]}</small>{s.get("name_br", b.esc(s["name"]))}</span><i>→</i></a>' for i, s in enumerate(b.SERVICES))
    rows = "".join(f'''<a class="v4-row rv" id="svc-{s['code']}" href="services/{s['code']}.html"><div class="photo"><img src="assets/img/photo/svc-{s['code']}.jpg" alt="" loading="lazy" width="1200" height="900"></div><div class="body"><span class="no">SERVICE {s['no']}</span><h3>{b.esc(s['name'])}</h3><div class="copy">{b.esc(s['copy'])}</div><p>{b.esc(s['short'])}</p></div><span class="go">詳しく見る →</span></a>''' for s in b.SERVICES)
    body = f"""
<section class="v4-hero">
  <div class="bar"><div class="wrap"><span>▶ 初月から最大2ヶ月無料</span><span>▶ 解約金・違約金なし</span><span>▶ 紹介コードでお申し込み</span></div></div>
  <div class="main">
    <div class="text">
      <div class="stamp">初月から最大2ヶ月無料</div>
      <h1>毎日の<span>「もしも」</span>に、<br>ひとつ足す安心。</h1>
      <p class="lead">{LEAD}</p>
      <div class="btns"><a class="btn btn-terra" href="signup.html">お申し込みはこちら</a><a class="btn btn-outline" href="contact.html">お問い合わせ</a></div>
    </div>
    <div class="photo"><picture><source media="(max-width:860px)" srcset="assets/img/photo/hero-sp.jpg"><img src="assets/img/photo/hero.jpg" alt="" width="2000" height="1100" fetchpriority="high"></picture><span class="tag">暮らしを支える会員サービス</span></div>
  </div>
</section>
<section class="v4-tiles"><div class="wrap"><div class="grid">{tiles}</div></div></section>
{STICKY}
<section class="v4-sec v4-worry" id="intro"><div class="wrap"><h2>こんな不安、ありませんか？</h2><div class="grid">
  <ul class="rv">{"".join(f"<li>{b.esc(w)}</li>" for w in b.WORRIES)}</ul>
  <div class="photo rv"><img src="assets/img/photo/worry.jpg" alt="" loading="lazy" width="1200" height="1000"></div>
</div></div></section>
<section class="v4-sec v4-svcs" id="services"><div class="wrap"><h2>暮らしを支える、5つのサービス</h2><div class="v4-list">{rows}</div></div></section>
<section class="v4-sec v4-info"><div class="wrap"><h2>お申し込み・お問い合わせのご案内</h2><div class="grid">
  <div class="v4-box rv"><h3>お申し込みについて</h3><table><tr><th>対象</th><td>販売パートナーの紹介コードをお持ちの方</td></tr><tr><th>無料期間</th><td>初月から最大2ヶ月</td></tr><tr><th>お支払い</th><td>クレジットカード／キャリア決済</td></tr><tr><th>解約</th><td>いつでも可。解約金なし</td></tr></table><p style="margin-top:14px"><a class="btn btn-terra btn-sm" href="signup.html">お申し込みの流れを見る</a></p></div>
  <div class="v4-box rv"><h3>ヘルプデスク</h3><table><tr><th>受付時間</th><td>{b.SITE['hours']}</td></tr><tr><th>お問い合わせ</th><td>フォームは24時間受付。3営業日以内にご返信します</td></tr><tr><th>電話</th><td>{b.SITE['tel']}</td></tr></table><p style="margin-top:14px"><a class="btn btn-outline btn-sm" href="contact.html">お問い合わせフォーム</a></p></div>
</div></div></section>
<section class="trust">
  <div class="media"><picture><source media="(max-width:760px)" srcset="assets/img/photo/trust-sp.jpg"><img src="assets/img/photo/trust.jpg" alt="" loading="lazy" width="1600" height="900"></picture></div>
  <div class="wrap"><div class="box rv"><span class="lbl">わたしたちの約束</span><h2>守られている安心は、想像以上に心地いい。</h2><p>保険会社との正式提携と、実績あるグループ会社による運営体制のもと、安心してご利用いただけるサービスを提供しています。</p></div></div>
</section>
<section class="v4-sec v4-faq" id="faq"><div class="wrap"><h2>よくあるご質問</h2><div class="faq rv">{faq_html()}</div></div></section>
<section class="closing"><div class="wrap"><div class="inner rv"><div><h2>不安を残さず、安心してお申し込みいただけるように。</h2><p>不明点など遠慮なくご質問ください。</p></div><div class="btns"><a class="btn btn-terra" href="signup.html">お申し込みはこちら</a><a class="btn btn-outline" href="contact.html">お問い合わせはこちら</a></div></div></div></section>
"""
    return dict(title="原色 × 市区町村", fonts="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;700;900&display=swap", css=css, body=body)

# ============================================================
# v5 シンプル × 化粧品サイト
# ============================================================
@variant("v5")
def v5():
    tokens = ''':root{
  --bg:#FFFFFF; --sand:#F7F2EE; --sand-2:#EFE6E0; --ink:#2A2626; --ink-2:#6A615E; --mute:#9E938F;
  --line:#EDE6E1; --line-2:#DCD2CB; --terra:#2A2626; --terra-2:#000; --tint:#F7F2EE; --rose:#D9B8AE;
  --font:"Noto Sans JP","Hiragino Kaku Gothic ProN","Hiragino Sans",sans-serif; --serif:"Cormorant Garamond",serif;
  --en:"Jost",sans-serif; --max:1120px; --gut:clamp(20px,5vw,56px); --ease:cubic-bezier(.22,1,.36,1);
}'''
    css = base_css(tokens) + '''
/* ===== v5 シンプル×化粧品 ===== */
body{font-weight:300;letter-spacing:.06em;line-height:2.1;font-size:14.5px}
h1,h2,h3{font-weight:400;letter-spacing:.12em}
.btn{border-radius:0;letter-spacing:.24em;font-weight:400;font-size:12px;padding:18px 40px}
.btn-terra{background:var(--ink)}.btn-terra:hover{background:#000}
.btn-outline{border-color:var(--ink)}
.nav a{letter-spacing:.2em;font-size:12px;font-weight:400}
.nav a.cta{background:var(--ink);border-radius:0;letter-spacing:.2em}
.brand .word{font-family:var(--en);font-weight:400;letter-spacing:.34em;font-size:15px;text-transform:uppercase}
.brand .mark{display:none}
.lbl{font-family:var(--en);letter-spacing:.3em;text-transform:uppercase;color:var(--mute);font-size:10.5px}.lbl::before{display:none}
.stamp{border-radius:0;background:transparent;border:1px solid var(--line-2);color:var(--ink-2);font-weight:400;letter-spacing:.14em;font-size:12px}.stamp::before{display:none}
.v5-hero{position:relative;text-align:center;overflow:hidden}
.v5-hero .media{height:min(70vh,720px);overflow:hidden;background:var(--sand)}
.v5-hero .media img{width:100%;height:100%;object-fit:cover;object-position:center 30%}
.v5-hero .wrap{padding:clamp(40px,6vw,72px) var(--gut) clamp(24px,4vw,48px);max-width:760px}
.v5-hero .en{font-family:var(--en);font-size:11px;letter-spacing:.4em;text-transform:uppercase;color:var(--mute);display:block;margin-bottom:22px}
.v5-hero h1{font-size:clamp(26px,3.2vw,40px);line-height:1.8;letter-spacing:.18em;font-weight:300}
.v5-hero .lead{margin:24px auto 0;max-width:30em;color:var(--ink-2)}
.v5-hero .btns{display:flex;gap:16px;justify-content:center;flex-wrap:wrap;margin-top:34px}
@media (max-width:860px){.v5-hero .media{height:min(115vw,62svh)}.v5-hero h1{font-size:clamp(22px,6.4vw,28px);letter-spacing:.14em}.v5-hero .btns .btn{width:100%}}
.v5-sh{text-align:center;margin-bottom:clamp(36px,5vw,56px)}
.v5-sh h2{font-size:clamp(22px,2.6vw,32px);line-height:1.7;letter-spacing:.2em;font-weight:300}
.v5-sh .lbl{display:block;margin-bottom:18px}
.v5-sh p{color:var(--ink-2);margin-top:16px;max-width:36em;margin-left:auto;margin-right:auto}
.v5-worry{padding:clamp(80px,10vw,140px) 0}
.v5-worry .grid{display:grid;grid-template-columns:5fr 7fr;gap:clamp(40px,8vw,120px);align-items:center}
.v5-worry .photo{aspect-ratio:4/5;overflow:hidden}.v5-worry .photo img{width:100%;height:100%;object-fit:cover}
.v5-worry ul{list-style:none;border-top:1px solid var(--line-2);margin-top:30px}
.v5-worry li{padding:18px 0;border-bottom:1px solid var(--line);text-align:left;letter-spacing:.08em}
@media (max-width:860px){.v5-worry .grid{grid-template-columns:1fr}.v5-worry .photo{max-width:70%;margin:0 auto}}
.v5-products{padding:clamp(80px,10vw,140px) 0;background:var(--sand)}
.v5-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:clamp(20px,3vw,40px)}
.v5-prod{text-decoration:none;color:inherit;text-align:center}
.v5-prod .photo{aspect-ratio:1/1;overflow:hidden;background:#fff}
.v5-prod .photo img{width:100%;height:100%;object-fit:cover;transition:transform 1.2s var(--ease)}
.v5-prod:hover .photo img{transform:scale(1.04)}
.v5-prod .no{display:block;font-family:var(--en);font-size:10.5px;letter-spacing:.3em;color:var(--mute);margin:22px 0 10px}
.v5-prod h3{font-size:16px;letter-spacing:.14em;font-weight:400}
.v5-prod .copy{margin-top:8px;color:var(--ink-2);font-size:13px;letter-spacing:.08em}
.v5-prod .more{display:inline-block;margin-top:14px;font-family:var(--en);font-size:10.5px;letter-spacing:.3em;text-transform:uppercase;border-bottom:1px solid var(--ink);padding-bottom:3px}
.v5-grid .v5-prod:nth-child(4),.v5-grid .v5-prod:nth-child(5){grid-column:span 1}
@media (min-width:861px){.v5-grid{grid-template-columns:repeat(6,1fr)}.v5-prod{grid-column:span 2}.v5-prod:nth-child(4){grid-column:2/4}.v5-prod:nth-child(5){grid-column:4/6}}
@media (max-width:860px){.v5-grid{grid-template-columns:1fr 1fr;gap:28px 16px}.v5-prod h3{font-size:14.5px}}
.v5-phil{padding:clamp(80px,10vw,140px) 0;text-align:center}
.v5-phil .wrap{max-width:720px}
.v5-phil h2{font-family:var(--serif);font-size:clamp(28px,4vw,48px);font-weight:400;letter-spacing:.08em;line-height:1.3;margin-bottom:28px}
.v5-phil p{color:var(--ink-2)}
.trust{padding:0}
.trust .media{position:relative;aspect-ratio:16/7}.trust .media::after{background:rgba(255,255,255,.12)}
.trust .wrap{position:absolute;inset:0;display:flex;align-items:center;justify-content:center}
.trust .box{background:rgba(255,255,255,.92);max-width:520px;text-align:center}
.trust .box .lbl{justify-content:center}
.trust h2{font-weight:300;letter-spacing:.16em;font-size:clamp(20px,2.4vw,28px)}
.trust .cta{justify-content:center}
@media (max-width:760px){.trust .media{aspect-ratio:4/5}.trust .wrap{position:absolute;padding:0 var(--gut)}.trust .box{margin:0}}
.v5-faq{padding:clamp(80px,10vw,140px) 0}
.v5-faq .faq{max-width:760px;margin:0 auto}
.v5-faq .faq summary{font-weight:400;letter-spacing:.08em;font-size:14.5px}
.closing .inner{border:0;text-align:center;grid-template-columns:1fr;gap:28px;padding-top:0}
.closing h2{font-weight:300;letter-spacing:.16em}
.closing .btns{align-items:center;flex-direction:row;justify-content:center;gap:16px}
.closing p{margin-left:auto;margin-right:auto}
.site-footer{background:#fff;border-top:1px solid var(--line)}
.site-footer .top .tag{font-weight:300;letter-spacing:.14em}
.site-footer .links a{letter-spacing:.14em;font-size:12px}
.sticky-cta span{letter-spacing:.14em;font-weight:400}
'''
    prods = "".join(f'''<a class="v5-prod rv" id="svc-{s['code']}" href="services/{s['code']}.html"><div class="photo"><img src="assets/img/photo/svc-{s['code']}.jpg" alt="" loading="lazy" width="1200" height="1200"></div><span class="no">NO. {s['no']}</span><h3>{b.esc(s['name'])}</h3><div class="copy">{b.esc(s['copy'])}</div><span class="more">View</span></a>''' for s in b.SERVICES)
    body = f"""
<section class="v5-hero">
  <div class="media"><picture><source media="(max-width:860px)" srcset="assets/img/photo/hero-sp.jpg"><img src="assets/img/photo/hero.jpg" alt="" width="1800" height="1200" fetchpriority="high"></picture></div>
  <div class="wrap">
    <span class="en">Kurashi Plus — Life support membership</span>
    <h1>毎日の「もしも」に、<br>ひとつ足す安心。</h1>
    <p class="lead">{LEAD}</p>
    <div class="btns"><a class="btn btn-terra" href="signup.html">お申し込み</a><a class="btn btn-outline" href="contact.html">お問い合わせ</a></div>
    <p style="margin-top:22px"><span class="stamp">初月から最大2ヶ月無料</span></p>
  </div>
</section>
{STICKY}
<section class="v5-worry" id="intro"><div class="wrap"><div class="grid">
  <div class="photo rv"><img src="assets/img/photo/worry.jpg" alt="" loading="lazy" width="1200" height="1500"></div>
  <div class="rv"><div class="v5-sh" style="text-align:left"><span class="lbl">Everyday</span><h2>こんな不安、<br>ありませんか。</h2><p style="margin-left:0">大きな保険は重い。でも、何もしないのも不安。暮らしの「よくある困りごと」に、ちょうどいい安心をご用意しました。</p></div><ul>{"".join(f"<li>{b.esc(w)}</li>" for w in b.WORRIES)}</ul></div>
</div></div></section>
<section class="v5-products" id="services"><div class="wrap">
  <div class="v5-sh rv"><span class="lbl">Services</span><h2>暮らしを支える、<br class="sp">5つのサービス</h2><p>家族の毎日に起こりやすい“困りごと”を、広く・やさしくカバーします。</p></div>
  <div class="v5-grid">{prods}</div>
</div></section>
<section class="v5-phil"><div class="wrap rv"><span class="lbl" style="display:block;margin-bottom:22px">Philosophy</span><h2>Small, everyday peace.</h2><p>置き配盗難や家電の突然の故障、Wi-Fi接続機器のトラブル、スマホの広告表示など。暮らしの中で起こる“ちょっとした不安や困りごと”を、まとめてサポートする会員サービスです。</p></div></section>
<section class="trust">
  <div class="media"><picture><source media="(max-width:760px)" srcset="assets/img/photo/trust-sp.jpg"><img src="assets/img/photo/trust.jpg" alt="" loading="lazy" width="1600" height="900"></picture></div>
  <div class="wrap"><div class="box rv"><span class="lbl">Promise</span><h2>守られている安心は、<br>想像以上に心地いい。</h2><p>保険会社との正式提携と、実績あるグループ会社による運営体制のもと、安心してご利用いただけるサービスを提供しています。</p><div class="cta"><a class="btn btn-terra" href="signup.html">お申し込み</a></div></div></div>
</section>
<section class="v5-faq" id="faq"><div class="wrap"><div class="v5-sh rv"><span class="lbl">FAQ</span><h2>よくあるご質問</h2></div><div class="faq rv">{faq_html()}</div></div></section>
<section class="closing"><div class="wrap"><div class="inner rv"><div><h2>不安を残さず、安心して<br>お申し込みいただけるように。</h2><p>不明点など遠慮なくご質問ください。ヘルプデスク（{b.SITE['hours_short']}）がお答えします。</p></div><div class="btns"><a class="btn btn-terra" href="signup.html">お申し込み</a><a class="btn btn-outline" href="contact.html">お問い合わせ</a></div></div></div></section>
"""
    return dict(title="シンプル × 化粧品サイト", fonts="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@300;400;500&family=Cormorant+Garamond:wght@400;500&family=Jost:wght@300;400&display=swap", css=css, body=body)

# ============================================================
# 生成
# ============================================================
def build_variant(name):
    spec = VARIANTS[name]()
    root = os.path.join(MAIN, "variants", name)
    os.makedirs(os.path.join(root, "assets", "css"), exist_ok=True)
    os.makedirs(os.path.join(root, "assets", "js"), exist_ok=True)
    os.makedirs(os.path.join(root, "assets", "img"), exist_ok=True)
    # 共有アセット
    for f in ["assets/js/main.js", "config.js", "assets/img/mark.svg", "assets/img/logo.svg", "assets/img/favicon.png", "assets/img/icon-180.png", "assets/img/og.png"]:
        src = os.path.join(MAIN, f)
        if os.path.exists(src):
            shutil.copy(src, os.path.join(root, f))
    with open(os.path.join(root, "assets", "css", "style.css"), "w", encoding="utf-8") as f:
        f.write(spec["css"])
    # build モジュールをこのパターン向けに差し替え
    b.ROOT = root
    b.FONTS = spec["fonts"]
    b.header = lambda depth: common_header(b.rel(depth))
    b.footer = lambda depth: common_footer(b.rel(depth))
    def build_index():
        b.page("index.html", "", b.SITE["desc"], spec["body"], 0, body_class="home")
    b.build_index = build_index
    b.build_index(); b.build_services(); b.build_terms(); b.build_privacy(); b.build_legal(); b.build_signup(); b.build_contact(); b.build_auth(); b.build_404()
    b.ROOT = MAIN
    return spec["title"]

def build_gallery(titles):
    items = "".join(f'<a class="item" href="{k}/index.html"><img src="{k}/shot-pc.jpg" alt="" loading="lazy"><div><span>{k.upper()}</span><b>{t}</b></div></a>' for k, t in titles.items())
    html = f"""<!DOCTYPE html><html lang="ja"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>くらしプラス デザイン案 5パターン</title>
<link rel="icon" href="../assets/img/favicon.png"><meta name="robots" content="noindex">
<style>body{{margin:0;font-family:"Hiragino Kaku Gothic ProN","Hiragino Sans",sans-serif;background:#F4F4F2;color:#222;padding:40px 24px}}h1{{font-size:20px;margin:0 0 6px}}p{{color:#666;font-size:13px;margin:0 0 28px}}.g{{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:20px}}.item{{display:block;background:#fff;border-radius:10px;overflow:hidden;text-decoration:none;color:inherit;box-shadow:0 1px 3px rgba(0,0,0,.08)}}.item img{{display:block;width:100%;aspect-ratio:4/3;object-fit:cover;object-position:top}}.item div{{padding:14px 16px}}.item span{{display:block;font-size:11px;letter-spacing:.2em;color:#999}}.item b{{display:block;font-size:16px;margin-top:4px}}</style></head>
<body><h1>くらしプラス デザイン案 5パターン</h1><p>文言・下層ページは共通。配色・書体・トップの構成・写真を変えています。</p><div class="g">{items}</div>
<p style="margin-top:28px"><a href="../index.html">現行サイトへ</a></p></body></html>"""
    with open(os.path.join(MAIN, "variants", "index.html"), "w", encoding="utf-8") as f:
        f.write(html)

if __name__ == "__main__":
    names = sys.argv[1:] or list(VARIANTS)
    titles = {}
    for n in names:
        titles[n] = build_variant(n)
        print("built", n, titles[n])
    if not sys.argv[1:]:
        build_gallery(titles)
