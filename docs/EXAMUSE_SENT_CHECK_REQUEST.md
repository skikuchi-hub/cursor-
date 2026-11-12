# 依頼②：手で送った注文メールを自動で「発注済み」にする（Mac 上の Claude セッション向け 作業指示）

この文書は、Mac 上（Claude デスクトップアプリ、デスクトップのフォルダを開いたセッション）で実装してもらうための指示書です。
クラウドの共通セッションからは Mac 内のファイルに届かないため、ここに必要な情報をまとめています。

## まず読むもの
- このリポジトリ `HANDOVER.md` の 7 章「EXAmuse 景品仕入れ自動化」（流れ・ファイル配置・④の意味）
- `tools/examuse/examuse_common.py`（Apple Mail を AppleScript で読む `list_mail_ids` / `fetch_source`、`MAIL_ACCOUNT="EXAmuse"`、`MAIL_BOX="INBOX"`）
- `tools/examuse/examuse_sync.py`（2 分ごとのループ。`process_requests` が発注要求を処理）
- Mac 側の本番ファイル：`~/Library/Application Support/examuse-order/`（examuse_common.py, examuse_sync.py, **examuse_gsheet.py**, examuse_order.py, gsheet.json, db.json）。リポジトリに無いのは examuse_gsheet.py と examuse_order.py。
- Apps Script：`~/EXAmuse景品仕入れ/GoogleSheets連携_AppsScript.gs`（バージョン 8）。メニュー「EXAmuse発注」の **④ 下書きを手動で送った→発注済みにして景品マスタへ登録／発注履歴更新** の関数と `doPost` を読む。

## やりたいこと
Apple Mail（アカウント EXAmuse、amuse@exploration-holdings.jp）で、Mac が作った下書き（件名に 発注No `EH-YYYYMMDD-n` を含む）を菊地さんが **手で送信** したら、人が ④ を押さなくても自動で ④ と同じ処理（発注済み＋景品マスタ登録＋発注履歴更新）が走るようにする。

## 仕様
1. `examuse_sync.py` の 2 分ループで、Apple Mail の **送信済みメールボックス**（アカウント EXAmuse の「Sent Messages」等。名前は AppleScript で `sent mailbox` を使うか実機で確認）を見る。宛先に `inf_main@8infinity.jp` を含み、件名または本文から発注No `EH-\d{8}-\d+` が取れるメールを対象にする。
2. 発注No ごとに一度だけ処理する。`db.json` に `sent_done: {発注No: {message_id, at}}` のように記録し、二重登録しない。スプレッドシート側の発注状況が既に「発注済み」なら登録せず記録だけ残す。
3. ④ の処理は **Apps Script 側の既存関数をそのまま使う**。`doPost` に既にその action があるならそれを呼ぶ。無い場合、`doPost` を変えると「新しいデプロイ」が必要で URL が変わり `gsheet.json` の更新も要るので、できるだけ避ける。代替：Mac 側（examuse_gsheet.py）で発注状況・景品マスタ・発注履歴を直接書く既存の関数があるならそれを使う。どうしても doPost を変えるときは、新しいデプロイ → gsheet.json 更新 → HANDOVER 7 章に手順を書く。
4. あいまいなとき（発注No が 2 つ以上、発注要求と商品が一致しない、スプシに該当発注No が無い）は **ログだけ出して何もしない**。`~/EXAmuse景品仕入れ/examuse-sync.log` に `[送信済み検知]` で分かる行を出す。
5. **メールは絶対に送らない**（下書き作成も不要）。スプレッドシートの行を消さない。
6. 失敗しても 2 分ループ全体を止めない（try/except で囲み、ログ）。
7. コードはこのリポジトリの `tools/examuse/` に入れる（examuse_common.py / examuse_sync.py を更新。examuse_gsheet.py に手を入れたなら、そのファイルもリポジトリに追加してよい。gsheet.json・db.json は秘密なので入れない）。
8. Mac への配置手順を書く：`~/Library/Application Support/examuse-order/` の該当ファイルを差し替え、ループ（launchd か常駐プロセス）を再起動する手順。実機で `python3 examuse_sync.py --quiet` を一度手で走らせてログを確認する。
9. `HANDOVER.md` の 7 章に追記：送信済み検知の仕組み、`db.json` の `sent_done`、ログの見方、止め方。
10. テスト：送信済みに EH-20261102-1 等の過去メールがあるので、**初回起動時に過去分を一括で発注済みにしないこと**。初回は「起動時刻より前の送信済みメールは記録だけして処理しない」か、`db.json` に初期化時刻を持つ。既に発注済みのものはスプシ側の状態で弾く。

## Git ルール
- ブランチは `claude/examuse-prize-handover-8s2xx8` だけ。他のブランチを作らない。
- 作業前と push 前に `git pull --rebase origin claude/examuse-prize-handover-8s2xx8`。force push しない。
- コミット末尾に `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` を付ける。

## 完了報告に入れること
- 変更したファイル一覧、Mac へ配置した手順（実際にやったこと）、実機でのログ 2〜3 行、HANDOVER 7 章の追記箇所。
