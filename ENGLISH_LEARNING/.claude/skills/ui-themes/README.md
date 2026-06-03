# UI Themes Skill — ENGLISH LEARNING App

三個主題的設計規格、色票與使用方式。

---

## 主題一：禅・無印（zen）

**風格定位**：日系極簡、安靜清爽、高閱讀性

| Token | 值 | 說明 |
|---|---|---|
| 背景 `--bg` | `#FAFAFA` | 淺灰白 |
| 卡片 `--card` | `#FFFFFF` | 純白 |
| 主文字 `--text` | `#1A1A1A` | 近黑 |
| 輔助文字 `--muted` | `#888888` | 中灰 |
| 主色 `--accent` | `#4A7C59` | 抹茶綠 |
| 側欄背景 | `#F5F5F5` | 淺灰 |

**字型**：Noto Sans JP (300 / 400 / 500)

**特徵**：
- 所有圓角 2px（接近直角）
- 按鈕：白底灰框，hover 綠色
- h3：左側 4px 綠色豎線
- Metric 卡片：頂部綠色細線
- 主色 accent（說話者、進度條）：`#4A7C59`

---

## 主題二：動物風 v2（animal）

**風格定位**：暖色系、可愛活潑、適合輕鬆學習

| Token | 值 | 說明 |
|---|---|---|
| 背景 `--bg` | `#FFFBF2` | 奶油米白 |
| 卡片 `--card` | `#FFFFFF` | 純白 |
| 主文字 `--text` | `#6B5644` | 暖棕 |
| 輔助文字 `--muted` | `#B6A088` | 淺棕 |
| 主色蜂蜜 `--accent` | `#F4C152` | 蜂蜜黃 |
| 薄荷 `--accent2` | `#9FD8A6` | 薄荷綠 |
| 粉色 `--pink` | `#FBD7E4` | 粉紅 |
| 深蜂蜜 | `#E8AE3A` | 深黃 |

**字型**：Zen Maru Gothic（內文）、Mochiy Pop One（標題）

**特徵**：
- 大圓角（18px～20px）
- 標題：Mochiy Pop One + 粉色馬克筆底線
- 按鈕：圓角膠囊形、蜂蜜漸層 primary
- h3：左側 11px 綠色圓點 + 棕色邊框
- Metric 卡片：白底圓角陰影，數值蜂蜜色
- 品詞徽章 vocab list：`#FCEFCF` 底 / `#B0863A` 字

---

## 主題三：大字報（bold）

**風格定位**：編輯感遊戲風、高對比、大字標題

| Token | 值 | 說明 |
|---|---|---|
| 背景 `--bg` | `#F2F2E6` | 奶白鼠尾草 |
| 卡片 `--card` | `#FFFFFF` | 純白 |
| 主文字 `--text` | `#1A1A1A` | 近黑 |
| 輔助文字 `--muted` | `#555555` | 深灰 |
| 主色石灰綠 `--accent` | `#C8E64C` | 石灰綠 |
| 深石灰綠 | `#A8C030` | hover 用 |
| 金黃徽章 | `#F5C842` | 數字圓形 badge |
| 側欄背景 | `#1A1A1A` | 黑色 |

**字型**：Noto Sans TC / Noto Sans JP（900 超粗體標題）

**特徵**：
- 所有圓角 2px（幾乎直角）
- 側欄黑底，石灰綠 active 左線
- 標題：超粗體 900，石灰綠反白 highlight 區塊
- 按鈕：黑框白底，hover 變石灰綠底
- h3：左側 6px 石灰綠矩形豎線
- Metric 卡片：頂部 4px 石灰綠粗線
- 品詞徽章 vocab list：`#C8E64C` 底 / `#1A1A1A` 字
- code 標籤：石灰綠底黑字

---

## 在 app.py 中新增主題的步驟

1. **LANG dict** 加入 `"theme_xxx": {"ja": "...", "zh": "..."}`
2. **`_theme_labels`** dict 加入 `"xxx": t("theme_xxx")`
3. **標題區** 加入 `elif THEME == "xxx":` 渲染
4. **`XXX_CSS`** 字串：完整 Streamlit CSS override
5. **`_theme_css`** dict 加入 `"xxx": XXX_CSS`
6. **accent 色**：更新 `_acc`, `_vw/_vpb/_vpf/_vmut/_vsrc`, `_q_acc`, `_n_hl/_n_txt/_n_btn/_n_btn_h`

---

## 設計預覽工作流程

```bash
cp .claude/skills/design-preview/template.html /tmp/mock.html
# 編輯 /tmp/mock.html 套用新主題
bash .claude/skills/design-preview/render.sh /tmp/mock.html /tmp/preview.png 1200x900
```

預覽確認後再實作到 app.py。
