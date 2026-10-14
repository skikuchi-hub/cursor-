# ジャービス（jarvis-bridge）

iPhone・iMac・MacBook のどれからでも、**声で話しかけるだけで Mac の Claude Code が仕事をする**ための土台。

```
 話しかける                         考える・常駐する                 手を動かす
┌────────────┐   声    ┌──────────────────────┐  MCP   ┌──────────────────┐  claude -p  ┌─────────────────────┐
│ iPhone      │ ─────▶ │ ChatGPT の Dot        │ ─────▶ │ jarvis-bridge     │ ──────────▶ │ Claude Code          │
│ iMac        │        │ 「ジャービス」         │ ◀───── │ （各 Mac で常駐）  │ ◀────────── │ ＋ 秘書・経理・監査… │
│ MacBook     │        └──────────────────────┘ 結果   │                   │             │    のスキル          │
│             │   声（Siri ショートカット）── REST ──▶ │  iMac ⇄ MacBook   │             └─────────────────────┘
└────────────┘ ◀── 通知（Mac の通知・iPhone の ntfy）── │  で仕事を回せる    │
                                                        └──────────────────┘
```

- **Dot（ジャービス）**：会話・常駐・段取り。長い仕事は「取りかかりました」と言って、終わったら知らせてくれる。
- **jarvis-bridge**：このフォルダ。各 Mac で常駐し、Dot や Siri からの指示を Claude Code に渡す。
- **Claude Code**：今ある秘書（`ai-secretary`）や各スキルがそのまま「ジャービスの手足」になる。
- **会話の続き**：「OK、送って」「さっきのを Wetopia 分だけ」は、前の作業の続き（同じ Claude の会話）として動く。
- **安全**：メール送信・支払い・請求の確定・削除は、Claude Code が直前で止めて「よいですか？」と聞く。
  菊地さんが OK と言うまで進まない。

| 場所 | 話しかけ方 | 返ってくる |
|---|---|---|
| どこでも（iPhone） | ChatGPT アプリの音声（アクションボタンに割り当てると一押し）／「Hey Siri、ジャービス」 | 声＋ iPhone 通知 |
| 自宅・会社（iMac） | ChatGPT デスクトップアプリ（⌥Space）の音声／Siri | 声＋ Mac 通知（読み上げも可） |
| 外出先（MacBook） | 同上。「MacBook でやって」と言えば MacBook の Claude Code が動く | 同上 |

---

## セットアップ

所要 30〜40 分。ふだん仕事を回す **iMac** から始めます。

### 1. iMac に jarvis-bridge を入れる

ターミナルで:

```bash
cd ~ && git clone https://github.com/skikuchi-hub/cursor-.git jarvis-repo   # もう clone 済みなら不要
cd ~/jarvis-repo && git checkout claude/jarvis && cd jarvis
./scripts/install-mac.sh imac
```

- `.env` が自動でできます。中の **`JARVIS_WORKDIR`**（Claude Code を動かすフォルダ）を、
  いつも Claude Code を開いているフォルダ（スキルや書類があるところ）に直してください。既定はデスクトップ。
- 直したら `./scripts/install-mac.sh` をもう一度実行すると反映されます。
- ログイン時に自動で起動し、落ちても自動で立ち上がります。ログ: `~/Library/Logs/jarvis-bridge.log`

### 2. iMac を眠らせない

システム設定 → ディスプレイ → 詳細 →「ディスプレイがオフのときに自動でスリープさせない」をオン。
（または ターミナルで `sudo pmset -a sleep 0 disksleep 0`）

### 3. 外から届くようにする（Tailscale Funnel）

ChatGPT はクラウドから呼んでくるので、iMac に HTTPS の入口が要ります。独自ドメインが要らない Tailscale Funnel を使います。

