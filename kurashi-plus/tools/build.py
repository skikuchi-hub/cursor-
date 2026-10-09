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
    "desc": "くらしプラスは、置き配保険・ライフコストコンシェルジュ・Wi-Fi接続機器補償・家電保証・クマモリ（広告ブロック）の5つで、暮らしのちいさな不安や困りごとをまとめて支える株式会社WSTの会員サービスです。",
    "company": "株式会社WST",
    "company_url": "https://wst-corp.jp/",
    "rep": "石原 里基",
    "zip": "〒815-0041",
    "addr": "福岡県福岡市南区野間1-1-2 5F",
    "tel": "0120-933-565",
    "privacy_tel": "0120-502-443",
    "email": "info@wst-inc.jp",
    "hours": "平日12:00〜18:00（土日祝日・年末年始を除く）",
    "hours_short": "平日12:00〜18:00、土日祝日・年末年始を除く",
    "free": "最大2ヶ月無料",
    "price": "1,330",
    "price_tax": "1,463",
    "show_price": False,   # True にすると各ページに月額を表示する（本家 HOME LINK と同じく既定は非表示）
    "effective": "2026年4月1日",
}

SERVICES = [
    {
        "code": "okihai", "no": "01",
        "name": "置き配保険", "terms_name": "置き配補償",
        "tag": "盗難補償",
        "copy": "届いた瞬間から、守られている。", "copy_br": "届いた瞬間から、<br>守られている。",
        "short": "置き配時の盗難はもちろん、自宅内での盗難も補償の対象。安心して置き配を使える環境を整えます。",
        "paras": [
            "EC利用が当たり前になった今でも、「もし盗まれたらどうしよう」という不安は残ります。",
            "本サービスでは、置き配時の盗難はもちろん、自宅内での盗難も補償対象。",
            "安心して置き配を利用できる環境を整え、日々の受け取りをもっと気軽にします。",
        ],
        "fine": "置き配時の盗難だけではなく、自宅内の盗難も対象となります。（申請や必要手続きは案内に従ってください）",
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
        "spec": [("対象", "置き配の荷物、自宅・物置・車庫内の持ち物"), ("上限", "1事故 30万円（免責0円）"), ("対象者", "ご本人＋同居のご家族")],
        "photo": "svc-okihai.jpg",
    },
    {
        "code": "lifecost", "no": "02",
        "name": "ライフコストコンシェルジュ", "name_br": "ライフコスト<br>コンシェルジュ", "terms_name": "ライフコスト診断サポート",
        "tag": "固定費の見直し相談",
        "copy": "暮らしの固定費を、もっと軽く。", "copy_br": "暮らしの固定費を、<br>もっと軽く。",
        "short": "電気・ガス・水道・インターネット・携帯など、毎月のライフラインの固定費を、専門家が何度でも無料で見直し。",
        "paras": [
            "電気・ガス・水道・インターネット・携帯など、毎月かかるライフラインの固定費を見直しませんか。",
            "ライフラインのスペシャリストが現状をヒアリングし、お客様に最適なプランをご提案。家計の負担をやさしく軽くします。",
        ],
        "fine": "電気・ガス・水道・インターネット・携帯電話などのライフラインに関するご相談を、何度でも無料でお受けいたします。専門家がお客様の現状を丁寧にヒアリングし、最適なプランをご案内。お切替手続きやサービスご利用開始まで、担当者が一貫してサポートいたします。",
        "points": [
            "電気・ガス・水道・インターネット・携帯電話の固定費をまとめて診断",
            "ご相談は何度でも無料。現状のヒアリングから最適なプランのご提案まで",
            "お切替の手続きからご利用開始まで、担当者が一貫してサポート",
            f"ヘルプデスクは{SITE['hours_short']}",
        ],
        "detail": [
            ("サービス内容", "保険料・通信費・光熱費・住居費など、暮らしにかかる固定費の診断と相談サポートを提供します。ライフラインのスペシャリストが現状を丁寧にヒアリングし、お客様に合ったプランをご案内します。"),
            ("ご相談の流れ", "ヘルプデスクへご連絡いただき、現在のご契約内容や毎月の支出をお聞かせください。診断結果とご提案をお伝えし、お切替をご希望の場合は手続きからご利用開始まで担当者がサポートします。"),
            ("ご注意", "本サービスで提供する情報および助言は一般的な情報提供を目的とするもので、特定の金融商品・保険商品等の推奨・勧誘や売買の助言ではありません。ご提案に基づく契約変更等は、お客様ご自身のご判断で行っていただきます。"),
        ],
        "terms": "lifecost",
        "spec": [("対象", "電気・ガス・水道・ネット・携帯などの固定費"), ("相談", "何度でも無料"), ("対応時間", "平日12:00〜18:00")],
        "photo": "svc-lifecost.jpg",
    },
    {
        "code": "wifi", "no": "03",
        "name": "Wi-Fi接続機器補償", "name_br": "Wi-Fi接続<br>機器補償", "terms_name": "Wi-Fi接続機器補償",
        "tag": "通信機器の故障・破損・盗難",
        "copy": "つかえない、をなくす。",
        "short": "スマホ・タブレット・PC・イヤホンなど、Wi-FiやBluetoothにつながる機器の急な故障や損壊に、修理費用を補償。",
        "paras": [
            "通信機器※の故障は、在宅ワークやご家族との大切な時間に影響を与えることも。",
            "突然のトラブルにも、修理・補償で迅速に対応し、安心して使い続けられる環境をサポートします。",
        ],
        "fine": "会員様が所有するスマホやタブレット、PC、Bluetoothイヤホンなど、Wi-FiまたはBluetoothに接続するデバイスを総合的にサポートします。急な故障や損壊にも対応し、修理費用を補償する安心のサービスです。\n※スマートフォン、携帯電話、パソコン、タブレット、ゲーム機、ワイヤレスイヤホン、スマートウォッチが対象",
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
        "spec": [("対象", "スマホ・タブレット・PC・ゲーム機・イヤホン等"), ("上限", "修理可 10万円／修理不可 2.5万円"), ("免責", "5,000円・年1回まで")],
        "photo": "svc-wifi.jpg",
    },
    {
        "code": "kaden", "no": "04",
        "name": "家電保証", "terms_name": "家電保証",
        "tag": "家電の延長保証",
        "copy": "買ったあとも、ずっと安心。", "copy_br": "買ったあとも、<br>ずっと安心。",
        "short": "冷蔵庫や洗濯機などの家電の故障を、メーカー保証が切れたあとも補償。思いがけない出費に、あらかじめ備えます。",
        "paras": [
            "冷蔵庫や洗濯機などの家電の故障は、思いがけない大きな出費につながることがあります。",
            "保証期間終了後も修理費用を補償し、万が一の際の負担を軽減。",
            "“壊れてから慌てる”のではなく、あらかじめ備える安心を提供します。",
        ],
        "fine": "メーカーの延長保証よりも安価に幅広いケースで延長保証できるサービスです。",
        "points": [
            "ご自宅で使用している家電製品の自然故障による修理費用を補償",
            "メーカー保証が終了したあとの故障でも対象",
            "メーカーの延長保証より安価に、幅広いケースをカバー",
            "対象製品・上限金額・免責事項は利用規約をご確認ください",
        ],
        "detail": [
            ("サービス内容", "ご自宅で使用している対象家電製品に自然故障が発生した場合に、修理費用を補償するサービスです。対象製品の品目、1回あたり・年間の補償上限、製造年数などの条件は利用規約で定めます。"),
            ("ご注意", "落下・水没などの外的要因による故障、消耗品の交換、購入から一定期間内のメーカー保証対象の故障などは対象外となる場合があります。詳しくは利用規約をご確認ください。"),
        ],
        "terms": "kaden",
        "spec": [("対象", "ご自宅の家電製品の自然故障"), ("補償", "修理費用（上限は規約に定める）"), ("備考", "メーカー保証終了後も対象")],
        "photo": "svc-kaden.jpg",
    },
    {
        "code": "kumamori", "no": "05",
        "name": "クマモリ（広告ブロック）", "name_br": "クマモリ<br>（広告ブロック）", "terms_name": "クマモリ（広告ブロック）",
        "tag": "広告ブロック・セキュリティ",
        "copy": "広告ではなく、選ばれた情報を。", "copy_br": "広告ではなく、<br>選ばれた情報を。",
        "short": "ネット上だけでなくアプリ内の広告も抑え、フィッシング詐欺サイトやマルウェアサイトもブロック。家族みんなのスマホを見守ります。",
        "paras": [
            "外出先や日常の中で、意図しない広告表示に戸惑った経験はありませんか？",
            "クマモリ（広告ブロック）は、不要な広告や不適切な表示を抑え、日々のご利用を継続的に見守りながら、ご家族みなさまが安心してスマートフォンを使える環境を整えます。",
        ],
        "fine": "ネット上だけでなくアプリ内の広告も徹底的に排除し、快適なインターネット環境を提供します。さらに、フィッシング詐欺サイトやマルウェアサイトのブロック機能も搭載し、安全性も抜群です。\n※スマートフォン（iOS / Android）のみ対応／一部サービス・仕様により表示される場合があります。",
        "points": [
            "ブラウザだけでなく、アプリ内の広告もブロック",
            "フィッシング詐欺サイト・マルウェアサイトへのアクセスを遮断",
            "広告を読み込まないから、表示が速く通信量も節約",
            "スマートフォン（iOS / Android）に対応",
        ],
        "detail": [
            ("サービス内容", "スマートフォンにアプリをインストールして使う広告ブロックサービスです。お申し込み後にご案内する手順でアプリを有効化してください。"),
            ("ご注意", "広告の表示仕様は各サービス・アプリの都合で変更されることがあり、一部サービス・仕様により広告が表示される場合があります。対応OS・端末はアプリの案内をご確認ください。"),
        ],
        "terms": "kumamori",
        "spec": [("対象", "ブラウザ・アプリ内の広告"), ("機能", "フィッシング・マルウェアサイト遮断"), ("対応", "iOS / Android")],
        "photo": "svc-kumamori.jpg",
    },
]

