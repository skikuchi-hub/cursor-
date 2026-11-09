#!/bin/bash
# =====================================================================
# 条件表 自動保存 インストーラー（Mac用）
#
# これを1回実行すると：
#   1. 本体スクリプトを ~/Library/Application Support/JokenhyoSave/ に置く
#   2. 毎週月曜 8:00 に自動で動くよう登録する（launchd）
#   3. その場で1回テスト実行する（Mail の操作許可ダイアログが出たら「OK」）
#
# 本体の動き：
#   Apple Mail の kanri@exploration-holdings.jp の送信済みメールから、
#   過去8日間の「条件表」メールの添付PDF（受信箱のCC控え・送信済みの両方）を取り出し、
#   デスクトップ/Exploration Holdings株式会社/単価表/{会社名}/{yyyymm}/{商材フォルダ}/
#   に原本ファイル名のまま保存する。同名ファイルが既にあればスキップ。
#
# 解除したいとき：同じフォルダの 条件表自動保存_解除.command を実行
# =====================================================================
set -u

APP_DIR="$HOME/Library/Application Support/JokenhyoSave"
RUN_SCRIPT="$APP_DIR/条件表自動保存.command"
LABEL="jp.exploration-holdings.jokenhyo-save"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

mkdir -p "$APP_DIR" "$HOME/Library/LaunchAgents"

# ---------------------------------------------------------------------
# 本体スクリプト
# ---------------------------------------------------------------------
cat > "$RUN_SCRIPT" <<'MAIN_SCRIPT_EOF'
#!/bin/bash
# 条件表 自動保存（毎週月曜 8:00 に launchd から Terminal 経由で起動）
set -u

BASE="$HOME/Desktop/Exploration Holdings株式会社/単価表"
DAYS="${1:-8}"   # 何日前まで見るか（引数で変更可。例: bash 条件表自動保存.command 14）
LOG_DIR="$HOME/Library/Logs/JokenhyoSave"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/$(date +%Y%m%d_%H%M%S).log"
# Mail はサンドボックスのため、一時保存先はダウンロードフォルダ内にする
WORK="$HOME/Downloads/.jokenhyo_work_$$"
mkdir -p "$WORK"
trap 'rm -rf "$WORK"' EXIT

log() { echo "$*" | tee -a "$LOG"; }

# Mac のファイル名は濁点などが分解された形(NFD)で入っていることがあるため、比較前に NFC へそろえる
if iconv -f UTF-8-MAC -t UTF-8 </dev/null >/dev/null 2>&1; then
  nfc() { iconv -f UTF-8-MAC -t UTF-8 2>/dev/null; }
else
  nfc() { cat; }
fi

# 全角・半角スペースを前後から取り除く
trim() {
  local s="$1"
  while :; do
    case "$s" in
      " "*) s="${s# }" ;;
      "　"*) s="${s#　}" ;;
      *" ") s="${s% }" ;;
      *"　") s="${s%　}" ;;
      *) break ;;
    esac
  done
  printf '%s' "$s"
}

# 件名 or ファイル名「【○○ 御中】…」から会社名を取り出す
company_from() {
  local s="$1"
  case "$s" in *"【"*"】"*) ;; *) return 1 ;; esac
  s="${s#*【}"; s="${s%%】*}"
  s="${s%御中}"; s="${s%様}"; s="$(trim "$s")"; s="${s%御中}"; s="${s%様}"
  trim "$s"
}

# 「【○○ 御中】202605 @nifty光条件表.pdf」→「@nifty光」
shozai_from() {
  local s="$1"
  s="${s%.*}"                       # 拡張子
  case "$s" in *"】"*) s="${s#*】}" ;; esac
  s="$(trim "$s")"
  s="$(printf '%s' "$s" | LC_ALL=C sed -E 's/^令和[0-9]*年[0-9]*月度//; s/^[0-9]{6,8}//')"
  s="$(trim "$s")"
  s="${s%条件通知書}"; s="${s%条件表}"; s="${s%通知書}"
  s="$(trim "$s")"; s="${s%の}"
  trim "$s"
}

