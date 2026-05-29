# =============================================================
# app.py
# 功能：Streamlit 網頁介面
#       讓使用者上傳音檔、查看分析結果、瀏覽歷史記錄
# 使用方式：在終端機執行 → streamlit run src/app.py
# =============================================================

import os
import sys
import json
import tempfile
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(__file__))
from database import (init_database, get_all_sessions, get_vocabulary_due_today,
                       delete_session, get_all_vocabulary, delete_vocabulary,
                       save_news_article, get_saved_news, delete_saved_news)

load_dotenv()
init_database()


# ══════════════════════════════════════════════════════════════
# 発音ボタン（components.html で iframe 内 JS を実行）
#   st.markdown の onclick は DOMPurify で除去されるため使えない。
#   iOS は cancel→speak を同一ユーザー操作内で同期実行（setTimeout 不可）。
# ══════════════════════════════════════════════════════════════
def speak_button(word, label="🔊", height=44, font_size=13):
    safe = (word or "").replace("\\", "\\\\").replace("'", "\\'").replace('"', '\\"')
    components.html(
        f"""
<button onclick="(function(){{
  if(!window.speechSynthesis) return;
  var u = new SpeechSynthesisUtterance('{safe}');
  u.lang='en-US'; u.rate=0.85; u.volume=1;
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(u);
}})()" style="
  font-family:'Noto Sans JP',sans-serif;
  background:#F5F5F5; color:#555;
  border:1px solid #E0E0E0; border-radius:2px;
  padding:6px 14px; font-size:{font_size}px; letter-spacing:.08em;
  cursor:pointer; -webkit-tap-highlight-color:transparent;
" onmouseover="this.style.background='#ECECEC'"
  onmouseout="this.style.background='#F5F5F5'">{label}</button>
""",
        height=height,
    )

# ══════════════════════════════════════════════════════════════
# 頁面基本設定（set_page_config は最初の st 命令でなければならない）
# ══════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="英文対話分析 / 英文對話分析",
    page_icon="🎙️",
    layout="centered"
)

# ══════════════════════════════════════════════════════════════
# 介面語言切換（ja = 日本語 / zh = 繁體中文）
# ══════════════════════════════════════════════════════════════
if "lang" not in st.session_state:
    st.session_state["lang"] = "ja"

# 言語セレクタは「タイトルより前」に実行する必要がある。
# （Streamlit は上から実行するため、後ろで切り替えるとタイトルが1テンポ遅れる）
_lang_choice = st.sidebar.radio(
    "Language", ["日本語", "中文"],
    index=0 if st.session_state["lang"] == "ja" else 1,
    horizontal=True, label_visibility="collapsed", key="lang_sel",
)
st.session_state["lang"] = "ja" if _lang_choice == "日本語" else "zh"

