# =============================================================
# srs.py
# 功能：實作 SM-2 間隔重複演算法（Spaced Repetition System）
#       根據使用者的記憶程度，自動計算下次複習日期。
#
# SM-2 演算法簡介：
#   - 使用者複習單字後，給一個「記憶品質」分數（0~5）
#   - 分數越高 → 下次複習間隔越長（因為記得很好）
#   - 分數越低 → 間隔縮短，甚至明天就要再複習
#   - ease_factor（難易係數）會根據表現自動調整
# =============================================================

import sqlite3
from datetime import date, timedelta
from database import get_connection

# ── 記憶品質分數對照 ───────────────────────────────────────────
# 我們在介面上提供三個按鈕，對應到 SM-2 的分數：
QUALITY_MAP = {
    "忘れた / 忘記了":       0,   # 完全不記得 → 重新開始
    "なんとか / 勉強記得":   3,   # 有點印象    → 短間隔
    "覚えた / 記得了":       4,   # 記得        → 中間隔
    "完璧 / 很熟悉":         5,   # 非常熟悉    → 長間隔
}


def calculate_next_review(interval_days, ease_factor, review_count, quality):
    """
    根據 SM-2 演算法計算下次複習的間隔天數和新的難易係數。

    參數：
        interval_days  → 目前的間隔天數
        ease_factor    → 目前的難易係數（通常在 1.3 ~ 3.0 之間）
        review_count   → 已複習次數
        quality        → 這次記憶品質（0~5）

    回傳：
        (new_interval, new_ease_factor) → 新的間隔天數和難易係數
    """
    if quality < 3:
        # 記不起來：重新從第一天開始，不改變難易係數
        new_interval = 1
        new_ease_factor = ease_factor
    else:
        # 記得：根據複習次數決定間隔
        if review_count == 0:
            new_interval = 1       # 第一次複習後，明天再複習
        elif review_count == 1:
            new_interval = 6       # 第二次複習後，6 天後再複習
        else:
            # 之後每次乘以難易係數，間隔越來越長
            new_interval = round(interval_days * ease_factor)

        # 根據表現更新難易係數（SM-2 公式）
        # quality 越高，ease_factor 上升；越低，下降
        new_ease_factor = ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))

        # 難易係數最低不能低於 1.3（避免間隔縮得太短）
        if new_ease_factor < 1.3:
            new_ease_factor = 1.3

    return new_interval, round(new_ease_factor, 2)


def update_vocabulary_after_review(vocab_id, quality):
    """
    使用者複習完一個單字後，更新資料庫裡的 SRS 資料。

    參數：
        vocab_id → 單字在資料庫的 ID
        quality  → 這次記憶品質（0~5）
    """
    conn = get_connection()
    cursor = conn.cursor()

    # 先查出這個單字目前的 SRS 資料
    cursor.execute(
        "SELECT interval_days, ease_factor, review_count FROM vocabulary WHERE id = ?",
        (vocab_id,)
    )
    row = cursor.fetchone()

    if not row:
        conn.close()
        return

    interval_days = row["interval_days"]
    ease_factor   = row["ease_factor"]
    review_count  = row["review_count"]

    # 用 SM-2 演算法計算新的間隔和難易係數
    new_interval, new_ease = calculate_next_review(
        interval_days, ease_factor, review_count, quality
    )

    # 計算下次複習日期 = 今天 + 新間隔
    next_review_date = (date.today() + timedelta(days=new_interval)).isoformat()

    # 更新資料庫
    cursor.execute("""
        UPDATE vocabulary
        SET interval_days = ?,
            ease_factor   = ?,
            review_count  = review_count + 1,
            next_review   = ?
        WHERE id = ?
    """, (new_interval, new_ease, next_review_date, vocab_id))

    conn.commit()
    conn.close()

