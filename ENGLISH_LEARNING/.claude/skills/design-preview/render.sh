#!/usr/bin/env bash
# =============================================================
# design-preview/render.sh — 静的 HTML を PNG に書き出して開く。
#   Streamlit のスクショは当てにならないため、配色/部品を再現した
#   静的 HTML モックを headless Chrome で撮影してユーザーに見せる。
#
# 使い方: bash render.sh HTML [OUT.png] [WIDTHxHEIGHT]
#   HTML : モックの HTML（相対/絶対どちらでも可）
#   OUT  : 出力 PNG（既定 /tmp/preview.png）
#   SIZE : 例 1000x820（既定）
# =============================================================
set -uo pipefail

HTML="${1:?usage: render.sh HTML [OUT.png] [WIDTHxHEIGHT]}"
OUT="${2:-/tmp/preview.png}"
SIZE="${3:-1000x820}"
W="${SIZE%x*}"; H="${SIZE#*x}"

# 絶対パス化（file:// に必要）
case "$HTML" in /*) ABS="$HTML";; *) ABS="$PWD/$HTML";; esac

CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
[ -x "$CHROME" ] || CHROME="/Applications/Chromium.app/Contents/MacOS/Chromium"
[ -x "$CHROME" ] || { echo "✗ Chrome/Chromium が見つかりません"; exit 1; }

"$CHROME" --headless=new --disable-gpu --hide-scrollbars \
  --force-device-scale-factor=2 --screenshot="$OUT" \
  --window-size="$W,$H" "file://$ABS" 2>/dev/null
sleep 1   # Web フォント読込待ち

if [ -f "$OUT" ]; then
  echo "✓ rendered $OUT  ($SIZE)"
  open "$OUT" 2>/dev/null || true
else
  echo "✗ render failed"; exit 1
fi