# 商材フォルダ名を決める（上位店が複数ある商材は「商材名(○○商流)」）
#   出力：フォルダ名。判断できないときは return 1
resolve_shozai_folder() {
  local company_dir="$1" shozai="$2"
  local own all
  shozai="$(printf '%s' "$shozai" | nfc)"
  own="$(find "$company_dir" -mindepth 2 -maxdepth 2 -type d 2>/dev/null | awk -F/ '{print $NF}' | nfc | sort -u)"
  all="$(find "$BASE" -mindepth 3 -maxdepth 3 -type d 2>/dev/null | awk -F/ '{print $NF}' | nfc | sort -u)"

  local own_plain own_ryu
  own_plain="$(printf '%s\n' "$own" | grep -Fx -- "$shozai" || true)"
  own_ryu="$(printf '%s\n' "$own" | grep -F -e "${shozai}(" -e "${shozai}（" | grep -E '商流(\)|）)$' || true)"

  if [ -n "$own_plain" ] && [ -z "$own_ryu" ]; then printf '%s' "$shozai"; return 0; fi
  if [ -z "$own_plain" ] && [ -n "$own_ryu" ] && [ "$(printf '%s\n' "$own_ryu" | wc -l | tr -d ' ')" = "1" ]; then
    printf '%s' "$own_ryu"; return 0
  fi
  if [ -z "$own_plain" ] && [ -z "$own_ryu" ]; then
    # この会社では初めての商材：他社で「(○○商流)」に分かれているなら判断できない
    if printf '%s\n' "$all" | grep -F -e "${shozai}(" -e "${shozai}（" | grep -Eq '商流(\)|）)$'; then return 1; fi
    printf '%s' "$shozai"; return 0
  fi
  return 1
}

log "===== 条件表 自動保存 $(date '+%Y-%m-%d %H:%M') ====="
if [ ! -d "$BASE" ]; then
  log "保存先フォルダが見つかりません: $BASE"
  osascript -e 'display notification "単価表フォルダが見つかりません" with title "条件表 自動保存"' >/dev/null 2>&1
  exit 1
fi

# ---------------------------------------------------------------------
# Apple Mail から添付を取り出す
#   出力行: ATT<TAB>yyyymm<TAB>件名<TAB>保存した一時パス
#           SKIP<TAB>件名<TAB>理由
# ---------------------------------------------------------------------
# （Mac 標準の bash 3.2 は $( ) の中のヒアドキュメントを正しく読めないため、先にファイルへ書き出す）
AS_FILE="$WORK/fetch.applescript"
cat > "$AS_FILE" <<'APPLESCRIPT_EOF'
on pad2(n)
    if n < 10 then return "0" & (n as text)
    return n as text
end pad2

on run argv
    set outDir to item 1 of argv
    set nDays to (item 2 of argv) as integer
    set cutoff to (current date) - nDays * days
    set kanri to "kanri@exploration-holdings.jp"
    set resultLines to {}
    set seenIds to {}
    set idx to 0
    tell application "Mail"
        set boxes to {}
        try
            set end of boxes to sent mailbox
        end try
        repeat with a in accounts
            try
                if (email addresses of a) contains kanri then
                    repeat with mb in mailboxes of a
                        set mbName to name of mb
                        if mbName contains "Sent" or mbName contains "送信" or mbName is "INBOX" or mbName contains "受信" then set end of boxes to mb
                    end repeat
                end if
            end try
        end repeat
        repeat with mb in boxes
            try
                set msgs to (messages of mb whose date sent > cutoff and (subject contains "条件表" or subject contains "通知書"))
            on error
                set msgs to {}
            end try
            repeat with m in msgs
                try
                    set mid to message id of m
                    if seenIds does not contain mid and (sender of m) contains kanri then
                        set end of seenIds to mid
                        set subj to subject of m
                        set d to date sent of m
                        set ym to ((year of d) as text) & my pad2((month of d) as integer)
                        set idx to idx + 1
                        set msgDir to outDir & "/" & idx
                        do shell script "mkdir -p " & quoted form of msgDir
                        repeat with att in mail attachments of m
                            set attName to name of att
                            set lowerName to do shell script "printf '%s' " & quoted form of attName & " | tr 'A-Z' 'a-z'"
                            if lowerName ends with ".pdf" then
                                set p to msgDir & "/" & attName
                                try
                                    save att in POSIX file p
                                    set end of resultLines to "ATT" & tab & ym & tab & subj & tab & p
                                on error errMsg
                                    set end of resultLines to "SKIP" & tab & subj & tab & "添付を取り出せませんでした(" & attName & "): " & errMsg
                                end try
                            end if
                        end repeat
                    end if
                end try
            end repeat
        end repeat
    end tell
    set AppleScript's text item delimiters to linefeed
    return resultLines as text
end run
APPLESCRIPT_EOF
MAIL_OUT="$(osascript "$AS_FILE" "$WORK" "$DAYS")"
rc=$?
if [ $rc -ne 0 ]; then
  log "Apple Mail からの取得に失敗しました（Mail の操作許可・Mail が起動できるか確認してください）"
  osascript -e 'display notification "Mail からの取得に失敗しました" with title "条件表 自動保存"' >/dev/null 2>&1
  exit 1
fi

saved=0; skipped=0; review=0
SAVED_LIST=""; SKIP_LIST=""; REVIEW_LIST=""

while IFS=$'\t' read -r kind f2 f3 f4; do
  [ -z "${kind:-}" ] && continue
  if [ "$kind" = "SKIP" ]; then
    review=$((review+1)); REVIEW_LIST="$REVIEW_LIST
  ・$f2 … $f3"
    continue
  fi
  ym="$f2"; subj="$f3"; tmp="$f4"
  fname="${tmp##*/}"

  company="$(company_from "$fname" || company_from "$subj" || true)"
  shozai="$(shozai_from "$fname")"
  if [ -z "$shozai" ]; then
    # ファイル名から取れない場合は件名から
    shozai="$(shozai_from "$subj.x")"
    case "$shozai" in *"・"*) shozai="" ;; esac   # 複数商材の件名では決められない
  fi
  if [ -z "$company" ] || [ -z "$shozai" ]; then
    review=$((review+1)); REVIEW_LIST="$REVIEW_LIST
  ・${fname} … 会社名/商材名を読み取れません（件名: ${subj}）"
    continue
  fi

  company_dir="$BASE/$company"
  # 同じ会社フォルダ内に同名ファイルがあればスキップ（どの月・商材でも）
  fname_nfc="$(printf '%s' "$fname" | nfc)"
  if [ -d "$company_dir" ] && find "$company_dir" -type f 2>/dev/null | awk -F/ '{print $NF}' | nfc | grep -Fxq -- "$fname_nfc"; then
    skipped=$((skipped+1)); SKIP_LIST="$SKIP_LIST
  ・$company / $fname"
    continue
  fi

  folder="$(resolve_shozai_folder "$company_dir" "$shozai" || true)"
  if [ -z "$folder" ]; then
    review=$((review+1)); REVIEW_LIST="$REVIEW_LIST
  ・${fname} … 「${shozai}」は上位店が複数あり商流フォルダを決められません（会社: ${company}）"
    continue
  fi

  dest="$company_dir/$ym/$folder"
  mkdir -p "$dest"
  cp -n "$tmp" "$dest/$fname"
  saved=$((saved+1)); SAVED_LIST="$SAVED_LIST
  ・単価表/$company/$ym/$folder/$fname"
