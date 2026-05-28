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
    layout="wide"
)

st.title("🎙️ 英文対話分析・スマート単語帳 / 英文對話分析與智慧單字本")
st.caption("英語会話の録音をアップロードして、AIが文法分析・単語整理します / 上傳英文對話錄音，AI 幫你分析文法、整理單字")

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
        label_visibility="collapsed"
    )

    st.markdown("---")
    st.caption("🌐 外部分享 / Share")
    st.info("直接將此頁面網址分享給朋友即可 / Share this page URL directly with friends")

# ══════════════════════════════════════════════════════════════
# 頁面一：上傳分析
# ══════════════════════════════════════════════════════════════
if page == "🎙️ アップロード・分析 / 上傳分析":

    st.header("音声ファイルをアップロードして分析 / 上傳音檔開始分析")

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
                    analysis = analyze(transcript, diarized=diarized)

                from database import save_session
                session_id = save_session(uploaded_file.name, transcript, analysis, diarized=diarized)

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
  body {{ margin: 0; padding: 0; background: transparent; }}
  .news-body {{
    font-size: 16px;
    line-height: 2.0;
    color: #e8e8e8;
    font-family: Georgia, serif;
  }}
  .w {{
    cursor: pointer;
    border-radius: 3px;
    padding: 1px 3px;
    transition: background 0.15s;
    position: relative;
  }}
  .w:hover {{ background: #2a5ea8; color: #fff; }}
  #tooltip {{
    position: fixed;
    background: #1e2a3a;
    color: #f0f0f0;
    border: 1px solid #3a6ea8;
    border-radius: 8px;
    padding: 7px 12px;
    font-size: 14px;
    line-height: 1.6;
    pointer-events: none;
    display: none;
    z-index: 9999;
    max-width: 220px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.5);
  }}
  #tooltip .en {{ font-weight: bold; color: #7eb8f7; font-size: 15px; }}
  #tooltip .jp {{ color: #f9ca74; }}
  #tooltip .zh {{ color: #a8e6a3; }}
  .tip {{ font-size: 12px; color: #888; margin-bottom: 6px; }}
  #ctx-menu {{
    position: fixed;
    background: #1e2a3a;
    border: 1px solid #3a6ea8;
    border-radius: 10px;
    padding: 12px;
    z-index: 99999;
    min-width: 220px;
    box-shadow: 0 6px 20px rgba(0,0,0,0.6);
  }}
  #ctx-menu .ctx-word {{ color:#7eb8f7; font-weight:bold; font-size:16px; margin-bottom:8px; }}
  #ctx-menu select, #ctx-menu input {{
    width: 100%; background: #0e1621; color: #fff;
    border: 1px solid #3a6ea8; border-radius: 4px;
    padding: 5px 7px; font-size: 13px;
    box-sizing: border-box; margin-bottom: 6px;
  }}
  #ctx-menu button {{
    width: 100%; background: #29629e; color: #fff;
    border: none; border-radius: 5px;
    padding: 7px; cursor: pointer; font-size: 14px;
  }}
  #ctx-menu button:hover {{ background: #3a7abf; }}
  #ctx-saved {{
    color: #4caf82; font-size: 13px; text-align: center;
    margin-top: 6px; display: none;
  }}
</style>

<div id="tooltip"></div>
<p class="tip">🔊 Hover over any word — hear pronunciation + see Japanese / Chinese translation</p>
<div class="news-body">{words_html}</div>

<script>
const GLOSSARY = {glossary_js};

function onHover(el) {{
  const word = el.dataset.word;

  // 發音
  const utt = new SpeechSynthesisUtterance(word);
  utt.lang = 'en-US';
  utt.rate = 0.85;
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(utt);

  // tooltip
  const entry = GLOSSARY[word];
  const tip = document.getElementById('tooltip');
  if (entry) {{
    tip.innerHTML =
      '<span class="en">' + el.innerText + '</span><br>' +
      '<span class="jp">🇯🇵 ' + entry.jp + '</span><br>' +
      '<span class="zh">🇹🇼 ' + entry.zh + '</span>';
    tip.style.display = 'block';
  }} else {{
    tip.innerHTML = '<span class="en">' + el.innerText + '</span>';
    tip.style.display = 'block';
  }}
}}

document.addEventListener('mousemove', function(e) {{
  const tip = document.getElementById('tooltip');
  if (tip.style.display === 'block') {{
    tip.style.left = (e.clientX + 14) + 'px';
    tip.style.top  = (e.clientY - 10) + 'px';
  }}
}});

document.addEventListener('mouseout', function(e) {{
  if (!e.target.classList.contains('w')) {{
    document.getElementById('tooltip').style.display = 'none';
  }}
}});

// ── 右鍵選單 ───────────────────────────────────────────
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

  // 防止跑出畫面
  const x = Math.min(e.clientX, window.innerWidth - 240);
  const y = Math.min(e.clientY, window.innerHeight - 180);
  menu.style.left = x + 'px';
  menu.style.top  = y + 'px';
  document.body.appendChild(menu);

  // 點其他地方關閉
  setTimeout(() => {{
    document.addEventListener('click', () => {{
      const m = document.getElementById('ctx-menu');
      if (m) m.remove();
    }}, {{once: true}});
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

                # ── 重點單字
                if vocab:
                    vocab_md = "\n**📖 Key Vocabulary:**\n"
                    for v in vocab:
                        vocab_md += f"- **{v.get('word')}** — {v.get('definition')}\n  > *{v.get('example')}*\n"
                    st.markdown(vocab_md)

                # ── 儲存按鈕 ──────────────────────────────────────
                if st.button("💾 儲存此新聞 / この記事を保存", key=f"save_news_{len(st.session_state.news_messages)}"):
                    import json as _j
                    save_news_article(title, source, date, body, _j.dumps(vocab, ensure_ascii=False))
                    st.toast("✅ 新聞已儲存 / 記事を保存しました", icon="💾")

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
                if st.button("🗑️ 刪除 / 削除", key=f"del_news_{n['id']}"):
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
            pos_badge = f" `{pos}`" if pos else ""
            st.markdown(f"## {word['word']}{pos_badge}")
            st.caption(f"復習回数 / 已複習 {word['review_count']} 回　｜　難易度 / 難易係數：{word['ease_factor']}")

            if not st.session_state.show_answer:
                if st.button("👁️ 答えを見る / 顯示答案", use_container_width=True):
                    st.session_state.show_answer = True
                    st.rerun()

            else:
                st.info(f"**意味 / 中文：** {word['definition']}")
                st.write(f"**例文 / 例句：** *{word['example']}*")

                st.markdown("**どれだけ覚えていますか？/ 你記得多少？**")
                col1, col2, col3, col4 = st.columns(4)

                for col, (label, quality) in zip(
                    [col1, col2, col3, col4], QUALITY_MAP.items()
                ):
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
            col_w, col_d, col_s, col_del = st.columns([2, 5, 1.5, 1])
            with col_w:
                pos = f" `{v['part_of_speech']}`" if v.get("part_of_speech") else ""
                st.markdown(f"**{v['word']}**{pos}")
            with col_d:
                if v.get("source") == "pronunciation":
                    st.caption(v.get("example", ""))
                else:
                    st.caption(v.get("definition", ""))
            with col_s:
                st.caption(source_labels.get(v.get("source", ""), "📖"))
            with col_del:
                if st.button("🗑️", key=f"del_vocab_{v['id']}", help="刪除此單字"):
                    delete_vocabulary(v["id"])
                    st.rerun()
