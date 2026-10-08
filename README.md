# クレーンログ（GitHub Pages 版）

スタッフが巡回・景品・経費を入力するアプリ。入力はその場で Google スプレッドシート
「クレーンゲーム日報」の各タブに書き込まれる。アプリ本体は GitHub Pages で配信し、
修正はこのリポジトリへの push だけで反映される（利用者はアプリを書き換えられない）。

```
index.html            アプリ本体（画面・ロジック）
config.js             接続設定（Apps Script ウェブアプリの URL）
icon-180.png          ホーム画面アイコン
apps-script/Code.gs   スプレッドシート側 API（Apps Script）
apps-script/appsscript.json  Apps Script のマニフェスト
```

## 仕組み

- 記録は訪問ごと。売上欄は機械に出ている **今月の累計** を入力し、前回訪問との差分（今回分）が記録される。
- 削除は登録した本人と管理者だけ。

- 利用者はURLを開き、スタッフごとの **PIN** を入れる（端末に記憶、2回目以降は不要）。
- 保存はすべて Apps Script 経由。Apps Script は
  1. 隠しタブ `_app_db` にアプリの記録を JSON で保存（アプリが読む正）
  2. 同時に「巡回ログ」「部屋別ログ」「景品マスタ」「経費台帳」へ行を追加（旧「転記」の自動化）
  3. 各タブの最終列「アプリID」で行を対応づけ、アプリで削除するとタブの行も消える
- 景品マスタ・過去他社データは毎回タブから読んでアプリに返す（別途の同期は不要）。
- 60秒ごと、またはアプリを前面に戻したときに最新を取り直す。
- 「仕入れ」タブは、仕入れ想定商品スプシ（EXAmuse 発注システム）の「商品一覧」を読んでカード表示し、
  見送り／保留／発注の判断と「発注要求」タブへの書き込みを行う（Mac 側の発注処理はそのまま）。詳細は HANDOVER.md。

## 初回セットアップ

### 1. Apps Script をデプロイ（スプレッドシート側）

1. スプレッドシート「クレーンゲーム日報」を開き、**拡張機能 → Apps Script**
2. `apps-script/Code.gs` の中身を `コード.gs` に貼り付けて保存（⌘S）
3. プロジェクトの設定（歯車）→「appsscript.json マニフェストを表示」を有効にし、
   `apps-script/appsscript.json` の中身を貼り付けて保存（タイムゾーンを Asia/Tokyo にするため）
4. エディタ上部の関数選択で `setup` を選んで ▶ 実行（初回は権限の承認が出る）
   → 「スタッフ」タブと `_app_db` タブができる。「スタッフ」タブに初期PINが入っている
5. **デプロイ → 新しいデプロイ → 種類：ウェブアプリ**
   - 次のユーザーとして実行：**自分**
   - アクセスできるユーザー：**全員**
   - 表示された **ウェブアプリのURL** を控える

### 2. config.js に URL を入れる

`config.js` の `api` に手順1のURLを入れて push する（Claude Code に「このURLを設定して」と頼めばよい）。

### 3. GitHub Pages を有効にする

リポジトリの **Settings → Pages → Build and deployment → Source: Deploy from a branch**、
Branch にこのアプリの入ったブランチ、フォルダ `/ (root)` を選んで Save。
数分後に `https://<ユーザー名>.github.io/<リポジトリ名>/` で開ける。

### 4. スタッフへの配布

- 「スタッフ」タブで名前・PIN・権限（管理者／スタッフ）・有効を管理する
  - PIN は重複しないこと。辞めた人は「有効」のチェックを外す
  - 管理者は担当を切り替えて記録できる。スタッフは PIN の本人として記録される
- URL と PIN を渡す。iPhone は Safari の共有 → 「ホーム画面に追加」でアプリのように使える

## 日々の修正

画面や計算の修正は `index.html` を直して push するだけ。1分ほどで反映される。
Apps Script 側（`Code.gs`）を変えたときの手順（案内するときは必ず対象スプシの URL を添える）：

1. スプレッドシート「クレーンゲーム日報」 https://docs.google.com/spreadsheets/d/1yEl5weYRtWN5Ydp2lSxnqnQCyC9W-SameJpIF8o6eYs
   → 拡張機能 → Apps Script を開き、GitHub の `apps-script/Code.gs` を **Copy raw file** でコピーして `コード.gs` に貼り直して保存
2. （指示があれば）指定の関数を選んで ▶ 実行
3. **デプロイ → デプロイを管理 → 編集 → バージョン：新バージョン → デプロイ**（URLは変わらない）

## 手動メンテ関数（Apps Script エディタから実行）

`setup`（初期化）／`importFromDrive`（旧アプリ移行）／`repairDates`（日付の書き直し）／`fixVisitDates`（移行分の訪問日修正）／
`recomputeSalesDeltas`（累計→差分の再計算）／`rebuildPrizeStats`（景品実績の作り直し）／`importPhotoChecks`（写真チェック結果の取り込み）。詳細は HANDOVER.md、写真の自動チェックは docs/PHOTO_CHECK.md。

## PIN を入れ直す

アプリ上部の「担当：◯◯」を1.2秒長押しすると PIN 入力に戻れる（端末を他の人に渡すときなど）。
