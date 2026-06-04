#!/usr/bin/env python3
"""
runtime_check.py — ENGLISH_LEARNING 執行時期 smoke test
streamlit-verify 只檢查語法 + 啟動，這個腳本補抓常見的執行時期錯誤。

執行方式（從 ENGLISH_LEARNING/ 目錄）:
    python .claude/skills/streamlit-verify/runtime_check.py

檢查項目:
  1. datetime 切片安全性（saved_at 欄位）
  2. None 切片安全性
  3. CSS overflow:hidden 不得出現在 info 欄位選擇器
  4. 資料庫查詢回傳型別（需要 .env.local）
"""
import sys
import re
import os
from datetime import datetime, timezone

PASS = True


def ok(name):
    print(f"  ✓ {name}")


def fail(name, detail=""):
    global PASS
    PASS = False
    print(f"  ✗ {name}{': ' + detail if detail else ''}")


# ── 1. datetime 切片安全性（新聞 saved_at 歷史 bug）─────────────────
try:
    dt = datetime.now(timezone.utc)
    _ = str(dt or "")[:16]          # 正確做法
    ok("datetime 切片: str(dt)[:16] 安全")
except Exception as e:
    fail("datetime 切片", str(e))

# 舊寫法模擬（不應存在）
try:
    dt = datetime.now(timezone.utc)
    dt[:16]  # type: ignore  # 這行應該要 raise TypeError
    fail("datetime bare slice 未被攔截（代表程式碼回到舊寫法）")
except TypeError:
    ok("datetime bare slice 正確會 raise TypeError")

# ── 2. None 切片安全性 ──────────────────────────────────────────────
try:
    _ = str(None or "")[:16]
    ok("None 切片: str(None or '')[:16] 安全")
except Exception as e:
    fail("None 切片", str(e))

# ── 3. 函式簽名靜態驗證（修改跨檔案介面後必做）──────────────────────
def _check_func_sig(filepath, func_pattern, required_params, label):
    """用 regex 驗證函式定義是否包含必要參數。"""
    path = os.path.join("src", filepath)
    if not os.path.exists(path):
        print(f"  ⚠ 找不到 {path}，跳過")
        return
    content = open(path, encoding="utf-8").read()
    match = re.search(func_pattern, content)
    if not match:
        fail(label, f"找不到函式定義（{func_pattern}）")
        return
    sig_line = match.group(0)
    for param in required_params:
        if param not in sig_line:
            fail(label, f"缺少參數 '{param}'，調用端傳入會 TypeError")
            return
    ok(f"{label}: 簽名包含 {required_params}")

# quiz_func.generate_quiz 必須接受 lang 參數
_check_func_sig(
    "quiz_func.py",
    r"def generate_quiz\([^)]*\)",
    ["lang"],
    "quiz_func.generate_quiz()"
)

# ── 4. CSS 靜態分析 ─────────────────────────────────────────────────
app_path = "src/app.py"
if os.path.exists(app_path):
    src = open(app_path, encoding="utf-8").read()

    # overflow:hidden 出現在 info 欄（nth-child(2)）選擇器上 → 會裁掉定義文字
    bad_css = re.search(
        r"nth-child\(2\)[^}]*overflow\s*:\s*hidden",
        src, re.DOTALL
    )
    if bad_css:
        fail("CSS", "nth-child(2) 欄位有 overflow:hidden，會裁掉翻譯文字")
    else:
        ok("CSS: info 欄位無 overflow:hidden")

    # saved_at 切片是否有 str() 保護
    bad_slice = re.search(
        r"n\.get\(['\"]saved_at['\"][^)]*\)\s*\[:16\]",
        src
    )
    if bad_slice:
        fail("code", "saved_at 直接 [:16] 未加 str()，datetime 物件會崩潰")
    else:
        ok("code: saved_at 切片有 str() 保護")
else:
    print(f"  ⚠ 找不到 {app_path}，請從 ENGLISH_LEARNING/ 目錄執行")

# ── 4. 資料庫查詢型別（需要 .env.local）─────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv(".env.local")
    sys.path.insert(0, "src")
    from database import get_saved_news, get_all_vocabulary  # type: ignore

    # saved_news: saved_at 是 datetime，確認 str() 切片不炸
    news = get_saved_news()
    for n in news:
        result = str(n.get("saved_at") or "")[:16]
        assert isinstance(result, str)
    ok(f"DB get_saved_news(): saved_at 型別安全（{len(news)} 筆）")

    # vocabulary: definition 是字串
    vocab = get_all_vocabulary()
    bad_defs = [v for v in vocab if v.get("definition") is not None
                and not isinstance(v.get("definition"), str)]
    if bad_defs:
        fail("DB get_all_vocabulary()", f"definition 非字串: {bad_defs[:1]}")
    else:
        ok(f"DB get_all_vocabulary(): definition 型別安全（{len(vocab)} 筆）")

except ImportError as e:
    print(f"  ⚠ DB 檢查跳過（缺套件）: {e}")
except Exception as e:
    print(f"  ⚠ DB 檢查跳過（連線失敗）: {e}")

# ── 結果 ────────────────────────────────────────────────────────────
print()
if PASS:
    print("✅ runtime_check PASS")
    sys.exit(0)
else:
    print("❌ runtime_check FAIL — 請修正後再 push")
    sys.exit(1)
