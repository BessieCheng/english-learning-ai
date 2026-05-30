#!/usr/bin/env bash
# =============================================================
# streamlit-verify — ENGLISH_LEARNING の Streamlit アプリを検証する。
#   1) 構文チェック（ast.parse）
#   2) headless で起動
#   3) HTTP 200 を確認
#   4) ログにエラーが無いか確認
#   5) 後始末（プロセス停止）
#
# 使い方:  bash .claude/skills/streamlit-verify/verify.sh [APP] [PORT]
#   APP : 対象ファイル（既定 src/app.py、リポジトリ root から相対）
#   PORT: ポート（既定 8567）
# 終了コード 0 = PASS / 1 = FAIL
# =============================================================
set -uo pipefail

APP="${1:-src/app.py}"
PORT="${2:-8567}"
PY=/opt/anaconda3/bin/python
ST=/opt/anaconda3/bin/streamlit
LOG="$(mktemp -t stverify.XXXXXX).log"

echo "▶ streamlit-verify: $APP  (port $PORT)"

# 1) 構文チェック
if ! "$PY" -c "import ast; ast.parse(open('$APP').read()); print('  ✓ syntax OK')"; then
  echo "❌ FAIL — syntax error"; exit 1
fi

# 2) headless で起動（app の隣で実行）
APPDIR="$(dirname "$APP")"; APPFILE="$(basename "$APP")"
( cd "$APPDIR" && "$ST" run "$APPFILE" \
    --server.port "$PORT" --server.headless true \
    --server.enableXsrfProtection false ) > "$LOG" 2>&1 &
SPID=$!

# 3) 立ち上がるまで待つ（最大 ~22 秒）
CODE=000
for _ in $(seq 1 22); do
  sleep 1
  CODE=$(curl -s -o /dev/null -w '%{http_code}' "http://localhost:$PORT" 2>/dev/null || echo 000)
  [ "$CODE" = "200" ] && break
done

# 4) ログのエラー確認（良性の行は除外）
ERRS=$(grep -iE "error|traceback|exception" "$LOG" \
        | grep -viE "enableXsrf|gatherUsage|usage statistics" || true)

# 5) 後始末（"Terminated" のジョブ制御メッセージを抑制）
{ kill "$SPID" && wait "$SPID"; } 2>/dev/null
pkill -f "streamlit run $APPFILE" 2>/dev/null

# 6) レポート
echo "  HTTP: $CODE"
if [ -n "$ERRS" ]; then echo "  log issues:"; echo "$ERRS" | sed 's/^/    /'; fi
if [ "$CODE" = "200" ] && [ -z "$ERRS" ]; then
  echo "✅ PASS — boots clean, serves 200, no errors"
  rm -f "$LOG"; exit 0
else
  echo "❌ FAIL — see above (log: $LOG)"; exit 1
fi
