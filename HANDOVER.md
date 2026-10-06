# 引き継ぎ：クレーン日報アプリ（GitHub Pages 版）＋ EXAmuse 景品仕入れ自動化
2026-10-06 19:30 時点

## 0. 今日やったこと（結論）
- クレーン日報アプリを claude.ai のアーティファクトから **GitHub Pages ＋ Google Apps Script** に移植した。
  理由：アーティファクトでは「入力できる人＝アプリを書き換えられる人（編集者）」になり、バイト追加時に壊されるリスクがあったため。
- 新構成では、利用者は URL と PIN だけで使え、アプリの修正はこのリポジトリへ push した人（＝菊地さん／Claude Code）しかできない。
- 実機確認済み：PIN ログイン、経費／巡回ログ／景品登録の保存とスプシ反映、削除でシートの行も消えること。

## 1. 新アプリの場所
| もの | 場所 |
|---|---|
| 公開URL（スタッフが使う） | https://skikuchi-hub.github.io/cursor-/ |
| リポジトリ | https://github.com/skikuchi-hub/cursor- |
| 公開ブランチ（GitHub Pages のソース） | `claude/examuse-prize-handover-8s2xx8`（root） |
| Apps Script | 日報スプシにバインド。ウェブアプリURL：`https://script.google.com/macros/s/AKfycbzAD2-ZwW18IJxlIED4T5WMwpGWzOqM_NA8irYQSzhZ1y7Rjw7UkSt7lWDU5HXsZquAUQ/exec`（config.js に設定済み） |
| 日報スプシ | https://docs.google.com/spreadsheets/d/1yEl5weYRtWN5Ydp2lSxnqnQCyC9W-SameJpIF8o6eYs |

リポジトリの中身
```
index.html              アプリ本体（旧アーティファクトの画面をそのまま移植。データ層だけ Apps Script 連携に差し替え）
config.js               Apps Script ウェブアプリの URL
icon-180.png            ホーム画面アイコン
apps-script/Code.gs     スプシ側 API（Apps Script に貼ってあるものと同じ）
apps-script/appsscript.json  マニフェスト（timeZone Asia/Tokyo）※スプシ側へはまだ未反映。スプシが日本時間なら不要
README.md               セットアップ手順・運用メモ
HANDOVER.md             この文書
```

## 2. 仕組み
- **認証**：スプシ「スタッフ」タブ（名前／PIN／権限／有効／メモ）。PIN が一致した人として記録される。権限「管理者」だけ担当を切り替えて記録できる。「有効」を外すと入れなくなる。PIN は重複させない。
- **保存**：アプリ → Apps Script（POST, text/plain JSON）→
  1. 隠しタブ `_app_db` に JSON で保存（アプリが読む正。col/id/createdAt/updatedAt/by/json）
  2. 同時に各タブへ行を追加：weekly→「巡回ログ」A〜J ＋「部屋別ログ」A〜L、prizes→「景品マスタ」A〜F・K、expenses→「経費台帳」A〜F。各タブの最終列に「アプリID」列を自動追加して対応づけ。アプリで削除するとタブの行も消える。
  3. 旧「転記」機能は不要になった（ヘッダーのボタンは「📗 シート」リンクに変更）。sentAt は保存時に自動で入る。
- **読み込み**：起動時と60秒ごと（画面が前面のとき）に bootstrap を取得。景品マスタ・過去他社データはタブから毎回直接読む → **毎時の同期ルーチン（trig_013n9gxPcuMzu5RkSXjxoRX5）は新アプリには不要**。
- **オフライン**：前回の内容を端末に保持して表示のみ。保存はできない（トーストで案内）。
- **PIN を入れ直す**：ヘッダーの「担当：◯◯」を1.2秒長押し。
- API のアクション：`bootstrap` / `add` / `patch` / `remove` / `put`（詳細は Code.gs 冒頭コメント）。

## 3. 日々の修正のやり方（Claude Code から）
- 画面・計算の修正：`index.html` を直して **push するだけ**。GitHub Pages が1〜2分で反映。
  - 作業ブランチは `claude/examuse-prize-handover-8s2xx8`（Pages のソースなので、ここに push すると即公開される）。
  - ローカル確認は `scratchpad` の模擬API（Python）＋Playwright で行った。構文チェックは `node --check` で可能。
- Apps Script（Code.gs）の修正：リポジトリの `apps-script/Code.gs` を直す → Apps Script エディタに貼り直して保存 → **デプロイ → デプロイを管理 → 編集 → 新バージョン → デプロイ**（URL は変わらない）。「新しいデプロイ」を作ると URL が変わるので、その場合は config.js も更新して push。
- GitHub Pages は public リポジトリ。URL を知っていれば誰でも開けるが、PIN が無いと何も見えない・書けない。

