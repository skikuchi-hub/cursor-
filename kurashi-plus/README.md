# くらしプラス（KURASHI+）サービスサイト

株式会社WST の月額ライフサポートサービス「くらしプラス」のサービスサイト。
HOME LINK（home-link.jp）と同じ5サービス・同じ条件で、名称・ロゴ・配色・文章を変えた別ブランドのサイトです。
静的 HTML だけで動くので、GitHub Pages でもお名前.com などのレンタルサーバーでもそのまま公開できます。

```
index.html            トップ（困りごと・5つのサービス・FAQ・お申し込み導線）
signup.html           お申し込みのご案内（紹介コードの流れ。config.js の signupUrl で会員システムへ接続）
services/*.html       サービス詳細（okihai / wifi / gifukatsu / kumamori / kaden）
terms/*.html          利用規約（index + サービスごと。kumamori / kaden は準備中表示）
privacy.html          プライバシーポリシー
legal.html            特定商取引法に基づく表記
contact.html          お問い合わせフォーム  → thanks.html
login.html            会員ログイン         → mypage.html
404.html
config.js             接続設定（フォーム送信先・会員API）
assets/css/style.css  スタイル
assets/js/main.js     メニュー・フォーム・ログイン・マイページの動き
assets/img/           ロゴ（logo.svg / logo.png / mark.svg）、アイコン、OG画像
apps-script/Code.gs   お問い合わせ受信用 Apps Script（スプシ記録＋メール通知＋自動返信）
tools/build.py        ページ生成スクリプト（文言はここを直して再実行）
tools/terms_raw/*.txt 利用規約の原文（テキスト）
tools/render.js       ロゴPNG・OG画像・確認用スクリーンショット生成（Playwright）
```

## 文言を直すとき

`tools/build.py` の `SITE` / `SERVICES` / `FAQ` を編集して

```
python3 tools/build.py
```

を実行すると全ページが書き直されます（HTML を直接編集すると次回の生成で上書きされます）。
利用規約は `tools/terms_raw/<code>.txt` を置き換えて再実行。クマモリ・家電保証の規約テキストを
`kumamori.txt` / `kaden.txt` として置けば「準備中」が自動で本文に変わります。

## お問い合わせフォームの接続

1. Google スプレッドシートを新規作成 → 拡張機能 → Apps Script に `apps-script/Code.gs` を貼り付け
2. デプロイ → ウェブアプリ（実行ユーザー：自分／アクセス：全員）→ URL を控える
3. `config.js` の `contactApi` にその URL を入れて push

`contactApi` が空のあいだは、送信ボタンでメールソフト（info@wst-inc.jp 宛）が開く方式で動きます。

## 会員ログイン／マイページ

`config.js` の `authApi` が空のあいだはフロントだけで動くデモ表示です（入力したメールで
ログインしたことにし、申込・解約の状態はブラウザ内に保存）。本番の会員システム（HOME LINK の
マイページ設計書と同じ API 構成）ができたら `authApi` にベース URL を入れ、`main.js` の
ログイン処理をその API に合わせてください。

## 公開

- GitHub Pages：リポジトリの Settings → Pages → Branch を公開ブランチ／root にする
- お名前.com 等：このフォルダの中身をそのまま FTP でアップロード（`tools/` と `apps-script/` は不要）
- 独自ドメインを当てる場合は、GitHub Pages なら `CNAME` ファイルを追加して DNS を設定
