#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
くらしプラス（KURASHI+）サイト生成スクリプト
  python3 tools/build.py
サイト直下に index.html / services/*.html / terms/*.html / privacy.html などを書き出す。
文言を直すときはこのファイル（と tools/terms_raw/*.txt）を直して再実行する。
"""
import os, re, html

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SITE = {
    "name": "くらしプラス",
    "en": "KURASHI+",
    "tagline": "毎日の「もしも」に、ひとつ足す安心。",
    "desc": "くらしプラスは、置き配補償・Wi-Fi接続機器補償・ギフ活・広告ブロック・家電保証の5つのサービスから、必要なものだけを月額で選べる株式会社WSTのライフサポートサービスです。",
    "company": "株式会社WST",
    "rep": "石原 里基",
    "zip": "〒815-0041",
    "addr": "福岡県福岡市南区野間1-1-2 サンシャインシティビル野間5F",
    "email": "info@wst-inc.jp",
    "hours": "平日12:00〜18:00（土日祝日・年末年始を除く）",
    "hours_short": "平日12:00〜18:00、土日祝日・年末年始を除く",
    "price": "1,330",
    "price_tax": "1,463",
    "effective": "2026年4月1日",
}

# ---------- アイコン（線画 SVG） ----------
ICONS = {
    "okihai": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3 10.5 12 4l9 6.5"/><path d="M5 9.5V20h14V9.5"/><rect x="9" y="13" width="6" height="5" rx="1"/><path d="M12 13v5"/></svg>',
    "wifi": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="7" y="2.5" width="10" height="19" rx="2"/><path d="M11 18.5h2"/><path d="M8.5 9.5a5 5 0 0 1 7 0"/><path d="M10.3 11.6a2.5 2.5 0 0 1 3.4 0"/><circle cx="12" cy="13.8" r=".6" fill="currentColor"/></svg>',
    "gifukatsu": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="8" width="18" height="13" rx="2"/><path d="M3 12h18"/><path d="M12 8v13"/><path d="M12 8c-2-3-6-3-6-1s4 1 6 1Zm0 0c2-3 6-3 6-1s-4 1-6 1Z"/></svg>',
    "kumamori": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3 5 6v5c0 4.5 3 8.2 7 9.5 4-1.3 7-5 7-9.5V6l-7-3Z"/><path d="M9 12l2 2 4-4"/></svg>',
    "kaden": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="3" width="16" height="18" rx="2"/><circle cx="12" cy="13" r="4"/><path d="M8 7h.01M11 7h.01"/><path d="M14.5 10.5l-5 5"/></svg>',
}

SERVICES = [
    {
        "code": "okihai", "no": "01",
        "name": "置き配補償",
        "tag": "盗難補償",
        "short": "置き配で届いた荷物や自宅内の持ち物が盗まれたときに、1事故あたり最大30万円まで補償。",
        "lead": "玄関前に置いてもらった荷物が無くなった。自宅や物置から持ち物が盗まれた。そんな「まさか」のときに、引受保険会社から保険金をお支払いするサービスです。名前は「置き配補償」ですが、自宅内の盗難も補償の対象です。",
        "points": [
            "置き配の荷物も、自宅・物置・車庫内の持ち物も対象",
            "1事故あたり最大30万円まで補償（免責金額0円）",
            "ご本人だけでなく、同居のご家族も被保険者に",
            "警察への被害届と専用WEBフォームで、かんたん請求",
        ],
        "detail": [
            ("補償の対象", "日本国内で、ご自宅の敷地内の指定場所（玄関前・置き配バッグ・宅配ボックス・車庫・物置など）に配達業者が非対面で届けた荷物、およびご自宅や敷地内の施錠された物置・車庫に収容されている個人用の動産（金銭を含む）の盗難が対象です。"),
            ("補償金額", "1事故あたり30万円を上限に、動産は再調達価額、貴金属等は時価額（1個・1組ごとに30万円、1事故50万円まで）、金銭は20万円までを限度にお支払いします。免責金額はありません。"),
            ("対象外となる主なもの", "自動車・原動機付自転車、有価証券やクレジットカード等、動植物、業務用の商品や設備、紛失・置き忘れ、火災や自然災害に伴う盗難、地震・噴火・津波による損害など。詳しくは利用規約をご確認ください。"),
            ("保険金の請求", "盗難に気づいたらすぐに警察へ被害届を提出し、受理後に引受保険会社所定のWEBフォームから申請します。審査のうえ、引受保険会社からご本人へ直接お振込みします。"),
        ],
        "terms": "okihai",
    },
    {
        "code": "wifi", "no": "02",
        "name": "Wi-Fi接続機器補償",
        "tag": "スマホ・端末補償",
        "short": "スマホ・タブレット・ノートPC・ゲーム機・イヤホンなどの故障・破損・盗難を、修理費用最大10万円まで補償。",
        "lead": "お持ちのスマートフォンやタブレット、ノートパソコン、携帯ゲーム機、ワイヤレスイヤホン、スマートウォッチなどの無線通信端末が、故障（水濡れを含む）・外装破損・盗難で使えなくなったときに、修理費用または再購入費用を補償します。",
        "points": [
            "スマホだけでなく、タブレット・ノートPC・ゲーム機・イヤホン・スマートウォッチも対象",
            "修理できる場合は最大10万円、修理できない場合は最大2.5万円を補償",
            "水濡れによる故障、画面などの外装破損、盗難もカバー",
            "同居のご家族（2親等以内）と別居の未婚のお子さまも対象",
        ],
        "detail": [
            ("補償の対象", "ご本人が所有し個人で使う無線通信端末のうち、日本国内で発売されたメーカー正規品が対象です。偶然の事故による故障（水濡れ含む）・外装破損・盗難（警察に盗難届が受理されたもの）で使用不能になった場合の修理費用または再購入費用を補償します。"),
            ("補償金額", "修理可能な場合は1事故あたり10万円、修理不能な場合は1事故あたり2.5万円を上限に、免責金額5,000円を差し引いた額をお支払いします。お支払いは1年間に1回までです。"),
            ("対象外となる主なもの", "SIMカード・充電器などの付属品、加入時点で正常に動作していない端末、購入から1年以内のメーカー保証対象の故障、発売から3年を超えた端末の自然故障、紛失、日本国外での事故など。詳しくは利用規約をご確認ください。"),
            ("補償対象端末の登録", "初回の事故発生時に補償対象端末を登録し、以降は登録した端末が補償対象となります。修理不能で買い替えた場合は、新しい端末が対象になります。"),
        ],
        "terms": "wifi",
    },
    {
        "code": "gifukatsu", "no": "03",
        "name": "ギフ活",
        "tag": "優待・クーポン",
        "short": "グルメ・レジャー・ショッピング・旅行など全国の優待クーポンを、ご本人とご家族で使い放題。",
        "lead": "「ギフ活」は、会員様とそのご家族（配偶者・二親等以内のご親族）がご利用いただける福利厚生サービスです。グルメ、レジャー、ショッピング、旅行など幅広いジャンルのクーポン・優待・割引を、専用サイトからいつでもご利用いただけます。",
        "points": [
            "飲食店・ショッピング・レジャー施設など全国約85,000店舗で使える優待",
            "最大90%OFF以上のプレミアムクーポンも",
            "ご本人・配偶者・二親等以内のご親族まで利用可能",
            "専用サイトにログインするだけ。スマホからいつでも",
        ],
        "detail": [
            ("サービス内容", "お申し込み後に発行されるIDとパスワードでギフ活サイトにログインし、掲載されているクーポン・優待・割引をご利用いただけます。個々のクーポンの内容・利用条件・有効期間はギフ活サイトの記載をご確認ください。"),
            ("ご利用いただける方", "会員ご本人、配偶者の方、ご本人および配偶者の二親等以内のご親族がご利用になれます。"),
            ("ご注意", "クーポン等の譲渡・転売、営利目的での利用はできません。各施設のご利用にあたっては、施設ごとの利用規約に従ってください。"),
        ],
        "terms": "gifukatsu",
    },
    {
        "code": "kumamori", "no": "04",
        "name": "クマモリ 広告ブロック",
        "tag": "広告ブロック・セキュリティ",
        "short": "動画やアプリのわずらわしい広告をブロック。フィッシング詐欺サイトやマルウェアサイトからも守ります。",
        "lead": "広告ブロックアプリ「クマモリ」で、ブラウザ上だけでなくアプリ内の広告もすっきり。フィッシング詐欺サイトやマルウェアサイトのブロック機能も搭載しているので、ご家族のスマホも安心してお使いいただけます。",
        "points": [
            "YouTube やポータルサイト、アプリ内の広告をブロック",
            "フィッシング詐欺サイト・マルウェアサイトへのアクセスを遮断",
            "広告を読み込まないから、ページ表示が速く通信量も節約",
            "1契約で最大3台の端末にインストール可能",
        ],
        "detail": [
            ("サービス内容", "スマートフォン・タブレット等にアプリをインストールして使う広告ブロックサービスです。お申し込み後にご案内するライセンスでアプリを有効化してください。"),
            ("ご注意", "広告の表示仕様は各サービス・アプリの都合で変更されることがあり、将来にわたってすべての広告のブロックを保証するものではありません。対応OS・端末はアプリの案内をご確認ください。"),
        ],
        "terms": "kumamori",
    },
    {
        "code": "kaden", "no": "05",
        "name": "家電保証",
        "tag": "家電の故障補償",
        "short": "ご自宅の家電が故障したときの修理費用を補償。メーカー保証が切れたあとも安心です。",
        "lead": "エアコンや冷蔵庫、洗濯機、テレビなど、ご自宅で使っている家電製品が突然故障したときの修理費用を補償します。メーカー保証が切れた製品でも、急な出費を抑えて修理できます。",
        "points": [
            "ご自宅で使用している家電製品の自然故障による修理費用を補償",
            "メーカー保証が終了したあとの故障でも対象",
            "修理の手配から費用のお支払いまでをサポート",
            "対象製品・上限金額・免責事項は利用規約をご確認ください",
        ],
        "detail": [
            ("サービス内容", "ご自宅で使用している対象家電製品に自然故障が発生した場合に、修理費用を補償するサービスです。対象製品の品目、1回あたり・年間の補償上限、製造年数などの条件は利用規約で定めます。"),
            ("ご注意", "落下・水没などの外的要因による故障、消耗品の交換、購入から一定期間内のメーカー保証対象の故障などは対象外となる場合があります。詳しくは利用規約をご確認ください。"),
        ],
        "terms": "kaden",
    },
]

FAQ = [
    ("5つ全部に申し込まないといけませんか？", "いいえ。必要なサービスだけ1つから選べます。あとから追加・解約することもできます。"),
    ("料金はいくらですか？", f"各サービスとも月額{SITE['price']}円（税抜・税込{SITE['price_tax']}円）です。初期費用や解約金はありません。キャンペーン適用時は、その内容に従って減額・免除されることがあります。"),
    ("支払い方法は？", "クレジットカード決済またはキャリア決済（お申込みの方法により当社が指定します）に対応しています。"),
    ("最低利用期間や解約金はありますか？", "ありません。いつでも解約できます。解約は手続き完了を確認した月の末日に反映され、月途中の解約でも日割り計算は行いません。"),
    ("家族も使えますか？", "サービスによって異なります。置き配補償は同居のご家族、Wi-Fi接続機器補償は同居の2親等以内のご家族と別居の未婚のお子さま、ギフ活は配偶者と二親等以内のご親族がご利用いただけます。"),
    ("補償（保険金）の請求はどうすればいいですか？", "置き配補償・Wi-Fi接続機器補償は、盗難の場合は警察へ被害届を提出のうえ、引受保険会社所定のWEBフォームから申請します。審査後、引受保険会社からご本人へ直接お振込みします。詳しくは各サービスページと利用規約をご覧ください。"),
    ("法人でも申し込めますか？", "補償系サービス（置き配補償・Wi-Fi接続機器補償・家電保証）は個人のお客様が対象です。法人でのご利用についてはお問い合わせください。"),
    ("お問い合わせの受付時間は？", f"ヘルプデスクは{SITE['hours']}です。お問い合わせフォームは24時間受け付けています。"),
]

# ---------- レイアウト ----------
def rel(depth):
    return "../" * depth

def head(title, desc, depth, extra=""):
    r = rel(depth)
    full = f"{title}｜{SITE['name']}" if title else f"{SITE['name']}（{SITE['en']}）｜{SITE['tagline']}"
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{html.escape(full)}</title>
<meta name="description" content="{html.escape(desc)}">
<meta property="og:title" content="{html.escape(full)}">
<meta property="og:description" content="{html.escape(desc)}">
<meta property="og:type" content="website">
<meta property="og:image" content="{r}assets/img/og.png">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="{r}assets/img/favicon.png" type="image/png">
<link rel="apple-touch-icon" href="{r}assets/img/icon-180.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@300;400;500;700&family=Shippori+Mincho+B1:wght@500;600;700&family=Outfit:wght@200;300;400;500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{r}assets/css/style.css">
<script src="{r}config.js"></script>
{extra}
</head>
<body>
"""

def mark_svg(cls="mark"):
    return f'''<svg class="{cls}" viewBox="0 0 120 120" aria-hidden="true"><defs><linearGradient id="gm" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#1F6B66"/><stop offset="1" stop-color="#0F3D3A"/></linearGradient></defs><rect x="6" y="6" width="108" height="108" rx="30" fill="url(#gm)"/><path d="M60 28 L24 58 H34 V88 a4 4 0 0 0 4 4 H82 a4 4 0 0 0 4-4 V58 H96 Z" fill="none" stroke="#fff" stroke-width="7" stroke-linejoin="round" stroke-linecap="round"/><rect x="55" y="56" width="10" height="28" rx="3" fill="#D4B466"/><rect x="46" y="65" width="28" height="10" rx="3" fill="#D4B466"/></svg>'''

def header(depth):
    r = rel(depth)
    return f"""<header class="site-header">
  <div class="wrap">
    <a class="brand" href="{r}index.html" aria-label="{SITE['name']} トップへ">{mark_svg()}<span class="word">{SITE['name']}<small>{SITE['en']}</small></span></a>
    <button class="menu-btn" aria-label="メニュー" aria-expanded="false"><span></span><span></span><span></span></button>
    <nav class="nav">
      <a href="{r}index.html#services">サービス</a>
      <a href="{r}index.html#features">選ばれる理由</a>
      <a href="{r}index.html#price">料金</a>
      <a href="{r}index.html#faq">よくある質問</a>
      <a href="{r}contact.html">お問い合わせ</a>
      <a class="btn btn-primary btn-sm" href="{r}login.html">会員ログイン</a>
    </nav>
  </div>
</header>
"""

def footer(depth):
    r = rel(depth)
    svc_links = "".join(f'<li><a href="{r}services/{s["code"]}.html">{s["name"]}</a></li>' for s in SERVICES)
    return f"""<footer class="site-footer">
  <div class="big" aria-hidden="true">くらしプラス</div>
  <div class="wrap">
    <div class="cols">
      <div>
        <a class="brand" href="{r}index.html">{mark_svg()}<span class="word">{SITE['name']}<small>{SITE['en']}</small></span></a>
        <p>{SITE['tagline']}<br>運営：{SITE['company']}<br>{SITE['zip']} {SITE['addr']}<br>ヘルプデスク：{SITE['hours']}</p>
      </div>
      <div>
        <h4>Services</h4>
        <ul>{svc_links}</ul>
      </div>
      <div>
        <h4>Support / Legal</h4>
        <ul>
          <li><a href="{r}index.html#faq">よくある質問</a></li>
          <li><a href="{r}contact.html">お問い合わせ</a></li>
          <li><a href="{r}login.html">会員ログイン</a></li>
          <li><a href="{r}terms/index.html">利用規約</a></li>
          <li><a href="{r}privacy.html">プライバシーポリシー</a></li>
          <li><a href="{r}legal.html">特定商取引法に基づく表記</a></li>
        </ul>
      </div>
    </div>
    <div class="copy"><span>© {SITE['company']} All rights reserved.</span><span>{SITE['en']} — {SITE['tagline']}</span></div>
  </div>
</footer>
<script src="{r}assets/js/main.js"></script>
</body>
</html>
"""

def page(path, title, desc, body, depth=0, extra=""):
    out = head(title, desc, depth, extra) + header(depth) + body + footer(depth)
    full = os.path.join(ROOT, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(out)
    print("wrote", path)

def svc_card(s, depth=0):
    r = rel(depth)
    return f"""<a class="svc-card rv" href="{r}services/{s['code']}.html">
  <span class="no">{s['no']} / 05</span>
  <div class="art"><div class="svc-icon">{ICONS[s['code']]}</div></div>
  <span class="tag">{s['tag']}</span>
  <h3>{s['name']}</h3>
  <p>{s['short']}</p>
  <span class="more">くわしく見る <i>{ARROW}</i></span>
</a>"""

ARROW = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M13 5l7 7-7 7"/></svg>'

# ---------- トップ ----------
HERO_ART = """<svg viewBox="0 0 560 560" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
<defs>
  <linearGradient id="hg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#1F6B66"/><stop offset="1" stop-color="#0F3D3A"/></linearGradient>
  <linearGradient id="gold" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#E2C77A"/><stop offset="1" stop-color="#B08E3C"/></linearGradient>
  <radialGradient id="soft" cx="50%" cy="50%" r="50%"><stop offset="0" stop-color="#DCE8E4"/><stop offset="1" stop-color="#DCE8E4" stop-opacity="0"/></radialGradient>
  <filter id="sh" x="-20%" y="-20%" width="140%" height="140%"><feDropShadow dx="0" dy="18" stdDeviation="16" flood-color="#0F3D3A" flood-opacity=".16"/></filter>
</defs>
<circle cx="280" cy="280" r="250" fill="url(#soft)"/>
<g class="ring"><circle cx="280" cy="280" r="236" fill="none" stroke="#C2A14F" stroke-width="1" stroke-dasharray="2 10" opacity=".8"/></g>
<g class="ring r2"><circle cx="280" cy="280" r="196" fill="none" stroke="#1F6B66" stroke-width="1" stroke-dasharray="1 7" opacity=".55"/></g>
<circle cx="280" cy="280" r="156" fill="#FBF9F4" stroke="#E6DFCF"/>
<!-- 家 -->
<g filter="url(#sh)">
  <path d="M280 182 L186 262 V352 a12 12 0 0 0 12 12 H362 a12 12 0 0 0 12-12 V262 Z" fill="#fff" stroke="url(#hg)" stroke-width="3"/>
  <path d="M170 270 L280 176 L390 270" fill="none" stroke="url(#hg)" stroke-width="10" stroke-linecap="round" stroke-linejoin="round"/>
  <rect x="258" y="300" width="44" height="64" rx="4" fill="url(#gold)"/>
  <rect x="212" y="286" width="30" height="30" rx="4" fill="#DCE8E4"/>
  <rect x="318" y="286" width="30" height="30" rx="4" fill="#DCE8E4"/>
  <circle cx="294" cy="334" r="3" fill="#fff"/>
</g>
<!-- 浮かぶカード -->
<g transform="translate(66,110)"><g class="float d1" filter="url(#sh)"><rect width="128" height="60" rx="16" fill="#fff"/><circle cx="30" cy="30" r="16" fill="#0F3D3A"/><path d="M24 30l4 4 8-8" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><rect x="56" y="20" width="52" height="7" rx="3.5" fill="#DCE8E4"/><rect x="56" y="34" width="34" height="7" rx="3.5" fill="#EDE7DA"/></g></g>
<g transform="translate(372,118)"><g class="float d2" filter="url(#sh)"><rect width="128" height="60" rx="16" fill="#fff"/><circle cx="30" cy="30" r="16" fill="#C2A14F"/><path d="M30 22v16M22 30h16" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round"/><rect x="56" y="20" width="52" height="7" rx="3.5" fill="#F1E7CF"/><rect x="56" y="34" width="34" height="7" rx="3.5" fill="#EDE7DA"/></g></g>
<g transform="translate(384,382)"><g class="float d3" filter="url(#sh)"><rect width="128" height="60" rx="16" fill="#fff"/><circle cx="30" cy="30" r="16" fill="#1F6B66"/><path d="M30 21 24 24v6c0 4 2.6 7 6 8 3.4-1 6-4 6-8v-6z" fill="none" stroke="#fff" stroke-width="1.8" stroke-linejoin="round"/><rect x="56" y="20" width="52" height="7" rx="3.5" fill="#DCE8E4"/><rect x="56" y="34" width="34" height="7" rx="3.5" fill="#EDE7DA"/></g></g>
<g transform="translate(54,392)"><g class="float" filter="url(#sh)"><rect width="128" height="60" rx="16" fill="#fff"/><circle cx="30" cy="30" r="16" fill="#0F3D3A"/><rect x="24" y="24" width="12" height="12" rx="2" fill="none" stroke="#fff" stroke-width="1.8"/><rect x="56" y="20" width="52" height="7" rx="3.5" fill="#F1E7CF"/><rect x="56" y="34" width="34" height="7" rx="3.5" fill="#EDE7DA"/></g></g>
<!-- 小さな点 -->
<circle cx="120" cy="300" r="4" fill="#C2A14F"/><circle cx="450" cy="250" r="3" fill="#1F6B66"/><circle cx="300" cy="78" r="3" fill="#C2A14F"/>
</svg>"""

def build_index():
    cards = "\n".join(svc_card(s) for s in SERVICES)
    ARROW_BTN = ARROW.replace('<svg ','<svg class="arrow" ')
    MARQUEE = ''.join(f'<span>{x["name"]}</span>' for x in SERVICES)
    faq = "\n".join(f'<details class="rv"><summary>{html.escape(q)}</summary><div class="a">{html.escape(a)}</div></details>' for q, a in FAQ)
    body = f"""
<section class="hero">
  <div class="glow a"></div><div class="glow b"></div>
  <div class="wrap">
    <div>
      <span class="kicker rv">Life support subscription</span>
      <h1 class="rv rv-d1"><span class="l">毎日の「もしも」に、</span><span class="l"><em>ひとつ足す</em>安心。</span></h1>
      <p class="lead rv rv-d2">置き配の盗難、スマホの故障、家電のトラブル、わずらわしい広告。くらしプラスは、5つのサービスから必要なものだけを月額で選べる、{SITE['company']}のライフサポートサービスです。</p>
      <div class="cta rv rv-d3">
        <a class="btn btn-primary" href="#services">サービスを見る {ARROW_BTN}</a>
        <a class="btn btn-outline" href="contact.html">お問い合わせ</a>
      </div>
      <div class="meta rv rv-d4">
        <div>月額（税抜）<b><span>{SITE['price']}</span> 円〜</b></div>
        <div>初期費用・解約金<b>0 円</b></div>
        <div>最低利用期間<b>なし</b></div>
      </div>
    </div>
    <div class="hero-art rv rv-d2">{HERO_ART}</div>
  </div>
  <div class="scroll-cue">Scroll<i></i></div>
</section>
<div class="marquee" aria-hidden="true"><div class="track">{MARQUEE}{MARQUEE}</div></div>

<section class="section" id="services">
  <div class="wrap">
    <div class="section-head rv">
      <div class="en">Services</div>
      <h2>選べる、5つの安心。</h2>
      <p>補償からおトク、セキュリティまで。くらしに必要なものを、ひとつから。組み合わせも、あとからの追加も自由です。</p>
    </div>
    <div class="svc-grid">{cards}</div>
  </div>
</section>

<section class="section paper" id="features">
  <div class="wrap">
    <div class="section-head rv">
      <div class="en">Why Kurashi+</div>
      <h2>くらしプラスが選ばれる理由</h2>
    </div>
    <div class="feat">
      <div class="item rv"><div class="num">01</div><div><h3>必要なものだけ、ひとつから</h3><p>セット契約は不要。5つのサービスから使いたいものだけを選び、あとから追加や解約もできます。</p></div></div>
      <div class="item rv"><div class="num">02</div><div><h3>わかりやすい月額料金</h3><p>各サービス月額{SITE['price']}円（税抜）。初期費用や解約金はなく、最低利用期間もありません。</p></div></div>
      <div class="item rv"><div class="num">03</div><div><h3>ご家族もいっしょに安心</h3><p>補償サービスは同居のご家族も対象。ギフ活は配偶者や二親等以内のご親族もご利用いただけます。</p></div></div>
      <div class="item rv"><div class="num">04</div><div><h3>困ったときの窓口がある</h3><p>ヘルプデスクが{SITE['hours']}に対応。補償の請求方法や使い方のご相談も承ります。</p></div></div>
    </div>
  </div>
</section>

<section class="section" id="flow">
  <div class="wrap">
    <div class="section-head rv">
      <div class="en">How it works</div>
      <h2>ご利用の流れ</h2>
    </div>
    <div class="steps">
      <div class="step rv"><h3>サービスを選ぶ</h3><p>5つのサービスから、必要なものを選びます。複数の組み合わせもOK。</p></div>
      <div class="step rv"><h3>お申し込み</h3><p>お申込み窓口またはマイページから、お客様情報とお支払い方法（クレジットカード／キャリア決済）を登録します。</p></div>
      <div class="step rv"><h3>ご利用開始</h3><p>お申込み完了後、ご案内に沿ってご利用いただけます。補償は契約成立日の午前0時から開始します。</p></div>
      <div class="step rv"><h3>もしものときは</h3><p>ヘルプデスクへご連絡ください。補償の請求手続きをご案内します。</p></div>
    </div>
  </div>
</section>

<section class="section dark" id="price">
  <div class="wrap">
    <div class="section-head rv">
      <div class="en">Price</div>
      <h2>シンプルな、ひとつの料金。</h2>
      <p>どのサービスを選んでも同じ月額。必要な数だけ、必要なあいだだけ。</p>
    </div>
    <div class="price">
      <div class="rv">
        <div class="price-label">各サービス月額</div>
        <div class="amount"><span class="yen">¥</span>{SITE['price']}<span class="per">／月（税抜）</span></div>
        <div class="sub">税込 {SITE['price_tax']}円／月</div>
        <p class="fine">※ キャンペーン適用時は、その条件に従い減額・免除となる場合があります。<br>※ 料金は予告なく変更となる場合があります。</p>
      </div>
      <ul class="rv rv-d2">
        <li>初期費用 0円・解約金 0円</li>
        <li>最低利用期間なし。いつでも解約できます</li>
        <li>お支払いはクレジットカードまたはキャリア決済</li>
        <li>解約は当月末に反映（日割りなし）</li>
      </ul>
    </div>
  </div>
</section>

<section class="section" id="faq">
  <div class="wrap">
    <div class="section-head rv">
      <div class="en">FAQ</div>
      <h2>よくある質問</h2>
    </div>
    <div class="faq">{faq}</div>
  </div>
</section>

<section class="section">
  <div class="wrap">
    <div class="cta-band rv">
      <div>
        <h2>ご不明な点は、お気軽にどうぞ。</h2>
        <p>サービス内容や補償の範囲、お申込み方法について、ヘルプデスク（{SITE['hours_short']}）がお答えします。</p>
      </div>
      <a class="btn btn-light" href="contact.html">お問い合わせフォームへ {ARROW_BTN}</a>
    </div>
  </div>
</section>
"""
    page("index.html", "", SITE["desc"], body, 0)

# ---------- サービス詳細 ----------
def build_services():
    for s in SERVICES:
        pts = "".join(f"<li>{html.escape(p)}</li>" for p in s["points"])
        det = "".join(f"<h2>{html.escape(h)}</h2><p>{html.escape(t)}</p>" for h, t in s["detail"])
        others = "\n".join(svc_card(o, 1) for o in SERVICES if o["code"] != s["code"])
        body = f"""
<div class="wrap">
  <div class="page-head">
    <div class="breadcrumb"><a href="../index.html">トップ</a> › <a href="../index.html#services">サービス</a> › {s['name']}</div>
    <div class="en">Service {s['no']}</div>
    <h1>{s['name']}</h1>
    <p>{html.escape(s['short'])}</p>
  </div>
  <div class="svc-hero rv">
    <div class="wm">{s['no']}</div>
    <div>
      <div class="svc-icon">{ICONS[s['code']]}</div>
      <span class="tag">{s['tag']}</span>
      <h2>{html.escape(s['lead'])}</h2>
      <div class="price-line"><span class="yen">月額</span>¥{SITE['price']}<small>（税抜）／税込 {SITE['price_tax']}円</small></div>
      <p style="margin-top:26px"><a class="btn btn-primary" href="../contact.html">お申し込み・ご相談はこちら</a></p>
    </div>
    <ul class="points">{pts}</ul>
  </div>
  <div class="content">
    {det}
    <h2>料金・お支払い</h2>
    <p>月額{SITE['price']}円（税抜）。初期費用・解約金はありません。お支払いはクレジットカード決済またはキャリア決済です。解約は手続き完了を確認した月の末日に反映され、日割り計算はありません。</p>
    <h2>規約</h2>
    <p><a href="../terms/{s['terms']}.html">{s['name']} 利用規約</a>　／　<a href="../privacy.html">プライバシーポリシー</a>　／　<a href="../legal.html">特定商取引法に基づく表記</a></p>
    <div class="notice gray">本ページの内容は概要です。補償の条件・対象外事項などの詳細は利用規約をご確認ください。</div>
  </div>
</div>
<section class="section paper">
  <div class="wrap">
    <div class="section-head rv"><div class="en">Other services</div><h2>ほかのサービス</h2></div>
    <div class="svc-grid four">{others}</div>
  </div>
</section>
"""
        page(f"services/{s['code']}.html", s["name"], s["short"], body, 1)

# ---------- 利用規約 ----------
def terms_to_html(text):
    lines = [l.rstrip() for l in text.splitlines()]
    out, toc = [], []
    first = True
    n = 0
    for l in lines:
        if not l.strip():
            continue
        if first:
            first = False  # タイトル行はページ側で出す
            continue
        m = re.match(r"^(第\d+条（.+?）)$", l)
        if m:
            n += 1
            out.append(f'<h2 id="a{n}">{html.escape(l)}</h2>')
            toc.append(f'<a href="#a{n}">{html.escape(l)}</a>')
        elif l in ("附則", "以上"):
            out.append(f'<h2>{l}</h2>' if l == "附則" else f'<p style="text-align:right">{l}</p>')
        elif re.match(r"^(（\d+）|\d+\.\s|【)", l):
            out.append(f'<p class="item">{html.escape(l)}</p>')
        else:
            out.append(f"<p>{html.escape(l)}</p>")
    return "".join(out), "".join(toc)

def build_terms():
    idx_items = []
    for s in SERVICES:
        raw = os.path.join(ROOT, "tools", "terms_raw", f"{s['terms']}.txt")
        if os.path.exists(raw):
            with open(raw, encoding="utf-8") as f:
                body_html, toc = terms_to_html(f.read())
            inner = f'<div class="toc">{toc}</div>{body_html}'
            status = ""
        else:
            inner = f'<div class="notice">「{s["name"]}」の利用規約は現在準備中です。公開まで今しばらくお待ちください。ご不明な点は<a href="../contact.html">お問い合わせ</a>ください。</div>'
            status = "（準備中）"
        body = f"""
<div class="wrap">
  <div class="page-head">
    <div class="breadcrumb"><a href="../index.html">トップ</a> › <a href="index.html">利用規約</a> › {s['name']}</div>
    <div class="en">Terms</div>
    <h1>{s['name']} 利用規約{status}</h1>
    <p>施行日：{SITE['effective']}　提供：{SITE['company']}</p>
  </div>
  <div class="content terms card">{inner}</div>
</div>
"""
        page(f"terms/{s['terms']}.html", f"{s['name']} 利用規約", f"{SITE['name']}「{s['name']}」の利用規約です。", body, 1)
        idx_items.append(f'<li><a href="{s["terms"]}.html">{s["name"]} 利用規約{status}</a></li>')
    body = f"""
<div class="wrap">
  <div class="page-head">
    <div class="breadcrumb"><a href="../index.html">トップ</a> › 利用規約</div>
    <div class="en">Terms</div>
    <h1>利用規約</h1>
    <p>サービスごとに利用規約を定めています。お申し込みの前に必ずお読みください。</p>
  </div>
  <div class="content card"><ul>{"".join(idx_items)}</ul>
  <p style="margin-top:16px"><a href="../privacy.html">プライバシーポリシー</a>　／　<a href="../legal.html">特定商取引法に基づく表記</a></p></div>
</div>
"""
    page("terms/index.html", "利用規約", f"{SITE['name']}の各サービス利用規約の一覧です。", body, 1)

# ---------- プライバシーポリシー ----------
def build_privacy():
    c = SITE
    body = f"""
<div class="wrap">
  <div class="page-head">
    <div class="breadcrumb"><a href="index.html">トップ</a> › プライバシーポリシー</div>
    <div class="en">Privacy Policy</div>
    <h1>プライバシーポリシー</h1>
    <p>{c['company']}（以下「当社」といいます。）は、当社が提供する「{c['name']}」および関連サービス（以下「本サービス」といいます。）における個人情報の取扱いについて、以下のとおり定めます。</p>
  </div>
  <div class="content card">
    <h2>1. 取得する情報</h2>
    <p>当社は、本サービスの提供にあたり、次の情報を取得することがあります。</p>
    <ul><li>氏名、住所、電話番号、メールアドレス、生年月日などの登録情報</li><li>お支払いに関する情報（決済代行会社が発行するトークン等。カード番号そのものは当社で保持しません）</li><li>補償の請求にあたりご提出いただく情報（被害届の受理番号、修理の見積書・領収書等）</li><li>お問い合わせの内容、サポート対応の記録</li><li>アクセスログ、Cookie、端末情報などの利用状況に関する情報</li></ul>
    <h2>2. 利用目的</h2>
    <ul><li>本サービスの提供、本人確認、利用料金の請求のため</li><li>補償の引受保険会社・提携事業者との連携、保険金請求手続きのため</li><li>お問い合わせへの対応、重要なお知らせの連絡のため</li><li>当社および当社グループ会社が取り扱うサービスのご案内のため</li><li>サービスの改善、統計データの作成、新サービスの開発のため</li><li>法令に基づく対応のため</li></ul>
    <h2>3. 第三者への提供</h2>
    <p>当社は、次の場合を除き、ご本人の同意なく個人情報を第三者に提供しません。</p>
    <ul><li>補償サービスの提供に必要な範囲で、引受保険会社または提携事業者に提供する場合</li><li>決済処理のために決済代行会社に提供する場合</li><li>法令に基づく場合、人の生命・身体・財産の保護のために必要な場合</li><li>業務委託先に対し、利用目的の達成に必要な範囲で取り扱いを委託する場合</li></ul>
    <h2>4. 安全管理</h2>
    <p>当社は、個人情報への不正アクセス、紛失、漏えい、改ざん等を防止するため、必要かつ適切な安全管理措置を講じ、従業者および委託先を適切に監督します。</p>
    <h2>5. Cookie等の利用</h2>
    <p>本サービスのウェブサイトでは、利便性の向上やアクセス状況の分析のためにCookie等を利用することがあります。ブラウザの設定によりCookieを無効にできますが、一部機能がご利用いただけない場合があります。</p>
    <h2>6. 開示・訂正・利用停止等</h2>
    <p>ご本人から保有個人データの開示、訂正、追加、削除、利用停止等のご請求があった場合、法令に従い、本人確認のうえ速やかに対応します。下記窓口までご連絡ください。</p>
    <h2>7. 本ポリシーの変更</h2>
    <p>当社は、法令の改正やサービス内容の変更に応じて本ポリシーを改定することがあります。改定後の内容は当社ウェブサイトに掲載した時点から適用されます。</p>
    <h2>8. お問い合わせ窓口</h2>
    <p>{c['company']}　個人情報お問い合わせ窓口<br>{c['zip']} {c['addr']}<br>メール：<a href="mailto:{c['email']}">{c['email']}</a><br>受付時間：{c['hours']}</p>
    <p style="text-align:right">制定日：{c['effective']}</p>
  </div>
</div>
"""
    page("privacy.html", "プライバシーポリシー", f"{SITE['name']}（{SITE['company']}）のプライバシーポリシーです。", body, 0)

# ---------- 特商法 ----------
def build_legal():
    c = SITE
    rows = [
        ("販売業者", c["company"]),
        ("運営統括責任者", c["rep"]),
        ("所在地", f"{c['zip']} {c['addr']}"),
        ("お問い合わせ", f'メール：<a href="mailto:{c["email"]}">{c["email"]}</a><br>お問い合わせフォーム：<a href="contact.html">こちら</a><br>受付時間：{c["hours"]}<br>※電話番号は、ご請求いただければ遅滞なく開示いたします。'),
        ("販売価格", f"各サービス 月額{c['price']}円（税抜）／税込{c['price_tax']}円。各サービスページおよびお申込み画面に表示します。"),
        ("商品代金以外の必要料金", "インターネット接続にかかる通信料等はお客様のご負担となります。初期費用・解約金はありません。"),
        ("お支払い方法", "クレジットカード決済またはキャリア決済（当社が指定する方法）"),
        ("お支払い時期", "毎月、所定の期日に当月分をお支払いいただきます（決済方法により引落日は異なります）。"),
        ("サービスの提供時期", "お申込み完了後、当社所定の方法でご案内した日からご利用いただけます。補償サービスは利用契約成立日の午前0時から補償を開始します。"),
        ("解約について", "いつでも解約できます。最低利用期間の定めはありません。解約の効力は手続き完了を確認した月の末日に発生し、月途中の解約でも日割り計算は行いません。解約返戻金はありません。"),
        ("返品・キャンセルについて", "サービスの性質上、お客様都合による返金・キャンセルは承っておりません。本サービスは通信販売に該当するため、クーリング・オフの適用はありません。"),
        ("動作環境", "ギフ活・クマモリ広告ブロックのご利用には、インターネットに接続できるスマートフォン・タブレット・パソコン等が必要です。対応OS等は各サービスの案内をご確認ください。"),
        ("その他の特別な条件", "サービスの利用に際して特別な条件がある場合は、都度サービスサイト上に表示します。"),
    ]
    kv = "".join(f"<div>{k}</div><div>{v}</div>" for k, v in rows)
    body = f"""
<div class="wrap">
  <div class="page-head">
    <div class="breadcrumb"><a href="index.html">トップ</a> › 特定商取引法に基づく表記</div>
    <div class="en">Legal</div>
    <h1>特定商取引法に基づく表記</h1>
  </div>
  <div class="content card"><div class="kv">{kv}</div></div>
</div>
"""
    page("legal.html", "特定商取引法に基づく表記", f"{SITE['name']}（{SITE['company']}）の特定商取引法に基づく表記です。", body, 0)

# ---------- お問い合わせ ----------
def build_contact():
    c = SITE
    kinds = ["サービス内容について", "お申し込みについて", "補償の請求について", "ご契約内容・解約について", "お支払いについて", "その他"]
    opts = "".join(f"<option>{k}</option>" for k in kinds)
    body = f"""
<div class="wrap">
  <div class="page-head">
    <div class="breadcrumb"><a href="index.html">トップ</a> › お問い合わせ</div>
    <div class="en">Contact</div>
    <h1>お問い合わせ</h1>
    <p>サービス内容やお申し込み、補償の請求についてのご相談はこちらから。ヘルプデスク（{c['hours_short']}）より順次ご返信します。</p>
  </div>
  <div class="content card">
    <form id="contactForm" class="form" novalidate>
      <div class="field"><label for="name">お名前<span class="req">必須</span></label><input id="name" name="name" type="text" autocomplete="name" placeholder="山田 太郎" required></div>
      <div class="field"><label for="email">メールアドレス<span class="req">必須</span></label><input id="email" name="email" type="email" autocomplete="email" placeholder="example@example.com" required></div>
      <div class="field"><label for="tel">電話番号</label><input id="tel" name="tel" type="tel" autocomplete="tel" placeholder="090-0000-0000"><div class="help">お急ぎの場合はご記入ください。</div></div>
      <div class="field"><label for="kind">お問い合わせ種別</label><select id="kind" name="kind">{opts}</select></div>
      <div class="field"><label for="message">お問い合わせ内容<span class="req">必須</span></label><textarea id="message" name="message" required placeholder="ご契約中の方は、ご契約のサービス名もあわせてご記入ください。"></textarea></div>
      <label class="check"><input type="checkbox" name="agree"><span><a href="privacy.html" target="_blank" rel="noopener">プライバシーポリシー</a>に同意のうえ送信します。</span></label>
      <div class="err" role="alert"></div>
      <button type="submit" class="btn btn-primary btn-block">送信する</button>
    </form>
    <p style="margin-top:24px;font-size:14px;color:var(--muted)">メールでのお問い合わせ：<a href="mailto:{c['email']}">{c['email']}</a></p>
  </div>
</div>
"""
    page("contact.html", "お問い合わせ", f"{SITE['name']}へのお問い合わせフォームです。", body, 0)

    body = f"""
<div class="wrap">
  <div class="page-head" style="text-align:center">
    <div class="en">Thank you</div>
    <h1>お問い合わせを受け付けました</h1>
    <p style="margin:12px auto 0">ご入力いただいたメールアドレス宛に受付確認をお送りします。担当者より{c['hours']}の間にご返信いたしますので、今しばらくお待ちください。</p>
    <p style="margin-top:28px"><a class="btn btn-outline" href="index.html">トップページへ戻る</a></p>
  </div>
</div>
"""
    page("thanks.html", "送信完了", "お問い合わせを受け付けました。", body, 0)

# ---------- ログイン・マイページ ----------
def build_auth():
    body = f"""
<div class="wrap">
  <div class="page-head" style="padding-bottom:12px"></div>
  <div class="auth">
    <div class="card">
      <h1>会員ログイン</h1>
      <p class="sub">ご登録のメールアドレスとパスワードを入力してください。</p>
      <form id="loginForm" class="form" novalidate>
        <div class="field"><label for="email">メールアドレス</label><input id="email" name="email" type="email" autocomplete="username" required></div>
        <div class="field"><label for="password">パスワード</label><input id="password" name="password" type="password" autocomplete="current-password" minlength="8" required></div>
        <div class="err" role="alert"></div>
        <button type="submit" class="btn btn-primary btn-block">ログイン</button>
      </form>
      <div class="links"><a href="contact.html">パスワードをお忘れの方</a><a href="contact.html">新規お申し込み</a></div>
    </div>
  </div>
  <div style="height:56px"></div>
</div>
"""
    page("login.html", "会員ログイン", f"{SITE['name']}会員ログインページ。", body, 0)

    items = "".join(f"""<div class="my-item" data-code="{s['code']}" data-price="{SITE['price']}円">
      <div class="svc-icon">{ICONS[s['code']]}</div>
      <div><h3>{s['name']}</h3><div class="st">未加入</div></div>
      <div class="act"><button type="button" class="btn btn-teal btn-sm">申し込む</button></div>
    </div>""" for s in SERVICES)
    body = f"""
<div class="wrap" id="mypage">
  <div class="page-head">
    <div class="en">My page</div>
    <h1>マイページ</h1>
  </div>
  <div class="my-grid" style="padding-bottom:64px">
    <aside class="my-side">
      <div class="card">
        <div class="name">—</div>
        <div class="mail">—</div>
        <p style="font-size:13px;color:var(--muted);margin-top:10px">ご利用中のサービス：<b class="count">0</b> 件</p>
        <nav>
          <a href="#services">ご契約サービス</a>
          <a href="contact.html">お支払い方法の変更</a>
          <a href="contact.html">登録情報の変更</a>
          <a href="contact.html">お問い合わせ</a>
          <a href="#" class="logout">ログアウト</a>
        </nav>
      </div>
    </aside>
    <div>
      <h2 id="services" style="font-size:20px;margin-bottom:12px">ご契約サービス</h2>
      <div class="my-list">{items}</div>
      <p class="notice gray" style="margin-top:16px">お申し込み・解約はお手続き完了後にメールでご案内します。解約は当月末に反映され、日割り計算はありません。</p>
    </div>
  </div>
</div>
"""
    page("mypage.html", "マイページ", f"{SITE['name']}会員マイページ。", body, 0, extra='<meta name="robots" content="noindex">')

def build_404():
    body = """
<div class="wrap">
  <div class="page-head" style="text-align:center">
    <div class="en">404</div>
    <h1>ページが見つかりません</h1>
    <p style="margin:12px auto 0">URLが変更されたか、削除された可能性があります。</p>
    <p style="margin-top:28px"><a class="btn btn-outline" href="index.html">トップページへ戻る</a></p>
  </div>
</div>
"""
    page("404.html", "ページが見つかりません", "ページが見つかりません。", body, 0)

if __name__ == "__main__":
    build_index(); build_services(); build_terms(); build_privacy(); build_legal(); build_contact(); build_auth(); build_404()
    print("done")