## 4. 次にやること（未完了）
1. ~~実機テスト~~ 完了（2026-10-06 19:50）
2. ~~部屋別ログの確認~~ 完了
3. **石原さんへ切り替え**：「スタッフ」タブの石原さんの PIN を伝える。新URLをホーム画面に追加してもらう。
4. **旧アーティファクトのデータ移行**（https://claude.ai/code/artifact/10dbc25d-f011-4fbc-bfb0-33a4b3154aab）：
   - 旧 db に残っていたのは 巡回ログ6件（石原さん、週2026-10-05。うち4件は未転記）と目標設定1件。prizes/expenses は空。
   - 移行JSONを Drive に置き（`クレーン日報_旧アプリ移行データ_20261006.json`、ID 1VMiTTV6WhZJvxlVaIRccI90-q7NS18dG）、Code.gs に `importFromDrive()` を追加済み。
     Apps Script エディタに最新の Code.gs を貼り直して `importFromDrive` を実行すれば取り込まれる（再実行しても二重にならない。再デプロイ不要）。
   - 注意：福岡下山門通り店は同じ週に各機械2件ずつ入っている（10/5入力と10/6入力）。重複なら新アプリで片方を削除する（シートの行も消える）。
   - 移行が済んだら、石原さんの共有を外す or 閲覧者に落とす。毎時同期ルーチン trig_013n9gxPcuMzu5RkSXjxoRX5 は無効化してよい。
5. **appsscript.json の反映**（任意）：Apps Script のプロジェクト設定で「マニフェストを表示」→ `timeZone` を Asia/Tokyo に。スプシのタイムゾーンが日本なら省略可。
6. **バイト追加時**：「スタッフ」タブに行を追加（名前・PIN・権限「スタッフ」・有効✓）→ URL と PIN を渡すだけ。

## 5. 既知の注意点
- Apps Script の応答に1〜3秒かかる。保存ボタンは押下後に無効化される設計。
- 複数人が同時に保存しても LockService で直列化されるが、他人の入力が画面に出るのは次回の取得（最大60秒）後。
- 「巡回ログ」K〜O、「景品マスタ」G〜J、「経費台帳」G は配列数式のまま。行の追加・削除で数式範囲は自動調整される。
- チャット本文からコードをコピーすると引用符が変換されて構文エラーになる。コードは GitHub の「Copy raw file」から取る。
- GitHub への push は Claude GitHub App をリポジトリに入れて解決済み（今日の作業中に 403 で止まった経緯あり）。

## 6. EXAmuse 景品仕入れ自動化（変更なし。前回の引き継ぎそのまま）
- 関係者：菊地（amuse@exploration-holdings.jp、Apple Mail アカウント「EXAmuse」、Mac）／石原さん（巡回担当、Thunderbird。スプシのメニューから発注要求）／仕入先 株式会社インフィニティ inf_main@8infinity.jp
- 仕入れ想定商品スプシ：https://docs.google.com/spreadsheets/d/1c2dDei3-fMUtsAFXl4cnqvTMTuhjKrLEVSi0NSwEtAw
  タブ：商品一覧（A受信日…N発注ケース数 O発注個数 P発注金額 Q発注備考 R発注状況 …V商品キー W メール原文 X チェック結果 Y 機械タイプ）／発注要求／画像一覧／発注履歴／設定
  メニュー「EXAmuse発注」：①発注内容チェック ②Mailに下書き作成 ③発注メール送信 ④下書きを手動で送った→発注済みにして景品マスタへ登録／状況確認／体裁を整える
  Apps Script はバージョン8。コードは Mac の ~/EXAmuse景品仕入れ/GoogleSheets連携_AppsScript.gs。doPost を変えたときだけ「新しいデプロイ」が必要で、URL が変わるので Mac の gsheet.json も更新。
- 景品マスタへの追加ルール：発注メールを③送信（または Mac のボタンで送信）したときのみ自動追加。下書きは追加しない。既存行は上書きせず同名の直下に挿入。手動送信は④で登録。
- Mac 側：~/Library/Application Support/examuse-order/（examuse_common.py, examuse_sync.py, examuse_gsheet.py, examuse_order.py, gen_gs.py, master_snapshot.py, gsheet.json, db.json）。出力 ~/EXAmuse景品仕入れ（デスクトップのものはショートリンク。実体を戻さない）。launchd com.exploration.examuse-sync（2分ごと＋Mail更新時）。ログ ~/Library/Logs/examuse-sync.log
- 流れ：Apple Mail のインフィニティからのメール → 解析 → 商品一覧へ追加（画像は Drive「EXAmuse景品画像」経由）→ 数量入力 → ①→②or③ → 発注要求タブ → Mac が発注書 xlsx 作成＋Mail 下書き/送信（BCC amuse@…必須）→ 発注状況・発注履歴更新 → 送信時のみ景品マスタ追加。発注No EH-YYYYMMDD-連番。発注書 ~/EXAmuse景品仕入れ/発注書/発注書_YYYYMMDD_n.xlsx
- 状態：EH-20261006-1（10商品 ¥455,560 税抜）は④で登録済み。景品マスタ27行。EH-20261005-1 は未送信テスト、登録しない。待機中の発注要求なし。
- よくある依頼：「発注要求が処理中で止まってる」→ Mac 起動確認と examuse-sync.log。3分以上「処理中(Mac)」で発注Noが無ければ自動再取得。発注・送信・発注書作成は Mac 上でしか動かない。