WORRIES = [
    "玄関前に置かれた荷物が、気になって落ち着かない。",
    "毎月の電気代や通信費、見直したいけれど面倒。",
    "スマホを落として画面が割れた。修理代が高い。",
    "保証が切れた冷蔵庫が、ある日突然止まった。",
    "子どものスマホに出てくる広告が、ちょっと心配。",
]

FAQ = [
    ("サービスを利用したいけど「紹介コード」ってなに？", "本サービスはサービス説明不足や認識相違によるトラブル防止のため、販売パートナー様の紹介コードをお持ちの方限定でお申し込みいただけます。販売パートナー様とお繋がりがない場合は、一時的な紹介コードを発行いたしますので、お問い合わせフォームよりその旨をご連絡ください。"),
    ("最大2ヶ月無料は本当？", "本当です。2ヶ月間無料のため、1ヶ月目の無料期間の日数はお申込日によって前後しますのでご留意ください。（例：1/20お申込の場合、1月＋2月が無料期間）"),
    ("決済方法はなにがありますか？", "クレジットカード決済、キャリア決済からお選びいただけます。"),
    ("サービス詳細が知りたい", "各サービスの利用規約に記載があります。利用規約はお申込完了後に控えとして書面またはご登録のメールアドレスへお送りしていますので、そちらからもご確認いただけます。本サイトの利用規約ページでもご覧いただけます。"),
    ("キャッシュバックがあると言われたんだけどどうしたらいい", "申し訳ございません。キャッシュバックは原則当社では行っておりませんので、紹介コードをお渡しした代理店様にお問い合わせください。"),
    ("紹介コードを貰った代理店がわからない、忘れた", "お問い合わせフォームよりご連絡いただければ、お客様情報を確認のうえ、3営業日以内にご登録のメールアドレスへ回答いたします。迷惑メール設定をされている場合は、お手数ですが当社ドメインの受信許可をお願いいたします。"),
    ("お問い合わせフォームを送信したけど返信がない気がする", "お問い合わせフォームをご入力いただいた日より3営業日以内に、ご登録のメールアドレスへ返信いたします。迷惑メール設定をされている場合は、お手数ですが当社ドメインの受信許可をお願いいたします。"),
    ("解約したい", "お問い合わせフォームよりご連絡ください。ご入力いただいた日より3営業日以内に、ご登録のメールアドレスへ解約方法のご案内をお送りします。迷惑メール設定をされている場合は、お手数ですが当社ドメインの受信許可をお願いいたします。"),
    ("中途解約をした場合は違約金や解約金は発生しますか？", "一切発生しません。"),
    ("登録した覚えがない", "本サービスはサービス説明不足や認識相違によるトラブル防止およびメール到達確認のため、ご紹介店様からのお申込時にご登録いただいたメールアドレスまたはSMS（ショートメッセージ）へ決済登録URLをお送りし、お客様ご自身が決済情報をご入力いただかなければお申し込みが完了しない仕様になっております。ご不明点がございましたら、お問い合わせフォームよりご連絡ください。"),
    ("契約はしたがサービス内容に満足ができない", "ご期待に沿えず大変申し訳ございません。サービス品質向上とお客様満足度アップのため、可能であれば至らない点をご教示いただけますでしょうか。お問い合わせフォームよりその旨をご連絡いただけますと、場合によってはサービス利用料金の返金対応につきまして柔軟に対応させていただきます。"),
    ("お友達を紹介したい", "ありがとうございます。本サービスは、紹介コードを発行している代理店様を通じたお申し込み限定となっており、紹介コードをご入力いただかなければお申し込みが完了しない仕様です。一時的な紹介コードを発行いたしますので、お問い合わせフォームよりその旨をご連絡ください。"),
    ("サービス申込の年齢制限ありますか？", "ございません。"),
]

