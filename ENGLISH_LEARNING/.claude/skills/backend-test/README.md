# backend-test skill

用戶指出任何功能問題後，Claude 在後台直接呼叫 API/DB 測試，確認修好後才回報。

## 指令

```bash
# 測試批改功能（預設用截圖裡的句子）
python .claude/skills/backend-test/run.py quiz_grade

# 指定題目、回答
python .claude/skills/backend-test/run.py quiz_grade "中文題目" "英文回答"

# 測試出題（zh=中文介面, ja=日文介面）
python .claude/skills/backend-test/run.py quiz_gen zh
python .claude/skills/backend-test/run.py quiz_gen ja

# 測試單字查詢
python .claude/skills/backend-test/run.py vocab_lookup "illustrator"

# 測試資料庫連線
python .claude/skills/backend-test/run.py db_check
```

## 驗證邏輯

- `quiz_grade`：檢查分數格式、每條 note 是否為「日文 / 中文」雙語、feedback 格式
- `quiz_gen`：檢查 zh 和 ja 兩個欄位都有值
- `vocab_lookup`：檢查 definition_jp 和 definition_zh 都有值
- `db_check`：確認三個主要資料表都能查詢

## 使用時機

每次修改以下功能後，Claude 應主動執行對應測試再 push：
- `quiz_func.py` → `quiz_grade` + `quiz_gen`
- `analyze_func.py` → `vocab_lookup`
- `database.py` → `db_check`
