import os
from datetime import datetime
from fpdf import FPDF, XPos, YPos

# ── 色彩常數 ─────────────────────────────────────────────────────
BLUE       = (41, 98, 163)
GREEN      = (30, 140, 80)
DARK       = (30, 30, 30)
GRAY       = (70, 70, 70)
LIGHT_GRAY = (150, 150, 150)
BG_BLUE    = (235, 241, 252)
RED        = (180, 30, 30)
OK_GREEN   = (20, 130, 60)

MC = {"new_x": XPos.LMARGIN, "new_y": YPos.NEXT}


def _find_cjk_font():
    candidates = [
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/noto-cjk/NotoSansCJKtc-Regular.otf",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJKtc-Regular.otf",
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    raise FileNotFoundError("CJK 字型找不到，請確認已安裝 fonts-noto-cjk")


class AnalysisReport(FPDF):
    def header(self):
        self.set_font("CJK", size=9)
        self.set_text_color(*LIGHT_GRAY)
        self.cell(0, 8, "English Conversation Analysis Report / 英文対話分析レポート / 英文對話分析報告",
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
        self.ln(2)

    def footer(self):
        self.set_y(-15)
        self.set_font("CJK", size=8)
        self.set_text_color(*LIGHT_GRAY)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")


def _title(pdf, text):
    pdf.set_fill_color(*BLUE)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("CJK", size=13)
    pdf.cell(0, 9, f"  {text}", fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(*DARK)
    pdf.ln(3)


def _body(pdf, text, size=11, color=None):
    pdf.set_font("CJK", size=size)
    pdf.set_text_color(*(color or DARK))
    pdf.multi_cell(0, 7, text, **MC)
    pdf.ln(1)


def generate_report_pdf(audio_filename, transcript, analysis, diarized=None):
    pdf = AnalysisReport(orientation="P", unit="mm", format="A4")
    pdf.add_font("CJK", "", _find_cjk_font())
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    # 封面標題
    pdf.set_font("CJK", size=20)
    pdf.set_text_color(*BLUE)
    pdf.cell(0, 14, "英文対話分析レポート", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    pdf.set_font("CJK", size=13)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 8, "英文對話分析報告 / English Conversation Analysis Report",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    pdf.ln(5)

    # 基本資訊
    pdf.set_fill_color(*BG_BLUE)
    pdf.set_text_color(*DARK)
    pdf.set_font("CJK", size=11)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    for line in [
        f"音声ファイル / 音檔：{audio_filename}",
        f"分析日時 / 分析時間：{now}",
        f"総合評価 / 整體評分：{analysis.get('overall_score', '-')} / 10",
    ]:
        pdf.cell(0, 8, f"  {line}", fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(6)

    # 總體評語
    _title(pdf, "総合コメント / 總體評語  Overall Summary")
    _body(pdf, analysis.get("summary", ""))

    # 話者分離逐字稿
    _title(pdf, "話者別逐字稿 / 說話者分離逐字稿  Transcript by Speaker")
    if diarized and diarized.get("segments"):
        label_a = diarized.get("speaker_a_label", "Speaker A")
        label_b = diarized.get("speaker_b_label", "Speaker B")
        for seg in diarized["segments"]:
            spk = seg.get("speaker", "A")
            label = label_a if spk == "A" else label_b
            pdf.set_text_color(*BLUE) if spk == "A" else pdf.set_text_color(*GREEN)
            pdf.set_font("CJK", size=10)
            pdf.multi_cell(0, 6, f"[{label}]", **MC)
            pdf.set_text_color(40, 40, 40)
            pdf.multi_cell(0, 6, seg.get("text", ""), **MC)
            pdf.ln(2)
    else:
        _body(pdf, transcript, size=10)

    # 文法建議
    errors = analysis.get("grammar_errors", [])
    _title(pdf, f"文法アドバイス / 文法建議  Grammar  ({len(errors)} items)")
    if not errors:
        _body(pdf, "No grammar errors found. / 文法エラーなし / 沒有文法錯誤")
    else:
        label_a = diarized.get("speaker_a_label", "Speaker A") if diarized else "Speaker A"
        label_b = diarized.get("speaker_b_label", "Speaker B") if diarized else "Speaker B"
        for i, err in enumerate(errors, 1):
            spk = err.get("speaker", "A")
            spk_label = label_a if spk == "A" else label_b
            pdf.set_font("CJK", size=9)
            pdf.set_text_color(*BLUE) if spk == "A" else pdf.set_text_color(*GREEN)
            pdf.multi_cell(0, 5, f"[{spk_label}]", **MC)
            pdf.set_font("CJK", size=11)
            pdf.set_text_color(*RED)
            pdf.multi_cell(0, 7, f"[{i}] NG: {err.get('original', '')}", **MC)
            pdf.set_text_color(*OK_GREEN)
            pdf.multi_cell(0, 7, f"     OK: {err.get('correction', '')}", **MC)
            pdf.set_font("CJK", size=10)
            pdf.set_text_color(*GRAY)
            pdf.multi_cell(0, 6, f"     {err.get('explanation', '')}", **MC)
            pdf.ln(3)

    # 重點單字
    vocab = analysis.get("vocabulary_highlights", [])
    _title(pdf, f"重要単語 / 重點單字  Vocabulary  ({len(vocab)} words)")
    if not vocab:
        _body(pdf, "No vocabulary / 単語なし / 無重點單字")
    else:
        for v in vocab:
            pos = v.get("part_of_speech", "")
            word_line = v.get("word", "") + (f"  [{pos}]" if pos else "")
            pdf.set_font("CJK", size=12)
            pdf.set_text_color(*BLUE)
            pdf.cell(0, 8, word_line, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_font("CJK", size=10)
            pdf.set_text_color(60, 60, 60)
            pdf.multi_cell(0, 6, f"  意味 / 定義：{v.get('definition', '')}", **MC)
            pdf.set_text_color(100, 100, 100)
            pdf.multi_cell(0, 6, f"  例文 / 例句：{v.get('example', '')}", **MC)
            pdf.ln(3)

    # 發音提示
    tips = analysis.get("pronunciation_tips", [])
    if tips:
        _title(pdf, "発音のヒント / 發音提示  Pronunciation Tips")
        label_a = diarized.get("speaker_a_label", "Speaker A") if diarized else "Speaker A"
        label_b = diarized.get("speaker_b_label", "Speaker B") if diarized else "Speaker B"
        for tip in tips:
            if isinstance(tip, dict):
                spk = tip.get("speaker", "A")
                spk_label = label_a if spk == "A" else label_b
                pdf.set_font("CJK", size=9)
                pdf.set_text_color(*BLUE) if spk == "A" else pdf.set_text_color(*GREEN)
                pdf.multi_cell(0, 5, f"[{spk_label}]  {tip.get('example', '')}", **MC)
                pdf.set_font("CJK", size=10)
                pdf.set_text_color(*GRAY)
                pdf.multi_cell(0, 6, f"  {tip.get('tip', '')}", **MC)
                pdf.ln(2)
            else:
                _body(pdf, f"- {tip}", size=10)

    return bytes(pdf.output())
