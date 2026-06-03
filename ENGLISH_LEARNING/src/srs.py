from datetime import date, timedelta
from database import get_db, _cur

QUALITY_MAP = {
    "忘れた / 忘記了":       0,
    "なんとか / 勉強記得":   3,
    "覚えた / 記得了":       4,
    "完璧 / 很熟悉":         5,
}


def calculate_next_review(interval_days, ease_factor, review_count, quality):
    if quality < 3:
        new_interval = 1
        new_ease_factor = ease_factor
    else:
        if review_count == 0:
            new_interval = 1
        elif review_count == 1:
            new_interval = 6
        else:
            new_interval = round(interval_days * ease_factor)
        new_ease_factor = ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
        if new_ease_factor < 1.3:
            new_ease_factor = 1.3
    return new_interval, round(new_ease_factor, 2)


def update_vocabulary_after_review(vocab_id, quality):
    with get_db() as conn:
        cur = _cur(conn)
        cur.execute(
            "SELECT interval_days, ease_factor, review_count FROM vocabulary WHERE id = %s",
            (vocab_id,)
        )
        row = cur.fetchone()
        if not row:
            cur.close()
            return

        new_interval, new_ease = calculate_next_review(
            row["interval_days"], row["ease_factor"], row["review_count"], quality
        )
        next_review_date = date.today() + timedelta(days=new_interval)

        cur.execute("""
            UPDATE vocabulary
            SET interval_days = %s,
                ease_factor   = %s,
                review_count  = review_count + 1,
                next_review   = %s
            WHERE id = %s
        """, (new_interval, new_ease, next_review_date, vocab_id))
        cur.close()