CONTACT_KINDS = [
    "サービスについて",
    "紹介コードの発行依頼",
    "紹介コードを忘れた・分からない",
    "解約について",
    "返金について",
    "お申し込み内容の確認",
    "迷惑メール対策の解除依頼",
    "その他",
]

# ============================================================
# 共通パーツ
# ============================================================
ARROW = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M13 5l7 7-7 7"/></svg>'
ARROW_BTN = ARROW.replace('<svg ', '<svg class="arrow" ')
FONTS = "https://fonts.googleapis.com/css2?family=Zen+Old+Mincho:wght@400;500&family=Zen+Kaku+Gothic+New:wght@400;500;700&family=Jost:wght@300;400&display=swap"

def rel(depth):
    return "../" * depth

def esc(s):
    return html.escape(s)

def nl(s):
    return "<br>".join(esc(x) for x in s.split("\n"))

def head(title, desc, depth, extra=""):
    r = rel(depth)
    full = f"{title}｜{SITE['name']}" if title else f"{SITE['name']}｜{SITE['tagline']}"
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{esc(full)}</title>
<meta name="description" content="{esc(desc)}">
<meta property="og:title" content="{esc(full)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:type" content="website">
<meta property="og:image" content="{r}assets/img/og.png">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="{r}assets/img/favicon.png" type="image/png">
<link rel="apple-touch-icon" href="{r}assets/img/icon-180.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="{FONTS}" rel="stylesheet">
<link rel="stylesheet" href="{r}assets/css/style.css">
<script src="{r}config.js"></script>
{extra}
</head>
<body>
"""

def mark_svg(cls="mark"):
    return f'<svg class="{cls}" viewBox="0 0 12 12" aria-hidden="true"><circle cx="6" cy="6" r="6" fill="#B85C3C"/></svg>'

def header(depth):
    r = rel(depth)
    return f"""<header class="site-header">
  <div class="wrap">
    <a class="brand" href="{r}index.html" aria-label="{SITE['name']} トップへ">{mark_svg()}<span class="word">{SITE['name']}</span></a>
    <button class="menu-btn" aria-label="メニュー" aria-expanded="false"><span></span><span></span><span></span></button>
    <nav class="nav">
      <a href="{r}index.html#services">サービス</a>
      <a href="{r}index.html#faq">よくある質問</a>
      <a href="{r}contact.html">お問い合わせ</a>
      <a class="btn btn-outline btn-sm" href="{r}login.html">会員ログイン</a>
      <a class="btn btn-primary btn-sm" href="{r}signup.html">お申し込み</a>
    </nav>
  </div>
</header>
"""

def footer(depth):
    r = rel(depth)
    svc_links = "".join(f'<li><a href="{r}services/{s["code"]}.html">{s["name"]}</a></li>' for s in SERVICES)
    return f"""<footer class="site-footer">
  <div class="wrap">
    <div class="top">
      <div>
        <a class="brand" href="{r}index.html">{mark_svg()}<span class="word">{SITE['name']}</span></a>
        <p class="tag">{SITE['tagline']}</p>
      </div>
      <div class="cta">
        <a class="btn btn-primary" href="{r}signup.html">お申し込みはこちら {ARROW_BTN}</a>
        <a class="btn btn-outline" href="{r}contact.html">お問い合わせはこちら {ARROW_BTN}</a>
      </div>
    </div>
    <div class="cols">
      <div>
        <h4>Services</h4>
        <ul>{svc_links}</ul>
      </div>
      <div>
        <h4>Support</h4>
        <ul>
          <li><a href="{r}index.html#faq">よくある質問</a></li>
          <li><a href="{r}signup.html">お申し込みについて</a></li>
          <li><a href="{r}contact.html">お問い合わせ</a></li>
          <li><a href="{r}login.html">会員ログイン</a></li>
        </ul>
      </div>
      <div>
        <h4>Company</h4>
        <ul>
          <li><a href="{SITE['company_url']}" target="_blank" rel="noopener">会社情報（{SITE['company']}）</a></li>
          <li><a href="{r}terms/index.html">利用規約</a></li>
          <li><a href="{r}privacy.html">プライバシーポリシー</a></li>
          <li><a href="{r}legal.html">特定商取引法に基づく表示</a></li>
        </ul>
      </div>
    </div>
    <div class="copy"><span>© {SITE['company']}</span><span>{SITE['name']}は{SITE['company']}が提供するサービスです。</span></div>
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