LANG = {
    # ── ナビ / 導覽 ──
    "nav_history":   {"ja": "📚 履歴",          "zh": "📚 歷史記錄"},
    "nav_today":     {"ja": "🗓️ 今日の単語",     "zh": "🗓️ 今日單字"},
    "nav_news":      {"ja": "📰 ニュース",       "zh": "📰 新聞搜尋"},
    "nav_upload":    {"ja": "🎙️ 分析",          "zh": "🎙️ 上傳分析"},

    # ── サイドバー / 側邊欄 ──
    "side_subtitle": {"ja": "英文分析",          "zh": "英文分析"},
    "side_menu":     {"ja": "MENU",             "zh": "MENU"},
    "side_share":    {"ja": "SHARE",            "zh": "SHARE"},
    "side_share_desc": {"ja": "このページのURLを友達にシェア",
                        "zh": "將此頁面網址分享給朋友"},

    # ── タイトル / 標題 ──
    "title_main":    {"ja": "🎙️ 英文対話分析・スマート単語帳",
                      "zh": "🎙️ 英文對話分析與智慧單字本"},
    "title_sub":     {"ja": "AIで英会話を分析・単語を記憶",
                      "zh": "用 AI 分析英語對話、記憶單字"},

    # ── アップロード分析ページ / 上傳分析頁 ──
    "up_header":     {"ja": "音声をアップロードして分析",
                      "zh": "上傳音檔開始分析"},
    "up_link_exp":   {"ja": "📄 練習記事を設定（任意）",
                      "zh": "📄 連結練習文章（選填）"},
    "up_linked":     {"ja": "📰 連携中：",        "zh": "📰 已連結："},
    "up_view_body":  {"ja": "記事を確認",         "zh": "查看文章內容"},
    "up_unlink":     {"ja": "✖ 連携を解除",       "zh": "✖ 取消連結"},
    "up_link_hint":  {"ja": "記事を貼り付けるか .txt をアップロードすると、AIが原文と照合します",
                      "zh": "貼上文章或上傳 .txt 檔，AI 會對照原文分析"},
    "up_tab_paste":  {"ja": "📋 貼り付け",        "zh": "📋 貼上文字"},
    "up_tab_file":   {"ja": "📁 .txt",           "zh": "📁 上傳 .txt"},
    "up_title_in":   {"ja": "タイトル（任意）",    "zh": "文章標題（選填）"},
    "up_body_in":    {"ja": "記事本文を貼り付け",  "zh": "貼上文章內容"},
    "up_set_btn":    {"ja": "✅ 練習記事に設定",   "zh": "✅ 設定為練習文章"},
    "up_no_body":    {"ja": "記事本文を入力してください",
                      "zh": "請貼上文章內容"},
    "up_file_in":    {"ja": ".txt ファイルをアップロード",
                      "zh": "上傳 .txt 檔"},
    "up_ext_default":{"ja": "外部記事",           "zh": "外部文章"},
    "up_audio_in":   {"ja": "音声ファイルを選択（mp3・wav・m4a）",
                      "zh": "選擇音檔（mp3、wav、m4a）"},
    "up_done":       {"ja": "✅ アップロード完了：",
                      "zh": "✅ 已上傳："},
    "up_start":      {"ja": "🚀 分析開始",        "zh": "🚀 開始分析"},
    "up_sp_trans":   {"ja": "⏳ 文字起こし＋話者識別中（約30秒）...",
                      "zh": "⏳ 轉錄＋識別說話者中（約30秒）..."},
    "up_speakers":   {"ja": "位の話者、",          "zh": "位說話者，"},
    "up_segments":   {"ja": "セグメント",          "zh": "段"},
    "up_diar_err":   {"ja": "⚠️ 分離エラー（バックアップモード）:",
                      "zh": "⚠️ 分離錯誤（使用備用模式）:"},
    "up_transcript": {"ja": "💬 話者別逐字稿",     "zh": "💬 說話者分離逐字稿"},
    "up_sp_analyze": {"ja": "⏳ 分析中...",        "zh": "⏳ 正在分析..."},
    "up_complete":   {"ja": "🎉 分析完了！",       "zh": "🎉 分析完成！"},
    "up_m_score":    {"ja": "総合評価",           "zh": "整體評分"},
    "up_m_vocab":    {"ja": "新規単語",           "zh": "新增單字"},
    "up_m_unit":     {"ja": "個",                "zh": "個"},
    "up_h_grammar":  {"ja": "📝 文法アドバイス",   "zh": "📝 文法建議"},
    "up_no_grammar": {"ja": "文法エラーは見つかりませんでした！",
                      "zh": "沒有發現明顯文法錯誤！"},
    "up_h_vocab":    {"ja": "📚 学んだ単語",       "zh": "📚 學到的單字"},
    "up_example":    {"ja": "例文：",             "zh": "例句："},
    "up_h_pron":     {"ja": "🗣️ 発音のヒント",     "zh": "🗣️ 發音提示"},
    "up_pdf_btn":    {"ja": "📄 レポートをPDFでダウンロード",
                      "zh": "📄 下載 PDF 分析報告"},

    # ── ニュースページ / 新聞頁 ──
    "news_added":    {"ja": "を単語本に追加",      "zh": "已加入單字本"},
    "news_header":   {"ja": "📰 英語ニュース検索",  "zh": "📰 英文新聞搜尋"},
    "news_level":    {"ja": "📊 英語レベル",       "zh": "📊 英文程度"},
    "news_caption":  {"ja": "💡 どの言語でもOK、Geminiがリアルなニュースを検索します",
                      "zh": "💡 任何語言輸入主題，Gemini 會幫你找真實新聞"},
    "news_chat_in":  {"ja": "ニュースのテーマを入力... (e.g. AI, climate, economy)",
                      "zh": "輸入你想看的新聞主題... (e.g. AI, climate, economy)"},
    "news_search_fail": {"ja": "検索失敗：",       "zh": "搜尋失敗："},
    "news_tip_line": {"ja": "🔊 単語をタップで発音 ｜ 長押しで単語本に追加",
                      "zh": "🔊 點擊單字可聽發音 ｜ 長按可加入單字本"},
    "news_copy_exp": {"ja": "📋 記事をコピー",     "zh": "📋 複製文章給朋友"},
    "news_save_btn": {"ja": "💾 記事を保存",       "zh": "💾 儲存此新聞"},
    "news_saved_toast": {"ja": "✅ 記事を保存しました",
                         "zh": "✅ 新聞已儲存"},
    "news_practice_btn": {"ja": "🎙️ この記事で練習", "zh": "🎙️ 用這篇練習"},
    "news_h_saved":  {"ja": "💾 保存した記事",     "zh": "💾 已儲存新聞"},
    "news_no_saved": {"ja": "まだ保存した記事はありません",
                      "zh": "還沒有儲存的新聞"},
    "news_source":   {"ja": "ソース：",           "zh": "來源："},
    "news_saved_at": {"ja": "保存日 ",            "zh": "儲存於 "},
    "news_practice2":{"ja": "🎙️ この記事で練習",   "zh": "🎙️ 用這篇練習"},
    "news_delete":   {"ja": "🗑️ 削除",            "zh": "🗑️ 刪除"},

    # ── 履歴ページ / 歷史頁 ──
    "hist_header":   {"ja": "分析履歴",           "zh": "歷史分析記錄"},
    "hist_empty":    {"ja": "まだ記録がありません。音声をアップロードしてください！",
                      "zh": "還沒有任何記錄，請先上傳音檔分析！"},
    "hist_count1":   {"ja": "合計 ",              "zh": "共 "},
    "hist_count2":   {"ja": " 件",               "zh": " 筆記錄"},
    "hist_score":    {"ja": "評価：",             "zh": "評分："},
    "hist_tab_t":    {"ja": "💬 逐字起こし",       "zh": "💬 逐字稿"},
    "hist_tab_g":    {"ja": "📝 文法",            "zh": "📝 文法"},
    "hist_tab_p":    {"ja": "🗣️ 発音",            "zh": "🗣️ 發音"},
    "hist_tab_v":    {"ja": "📚 単語",            "zh": "📚 單字"},
    "hist_no_grammar": {"ja": "文法エラーなし",    "zh": "沒有文法錯誤"},
    "hist_no_pron":  {"ja": "発音提示なし",        "zh": "無發音提示"},
    "hist_no_vocab": {"ja": "単語なし",           "zh": "無單字"},
    "hist_example":  {"ja": "例文：",             "zh": "例句："},
    "hist_delete":   {"ja": "🗑️ 削除",            "zh": "🗑️ 刪除"},
    "hist_del_toast":{"ja": "削除しました",        "zh": "已刪除"},

    # ── 今日の単語ページ / 今日單字頁 ──
    "today_header":  {"ja": "今日の単語復習",      "zh": "今日單字複習"},
    "today_add_exp": {"ja": "➕ 単語を手動追加",   "zh": "➕ 手動新增單字"},
    "today_word_in": {"ja": "英単語",            "zh": "英文單字"},
    "today_add_btn": {"ja": "🔍 自動で調べて追加", "zh": "🔍 自動查詢並加入單字本"},
    "today_lookup":  {"ja": "Gemini で検索中：",   "zh": "Gemini 查詢中："},
    "today_ex":      {"ja": "例文：",             "zh": "例句："},
    "today_lookup_fail": {"ja": "検索失敗：",      "zh": "查詢失敗："},
    "today_no_word": {"ja": "単語を入力してください", "zh": "請輸入單字"},
    "today_all_done":{"ja": "🎉 今日復習する単語はありません。お疲れさまでした！",
                      "zh": "🎉 今天沒有需要複習的單字，很棒！"},
    "today_done1":   {"ja": "🎉 今日の ",         "zh": "🎉 今天的 "},
    "today_done2":   {"ja": " 単語をすべて完了！",  "zh": " 個單字全部複習完畢！"},
    "today_restart": {"ja": "最初から",           "zh": "重新開始"},
    "today_m_today": {"ja": "今日",              "zh": "今日"},
    "today_m_done":  {"ja": "完了",              "zh": "已複習"},
    "today_m_left":  {"ja": "残り",              "zh": "剩餘"},
    "today_progress":{"ja": "進捗：",             "zh": "進度："},
    "today_listen":  {"ja": "🔊 発音",            "zh": "🔊 發音"},
    "today_review_n":{"ja": "復習 ",             "zh": "複習 "},
    "today_review_unit": {"ja": " 回",           "zh": " 回"},
    "today_ease":    {"ja": "難易度 ",            "zh": "難易度 "},
    "today_show":    {"ja": "👁️ 答えを見る",       "zh": "👁️ 顯示答案"},
    "today_meaning": {"ja": "意味：",             "zh": "中文："},
    "today_ex_label":{"ja": "例文：",             "zh": "例句："},
    "today_how_much":{"ja": "どれだけ覚えていますか？", "zh": "你記得多少？"},
    "today_src_vocab":{"ja": "📖 重要単語",        "zh": "📖 重點單字"},
    "today_src_pron": {"ja": "🗣️ 発音ミス",        "zh": "🗣️ 發音錯誤"},
    "today_src_hesit":{"ja": "💭 迷った単語",       "zh": "💭 猶豫單字"},
    "today_src_manual":{"ja": "✏️ 手動追加",        "zh": "✏️ 手動新增"},
    "today_h_list":  {"ja": "📋 単語リスト",       "zh": "📋 單字總表"},
    "today_no_list": {"ja": "まだ単語がありません", "zh": "還沒有單字記錄"},
    "today_lbl_vocab":{"ja": "📖 重要",            "zh": "📖 重點"},
    "today_lbl_pron": {"ja": "🗣️ 発音",            "zh": "🗣️ 發音"},
    "today_lbl_hesit":{"ja": "💭 迷い",            "zh": "💭 猶豫"},
    "today_lbl_manual":{"ja": "✏️ 手動",           "zh": "✏️ 手動"},
    "today_search":  {"ja": "🔍 単語を検索",       "zh": "🔍 搜尋單字"},
    "today_cnt1":    {"ja": "合計 ",             "zh": "共 "},
    "today_cnt2":    {"ja": " 単語",             "zh": " 個單字"},
    "today_del_help":{"ja": "この単語を削除",       "zh": "刪除此單字"},
}


def t(key):
    return LANG.get(key, {}).get(st.session_state["lang"], key)


st.markdown(
    '<div style="padding:4px 0 20px;border-bottom:1px solid #E8E8E8;margin-bottom:28px;">'
    '<div style="font-size:24px;font-weight:400;letter-spacing:.04em;color:#1A1A1A;line-height:1.4;">'
    f'{t("title_main")}</div>'
    '<div style="font-size:14px;font-weight:400;color:#888;letter-spacing:.03em;margin-top:2px;">'
    f'{t("title_sub")}</div>'
    '</div>',
    unsafe_allow_html=True
)

# ── 禅・無印 テーマ + 手機響應式 CSS ────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@300;400;500&display=swap');

/* ── 全体背景・フォント ── */
html, body, [data-testid="stAppViewContainer"] {
    background-color: #FAFAFA !important;
    color: #1A1A1A !important;
}
/* 上部ツールバーを透明に（黒帯を消す） */
[data-testid="stHeader"] {
    background: transparent !important;
    background-color: rgba(0,0,0,0) !important;
}
[data-testid="stToolbar"] { background: transparent !important; }
[data-testid="stAppViewContainer"] {
    font-family: 'Noto Sans JP', 'Helvetica Neue', sans-serif !important;
    font-weight: 300;
}