done <<< "$MAIL_OUT"

log ""
log "保存: ${saved}件${SAVED_LIST}"
log "既存のためスキップ: ${skipped}件${SKIP_LIST}"
log "要確認（保存していません）: ${review}件${REVIEW_LIST}"
log ""
log "ログ: $LOG"

osascript -e "display notification \"保存 ${saved}件／スキップ ${skipped}件／要確認 ${review}件\" with title \"条件表 自動保存\"" >/dev/null 2>&1
MAIN_SCRIPT_EOF
chmod +x "$RUN_SCRIPT"

# ---------------------------------------------------------------------
# 毎週月曜 8:00 に実行する登録（Terminal で開いて実行＝Terminal の許可を使う）
# ---------------------------------------------------------------------
cat > "$PLIST" <<PLIST_EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/bin/open</string>
    <string>-a</string>
    <string>Terminal</string>
    <string>$RUN_SCRIPT</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Weekday</key><integer>1</integer>
    <key>Hour</key><integer>8</integer>
    <key>Minute</key><integer>0</integer>
  </dict>
</dict>
</plist>
PLIST_EOF

launchctl bootout "gui/$(id -u)/$LABEL" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"

echo "登録しました：毎週月曜 8:00 に条件表を単価表へ自動保存します。"
echo "（Mac がスリープ中だった場合は、次に起きたときに実行されます）"
echo ""
echo "テストで今すぐ1回実行します…"
echo ""
bash "$RUN_SCRIPT"