def sh(title, en="", desc="", center=False):
    enh = f'<span class="en">{en}</span>' if en else ''
    d = f'<p>{desc}</p>' if desc else ''
    return f'<div class="sh rv{" center" if center else ""}">{enh}<h2>{title}</h2>{d}</div>'

def price_note():
    if SITE["show_price"]:
        return f"各サービス月額{SITE['price']}円（税抜・税込{SITE['price_tax']}円）。初月から{SITE['free']}。"
    return f"料金はお申込み画面に表示します。初月から{SITE['free']}。"

# ============================================================
# トップ
# ============================================================
def svc_block(s, i):
    paras = "".join(f"<p>{esc(p)}</p>" for p in s["paras"])
    return f"""<article class="svc{' flip' if i % 2 else ''}" id="svc-{s['code']}">
  <div class="photo rv"><img src="assets/img/photo/{s['photo']}" alt="" loading="lazy" width="1200" height="900"></div>
  <div class="text">
    <div class="meta rv"><span class="no">{s['no']}</span><span class="name">{esc(s['name'])}</span></div>
    <h3 class="rv">{s.get("copy_br", esc(s["copy"]))}</h3>
    <div class="body rv">{paras}</div>
    <p class="fine rv">{nl(s['fine'])}</p>
    <a class="tlink rv" href="services/{s['code']}.html">詳しく見る {ARROW}</a>
  </div>
</article>"""

def build_index():
    index = "".join(f'<li class="rv"><a href="#svc-{s["code"]}"><span class="no">{s["no"]}</span><span class="name">{s.get("name_br", esc(s["name"]))}</span>{ARROW}</a></li>' for s in SERVICES)
    blocks = "\n".join(svc_block(s, i) for i, s in enumerate(SERVICES))
    worries = "".join(f'<li class="rv">{esc(w)}</li>' for w in WORRIES)
    faq = "\n".join(f'<details class="rv"><summary>{esc(q)}</summary><div class="a">{esc(a)}</div></details>' for q, a in FAQ)
    body = f"""
<section class="hero">
  <div class="media">
    <picture>
      <source media="(max-width:760px)" srcset="assets/img/photo/hero-sq.jpg">
      <img src="assets/img/photo/hero.jpg" alt="" width="1600" height="1100" fetchpriority="high">
    </picture>
  </div>
  <div class="wrap">
    <div class="copy">
      <span class="en rv">Life support membership</span>
      <h1 class="rv"><span class="l">毎日の「もしも」に、</span><span class="l">ひとつ足す安心。</span></h1>
    </div>
    <p class="lead rv">置き配の盗難、固定費の見直し、スマホや家電の故障、わずらわしい広告。暮らしのちいさな不安や困りごとを、まとめて支える会員サービスです。</p>
    <div class="card rv">
      <div class="free"><span class="en">Campaign</span><b>初月から{SITE['free']}</b></div>
      <a class="btn btn-terra btn-block" href="signup.html">お申し込みはこちら {ARROW_BTN}</a>
      <a class="btn btn-outline btn-block" href="contact.html">お問い合わせはこちら {ARROW_BTN}</a>
      <p class="note">お申し込みには販売パートナーの紹介コードが必要です。お持ちでない方は<a href="contact.html?kind=1">お問い合わせ</a>ください。</p>
    </div>
  </div>
</section>

<section class="section intro" id="intro">
  <div class="wrap">
    <div class="grid">
      <div>
        {sh("こんな不安、<br>ありませんか？", "Everyday worries", "大きな保険は重い。でも、何もしないのも不安。暮らしの「よくある困りごと」に、ちょうどいい安心をご用意しました。")}
        <ul class="worries">{worries}</ul>
      </div>
      <div class="photo rv"><img src="assets/img/photo/worry.jpg" alt="" loading="lazy" width="1200" height="1200"></div>
    </div>
  </div>
</section>

<section class="section sand" id="services">
  <div class="wrap">
    {sh("暮らしを支える、<br class=\"sp\">5つのサービス", "Services", "家族の毎日に起こりやすい“困りごと”を、広く・やさしくカバーします。", center=True)}
    <ul class="svc-index">{index}</ul>
    <p class="summary rv">置き配盗難や家電の突然の故障、Wi-Fi接続機器のトラブル、スマホの広告表示など。<br class="pc">暮らしの中で起こる“ちょっとした不安や困りごと”を、まとめてサポートする会員サービスです。</p>
  </div>
</section>

<section class="section blocks">
  <div class="wrap">{blocks}</div>
</section>

<section class="trust">
  <div class="media"><img src="assets/img/photo/trust.jpg" alt="" loading="lazy" width="1600" height="800"></div>
  <div class="wrap">
    <span class="en rv">Our promise</span>
    <h2 class="rv">守られている安心は、<br>想像以上に心地いい。</h2>
    <p class="rv">保険会社との正式提携と、実績あるグループ会社による運営体制のもと、安心してご利用いただけるサービスを提供しています。</p>
    <div class="cta rv"><a class="btn btn-terra" href="signup.html">お申し込みはこちら {ARROW_BTN}</a></div>
  </div>
</section>

<section class="section" id="faq">
  <div class="wrap">
    {sh("よくあるご質問", "FAQ", center=True)}
    <div class="faq">{faq}</div>
  </div>
</section>

<section class="section cta-section">
  <div class="wrap">
    <div class="cta-band rv">
      <div>
        <h2>不安を残さず、安心して<br>お申し込みいただけるように。</h2>
        <p>不明点など遠慮なくご質問ください。ヘルプデスク（{SITE['hours_short']}）がお答えします。</p>
      </div>
      <div class="btns">
        <a class="btn btn-terra" href="signup.html">お申し込みはこちら {ARROW_BTN}</a>
        <a class="btn btn-outline" href="contact.html">お問い合わせはこちら {ARROW_BTN}</a>
      </div>
    </div>
  </div>
</section>
"""
    page("index.html", "", SITE["desc"], body, 0)

