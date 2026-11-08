#!/bin/bash
# 条件表 自動保存 の毎週実行を止める（本体とログも削除）
LABEL="jp.exploration-holdings.jokenhyo-save"
launchctl bootout "gui/$(id -u)/$LABEL" >/dev/null 2>&1
rm -f "$HOME/Library/LaunchAgents/$LABEL.plist"
rm -rf "$HOME/Library/Application Support/JokenhyoSave"
echo "条件表 自動保存 の毎週実行を解除しました。（単価表に保存済みのファイルはそのまま残っています）"