/* ── メインエリア ── */
.main .block-container {
    max-width: 100%;
    padding: 2rem 2rem 4rem;
    overflow-x: hidden;
    box-sizing: border-box;
    background: #FAFAFA;
}

/* ── タイトル・見出し ── */
h1 { font-size: 1.5rem !important; font-weight: 400 !important;
     letter-spacing: .04em !important; color: #1A1A1A !important; }
h2 { font-size: 1.2rem !important; font-weight: 400 !important;
     letter-spacing: .03em !important; color: #1A1A1A !important;
     border-bottom: 1px solid #E8E8E8 !important; padding-bottom: .4rem !important; }
h3 { font-size: 1.05rem !important; font-weight: 500 !important; color: #1A1A1A !important; }
.stCaption p { color: #AAAAAA !important; font-size: 11px !important; letter-spacing: .08em; }

/* ── サイドバー ── */
[data-testid="stSidebar"] {
    background-color: #F5F5F5 !important;
    border-right: 1px solid #EBEBEB !important;
}
[data-testid="stSidebar"] * { font-family: 'Noto Sans JP', sans-serif !important; }
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3, [data-testid="stSidebar"] p {
    color: #555 !important; font-weight: 400 !important;
}
[data-testid="stSidebar"] .stRadio label {
    font-size: 13px !important; color: #555 !important;
    padding: 8px 0 !important; letter-spacing: .04em;
    border-bottom: 1px solid #EBEBEB !important;
}
[data-testid="stSidebar"] .stRadio [aria-checked="true"] + div {
    color: #4A7C59 !important; font-weight: 500 !important;
}

/* ── ボタン ── */
.stButton > button {
    background-color: #FFF !important;
    color: #1A1A1A !important;
    border: 1px solid #DDD !important;
    border-radius: 2px !important;
    font-family: 'Noto Sans JP', sans-serif !important;
    font-weight: 400 !important;
    letter-spacing: .08em !important;
    font-size: 13px !important;
    padding: 8px 20px !important;
    transition: border-color .2s, color .2s !important;
    white-space: normal !important;
    word-break: break-word !important;
    line-height: 1.4 !important;
    min-height: 40px !important;
}
.stButton > button:hover {
    border-color: #4A7C59 !important;
    color: #4A7C59 !important;
    background-color: #FFF !important;
}
/* primary ボタン */
.stButton > button[kind="primary"],
[data-testid="baseButton-primary"] {
    background-color: #4A7C59 !important;
    color: #FFF !important;
    border: none !important;
}
[data-testid="baseButton-primary"]:hover {
    background-color: #3D6A4B !important;
    color: #FFF !important;
}

/* ── 入力・セレクト ── */
input, textarea, select,
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea {
    background: #FFF !important;
    border: 1px solid #E0E0E0 !important;
    border-radius: 2px !important;
    color: #1A1A1A !important;
    font-family: 'Noto Sans JP', sans-serif !important;
    font-size: 13px !important;
}
input:focus, textarea:focus {
    border-color: #4A7C59 !important;
    box-shadow: none !important;
}

/* ── メトリクス（新旧 Streamlit 両対応の testid）── */
[data-testid="metric-container"],
[data-testid="stMetric"] {
    background: #FFF !important;
    border: 1px solid #E8E8E8 !important;
    border-top: 2px solid #4A7C59 !important;
    border-radius: 2px !important;
    padding: 18px 20px !important;
}
[data-testid="stMetricValue"] {
    font-size: 2rem !important; font-weight: 300 !important;
    color: #1A1A1A !important;
}
[data-testid="stMetricLabel"] {
    font-size: 11px !important; color: #AAA !important;
    letter-spacing: .12em !important;
}

/* ── エクスパンダー ── */
[data-testid="stExpander"] {
    border: 1px solid #E8E8E8 !important;
    border-radius: 2px !important;
    background: #FFF !important;
}
[data-testid="stExpander"] summary {
    background: #FFF !important;
    font-size: 13px !important;
    color: #555 !important;
    letter-spacing: .04em;
}
[data-testid="stExpander"] summary:hover { color: #4A7C59 !important; }

/* ── タブ ── */
[data-testid="stTabs"] [role="tablist"] {
    border-bottom: 1px solid #E8E8E8 !important;
    gap: 0 !important;
}
[data-testid="stTabs"] button[role="tab"] {
    font-size: 12px !important; color: #AAA !important;
    letter-spacing: .1em !important; font-weight: 400 !important;
    padding: 8px 20px !important; border-bottom: 2px solid transparent !important;
    background: transparent !important; border-radius: 0 !important;
}
[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
    color: #4A7C59 !important; border-bottom-color: #4A7C59 !important;
    font-weight: 500 !important;
}

/* ── info / success / warning / error ── */
[data-testid="stAlert"] {
    border-radius: 2px !important;
    border-left-width: 3px !important;
    font-size: 13px !important;
}
.stSuccess { background: #F0F7F2 !important; border-color: #4A7C59 !important; color: #2D5E3A !important; }
.stInfo    { background: #F5F8FF !important; border-color: #6B8FC4 !important; color: #2A4A7A !important; }
.stWarning { background: #FDF8F0 !important; border-color: #C4A45A !important; color: #7A5A1A !important; }

/* ── 進捗バー ── */
[data-testid="stProgress"] { margin: 4px 0 !important; }
/* track（背景）灰 */
[data-testid="stProgress"] > div {
    background: #ECECEC !important;
    border-radius: 2px !important;
    height: 4px !important;
    overflow: hidden !important;
}
/* fill（進捗）抹茶緑 */
[data-testid="stProgress"] > div > div {
    background: #4A7C59 !important;
    border-radius: 2px !important;
    height: 4px !important;
}
[data-testid="stProgress"] p {
    color: #999 !important; font-size: 12px !important;
    letter-spacing: .05em !important; margin-top: 4px !important;
}

/* ── divider ── */
hr { border-color: #E8E8E8 !important; border-width: 1px 0 0 !important; }

/* ── code ── */
code { background: #F5F5F5 !important; color: #555 !important;
       font-size: .85em !important; padding: 1px 6px !important;
       border-radius: 2px !important; }

/* ── ファイルアップローダー ── */
[data-testid="stFileUploader"] {
    border: 1px solid #E0E0E0 !important;
    border-radius: 2px !important;
    background: #FFF !important;
}
/* Upload/Browse ボタンを Zen 風に（黒を消す）*/
[data-testid="stFileUploader"] button,
[data-testid="stFileUploaderDropzone"] button {
    background: #FFF !important;
    color: #4A7C59 !important;
    border: 1px solid #4A7C59 !important;
    border-radius: 2px !important;
    font-weight: 400 !important;
    letter-spacing: .05em !important;
    box-shadow: none !important;
}
[data-testid="stFileUploader"] button:hover {
    background: #F0F7F2 !important;
    color: #3D6A4B !important;
}

/* ── チャット入力（ニュース検索）の黒帯を消す ── */
[data-testid="stBottom"],
[data-testid="stBottomBlockContainer"],
[data-testid="stChatInput"] {
    background: #FAFAFA !important;
}
[data-testid="stChatInput"] > div {
    background: #FFF !important;
    border: 1px solid #E0E0E0 !important;
    border-radius: 2px !important;
}
[data-testid="stChatInput"] textarea {
    background: #FFF !important;
    color: #1A1A1A !important;
}
[data-testid="stChatInput"] button {
    background: #4A7C59 !important;
    border-radius: 2px !important;
}

/* ── selectbox ── */
[data-testid="stSelectbox"] > div > div {
    background: #FFF !important;
    border: 1px solid #E0E0E0 !important;
    border-radius: 2px !important;
    color: #1A1A1A !important;
    font-size: 13px !important;
}

/* ── トースト通知 ── */
[data-testid="stToast"] {
    background: #1A1A1A !important;
    color: #FFF !important;
    border-radius: 2px !important;
    font-size: 13px !important;
}

/* ── 手機 (768px 以下) ── */
@media (max-width: 768px) {
    .main .block-container { padding: .75rem .75rem 3rem !important; }
    h1 { font-size: 1.15rem !important; line-height: 1.5 !important; }
    h2 { font-size: 1rem !important; }
    h3 { font-size: .9rem !important; }
    /* 側邊欄ヘッダー */
    [data-testid="stSidebar"] h2 { font-size: .95rem !important; }
    /* 欄位不溢出 */
    [data-testid="column"] { overflow: hidden; min-width: 0; }
    code, pre { white-space: pre-wrap !important; word-break: break-word !important; }
    /* タブ */
    [data-testid="stTabs"] button[role="tab"] {
        padding: 8px 8px !important; font-size: 11px !important;
    }
    /* metric */
    [data-testid="stMetricValue"] { font-size: 1.6rem !important; }
    /* caption */
    .stCaption p { font-size: 11px !important; }
    /* ボタン */
    .stButton > button {
        font-size: 12px !important; padding: 7px 10px !important;
        white-space: normal !important; word-break: break-word !important;
        line-height: 1.35 !important; min-height: 38px !important;
    }
    /* expander */
    [data-testid="stExpander"] summary p { font-size: 12px !important; }
    /* selectbox / input */
    [data-testid="stSelectbox"] > div > div,
    [data-testid="stTextInput"] input { font-size: 13px !important; }
    /* 進捗バー高さ調整 */
    [data-testid="stProgress"] > div { height: 3px !important; }
    [data-testid="stProgress"] > div > div { height: 3px !important; }
}
@media (max-width: 390px) {
    .main .block-container { padding: .5rem .5rem 3rem !important; }
    h1 { font-size: 1rem !important; }
    [data-testid="stTabs"] button[role="tab"] {
        padding: 7px 6px !important; font-size: 10px !important;
    }
}

/* ════ 精緻化（脫離預設樣式）════ */
/* subheader を section 見出し風に */
h3 {
    position: relative !important;
    padding-left: 14px !important;
    letter-spacing: .06em !important;
    margin-top: 8px !important;
}
h3::before {
    content: '' !important;
    position: absolute !important;
    left: 0 !important; top: 50% !important;
    transform: translateY(-50%) !important;
    width: 4px !important; height: 16px !important;
    background: #4A7C59 !important;
    border-radius: 1px !important;
}
/* sidebar radio をメニューカード風に */
[data-testid="stSidebar"] .stRadio > div {
    gap: 0 !important;
}
[data-testid="stSidebar"] .stRadio label {
    padding: 11px 4px !important;
    margin: 0 !important;
    transition: color .15s, padding-left .15s !important;
}
[data-testid="stSidebar"] .stRadio label:hover {
    color: #4A7C59 !important;
    padding-left: 8px !important;
}
/* expander をカード風に強化 */
[data-testid="stExpander"] {
    box-shadow: 0 1px 2px rgba(0,0,0,.03) !important;
    margin-bottom: 10px !important;
    transition: box-shadow .15s !important;
}
[data-testid="stExpander"]:hover {
    box-shadow: 0 2px 8px rgba(0,0,0,.06) !important;
}
/* metric ラベルを大文字スタイルに */
[data-testid="stMetricLabel"] {
    text-transform: uppercase !important;
    font-weight: 500 !important;
}
/* divider を細く上品に */
[data-testid="stMarkdownContainer"] hr {
    margin: 1.5rem 0 !important;
    border-color: #ECECEC !important;
}
/* 全体行間 */
[data-testid="stAppViewContainer"] p { line-height: 1.7 !important; }
/* file uploader 内テキスト */
[data-testid="stFileUploader"] section {
    background: #FFF !important;
    border: 1px dashed #DDD !important;
    border-radius: 2px !important;
}
/* スクロールバー（webkit）*/
::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-thumb { background: #DDD; border-radius: 4px; }
::-webkit-scrollbar-track { background: transparent; }

/* サイドバー開閉ボタンの material icon 文字化対策（keyboard_double_arrow 等を隠す）*/
[data-testid="stSidebarCollapseButton"] span,
[data-testid="collapsedControl"] span,
[data-testid="stSidebarCollapsedControl"] button span {
    font-family: 'Material Symbols Rounded','Material Symbols Outlined','Material Icons' !important;
}
/* それでも文字化けする場合は隠して ☰ を代わりに表示 */
[data-testid="collapsedControl"] button,
[data-testid="stSidebarCollapsedControl"] button {
    font-size: 0 !important;
}
[data-testid="collapsedControl"] button::after,
[data-testid="stSidebarCollapsedControl"] button::after {
    content: '☰' !important;
    font-size: 22px !important;
    color: #555 !important;
}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# 側邊欄：導覽選單
# ══════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown(
        '<div style="padding:4px 0 8px;">'
        f'<div style="font-size:15px;font-weight:500;color:#1A1A1A;letter-spacing:.05em;">🎙 {t("side_subtitle")}</div>'
        '<div style="font-size:10px;color:#BBB;letter-spacing:.22em;margin-top:2px;">ENGLISH LEARNING AI</div>'
        '</div>'
        f'<div style="font-size:10px;letter-spacing:.28em;color:#BBB;margin:18px 0 8px;">{t("side_menu")}</div>',
        unsafe_allow_html=True
    )
    PAGE_KEYS = ["history", "today", "news", "upload"]
    page_labels = [t("nav_history"), t("nav_today"), t("nav_news"), t("nav_upload")]
    # index で現在ページを記憶（言語切替でラベルが変わっても壊れない）
    if "page_idx" not in st.session_state:
        st.session_state["page_idx"] = 0
    sel = st.radio("menu", page_labels,
                   index=st.session_state["page_idx"],
                   label_visibility="collapsed")
    st.session_state["page_idx"] = page_labels.index(sel)
    page = PAGE_KEYS[st.session_state["page_idx"]]

    st.markdown(
        f'<div style="font-size:10px;letter-spacing:.28em;color:#BBB;margin:24px 0 8px;">{t("side_share")}</div>'
        '<div style="font-size:11px;color:#999;line-height:1.7;letter-spacing:.03em;">'
        f'{t("side_share_desc")}</div>',
        unsafe_allow_html=True
    )

# ══════════════════════════════════════════════════════════════
# 頁面一：上傳分析
# ══════════════════════════════════════════════════════════════
if page == "upload":

    st.header(t("up_header"))

    # ── 練習文章（從新聞頁帶入 或 手動貼上/上傳）────────────────
    practice_news = st.session_state.get("practice_news")

    with st.expander(t("up_link_exp"), expanded=bool(practice_news)):
        if practice_news:
            st.success(f"{t('up_linked')}**{practice_news['title']}**")
            with st.expander(t("up_view_body")):
                st.write(practice_news["body"])
            if st.button(t("up_unlink"), key="clear_practice"):
                del st.session_state["practice_news"]
                st.rerun()
        else:
            st.caption(t("up_link_hint"))

            ext_tab1, ext_tab2 = st.tabs([t("up_tab_paste"), t("up_tab_file")])

            with ext_tab1:
                ext_title = st.text_input(t("up_title_in"), key="ext_title", placeholder="e.g. BBC News: AI in 2025")
                ext_body  = st.text_area(t("up_body_in"), key="ext_body", height=150, placeholder="Paste article text here...")
                if st.button(t("up_set_btn"), key="set_ext_text"):
                    if ext_body.strip():
                        st.session_state["practice_news"] = {
                            "title": ext_title.strip() or t("up_ext_default"),
                            "body":  ext_body.strip()
                        }
                        st.rerun()
                    else:
                        st.warning(t("up_no_body"))

            with ext_tab2:
                txt_file = st.file_uploader(t("up_file_in"), type=["txt"], key="ext_txt")
                if txt_file:
                    txt_content = txt_file.read().decode("utf-8", errors="ignore")
                    if st.button(t("up_set_btn"), key="set_ext_file"):
                        st.session_state["practice_news"] = {
                            "title": txt_file.name.replace(".txt", ""),
                            "body":  txt_content.strip()
                        }
                        st.rerun()

    uploaded_file = st.file_uploader(
        t("up_audio_in"),
        type=["mp3", "wav", "m4a", "flac"]
    )

    if uploaded_file is not None:
        st.audio(uploaded_file)
        st.success(f"{t('up_done')}{uploaded_file.name}")

        if st.button(t("up_start"), type="primary", use_container_width=True):

            suffix = os.path.splitext(uploaded_file.name)[1]
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(uploaded_file.read())
                tmp_path = tmp.name

            try:
                # ── Step 1+2：AssemblyAI 轉錄 + 說話者分離（一次完成）─
                with st.spinner(t("up_sp_trans")):
                    from diarize_func import diarize, _fallback
                    try:
                        diarized = diarize(tmp_path)
                        transcript = diarized.get("transcript", "")
                        st.info(f"🔍 {diarized.get('speaker_count')} {t('up_speakers')}{len(diarized.get('segments', []))} {t('up_segments')}")
                    except Exception as diarize_err:
                        st.warning(f"{t('up_diar_err')}\n\n`{diarize_err}`")
                        from transcribe_func import transcribe
                        whisper_result = transcribe(tmp_path)
                        transcript = whisper_result["text"]
                        diarized = _fallback(transcript)

                # ── 話者分離結果を表示 ─────────────────────────
                label_a = diarized.get("speaker_a_label", "Speaker A")
                label_b = diarized.get("speaker_b_label", "Speaker B")

                with st.expander(t("up_transcript"), expanded=True):
                    # 話者 A → 青, 話者 B → 緑 で色分け
                    for seg in diarized.get("segments", []):
                        spk = seg.get("speaker", "A")
                        text = seg.get("text", "")
                        if spk == "A":
                            st.markdown(
                                f'<div style="background:#1a3a5c;border-left:4px solid #4a9eff;'
                                f'padding:8px 12px;margin:4px 0;border-radius:4px;">'
                                f'<b style="color:#4a9eff">{label_a}</b><br>'
                                f'<span style="color:#e8e8e8">{text}</span></div>',
                                unsafe_allow_html=True
                            )
                        else:
                            st.markdown(
                                f'<div style="background:#1a3d2b;border-left:4px solid #4caf82;'
                                f'padding:8px 12px;margin:4px 0;border-radius:4px;">'
                                f'<b style="color:#4caf82">{label_b}</b><br>'
                                f'<span style="color:#e8e8e8">{text}</span></div>',
                                unsafe_allow_html=True
                            )

                # ── Step 3：AI 分析（話者情報付き）─────────────
                with st.spinner(t("up_sp_analyze")):
                    from analyze_func import analyze
                    ref = st.session_state.get("practice_news", {}).get("body")
                    analysis = analyze(transcript, diarized=diarized, reference_text=ref)

                from database import save_session
                ref_title = st.session_state.get("practice_news", {}).get("title")
                session_id = save_session(uploaded_file.name, transcript, analysis, diarized=diarized, reference_title=ref_title)

                st.success(t("up_complete"))

                col1, col2 = st.columns(2)
                with col1:
                    st.metric(t("up_m_score"), f"{analysis.get('overall_score')} / 10")
                with col2:
                    st.metric(t("up_m_vocab"), f"{len(analysis.get('vocabulary_highlights', []))} {t('up_m_unit')}")

                st.info(f"💬 {analysis.get('summary')}")

                # ── 文法エラー（話者ラベル付き）────────────────
                errors = analysis.get("grammar_errors", [])
                st.subheader(t("up_h_grammar"))
                if errors:
                    for err in errors:
                        spk = err.get("speaker", "A")
                        spk_label = label_a if spk == "A" else label_b
                        color = "#4a9eff" if spk == "A" else "#4caf82"
                        header = (
                            f'<span style="color:{color};font-size:12px">[{spk_label}]</span>  '
                            f'❌ {err.get("original")}  →  ✅ {err.get("correction")}'
                        )
                        with st.expander(f"[{spk_label}]  {err.get('original')}  →  {err.get('correction')}"):
                            st.markdown(f'<span style="color:{color}">**{spk_label}**</span>', unsafe_allow_html=True)
                            st.write(err.get("explanation"))
                else:
                    st.success(t("up_no_grammar"))

                vocab = analysis.get("vocabulary_highlights", [])
                st.subheader(t("up_h_vocab"))
                if vocab:
                    for v in vocab:
                        pos_tag = f" `{v.get('part_of_speech')}`" if v.get('part_of_speech') else ""
                        with st.expander(f"**{v.get('word')}**{pos_tag}　{v.get('definition')}"):
                            st.write(f"{t('up_example')}*{v.get('example')}*")

                tips = analysis.get("pronunciation_tips", [])
                if tips:
                    st.subheader(t("up_h_pron"))
                    for tip in tips:
                        if isinstance(tip, dict):
                            spk = tip.get("speaker", "A")
                            spk_label = label_a if spk == "A" else label_b
                            color = "#4a9eff" if spk == "A" else "#4caf82"
                            with st.expander(f"[{spk_label}]  {tip.get('example', '')}"):
                                st.markdown(f'<span style="color:{color}">**{spk_label}**</span>', unsafe_allow_html=True)
                                st.write(tip.get("tip", ""))
                        else:
                            st.write(f"• {tip}")

                # ── PDF ダウンロード ──────────────────────────
                st.markdown("---")
                from generate_pdf import generate_report_pdf
                pdf_bytes = generate_report_pdf(
                    uploaded_file.name, transcript, analysis, diarized=diarized
                )
                st.download_button(
                    label=t("up_pdf_btn"),
                    data=pdf_bytes,
                    file_name=f"report_{uploaded_file.name}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    type="primary"
                )

            finally:
                os.unlink(tmp_path)

# ══════════════════════════════════════════════════════════════
# 頁面二：新聞搜尋（聊天框介面）
# ══════════════════════════════════════════════════════════════
elif page == "news":
    from news_search import fetch_news_with_gemini, TOEIC_LEVELS
    from database import add_vocabulary_manually

    # ── 處理從新聞頁面右鍵加入的單字 ─────────────────────────
    if st.query_params.get("save_word"):
        _w  = st.query_params.get("save_word", "")
        _d  = st.query_params.get("save_def", "")
        _pos = st.query_params.get("save_pos", "")
        if _w:
            add_vocabulary_manually(_w, _d, "", _pos)
            st.toast(f"📚 「{_w}」{t('news_added')}", icon="✅")
        st.query_params.clear()

    st.header(t("news_header"))

    # 程度選擇放在最上方
    level_key = st.selectbox(
        t("news_level"),
        list(TOEIC_LEVELS.keys())
    )
    st.caption(t("news_caption"))

    # 初始化聊天記錄
    if "news_messages" not in st.session_state:
        st.session_state.news_messages = []

    # 顯示歷史聊天記錄
    for msg in st.session_state.news_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"], unsafe_allow_html=True)

    # 聊天輸入框（任何語言皆可）
    if prompt := st.chat_input(t("news_chat_in")):

        # 顯示使用者訊息
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.news_messages.append({"role": "user", "content": prompt})

        # 用 Gemini + Google Search 找真實新聞（只取 1 篇）
        with st.chat_message("assistant"):
            with st.spinner("🔍 Searching real news with Gemini..."):
                try:
                    articles = fetch_news_with_gemini(prompt, level_key, count=1)
                except Exception as e:
                    st.error(f"{t('news_search_fail')}{e}")
                    st.stop()

            if not articles:
                reply = "No articles found. Please try a different topic."
                st.markdown(reply)
                st.session_state.news_messages.append({"role": "assistant", "content": reply})
            else:
                a = articles[0]
                title  = a.get("title", "")
                source = a.get("source", "")
                date   = a.get("date", "")
                body   = a.get("body", "")
                vocab  = a.get("vocabulary", [])

                # ── 標題 & 來源（純文字，存入歷史記錄用）
                header_md = f"### {title}\n*{source}  ·  {date}*"
                st.markdown(header_md)

                # ── 正文：hover 時播放發音 + 顯示中日翻譯 tooltip
                glossary = a.get("word_glossary", {})
                # 把 glossary 轉成 JS 物件字串（key 全部小寫方便比對）
                import json as _json
                glossary_lower = {k.lower().strip(".,!?\"'():"): v for k, v in glossary.items()}
                glossary_js = _json.dumps(glossary_lower, ensure_ascii=False)

                # 每個詞包在 <span> 裡，附上原始詞（去除標點）供查字典
                def make_span(token):
                    clean = token.lower().strip(".,!?\"'():")
                    return f'<span class="w" data-word="{clean}" onmouseover="onHover(this)" oncontextmenu="onRightClick(event,this)">{token}</span>'

                words_html = " ".join(make_span(w) for w in body.split())

                html_block = f"""
<style>
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; padding: 0; background: transparent; }}
  .news-body {{
    font-size: clamp(14px, 4vw, 16px);
    line-height: 2.0;
    color: #e8e8e8;
    font-family: Georgia, serif;
    word-break: break-word;
    overflow-wrap: break-word;
  }}
  .w {{
    cursor: pointer;
    border-radius: 3px;
    padding: 1px 3px;
    transition: background 0.15s;
    position: relative;
    -webkit-tap-highlight-color: transparent;
    touch-action: manipulation;
  }}
  .w:hover, .w.active {{ background: #2a5ea8; color: #fff; }}
  #tooltip {{
    position: fixed;
    background: #1e2a3a;
    color: #f0f0f0;
    border: 1px solid #3a6ea8;
    border-radius: 8px;
    padding: 7px 12px;
    font-size: clamp(12px, 3.5vw, 14px);
    line-height: 1.6;
    pointer-events: none;
    display: none;
    z-index: 9999;
    max-width: min(220px, 80vw);
    box-shadow: 0 4px 12px rgba(0,0,0,0.5);
  }}
  #tooltip .en {{ font-weight: bold; color: #7eb8f7; font-size: clamp(13px, 4vw, 15px); }}
  #tooltip .jp {{ color: #f9ca74; }}
  #tooltip .zh {{ color: #a8e6a3; }}
  .tip {{ font-size: clamp(11px, 3vw, 12px); color: #888; margin-bottom: 6px; }}
  #ctx-menu {{
    position: fixed;
    background: #1e2a3a;
    border: 1px solid #3a6ea8;
    border-radius: 10px;
    padding: 12px;
    z-index: 99999;
    width: min(260px, 85vw);
    box-shadow: 0 6px 20px rgba(0,0,0,0.6);
  }}
  #ctx-menu .ctx-word {{ color:#7eb8f7; font-weight:bold; font-size:clamp(14px,4vw,16px); margin-bottom:8px; }}
  #ctx-menu select, #ctx-menu input {{
    width: 100%; background: #0e1621; color: #fff;
    border: 1px solid #3a6ea8; border-radius: 4px;
    padding: 8px 7px; font-size: clamp(12px,3.5vw,13px);
    box-sizing: border-box; margin-bottom: 6px;
  }}
  #ctx-menu button {{
    width: 100%; background: #29629e; color: #fff;
    border: none; border-radius: 5px;
    padding: 10px; cursor: pointer; font-size: clamp(13px,3.5vw,14px);
  }}
  #ctx-menu button:hover, #ctx-menu button:active {{ background: #3a7abf; }}
  #ctx-saved {{
    color: #4caf82; font-size: 13px; text-align: center;
    margin-top: 6px; display: none;
  }}
</style>

<div id="tooltip"></div>
<p class="tip">{t('news_tip_line')}</p>
<div class="news-body">{words_html}</div>

<script>
const GLOSSARY = {glossary_js};
const isMobile = ('ontouchstart' in window);

function ttsSpeak(word) {{
  var s = window.speechSynthesis;
  if (!s) return;
  var go = function() {{
    var u = new SpeechSynthesisUtterance(word);
    u.lang = 'en-US'; u.rate = 0.85; u.volume = 1;
    s.speak(u);
  }};
  if (s.speaking || s.pending) {{ s.cancel(); setTimeout(go, 80); }}
  else {{ go(); }}
}}

function showTooltip(el, x, y) {{
  const word = el.dataset.word;
  const entry = GLOSSARY[word];
  const tip = document.getElementById('tooltip');
  if (entry) {{
    tip.innerHTML =
      '<span class="en">' + el.innerText + '</span><br>' +
      '<span class="jp">🇯🇵 ' + entry.jp + '</span><br>' +
      '<span class="zh">🇹🇼 ' + entry.zh + '</span>';
  }} else {{
    tip.innerHTML = '<span class="en">' + el.innerText + '</span>';
  }}
  tip.style.display = 'block';
  const tipW = tip.offsetWidth || 220;
  const tipH = tip.offsetHeight || 80;
  const vw = window.innerWidth;
  const vh = window.innerHeight;
  let tx = (x + 14 + tipW > vw - 8) ? (x - tipW - 8) : (x + 14);
  let ty = (y + tipH > vh - 8) ? (vh - tipH - 8) : (y - 10);
  tip.style.left = Math.max(4, tx) + 'px';
  tip.style.top  = Math.max(4, ty) + 'px';
}}

function onHover(el) {{
  if (isMobile) return;
  ttsSpeak(el.dataset.word);
}}

document.addEventListener('mousemove', function(e) {{
  if (isMobile) return;
  const tip = document.getElementById('tooltip');
  if (tip.style.display === 'block') {{
    showTooltip(document.querySelector('.w.active') || e.target, e.clientX, e.clientY);
  }}
}});

document.addEventListener('mouseout', function(e) {{
  if (!e.target.classList.contains('w')) {{
    document.getElementById('tooltip').style.display = 'none';
  }}
}});

// ── 行動裝置：點擊播放發音 + 長按開啟選單 ──────────────
let pressTimer = null;
let pressEl = null;

document.querySelectorAll('.w').forEach(function(el) {{
  // 桌機 hover tooltip
  el.addEventListener('mouseenter', function(e) {{
    if (!isMobile) showTooltip(el, e.clientX, e.clientY);
  }});
  el.addEventListener('mouseleave', function() {{
    if (!isMobile) document.getElementById('tooltip').style.display = 'none';
  }});

  // 觸控：點擊 = 發音，長按 = 右鍵選單
  el.addEventListener('touchstart', function(e) {{
    pressEl = el;
    el.classList.add('active');
    const touch = e.touches[0];

    // 點擊播放發音（iOS 相容）
    ttsSpeak(el.dataset.word);

    // 顯示 tooltip
    showTooltip(el, touch.clientX, touch.clientY);

    // 長按觸發選單
    pressTimer = setTimeout(function() {{
      e.preventDefault();
      document.getElementById('tooltip').style.display = 'none';
      onRightClick({{clientX: touch.clientX, clientY: touch.clientY, preventDefault: function(){{}} }}, el);
    }}, 600);
  }}, {{passive: true}});

  el.addEventListener('touchend', function() {{
    clearTimeout(pressTimer);
    if (pressEl) pressEl.classList.remove('active');
    setTimeout(function() {{
      document.getElementById('tooltip').style.display = 'none';
    }}, 1200);
  }});

  el.addEventListener('touchmove', function() {{
    clearTimeout(pressTimer);
    if (pressEl) pressEl.classList.remove('active');
    document.getElementById('tooltip').style.display = 'none';
  }});
}});

// ── 右鍵選單（桌機右鍵 / 行動裝置長按）────────────────
function onRightClick(e, el) {{
  e.preventDefault();
  document.getElementById('tooltip').style.display = 'none';
  const existing = document.getElementById('ctx-menu');
  if (existing) existing.remove();

  const word = el.dataset.word;
  const entry = GLOSSARY[word] || {{}};
  const defVal = entry.zh ? entry.zh + (entry.jp ? ' / ' + entry.jp : '') : '';

  const menu = document.createElement('div');
  menu.id = 'ctx-menu';
  menu.innerHTML = `
    <div class="ctx-word">📖 ${{el.innerText}}</div>
    <select id="ctx-pos">
      <option value="">品詞 / 詞性（選填）</option>
      <option value="noun">noun 名詞</option>
      <option value="verb">verb 動詞</option>
      <option value="adjective">adjective 形容詞</option>
      <option value="adverb">adverb 副詞</option>
      <option value="phrase">phrase 片語</option>
      <option value="idiom">idiom 慣用語</option>
    </select>
    <input id="ctx-def" placeholder="定義 / Definition" value="${{defVal}}">
    <button onclick="saveToVocab('${{word}}')">📚 加入單字本 / Add to Vocab</button>
    <div id="ctx-saved">✅ 已加入！</div>
  `;

  const menuW = Math.min(260, window.innerWidth * 0.85);
  const menuH = 200;
  const vw = window.innerWidth;
  const vh = window.innerHeight;
  const x = (e.clientX + menuW > vw - 8) ? (e.clientX - menuW - 4) : e.clientX;
  const y = (e.clientY + menuH > vh - 8) ? (vh - menuH - 8) : e.clientY;
  menu.style.left = Math.max(4, x) + 'px';
  menu.style.top  = Math.max(4, y) + 'px';
  document.body.appendChild(menu);

  setTimeout(() => {{
    document.addEventListener('touchstart', function closeMenu(ev) {{
      if (!menu.contains(ev.target)) {{ menu.remove(); document.removeEventListener('touchstart', closeMenu); }}
    }});
    document.addEventListener('click', function closeMenu2() {{
      const m = document.getElementById('ctx-menu');
      if (m) m.remove();
      document.removeEventListener('click', closeMenu2);
    }});
  }}, 100);
}}

function saveToVocab(word) {{
  const def = document.getElementById('ctx-def').value || '';
  const pos = document.getElementById('ctx-pos').value || '';
  document.getElementById('ctx-saved').style.display = 'block';

  setTimeout(() => {{
    const url = new URL(window.parent.location.href);
    url.searchParams.set('save_word', word);
    url.searchParams.set('save_def', def);
    url.searchParams.set('save_pos', pos);
    window.parent.location.href = url.toString();
  }}, 600);
}}
</script>
"""
                import streamlit.components.v1 as components
                components.html(html_block, height=max(320, len(body) // 2))

                # ── 複製文章按鈕 ──────────────────────────────────
                with st.expander(t("news_copy_exp")):
                    st.code(body, language=None)

                # ── 重點單字
                if vocab:
                    vocab_md = "\n**📖 Key Vocabulary:**\n"
                    for v in vocab:
                        vocab_md += f"- **{v.get('word')}** — {v.get('definition')}\n  > *{v.get('example')}*\n"
                    st.markdown(vocab_md)

                # ── 儲存 & 練習按鈕 ───────────────────────────────
                btn_col1, btn_col2 = st.columns(2)
                with btn_col1:
                    if st.button(t("news_save_btn"), key=f"save_news_{len(st.session_state.news_messages)}", use_container_width=True):
                        import json as _j
                        save_news_article(title, source, date, body, _j.dumps(vocab, ensure_ascii=False))
                        st.toast(t("news_saved_toast"), icon="💾")
                with btn_col2:
                    if st.button(t("news_practice_btn"), key=f"practice_news_{len(st.session_state.news_messages)}", use_container_width=True, type="primary"):
                        st.session_state["practice_news"] = {"title": title, "body": body}
                        st.session_state["page_idx"] = 3  # upload ページへ
                        st.rerun()

                # 存入歷史記錄（純文字版本）
                saved = f"{header_md}\n\n{body}\n\n" + (
                    "**📖 Key Vocabulary:**\n" +
                    "\n".join(f"- **{v.get('word')}** — {v.get('definition')}" for v in vocab)
                    if vocab else ""
                )
                st.session_state.news_messages.append({"role": "assistant", "content": saved})

    # ── 已儲存新聞清單 ─────────────────────────────────────────
    st.markdown("---")
    st.subheader(t("news_h_saved"))
    saved_list = get_saved_news()
    if not saved_list:
        st.info(t("news_no_saved"))
    else:
        for n in saved_list:
            with st.expander(f"📰 {n['title']}  ·  {n.get('date_str','')}"):
                st.caption(f"{t('news_source')}{n.get('source','')}　｜　{t('news_saved_at')}{n.get('saved_at','')[:16]}")
                st.write(n.get("body", ""))
                import json as _j
                vocab_saved = _j.loads(n.get("vocab_json") or "[]")
                if vocab_saved:
                    st.markdown("**📖 Key Vocabulary:**")
                    for v in vocab_saved:
                        st.markdown(f"- **{v.get('word')}** — {v.get('definition')}")
                btn_c1, btn_c2 = st.columns(2)
                with btn_c1:
                    if st.button(t("news_practice2"), key=f"practice_saved_{n['id']}", use_container_width=True, type="primary"):
                        st.session_state["practice_news"] = {"title": n["title"], "body": n.get("body", "")}
                        st.session_state["page_idx"] = 3  # upload ページへ
                        st.rerun()
                with btn_c2:
                    if st.button(t("news_delete"), key=f"del_news_{n['id']}", use_container_width=True):
                        delete_saved_news(n["id"])
                        st.rerun()

# ══════════════════════════════════════════════════════════════
# 頁面三：歷史記錄
# ══════════════════════════════════════════════════════════════
elif page == "history":

    st.header(t("hist_header"))

    sessions = get_all_sessions()

    if not sessions:
        st.info(t("hist_empty"))
    else:
        st.write(f"{t('hist_count1')}**{len(sessions)}**{t('hist_count2')}")

        for s in sessions:
            with st.expander(f"📅 {s['created_at']}　｜　{s['audio_file']}　｜　{t('hist_score')}{s['score']} / 10"):
                st.info(f"💬 {s['summary']}")

                analysis_h = json.loads(s['analysis_json']) if s.get('analysis_json') else {}
                diarized_h = json.loads(s['diarized_json']) if s.get('diarized_json') else None
                label_a_h = diarized_h.get("speaker_a_label", "Speaker A") if diarized_h else "Speaker A"
                label_b_h = diarized_h.get("speaker_b_label", "Speaker B") if diarized_h else "Speaker B"

                tab_t, tab_g, tab_p, tab_v = st.tabs([t("hist_tab_t"), t("hist_tab_g"), t("hist_tab_p"), t("hist_tab_v")])

                with tab_t:
                    if diarized_h and diarized_h.get("segments"):
                        for seg in diarized_h["segments"]:
                            spk = seg.get("speaker", "A")
                            label = label_a_h if spk == "A" else label_b_h
                            color_bg = "#F0F5FA" if spk == "A" else "#F0F7F2"
                            color_bd = "#6B8FC4" if spk == "A" else "#4A7C59"
                            st.markdown(
                                f'<div style="background:{color_bg};border-left:3px solid {color_bd};'
                                f'padding:8px 12px;margin:4px 0;border-radius:2px;">'
                                f'<b style="color:{color_bd};font-size:12px;letter-spacing:.05em">{label}</b><br>'
                                f'<span style="color:#333;font-size:13px">{seg.get("text","")}</span></div>',
                                unsafe_allow_html=True
                            )
                    else:
                        st.text(s['transcript'])

                with tab_g:
                    errors_h = analysis_h.get("grammar_errors", [])
                    if errors_h:
                        for err in errors_h:
                            spk = err.get("speaker", "A")
                            spk_label = label_a_h if spk == "A" else label_b_h
                            color = "#6B8FC4" if spk == "A" else "#4A7C59"
                            st.markdown(
                                f'<div style="border-left:3px solid {color};padding:6px 10px;margin:6px 0;">'
                                f'<span style="color:{color};font-size:12px">[{spk_label}]</span><br>'
                                f'❌ <b>{err.get("original")}</b>　→　✅ <b>{err.get("correction")}</b><br>'
                                f'<span style="color:#888;font-size:13px">{err.get("explanation","")}</span></div>',
                                unsafe_allow_html=True
                            )
                    else:
                        st.success(t("hist_no_grammar"))

                with tab_p:
                    tips_h = analysis_h.get("pronunciation_tips", [])
                    if tips_h:
                        for tip in tips_h:
                            if isinstance(tip, dict):
                                spk = tip.get("speaker", "A")
                                spk_label = label_a_h if spk == "A" else label_b_h
                                color = "#6B8FC4" if spk == "A" else "#4A7C59"
                                st.markdown(
                                    f'<div style="border-left:3px solid {color};padding:6px 10px;margin:6px 0;">'
                                    f'<span style="color:{color};font-size:12px">[{spk_label}]</span>　'
                                    f'<b>{tip.get("example","")}</b><br>'
                                    f'<span style="color:#888;font-size:13px">{tip.get("tip","")}</span></div>',
                                    unsafe_allow_html=True
                                )
                            else:
                                st.write(f"• {tip}")
                    else:
                        st.info(t("hist_no_pron"))

                with tab_v:
                    vocab_h = analysis_h.get("vocabulary_highlights", [])
                    if vocab_h:
                        for v in vocab_h:
                            pos_tag = f"　`{v.get('part_of_speech')}`" if v.get('part_of_speech') else ""
                            st.markdown(
                                f'**{v.get("word","")}**{pos_tag}　{v.get("definition","")}<br>'
                                f'<span style="color:#aaa;font-size:13px">{t("hist_example")}{v.get("example","")}</span>',
                                unsafe_allow_html=True
                            )
                            st.markdown("---")
                    else:
                        st.info(t("hist_no_vocab"))

                col_space, col_btn = st.columns([4, 1])
                with col_btn:
                    if st.button(t("hist_delete"), key=f"delete_{s['id']}",
                                 type="secondary", use_container_width=True):
                        delete_session(s['id'])
                        st.toast(t("hist_del_toast"), icon="🗑️")
                        st.rerun()

# ══════════════════════════════════════════════════════════════
# 頁面三：今日單字（閃卡複習模式）
# ══════════════════════════════════════════════════════════════
elif page == "today":  # noqa: E501
    from srs import update_vocabulary_after_review, QUALITY_MAP
    from database import add_vocabulary_manually

    st.header(t("today_header"))

    # ── 手動新增單字（輸入單字，Gemini 自動補齊）────────────────
    with st.expander(t("today_add_exp")):
        new_word = st.text_input(
            t("today_word_in"),
            key="manual_word",
            placeholder="e.g. resilient"
        )
        if st.button(t("today_add_btn"), key="manual_add_btn", use_container_width=True):
            if new_word.strip():
                from analyze_func import lookup_word
                with st.spinner(f"{t('today_lookup')}「{new_word.strip()}」..."):
                    try:
                        info = lookup_word(new_word.strip())
                        definition = f"{info['definition_zh']} / {info['definition_jp']}"
                        add_vocabulary_manually(
                            new_word.strip(),
                            definition,
                            info.get("example", ""),
                            info.get("part_of_speech", "")
                        )
                        st.success(
                            f"✅ **{new_word.strip()}**"
                            f"  `{info.get('part_of_speech','')}`  "
                            f"{definition}"
                        )
                        st.caption(f"{t('today_ex')}{info.get('example','')}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"{t('today_lookup_fail')}{e}")
            else:
                st.warning(t("today_no_word"))

    st.markdown("---")

    due_words = get_vocabulary_due_today()

    if not due_words:
        st.success(t("today_all_done"))
        st.balloons()
    else:
        if "card_index" not in st.session_state:
            st.session_state.card_index = 0
        if "show_answer" not in st.session_state:
            st.session_state.show_answer = False

        total = len(due_words)
        idx   = st.session_state.card_index

        if idx >= total:
            st.success(f"{t('today_done1')}{total}{t('today_done2')}")
            st.balloons()
            if st.button(t("today_restart")):
                st.session_state.card_index = 0
                st.session_state.show_answer = False
                st.rerun()

        else:
            # ── TODAY / DONE / 残り 三欄メトリクス ──
            m1, m2, m3 = st.columns(3)
            m1.metric(t("today_m_today"), total)
            m2.metric(t("today_m_done"), idx)
            m3.metric(t("today_m_left"), total - idx)

            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            st.progress((idx) / total, text=f"{t('today_progress')}{idx} / {total}")
            st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

            word = due_words[idx]

            source = word.get("source", "vocabulary")
            source_label = {
                "vocabulary":    t("today_src_vocab"),
                "pronunciation": t("today_src_pron"),
                "hesitant":      t("today_src_hesit"),
                "manual":        t("today_src_manual"),
            }.get(source, t("today_src_vocab"))
            pos = word.get("part_of_speech", "")
            pos_badge_html = f'<code style="font-size:14px;background:#F5F5F5;color:#888;padding:2px 8px;margin-left:8px;vertical-align:middle;">{pos}</code>' if pos else ""
            # ── 単語カード（中央寄せ・枠付き）。発音ボタンは下に speak_button で別途描画 ──
            st.markdown(
                f'<div style="background:#FFF;border:1px solid #E8E8E8;border-top:2px solid #4A7C59;'
                f'border-radius:2px 2px 0 0;border-bottom:none;padding:48px 32px 24px;text-align:center;margin:8px 0 0;">'
                f'<div style="font-size:10px;letter-spacing:.3em;color:#CCC;margin-bottom:20px;">'
                f'{source_label}</div>'
                f'<div style="font-size:40px;font-weight:300;letter-spacing:.12em;color:#1A1A1A;">'
                f'{word["word"]}{pos_badge_html}</div>'
                f'<div style="font-size:11px;color:#CCC;letter-spacing:.1em;margin-top:14px;">'
                f'{t("today_review_n")}{word["review_count"]}{t("today_review_unit")}　·　{t("today_ease")}{word["ease_factor"]}</div>'
                f'</div>',
                unsafe_allow_html=True
            )
            # 発音ボタン（実際に音が出る）— カード下端に配置
            bcol = st.columns([1, 1, 1])[1]
            with bcol:
                speak_button(word["word"], label=t("today_listen"), height=46)
            st.markdown(
                '<div style="border:1px solid #E8E8E8;border-top:none;border-radius:0 0 2px 2px;'
                'height:16px;margin:0 0 8px;background:#FFF;"></div>',
                unsafe_allow_html=True
            )

            if not st.session_state.show_answer:
                if st.button(t("today_show"), use_container_width=True, type="primary"):
                    st.session_state.show_answer = True
                    st.rerun()

            else:
                st.info(f"**{t('today_meaning')}** {word['definition']}")
                st.write(f"**{t('today_ex_label')}** *{word['example']}*")

                st.markdown(f"**{t('today_how_much')}**")
                items = list(QUALITY_MAP.items())
                row1_cols = st.columns(2)
                row2_cols = st.columns(2)
                all_cols = row1_cols + row2_cols

                for col, (label, quality) in zip(all_cols, items):
                    with col:
                        if st.button(label, use_container_width=True):
                            update_vocabulary_after_review(word["id"], quality)
                            st.session_state.card_index += 1
                            st.session_state.show_answer = False
                            st.rerun()

    # ── 單字總表 ──────────────────────────────────────────────────
    st.markdown("---")
    st.subheader(t("today_h_list"))

    all_vocab = get_all_vocabulary()
    if not all_vocab:
        st.info(t("today_no_list"))
    else:
        source_labels = {
            "vocabulary":    t("today_lbl_vocab"),
            "pronunciation": t("today_lbl_pron"),
            "hesitant":      t("today_lbl_hesit"),
            "manual":        t("today_lbl_manual"),
        }

        search_q = st.text_input(t("today_search"), placeholder="e.g. resilient", key="vocab_search")

        filtered = [v for v in all_vocab if search_q.lower() in v["word"].lower()] if search_q else all_vocab
        st.caption(f"{t('today_cnt1')}{len(filtered)}{t('today_cnt2')}")

        for v in filtered:
            col_w, col_tts, col_d, col_s, col_del = st.columns([2, 0.8, 3.4, 1.8, 1])
            with col_w:
                pos_html = f' <code style="font-size:0.7em;background:#F5F5F5;color:#888;padding:1px 5px;">{v["part_of_speech"]}</code>' if v.get("part_of_speech") else ""
                st.markdown(
                    f'<div style="padding-top:6px;"><span style="font-weight:500;color:#1A1A1A;">{v["word"]}</span>{pos_html}</div>',
                    unsafe_allow_html=True
                )
            with col_tts:
                speak_button(v["word"], label="🔊", height=40, font_size=14)
            with col_d:
                if v.get("source") == "pronunciation":
                    st.caption(v.get("example", ""))
                else:
                    st.caption(v.get("definition", ""))
            with col_s:
                src = source_labels.get(v.get("source", ""), "📖")
                ref = v.get("reference_title")
                if ref:
                    st.caption(f"{src}\n📰 {ref[:20]}{'…' if len(ref) > 20 else ''}")
                else:
                    st.caption(src)
            with col_del:
                if st.button("🗑️", key=f"del_vocab_{v['id']}", help=t("today_del_help")):
                    delete_vocabulary(v["id"])
                    st.rerun()