# ============================================================
# サービス詳細
# ============================================================
def build_services():
    for s in SERVICES:
        pts = "".join(f"<li>{esc(p)}</li>" for p in s["points"])
        det = "".join(f"<h2>{esc(h)}</h2><p>{esc(t)}</p>" for h, t in s["detail"])
        spec = "".join(f"<div>{esc(k)}</div><div>{esc(v)}</div>" for k, v in s["spec"])
        paras = "".join(f"<p>{esc(p)}</p>" for p in s["paras"])
        others = "".join(f'<li><a href="{o["code"]}.html"><span class="no">{o["no"]}</span><span class="name">{o.get("name_br", esc(o["name"]))}</span>{ARROW}</a></li>' for o in SERVICES if o["code"] != s["code"])
        body = f"""
<section class="svc-hero">
  <div class="wrap">
    <div class="text">
      <div class="breadcrumb"><a href="../index.html">トップ</a> › <a href="../index.html#services">サービス</a> › {esc(s['name'])}</div>
      <div class="meta"><span class="no">{s['no']}</span><span class="name">{esc(s['name'])}</span></div>
      <h1>{s.get("copy_br", esc(s["copy"]))}</h1>
      <div class="body">{paras}</div>
      <p class="fine">{nl(s['fine'])}</p>
      <div class="cta"><a class="btn btn-terra" href="../signup.html">お申し込みはこちら {ARROW_BTN}</a><a class="tlink" href="../contact.html">相談する {ARROW}</a></div>
    </div>
    <div class="photo"><img src="../assets/img/photo/{s['photo']}" alt="" width="1200" height="900"></div>
  </div>
</section>
<div class="wrap">
  <div class="content">
    <h2>サービスの特長</h2>
    <ul class="points">{pts}</ul>
    <h2>サービス概要</h2>
    <div class="kv">{spec}</div>
    {det}
    <h2>料金・お支払い</h2>
    <p>{price_note()}お支払いはクレジットカード決済またはキャリア決済です。最低利用期間や解約金はなく、いつでも解約できます。解約は手続き完了を確認した月の末日に反映され、日割り計算はありません。</p>
    <h2>規約</h2>
    <p><a href="../terms/{s['terms']}.html">{esc(s['terms_name'])} 利用規約</a>　／　<a href="../privacy.html">プライバシーポリシー</a>　／　<a href="../legal.html">特定商取引法に基づく表示</a></p>
    <div class="notice">本ページの内容は概要です。補償の条件・対象外事項などの詳細は利用規約をご確認ください。</div>
  </div>
</div>
<section class="section sand">
  <div class="wrap">
    {sh("ほかのサービス", "Other services", center=True)}
    <ul class="svc-index">{others}</ul>
  </div>
</section>
"""
        page(f"services/{s['code']}.html", s["name"], s["short"], body, 1)

# ============================================================
# 利用規約
# ============================================================
def terms_to_html(text):
    lines = [l.rstrip() for l in text.splitlines()]
    out, toc = [], []
    first = True
    n = 0
    for l in lines:
        if not l.strip():
            continue
        if first:
            first = False
            continue
        m = re.match(r"^(第\d+条（.+?）)$", l)
        if m:
            n += 1
            out.append(f'<h2 id="a{n}">{esc(l)}</h2>')
            toc.append(f'<a href="#a{n}">{esc(l)}</a>')
        elif l in ("附則", "以上"):
            out.append(f'<h2>{l}</h2>' if l == "附則" else f'<p style="text-align:right">{l}</p>')
        elif re.match(r"^(（\d+）|\d+\.\s|【)", l):
            out.append(f'<p class="item">{esc(l)}</p>')
        else:
            out.append(f"<p>{esc(l)}</p>")
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
            inner = f'<div class="notice">「{esc(s["name"])}」の利用規約は現在準備中です。公開まで今しばらくお待ちください。ご不明な点は<a href="../contact.html">お問い合わせ</a>ください。</div>'
            status = "（準備中）"
        alias = f"（サービス名：{esc(s['name'])}）" if s["terms_name"] != s["name"] else ""
        body = f"""
<div class="wrap">
  <div class="page-head">
    <div class="breadcrumb"><a href="../index.html">トップ</a> › <a href="index.html">利用規約</a> › {esc(s['name'])}</div>
    <span class="en">Terms</span>
    <h1>{esc(s['terms_name'])} 利用規約{status}</h1>
    <p>{alias}施行日：{SITE['effective']}　提供：{SITE['company']}</p>
  </div>
  <div class="content terms">{inner}</div>
</div>
"""
        page(f"terms/{s['terms']}.html", f"{s['terms_name']} 利用規約", f"{SITE['name']}「{s['name']}」の利用規約です。", body, 1)
        idx_items.append(f'<li><a href="{s["terms"]}.html">{esc(s["terms_name"])} 利用規約{status}</a>{alias}</li>')
    body = f"""
<div class="wrap">
  <div class="page-head">
    <div class="breadcrumb"><a href="../index.html">トップ</a> › 利用規約</div>
    <span class="en">Terms</span>
    <h1>利用規約</h1>
    <p>サービスごとに利用規約を定めています。お申し込みの前に必ずお読みください。</p>
  </div>
  <div class="content"><ul class="plain">{"".join(idx_items)}</ul>
  <p style="margin-top:24px"><a href="../privacy.html">プライバシーポリシー</a>　／　<a href="../legal.html">特定商取引法に基づく表示</a></p></div>
</div>
"""
    page("terms/index.html", "利用規約", f"{SITE['name']}の各サービス利用規約の一覧です。", body, 1)

