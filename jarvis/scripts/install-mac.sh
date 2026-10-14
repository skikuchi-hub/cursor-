#!/usr/bin/env bash
# jarvis-bridge を Mac に入れて、ログイン時に自動で起動するようにする。
# 使い方:  cd jarvis && ./scripts/install-mac.sh imac     （MacBook なら macbook）
# もう一度実行すると、設定（.env）はそのままで入れ直しだけ行う。
set -euo pipefail

cd "$(dirname "$0")/.."
DIR="$(pwd)"
MACHINE="${1:-}"
LABEL="com.jarvis.bridge"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
LOG="$HOME/Library/Logs/jarvis-bridge.log"

say_step() { printf '\n\033[1m▶ %s\033[0m\n' "$1"; }
die() { printf '\n\033[31m✗ %s\033[0m\n' "$1"; exit 1; }

say_step "必要なものの確認"
NODE="$(command -v node || true)"
[ -n "$NODE" ] || die "Node.js がありません。ターミナルで  brew install node  を実行してから、もう一度どうぞ。"
"$NODE" -e 'const [a,b]=process.versions.node.split(".").map(Number); process.exit(a>20||(a===20&&b>=12)?0:1)' \
  || die "Node.js が古いです（$("$NODE" -v)）。 brew upgrade node  をしてください。"
CLAUDE="$(command -v claude || true)"
[ -n "$CLAUDE" ] || die "claude コマンドが見つかりません。Claude Code を入れて、一度 claude でログインしてください。"
echo "node:   $NODE ($("$NODE" -v))"
echo "claude: $CLAUDE"

say_step "部品のインストール"
npm ci --omit=dev --no-audit --no-fund

say_step "設定ファイル（.env）"
if [ ! -f .env ]; then
  [ -n "$MACHINE" ] || read -r -p "この Mac の名前（imac / macbook など）: " MACHINE
  TOKEN="$(openssl rand -hex 24)"
  sed -e "s|^JARVIS_TOKEN=.*|JARVIS_TOKEN=$TOKEN|" \
      -e "s|^JARVIS_MACHINE=.*|JARVIS_MACHINE=$MACHINE|" \
      -e "s|^JARVIS_CLAUDE_BIN=.*|JARVIS_CLAUDE_BIN=$CLAUDE|" \
      .env.example > .env
  chmod 600 .env
  echo "作りました: $DIR/.env"
  echo "※ 2台目の Mac では、1台目の .env の JARVIS_TOKEN と同じ値に書き換えてください。"
else
  echo "既存の .env を使います。"
fi

say_step "自動起動（launchd）"
mkdir -p "$(dirname "$PLIST")" "$(dirname "$LOG")"
cat > "$PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array><string>$NODE</string><string>$DIR/src/server.js</string></array>
  <key>WorkingDirectory</key><string>$DIR</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key><string>$(dirname "$CLAUDE"):$(dirname "$NODE"):/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    <key>HOME</key><string>$HOME</string>
    <key>LANG</key><string>ja_JP.UTF-8</string>
  </dict>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>$LOG</string>
  <key>StandardErrorPath</key><string>$LOG</string>
</dict>
</plist>
PLIST
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
sleep 2

PORT="$(grep -E '^JARVIS_PORT=' .env | cut -d= -f2)"; PORT="${PORT:-8787}"
if curl -fsS "http://127.0.0.1:$PORT/healthz" >/dev/null; then
  echo "✓ 動いています（http://127.0.0.1:$PORT）。ログ: $LOG"
else
  die "起動できませんでした。ログを見てください:  tail -50 $LOG"
fi

cat <<EOF

次は README の「3. 外から届くようにする（Tailscale Funnel）」へ進んでください。
いまの合言葉を見るには:  grep JARVIS_TOKEN $DIR/.env
EOF
