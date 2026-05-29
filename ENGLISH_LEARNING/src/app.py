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
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(__file__))
from database import (init_database, get_all_sessions, get_vocabulary_due_today,
                       delete_session, get_all_vocabulary, delete_vocabulary,
                       save_news_article, get_saved_news, delete_saved_news)

load_dotenv()
init_database()

# ══════════════════════════════════════════════════════════════
# 頁面基本設定
# ══════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="英文対話分析システム / 英文對話分析系統",
    page_icon="🎙️",
    layout="centered"
)

st.title("🎙️ 英文対話分析・スマート単語帳 / 英文對話分析與智慧單字本")
st.caption("英語会話の録音をアップロードして、AIが文法分析・単語整理します / 上傳英文對話錄音，AI 幫你分析文法、整理單字")

# ── 禅・無印 テーマ + 手機響應式 CSS ────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@300;400;500&display=swap');

/* ── 全体背景・フォント ── */
html, body, [data-testid="stAppViewContainer"] {
    background-color: #FAFAFA !important;
    color: #1A1A1A !important;
}
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

/* ── メトリクス ── */
[data-testid="metric-container"] {
    background: #FFF !important;
    border: 1px solid #E8E8E8 !important;
    border-top: 2px solid #4A7C59 !important;
    border-radius: 2px !important;
    padding: 16px !important;
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
[data-testid="stProgress"] > div > div {
    background: #4A7C59 !important;
    border-radius: 0 !important;
    height: 2px !important;
}
[data-testid="stProgress"] > div {
    background: #E8E8E8 !important;
    border-radius: 0 !important;
    height: 2px !important;
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
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# 側邊欄：導覽選單
# ══════════════════════════════════════════════════════════════
with st.sidebar:
    st.header("📋 メニュー / 功能選單")
    page = st.radio(
        "選擇功能",
        ["📚 履歴 / 歷史記錄",
         "🗓️ 今日の単語 / 今日單字",
         "📰 ニュース検索 / 新聞搜尋",
         "🎙️ アップロード・分析 / 上傳分析"],
        label_visibility="collapsed",
        key="page_radio"
    )

    st.markdown("---")
    st.caption("🌐 外部分享 / Share")
    st.info("直接將此頁面網址分享給朋友即可 / Share this page URL directly with friends")

# ══════════════════════════════════════════════════════════════
# 頁面一：上傳分析
# ══════════════════════════════════════════════════════════════
if page == "🎙️ アップロード・分析 / 上傳分析":

    st.header("音声ファイルをアップロードして分析 / 上傳音檔開始分析")

    # ── 練習文章（從新聞頁帶入 或 手動貼上/上傳）────────────────
    practice_news = st.session_state.get("practice_news")

    with st.expander("📄 連結練習文章（選填）/ 練習記事を設定する（任意）", expanded=bool(practice_news)):
        if practice_news:
            st.success(f"📰 已連結：**{practice_news['title']}**")
            with st.expander("查看文章內容 / 記事を確認する"):
                st.write(practice_news["body"])
            if st.button("✖ 取消連結 / 連結を解除", key="clear_practice"):
                del st.session_state["practice_news"]
                st.rerun()
        else:
            st.caption("貼上外部文章，或上傳 .txt 檔，讓 AI 對照原文分析 / 外部記事を貼り付けるか .txt をアップロード")

            ext_tab1, ext_tab2 = st.tabs(["📋 貼上文字 / テキストを貼り付け", "📁 上傳 .txt / .txt をアップロード"])

            with ext_tab1:
                ext_title = st.text_input("文章標題（選填）/ タイトル（任意）", key="ext_title", placeholder="e.g. BBC News: AI in 2025")
                ext_body  = st.text_area("貼上文章內容 / 記事本文を貼り付け", key="ext_body", height=150, placeholder="Paste article text here...")
                if st.button("✅ 設定為練習文章 / 練習記事に設定", key="set_ext_text"):
                    if ext_body.strip():
                        st.session_state["practice_news"] = {
                            "title": ext_title.strip() or "外部文章",
                            "body":  ext_body.strip()
                        }
                        st.rerun()
                    else:
                        st.warning("請貼上文章內容 / 記事本文を入力してください")

            with ext_tab2:
                txt_file = st.file_uploader("上傳 .txt 檔 / .txt ファイルをアップロード", type=["txt"], key="ext_txt")
                if txt_file:
                    txt_content = txt_file.read().decode("utf-8", errors="ignore")
                    if st.button("✅ 設定為練習文章 / 練習記事に設定", key="set_ext_file"):
                        st.session_state["practice_news"] = {
                            "title": txt_file.name.replace(".txt", ""),
                            "body":  txt_content.strip()
                        }
                        st.rerun()

    uploaded_file = st.file_uploader(
        "音声ファイルを選択（mp3・wav・m4a対応）/ 選擇音檔（支援 mp3、wav、m4a）",
        type=["mp3", "wav", "m4a", "flac"]
    )

    if uploaded_file is not None:
        st.audio(uploaded_file)
        st.success(f"✅ アップロード完了 / 已上傳：{uploaded_file.name}")

        if st.button("🚀 分析開始 / 開始分析", type="primary", use_container_width=True):

            suffix = os.path.splitext(uploaded_file.name)[1]
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(uploaded_file.read())
                tmp_path = tmp.name

            try:
                # ── Step 1+2：AssemblyAI 轉錄 + 說話者分離（一次完成）─
                with st.spinner("⏳ 轉錄＋識別說話者中（約30秒）... / 文字起こし＋話者識別中..."):
                    from diarize_func import diarize, _fallback
                    try:
                        diarized = diarize(tmp_path)
                        transcript = diarized.get("transcript", "")
                        st.info(f"🔍 {diarized.get('speaker_count')} 位說話者，{len(diarized.get('segments', []))} 段")
                    except Exception as diarize_err:
                        st.warning(f"⚠️ 分離錯誤（使用備用模式）:\n\n`{diarize_err}`")
                        from transcribe_func import transcribe
                        whisper_result = transcribe(tmp_path)
                        transcript = whisper_result["text"]
                        diarized = _fallback(transcript)

                # ── 話者分離結果を表示 ─────────────────────────
                label_a = diarized.get("speaker_a_label", "Speaker A")
                label_b = diarized.get("speaker_b_label", "Speaker B")

                with st.expander("💬 話者別逐字稿 / 說話者分離逐字稿", expanded=True):
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
                with st.spinner("⏳ 分析中... / 正在分析..."):
                    from analyze_func import analyze
                    ref = st.session_state.get("practice_news", {}).get("body")
                    analysis = analyze(transcript, diarized=diarized, reference_text=ref)

                from database import save_session
                ref_title = st.session_state.get("practice_news", {}).get("title")
                session_id = save_session(uploaded_file.name, transcript, analysis, diarized=diarized, reference_title=ref_title)

                st.success("🎉 分析完了！/ 分析完成！")

                col1, col2 = st.columns(2)
                with col1:
                    st.metric("総合評価 / 整體評分", f"{analysis.get('overall_score')} / 10")
                with col2:
                    st.metric("新規単語 / 新增單字", f"{len(analysis.get('vocabulary_highlights', []))} 個")

                st.info(f"💬 {analysis.get('summary')}")

                # ── 文法エラー（話者ラベル付き）────────────────
                errors = analysis.get("grammar_errors", [])
                st.subheader("📝 文法アドバイス / 文法建議")
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
                    st.success("文法エラーは見つかりませんでした！/ 沒有發現明顯文法錯誤！")

                vocab = analysis.get("vocabulary_highlights", [])
                st.subheader("📚 学んだ単語 / 學到的單字")
                if vocab:
                    for v in vocab:
                        pos_tag = f" `{v.get('part_of_speech')}`" if v.get('part_of_speech') else ""
                        with st.expander(f"**{v.get('word')}**{pos_tag}　{v.get('definition')}"):
                            st.write(f"例文 / 例句：*{v.get('example')}*")

                tips = analysis.get("pronunciation_tips", [])
                if tips:
                    st.subheader("🗣️ 発音のヒント / 發音提示")
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
                    label="📄 レポートをPDFでダウンロード / 下載 PDF 分析報告",
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
elif page == "📰 ニュース検索 / 新聞搜尋":
    from news_search import fetch_news_with_gemini, TOEIC_LEVELS
    from database import add_vocabulary_manually

    # ── 處理從新聞頁面右鍵加入的單字 ─────────────────────────
    if st.query_params.get("save_word"):
        _w  = st.query_params.get("save_word", "")
        _d  = st.query_params.get("save_def", "")
        _pos = st.query_params.get("save_pos", "")
        if _w:
            add_vocabulary_manually(_w, _d, "", _pos)
            st.toast(f"📚 「{_w}」を単語本に追加 / 已加入單字本", icon="✅")
        st.query_params.clear()

    st.header("📰 英語ニュース検索 / 英文新聞搜尋")

    # 程度選擇放在最上方
    level_key = st.selectbox(
        "📊 英語レベル / 英文程度",
        list(TOEIC_LEVELS.keys())
    )
    st.caption("💡 任何語言輸入主題，Gemini 會幫你找真實新聞 / 何の言語でもOK、Geminiがリアルなニュースを検索します")

    # 初始化聊天記錄
    if "news_messages" not in st.session_state:
        st.session_state.news_messages = []

    # 顯示歷史聊天記錄
    for msg in st.session_state.news_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"], unsafe_allow_html=True)

    # 聊天輸入框（任何語言皆可）
    if prompt := st.chat_input("ニュースのテーマを入力 / 輸入你想看的新聞主題... (e.g. AI, climate, economy)"):

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
                    st.error(f"搜尋失敗 / 検索失敗：{e}")
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
<p class="tip">🔊 點擊單字可聽發音 / Tap a word to hear it &nbsp;｜&nbsp; 長按可加入單字本 / Long-press to save</p>
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
                with st.expander("📋 複製文章給朋友 / 記事をコピーする"):
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
                    if st.button("💾 儲存此新聞 / この記事を保存", key=f"save_news_{len(st.session_state.news_messages)}", use_container_width=True):
                        import json as _j
                        save_news_article(title, source, date, body, _j.dumps(vocab, ensure_ascii=False))
                        st.toast("✅ 新聞已儲存 / 記事を保存しました", icon="💾")
                with btn_col2:
                    if st.button("🎙️ 用這篇練習 / この記事で練習", key=f"practice_news_{len(st.session_state.news_messages)}", use_container_width=True, type="primary"):
                        st.session_state["practice_news"] = {"title": title, "body": body}
                        st.session_state["page_radio"] = "🎙️ アップロード・分析 / 上傳分析"
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
    st.subheader("💾 保存した記事 / 已儲存新聞")
    saved_list = get_saved_news()
    if not saved_list:
        st.info("まだ保存した記事はありません / 還沒有儲存的新聞")
    else:
        for n in saved_list:
            with st.expander(f"📰 {n['title']}  ·  {n.get('date_str','')}"):
                st.caption(f"來源 / ソース：{n.get('source','')}　｜　儲存於 {n.get('saved_at','')[:16]}")
                st.write(n.get("body", ""))
                import json as _j
                vocab_saved = _j.loads(n.get("vocab_json") or "[]")
                if vocab_saved:
                    st.markdown("**📖 Key Vocabulary:**")
                    for v in vocab_saved:
                        st.markdown(f"- **{v.get('word')}** — {v.get('definition')}")
                btn_c1, btn_c2 = st.columns(2)
                with btn_c1:
                    if st.button("🎙️ 用這篇練習 / 練習する", key=f"practice_saved_{n['id']}", use_container_width=True, type="primary"):
                        st.session_state["practice_news"] = {"title": n["title"], "body": n.get("body", "")}
                        st.session_state["page_radio"] = "🎙️ アップロード・分析 / 上傳分析"
                        st.rerun()
                with btn_c2:
                    if st.button("🗑️ 刪除 / 削除", key=f"del_news_{n['id']}", use_container_width=True):
                        delete_saved_news(n["id"])
                        st.rerun()

# ══════════════════════════════════════════════════════════════
# 頁面三：歷史記錄
# ══════════════════════════════════════════════════════════════
elif page == "📚 履歴 / 歷史記錄":

    st.header("分析履歴 / 歷史分析記錄")

    sessions = get_all_sessions()

    if not sessions:
        st.info("まだ記録がありません。音声ファイルをアップロードしてください！/ 還沒有任何記錄，請先上傳音檔分析！")
    else:
        st.write(f"合計 **{len(sessions)}** 件 / 共 **{len(sessions)}** 筆記錄")

        for s in sessions:
            with st.expander(f"📅 {s['created_at']}　｜　{s['audio_file']}　｜　評価 / 評分：{s['score']} / 10"):
                st.info(f"💬 {s['summary']}")

                analysis_h = json.loads(s['analysis_json']) if s.get('analysis_json') else {}
                diarized_h = json.loads(s['diarized_json']) if s.get('diarized_json') else None
                label_a_h = diarized_h.get("speaker_a_label", "Speaker A") if diarized_h else "Speaker A"
                label_b_h = diarized_h.get("speaker_b_label", "Speaker B") if diarized_h else "Speaker B"

                tab_t, tab_g, tab_p, tab_v = st.tabs(["💬 逐字稿 / 逐字起こし", "📝 文法 / 文法", "🗣️ 發音 / 発音", "📚 單字 / 単語"])

                with tab_t:
                    if diarized_h and diarized_h.get("segments"):
                        for seg in diarized_h["segments"]:
                            spk = seg.get("speaker", "A")
                            label = label_a_h if spk == "A" else label_b_h
                            color_bg = "#1a3a5c" if spk == "A" else "#1a3d2b"
                            color_bd = "#4a9eff" if spk == "A" else "#4caf82"
                            st.markdown(
                                f'<div style="background:{color_bg};border-left:4px solid {color_bd};'
                                f'padding:6px 10px;margin:3px 0;border-radius:4px;">'
                                f'<b style="color:{color_bd}">{label}</b><br>'
                                f'<span style="color:#e8e8e8;font-size:13px">{seg.get("text","")}</span></div>',
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
                            color = "#4a9eff" if spk == "A" else "#4caf82"
                            st.markdown(
                                f'<div style="border-left:3px solid {color};padding:6px 10px;margin:6px 0;">'
                                f'<span style="color:{color};font-size:12px">[{spk_label}]</span><br>'
                                f'❌ <b>{err.get("original")}</b>　→　✅ <b>{err.get("correction")}</b><br>'
                                f'<span style="color:#aaa;font-size:13px">{err.get("explanation","")}</span></div>',
                                unsafe_allow_html=True
                            )
                    else:
                        st.success("文法錯誤なし / 沒有文法錯誤")

                with tab_p:
                    tips_h = analysis_h.get("pronunciation_tips", [])
                    if tips_h:
                        for tip in tips_h:
                            if isinstance(tip, dict):
                                spk = tip.get("speaker", "A")
                                spk_label = label_a_h if spk == "A" else label_b_h
                                color = "#4a9eff" if spk == "A" else "#4caf82"
                                st.markdown(
                                    f'<div style="border-left:3px solid {color};padding:6px 10px;margin:6px 0;">'
                                    f'<span style="color:{color};font-size:12px">[{spk_label}]</span>　'
                                    f'<b>{tip.get("example","")}</b><br>'
                                    f'<span style="color:#aaa;font-size:13px">{tip.get("tip","")}</span></div>',
                                    unsafe_allow_html=True
                                )
                            else:
                                st.write(f"• {tip}")
                    else:
                        st.info("發音提示なし / 無發音提示")

                with tab_v:
                    vocab_h = analysis_h.get("vocabulary_highlights", [])
                    if vocab_h:
                        for v in vocab_h:
                            pos_tag = f"　`{v.get('part_of_speech')}`" if v.get('part_of_speech') else ""
                            st.markdown(
                                f'**{v.get("word","")}**{pos_tag}　{v.get("definition","")}<br>'
                                f'<span style="color:#aaa;font-size:13px">例句：{v.get("example","")}</span>',
                                unsafe_allow_html=True
                            )
                            st.markdown("---")
                    else:
                        st.info("単語なし / 無單字")

                col_space, col_btn = st.columns([4, 1])
                with col_btn:
                    if st.button("🗑️ 削除 / 刪除", key=f"delete_{s['id']}",
                                 type="secondary", use_container_width=True):
                        delete_session(s['id'])
                        st.toast("削除しました / 已刪除", icon="🗑️")
                        st.rerun()

# ══════════════════════════════════════════════════════════════
# 頁面三：今日單字（閃卡複習模式）
# ══════════════════════════════════════════════════════════════
elif page == "🗓️ 今日の単語 / 今日單字":  # noqa: E501
    from srs import update_vocabulary_after_review, QUALITY_MAP
    from database import add_vocabulary_manually

    st.header("今日の単語復習 / 今日單字複習")

    # ── 手動新增單字（輸入單字，Gemini 自動補齊）────────────────
    with st.expander("➕ 単語を手動追加 / 手動新增單字"):
        new_word = st.text_input(
            "英文單字 / English word",
            key="manual_word",
            placeholder="e.g. resilient"
        )
        if st.button("🔍 自動查詢並加入單字本 / Auto-lookup & Add", key="manual_add_btn", use_container_width=True):
            if new_word.strip():
                from analyze_func import lookup_word
                with st.spinner(f"Gemini 查詢「{new_word.strip()}」中..."):
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
                        st.caption(f"例句：{info.get('example','')}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"查詢失敗：{e}")
            else:
                st.warning("請輸入單字 / 単語を入力してください")

    st.markdown("---")

    due_words = get_vocabulary_due_today()

    if not due_words:
        st.success("🎉 今日復習する単語はありません。よくできました！/ 今天沒有需要複習的單字，很棒！")
        st.balloons()
    else:
        if "card_index" not in st.session_state:
            st.session_state.card_index = 0
        if "show_answer" not in st.session_state:
            st.session_state.show_answer = False

        total = len(due_words)
        idx   = st.session_state.card_index

        if idx >= total:
            st.success(f"🎉 今日の {total} 単語をすべて完了！/ 今天的 {total} 個單字全部複習完畢！")
            st.balloons()
            if st.button("最初から / 重新開始"):
                st.session_state.card_index = 0
                st.session_state.show_answer = False
                st.rerun()

        else:
            st.progress((idx) / total, text=f"進捗 / 進度：{idx} / {total}")

            word = due_words[idx]

            st.markdown("---")
            source = word.get("source", "vocabulary")
            source_label = {
                "vocabulary":    "📖 重點單字",
                "pronunciation": "🗣️ 發音錯誤",
                "hesitant":      "💭 猶豫單字",
                "manual":        "✏️ 手動新增",
            }.get(source, "📖 重點單字")
            st.caption(source_label)
            pos = word.get("part_of_speech", "")
            pos_badge_html = f' <code style="font-size:0.65em;background:#F5F5F5;color:#888;padding:1px 6px;">{pos}</code>' if pos else ""
            card_word_js = word['word'].replace("'", "\\'").replace('"', '\\"')
            card_tts = (
                f"var _s=window.speechSynthesis;if(_s){{var _u=new SpeechSynthesisUtterance('{card_word_js}');"
                f"_u.lang='en-US';_u.rate=0.85;_u.volume=1;"
                f"if(_s.speaking||_s.pending){{_s.cancel();setTimeout(function(){{_s.speak(_u);}},80);}}else{{_s.speak(_u);}}}}"
            )
            st.markdown(
                f'<h2 style="margin-bottom:0;font-weight:400;letter-spacing:.04em;">'
                f'{word["word"]}{pos_badge_html}&nbsp;'
                f'<span onclick="{card_tts}" '
                f'style="cursor:pointer;font-size:0.65em;padding:4px 10px;border-radius:2px;'
                f'background:#F5F5F5;border:1px solid #E0E0E0;color:#555;vertical-align:middle;'
                f'font-weight:300;letter-spacing:.1em;-webkit-tap-highlight-color:transparent;" '
                f'title="發音">🔊 發音</span></h2>',
                unsafe_allow_html=True
            )
            st.caption(f"復習回数 / 已複習 {word['review_count']} 回　｜　難易度 / 難易係數：{word['ease_factor']}")

            if not st.session_state.show_answer:
                if st.button("👁️ 答えを見る / 顯示答案", use_container_width=True):
                    st.session_state.show_answer = True
                    st.rerun()

            else:
                st.info(f"**意味 / 中文：** {word['definition']}")
                st.write(f"**例文 / 例句：** *{word['example']}*")

                st.markdown("**どれだけ覚えていますか？/ 你記得多少？**")
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
    st.subheader("📋 単語総リスト / 單字總表")

    all_vocab = get_all_vocabulary()
    if not all_vocab:
        st.info("還沒有單字記錄 / 単語がありません")
    else:
        source_labels = {
            "vocabulary":    "📖 重點",
            "pronunciation": "🗣️ 發音",
            "hesitant":      "💭 猶豫",
            "manual":        "✏️ 手動",
        }

        search_q = st.text_input("🔍 搜尋單字 / 単語を検索", placeholder="e.g. resilient", key="vocab_search")

        filtered = [v for v in all_vocab if search_q.lower() in v["word"].lower()] if search_q else all_vocab
        st.caption(f"共 {len(filtered)} 個單字 / 合計 {len(filtered)} 単語")

        for v in filtered:
            col_w, col_d, col_s, col_del = st.columns([2, 4, 2, 1])
            with col_w:
                pos_html = f' <code style="font-size:0.7em;background:#F5F5F5;color:#888;padding:1px 5px;">{v["part_of_speech"]}</code>' if v.get("part_of_speech") else ""
                word_js = v['word'].replace("'", "\\'").replace('"', '\\"')
                word_tts = (
                    f"var _s=window.speechSynthesis;if(_s){{var _u=new SpeechSynthesisUtterance('{word_js}');"
                    f"_u.lang='en-US';_u.rate=0.85;_u.volume=1;"
                    f"if(_s.speaking||_s.pending){{_s.cancel();setTimeout(function(){{_s.speak(_u);}},80);}}else{{_s.speak(_u);}}}}"
                )
                st.markdown(
                    f'<span style="font-weight:500;color:#1A1A1A;">{v["word"]}</span>{pos_html}&nbsp;'
                    f'<span onclick="{word_tts}" '
                    f'style="cursor:pointer;font-size:0.9em;padding:2px 6px;border-radius:2px;'
                    f'background:#F5F5F5;border:1px solid #E8E8E8;color:#888;'
                    f'-webkit-tap-highlight-color:transparent;" '
                    f'title="發音">🔊</span>',
                    unsafe_allow_html=True
                )
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
                if st.button("🗑️", key=f"del_vocab_{v['id']}", help="刪除此單字"):
                    delete_vocabulary(v["id"])
                    st.rerun()