# ============================================================
# プライバシーポリシー（株式会社WST の方針）
# ============================================================
def build_privacy():
    c = SITE
    body = f"""
<div class="wrap">
  <div class="page-head">
    <div class="breadcrumb"><a href="index.html">トップ</a> › プライバシーポリシー</div>
    <span class="en">Privacy policy</span>
    <h1>個人情報保護方針<br class="sp">（プライバシーポリシー）</h1>
    <p>{c['company']}（以下「当社」といいます。）は、個人情報の保護に万全を期し、社会・顧客・取引先・従業員の信頼に応えるため、次のとおり方針を定めます。</p>
  </div>
  <div class="content">
    <h2>1. 法令・ガイドライン等の遵守</h2>
    <p>当社は、個人情報の取扱いに関し、個人情報保護法およびマイナンバー法等の法令および個人情報保護委員会のガイドラインその他の法規範を遵守します。</p>
    <h2>2. 個人情報の取得・利用</h2>
    <p>当社は、個人情報を取得する場合は、利用目的を明確にし、適切な方法により取得・利用します。</p>
    <h2>3. セキュリティ対策</h2>
    <p>当社は、個人情報の安全性確保の重要性を認識し、不正アクセス、個人情報の紛失、破壊、改ざんおよび漏えいリスクに対して予防措置を講じ、セキュリティを確保します。</p>
    <h2>4. 委託先の監督</h2>
    <p>当社は、個人情報の取扱いを外部に委託する場合は、委託先において適切な取扱いが確保されるよう必要かつ適切な監督を行います。</p>
    <h2>5. 安全管理措置</h2>
    <p>当社の業務において個人情報を取り扱うすべての者は、個人情報の重要性を認識し、法令・ガイドライン等および個人情報について適切な取得、利用、提供、廃棄等の方法を定めた社内規程に従い適切に取り扱います。</p>
    <h2>6. 管理体制の継続的改善</h2>
    <p>当社は、社会動向を注視しつつ個人情報の管理体制を見直し、継続的に改善します。</p>
    <h2>7. 対応窓口の設置</h2>
    <p>当社は、保有する個人情報に関する質問・苦情および開示等に関する窓口を設置します。</p>

    <h2 class="big">個人情報の取扱いについて</h2>
    <p>当社は、個人情報保護法等の関係法令等を遵守し、以下のとおり個人情報を取り扱います。</p>
    <h3>1. 個人情報の取得・利用</h3>
    <p>当社は、個人情報を取得する際、利用目的を公表または通知し、適正な手段によって取得します。当社は、利用目的の達成に必要な範囲内で、取得した個人情報を適正に利用します。</p>
    <h3>2. 個人情報・保有個人データの利用目的</h3>
    <p>当社は、（1）業務等の範囲において、取得した個人情報および保有個人データを（2）利用目的の範囲内で利用します。</p>
    <p class="sub">(1) 業務等の範囲</p>
    <ul><li>ライフラインサポート業務</li><li>キャンペーン告知業務</li><li>各種当社取扱商品のご案内業務</li><li>その他会社の目的として登記されている業務</li></ul>
    <p class="sub">(2) 利用目的</p>
    <p>①取引先（法人等の団体である場合はその役職員）に関する個人情報・保有個人データ</p>
    <ul><li>製品・サービスの提供または受領など契約に基づく義務の履行・権利の行使</li><li>業務上の連絡、打合せおよびお問い合わせへの対応その他業務実施のために必要な対応</li><li>製品・サービスに関連するアフターサービスのご案内および提供</li><li>製品・サービスに関連する企画提案、新製品・サービスのご案内、その他企業ＰＲ</li><li>上記各業務に関連・付随するアンケート調査の実施</li><li>上記に関連・付随する各種対応</li></ul>
    <p>②受託業務に関して取得する個人情報・保有個人データ</p>
    <ul><li>業務上の調査、統計処理、解析、確認、関連資料の作成等</li><li>受託業務遂行のためのアンケート調査および住民説明会の実施等</li></ul>
    <h3>3. 共同利用について</h3>
    <p>当社は、個人情報について以下のとおり共同利用します。</p>
    <ul><li>共同して利用される個人データの項目：氏名、生年月日、性別、住所、電話番号、メールアドレスその他利用目的を達成するために必要な項目</li><li>共同して利用する者の範囲：当社およびそのグループ会社、関連会社、取引先、その他当社と関わりのある法人格</li><li>利用目的：上記「2. 個人情報・保有個人データの利用目的」をご参照ください。</li></ul>
    <h3>4. 第三者提供について</h3>
    <p>当社は、原則として、本人の同意を得ずに個人情報を第三者に提供しません。ただし、以下の場合は、本人の同意なく個人情報を提供することがあります。</p>
    <ul><li>法令に基づく場合</li><li>人の生命、身体または財産の保護のために必要がある場合であって、本人の同意を得ることが困難である場合</li><li>公衆衛生の向上または児童の健全な育成の推進のためにとくに必要がある場合であって、本人の承諾を得ることが困難である場合</li><li>国の機関若しくは地方公共団体またはその委託を受けた者が法令の定める事務を遂行することに対して協力する必要がある場合で、本人の同意を得ることによりその事務の遂行に支障をおよぼすおそれがある場合</li></ul>
    <h3>5. 個人情報処理の外部委託</h3>
    <p>当社は、個人情報取扱い業務の全部または一部を業務に応じて当社が個人情報に関する機密保持契約を締結した企業に対して業務委託することがあります。</p>
    <h3>6. データ内容の正確性の確保等</h3>
    <p>当社は、利用目的の達成に必要な範囲で個人データを正確かつ最新の内容に保つとともに、利用する必要がなくなったときは当該個人データを遅滞なく消去することに努めます。</p>
    <h3>7. 保有個人データの開示等の請求に対する対応</h3>
    <p>保有個人データの利用目的・内容に関する開示、訂正・追加・削除、利用停止・消去、第三者提供の停止および第三者提供記録の開示の請求については、下記8.の【当社の問合せ窓口】までご連絡ください。なお、以下の拒否事由がある場合には、非開示とします。</p>
    <ul><li>請求書と本人確認書類の氏名や住所が一致しないなど本人確認ができない場合</li><li>代理人による請求の際に代理権が確認できない場合</li><li>請求書の記載事項に不備があった場合</li><li>請求者に関する保有個人データの不存在または開示対象ではない場合</li><li>本人または第三者の生命、身体、財産その他の権利利益を侵害するおそれがある場合</li><li>当社の業務の適正な実施に著しい支障を及ぼすおそれがある場合</li><li>他の法令に反することとなる場合</li></ul>
    <h3>8. 個人情報取扱業者名および個人情報に関する質問・苦情の問合せ先</h3>
    <p>当社における個人情報に関する質問・苦情に関しては、以下の問合せ窓口にご連絡ください。</p>
    <div class="kv">
      <div>個人情報取扱業者名</div><div>{c['company']}</div>
      <div>所在地</div><div>{c['zip']} {c['addr']}</div>
      <div>電話</div><div>{c['privacy_tel']}</div>
    </div>
  </div>
</div>
"""
    page("privacy.html", "プライバシーポリシー", f"{SITE['name']}（{SITE['company']}）の個人情報保護方針です。", body, 0)