1. [Tailscale](https://tailscale.com/download/mac) を入れてログイン（無料プランで可）。
2. ターミナルで:
   ```bash
   tailscale funnel --bg 8787
   ```
   初回は「Funnel を有効にする」リンクが出るので、開いて許可してから、もう一度同じコマンドを実行。
3. `https://imac.xxxx.ts.net` のような URL が出ます。これが **iMac の公開 URL**。
4. 確認: ブラウザで `https://imac.xxxx.ts.net/healthz` を開いて `{"ok":true,...}` が出れば OK。

> 独自ドメインを Cloudflare に置いているなら、Cloudflare Tunnel（`cloudflared`）でも同じことができます。

### 4. ChatGPT にジャービスを作る

1. 合言葉を確認: `grep JARVIS_TOKEN ~/jarvis-repo/jarvis/.env`
2. ChatGPT（Pro）→ 設定 → アプリ（コネクタ）→ 詳細設定 →**開発者モード**をオン。
3. 「アプリを作成」：
   - 名前: `jarvis-bridge`
   - URL: `https://imac.xxxx.ts.net/t/<合言葉>/mcp`
   - 認証: なし（合言葉は URL に入っています。**この URL は人に見せない**）
4. **Dot を作る**：名前「ジャービス」。指示欄に [`prompts/jarvis.md`](prompts/jarvis.md) の `---` から下を貼り、
   アプリ `jarvis-bridge` を使えるようにする。
5. ためしに話しかける：「ジャービス、いま動いてる作業ある？」→ `list_tasks` が呼ばれれば接続 OK。

> ChatGPT の画面の名前（「アプリ」「コネクタ」など）は時期によって変わります。見当たらなければ「開発者モード」「カスタムアプリ」で探してください。
> Dot に声で話しかけられない場合は、ChatGPT の**プロジェクト「ジャービス」**を作り、同じ指示とアプリを付けて音声モードで話せば同じように動きます。

### 5. 声の入口を各端末に

**iPhone**
- ChatGPT アプリ → 音声モード。設定 → アクションボタン → ショートカット →「ChatGPT の音声会話を開始」にすると一押しで話せます。
- 通知：[ntfy](https://apps.apple.com/app/ntfy/id1625396347) アプリを入れ、推測されにくい名前のトピック
  （例 `jarvis-8f3k2q9x`）を購読。`.env` の `JARVIS_NTFY_URL=https://ntfy.sh/jarvis-8f3k2q9x` を設定して install し直す。

**iMac / MacBook**
- ChatGPT デスクトップアプリ → ⌥Space で呼び出し → 音声ボタン。
- iMac で結果を声で聞きたいときは `.env` の `JARVIS_MAC_SAY=1`。

**Siri（ChatGPT を開かずに直接）**
「Hey Siri、ジャービス」で Claude Code に直接頼めます。ショートカットアプリで新規作成し、次の順に並べます:

1. **テキストを音声入力**（言語: 日本語）
2. **URL の内容を取得**
   - URL: `https://imac.xxxx.ts.net/t/<合言葉>/api/ask`
   - 方法: POST、本文を要求: JSON → `text` ＝（1 の音声入力されたテキスト）
3. **辞書の値を取得**：キー `say`（2 の結果から）
4. **テキストを読み上げる**：3 の値

ショートカット名を「ジャービス」にすれば完成。iCloud で Mac にも同期されます。
直前の作業が確認待ちのときに「OK、送って」と話すと、その続きとして進みます。50 秒で終わらない仕事は
「終わったら通知します」と言って、終わり次第 ntfy／Mac 通知が来ます。

### 6. MacBook も手足にする（任意）

1. MacBook でも 1 と 3 を行う（`./scripts/install-mac.sh macbook`）。
2. MacBook の `.env` の `JARVIS_TOKEN` を **iMac と同じ値**にする。
3. 両方の `.env` にお互いを書く:
   - iMac: `JARVIS_PEERS=macbook=https://macbook.xxxx.ts.net`
   - MacBook: `JARVIS_PEERS=imac=https://imac.xxxx.ts.net`
4. 両方で `./scripts/install-mac.sh` をもう一度実行。

ChatGPT に登録するのは iMac の URL だけで構いません。「MacBook でやって」と言えば iMac が MacBook に仕事を回します。
（iMac が止まっている日に備えるなら、MacBook の URL も別アプリとして登録しておく）

---

## 中身

```
jarvis/
  src/server.js        入口（MCP と REST）。Mac 同士の受け渡しもここ
  src/tasks.js         作業の受付・順番待ち・Claude Code の実行・記録・通知
  src/config.js        .env の読み込み
  prompts/hands.md     Claude Code 側に足す指示（止まるところ、最後の返事の形）
  prompts/jarvis.md    Dot（ジャービス）の指示文
  scripts/install-mac.sh  インストールと自動起動
  data/tasks.json      作業の記録（直近 300 件。git には入らない）
```

### ChatGPT から使える道具（MCP）

| 道具 | すること |
|---|---|
| `run_task` | 指示を Claude Code に渡す。最大 45 秒待って、終われば結果、終わらなければ task_id を返す。`continue_task_id` で続き、`machine` で Mac を指定 |
| `get_task` | 作業の状態と結果 |
| `list_tasks` | 全 Mac の最近の作業と、どの Mac がつながっているか |
| `cancel_task` | 作業を止める |

### REST（Siri・ほかの Mac 用）

すべて `Authorization: Bearer <合言葉>` か、URL の頭に `/t/<合言葉>` を付ける。

| | |
|---|---|
| `POST /api/ask` `{text}` | 話した内容を頼んで最大 50 秒待ち、読み上げ用の `say` を返す（Siri 用） |
| `POST /api/tasks` `{instruction, continue_task_id?, machine?, wait_seconds?}` | 作業を頼む |
| `GET /api/tasks/:id?wait=秒` | 状態と結果 |
| `GET /api/tasks` | 一覧 |
| `POST /api/tasks/:id/cancel` | 止める |
| `GET /healthz` | 生きているか（合言葉不要） |

### Claude Code の許可について

既定は `JARVIS_PERMISSION_MODE=auto`（Claude Code が危ない操作かを判断しながら自動で進める）。
auto が使えない環境では `acceptEdits` にして、使うコマンドを `~/.claude/settings.json` の `permissions.allow` に足してください。
送信・支払い・削除の前で止まるのは `prompts/hands.md` の指示によるもので、許可モードとは別に効きます。

## 困ったとき

| 症状 | 見るところ |
|---|---|
| ジャービスが「つながっていません」 | iMac が起きているか／`https://imac.xxxx.ts.net/healthz`／`tailscale funnel status` |
| 動かない・すぐ失敗する | `tail -50 ~/Library/Logs/jarvis-bridge.log`。claude にログインし直す（ターミナルで `claude`） |
| 作業が「中断」になった | jarvis-bridge が再起動した。「さっきの続きやって」で続きから頼める |
| 合言葉を変えたい | `.env` の `JARVIS_TOKEN` を変えて install し直し、ChatGPT のアプリ URL と Siri ショートカットも直す |

## これから足せること

- **終わった瞬間に Dot へ知らせる（MCP Events）**：いまは Dot が `get_task` で見に来る方式。
  ChatGPT の MCP Events は仕様が下書き段階で、イベントの中身が Dot に届かない不具合も報告されているため、安定してから足す。
- **OAuth 認証**：URL の合言葉の代わりに、ChatGPT 標準のログイン方式にする。
- **自分専用リポジトリへ移す**：このリポジトリはクレーンログ（GitHub Pages）なので、ジャービスは別の非公開リポジトリに移すのがおすすめ。