# ============================================================
# 特商法
# ============================================================
def build_legal():
    c = SITE
    rows = [
        ("販売業者", c["company"]),
        ("運営統括責任者", c["rep"]),
        ("所在地", f"{c['zip']} {c['addr']}"),
        ("電話番号", c["tel"]),
        ("お問い合わせ", f'<a href="mailto:{c["email"]}">{c["email"]}</a><br><a href="contact.html">お問い合わせフォーム</a>（受付時間：{c["hours"]}）'),
        ("販売価格", "購入画面において表示いたします。"),
        ("お支払い方法", "クレジットカード払い（Visa、MasterCard、JCB、アメリカン・エキスプレス、ダイナースクラブ、ディスカバー）の一括払い、またはキャリア決済"),
        ("お支払い時期", "毎月、所定の期日に当月分をお支払いいただきます。"),
        ("サービスの提供時期", "お申込み完了後、当社所定の方法でご案内した日からご利用いただけます。"),
        ("返品・キャンセルについて", "お客様都合による返金・キャンセルは承っておりません。本サービスは通信販売に該当するため、クーリング・オフの適用はありません。なお、最低利用期間や解約金はなく、いつでも解約できます。"),
        ("その他の特別な条件", "サービスの利用に際して特別な条件がある場合は、都度サービスサイト上に表示します。"),
    ]
    kv = "".join(f"<div>{k}</div><div>{v}</div>" for k, v in rows)
    body = f"""
<div class="wrap">
  <div class="page-head">
    <div class="breadcrumb"><a href="index.html">トップ</a> › 特定商取引法に基づく表示</div>
    <span class="en">Legal notice</span>
    <h1>特定商取引法に基づく表示</h1>
  </div>
  <div class="content"><div class="kv">{kv}</div></div>
</div>
"""
    page("legal.html", "特定商取引法に基づく表示", f"{SITE['name']}（{SITE['company']}）の特定商取引法に基づく表示です。", body, 0)

# ============================================================
# お申し込み・お問い合わせ
# ============================================================
def build_signup():
    body = f"""
<div class="wrap">
  <div class="page-head">
    <div class="breadcrumb"><a href="index.html">トップ</a> › お申し込み</div>
    <span class="en">Sign up</span>
    <h1>お申し込みについて</h1>
    <p>{SITE['name']}は、サービス説明不足や認識相違によるトラブルを防ぐため、販売パートナーの「紹介コード」をお持ちの方限定でお申し込みいただけます。初月から{SITE['free']}。</p>
  </div>
  <div class="content">
    <ol class="flow">
      <li><b>紹介コードを確認</b><span>販売パートナー（代理店）からお渡しした紹介コードをご用意ください。お持ちでない方は、一時的な紹介コードを発行しますのでお問い合わせください。</span></li>
      <li><b>お申し込み手続き</b><span>お申込み窓口で紹介コードとお客様情報をご登録いただきます。</span></li>
      <li><b>決済登録</b><span>ご登録のメールアドレスまたはSMSに決済登録URLをお送りします。お客様ご自身で決済情報をご入力いただくと、お申し込み完了です。</span></li>
      <li><b>ご利用開始</b><span>完了後、各サービスのご案内と利用規約の控えをお送りします。</span></li>
    </ol>
    <div class="signup-cta">
      <a class="btn btn-terra" id="signupBtn" href="contact.html?kind=5">お申し込み手続きへ進む {ARROW_BTN}</a>
      <a class="btn btn-outline" href="contact.html?kind=1">紹介コードをお持ちでない方 {ARROW_BTN}</a>
    </div>
    <p class="fine">お申し込み前に<a href="terms/index.html">利用規約</a>・<a href="privacy.html">プライバシーポリシー</a>・<a href="legal.html">特定商取引法に基づく表示</a>をご確認ください。</p>
  </div>
</div>
"""
    page("signup.html", "お申し込み", f"{SITE['name']}のお申し込み方法のご案内です。", body, 0)

def build_contact():
    c = SITE
    opts = "".join(f"<option>{k}</option>" for k in CONTACT_KINDS)
    body = f"""
<div class="wrap">
  <div class="page-head">
    <div class="breadcrumb"><a href="index.html">トップ</a> › お問い合わせ</div>
    <span class="en">Contact</span>
    <h1>お問い合わせ</h1>
    <p>サービス内容やお申し込み、解約についてのご相談はこちらから。ご入力いただいた日より3営業日以内に、ご登録のメールアドレスへご返信します（ヘルプデスク：{c['hours_short']}）。</p>
  </div>
  <div class="content">
    <form id="contactForm" class="form" novalidate>
      <div class="field"><label for="kind">お問い合わせ種別</label><select id="kind" name="kind">{opts}</select></div>
      <div class="field"><label for="name">お名前<span class="req">必須</span></label><input id="name" name="name" type="text" autocomplete="name" placeholder="山田 太郎" required></div>
      <div class="field"><label for="email">メールアドレス<span class="req">必須</span></label><input id="email" name="email" type="email" autocomplete="email" placeholder="example@example.com" required></div>
      <div class="field"><label for="tel">電話番号</label><input id="tel" name="tel" type="tel" autocomplete="tel" placeholder="090-0000-0000"><div class="help">お急ぎの場合はご記入ください。</div></div>
      <div class="field"><label for="message">お問い合わせ内容<span class="req">必須</span></label><textarea id="message" name="message" required placeholder="ご契約中の方は、ご契約のサービス名や紹介コードもあわせてご記入ください。"></textarea></div>
      <label class="check"><input type="checkbox" name="agree"><span><a href="privacy.html" target="_blank" rel="noopener">プライバシーポリシー</a>に同意のうえ送信します。</span></label>
      <div class="err" role="alert"></div>
      <button type="submit" class="btn btn-primary btn-block">送信する</button>
    </form>
    <p class="fine" style="margin-top:28px">迷惑メール設定をされている場合は、当社ドメインからのメールを受信できるようご設定ください。</p>
  </div>
</div>
"""
    page("contact.html", "お問い合わせ", f"{SITE['name']}へのお問い合わせフォームです。", body, 0)

    body = f"""
<div class="wrap">
  <div class="page-head center">
    <span class="en">Thank you</span>
    <h1>お問い合わせを受け付けました</h1>
    <p>ご入力いただいた日より3営業日以内に、ご登録のメールアドレスへご返信いたします。今しばらくお待ちください。</p>
    <p style="margin-top:32px"><a class="btn btn-outline" href="index.html">トップページへ戻る</a></p>
  </div>
</div>
"""
    page("thanks.html", "送信完了", "お問い合わせを受け付けました。", body, 0)

# ============================================================
# ログイン・マイページ
# ============================================================
def build_auth():
    body = f"""
<div class="wrap">
  <div class="auth">
    <span class="en">Member login</span>
    <h1>会員ログイン</h1>
    <p class="sub">ご登録のメールアドレスとパスワードを入力してください。</p>
    <form id="loginForm" class="form" novalidate>
      <div class="field"><label for="email">メールアドレス</label><input id="email" name="email" type="email" autocomplete="username" required></div>
      <div class="field"><label for="password">パスワード</label><input id="password" name="password" type="password" autocomplete="current-password" minlength="8" required></div>
      <div class="err" role="alert"></div>
      <button type="submit" class="btn btn-primary btn-block">ログイン</button>
    </form>
    <div class="links"><a href="contact.html?kind=7">パスワードをお忘れの方</a><a href="signup.html">新規お申し込み</a></div>
  </div>
</div>
"""
    page("login.html", "会員ログイン", f"{SITE['name']}会員ログインページ。", body, 0)

    items = "".join(f"""<div class="my-item" data-code="{s['code']}">
      <div class="no">{s['no']}</div>
      <div><h3>{esc(s['name'])}</h3><div class="st">未加入</div></div>
      <div class="act"><button type="button" class="btn btn-primary btn-sm">申し込む</button></div>
    </div>""" for s in SERVICES)
    body = f"""
<div class="wrap" id="mypage">
  <div class="page-head">
    <span class="en">My page</span>
    <h1>マイページ</h1>
  </div>
  <div class="my-grid">
    <aside class="my-side">
      <div class="name">—</div>
      <div class="mail">—</div>
      <p class="cnt">ご利用中のサービス：<b class="count">0</b> 件</p>
      <nav>
        <a href="#services">ご契約サービス</a>
        <a href="contact.html">お支払い方法の変更</a>
        <a href="contact.html">登録情報の変更</a>
        <a href="contact.html">お問い合わせ</a>
        <a href="#" class="logout">ログアウト</a>
      </nav>
    </aside>
    <div>
      <h2 id="services">ご契約サービス</h2>
      <div class="my-list">{items}</div>
      <p class="notice" style="margin-top:16px">お申し込み・解約はお手続き完了後にメールでご案内します。解約は当月末に反映され、日割り計算はありません。</p>
    </div>
  </div>
</div>
"""
    page("mypage.html", "マイページ", f"{SITE['name']}会員マイページ。", body, 0, extra='<meta name="robots" content="noindex">')

def build_404():
    body = """
<div class="wrap">
  <div class="page-head center">
    <span class="en">404</span>
    <h1>ページが見つかりません</h1>
    <p>URLが変更されたか、削除された可能性があります。</p>
    <p style="margin-top:32px"><a class="btn btn-outline" href="index.html">トップページへ戻る</a></p>
  </div>
</div>
"""
    page("404.html", "ページが見つかりません", "ページが見つかりません。", body, 0)

if __name__ == "__main__":
    build_index(); build_services(); build_terms(); build_privacy(); build_legal(); build_signup(); build_contact(); build_auth(); build_404()
    print("done")
