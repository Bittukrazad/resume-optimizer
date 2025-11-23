# report_generator.py
from fpdf import FPDF
import re
import os

def clean_text_for_pdf(text):
    """Remove emojis and ALL unsupported Unicode for PDF compatibility"""
    if not isinstance(text, str):
        text = str(text)
    
    # AGGRESSIVE: First convert to ASCII-compatible encoding
    try:
        text = text.encode('ascii', 'ignore').decode('ascii')
    except:
        pass
    
    # Basic emoji replacements
    emoji_map = {
        "🎯": "[TARGET]", "✅": "[OK]", "❌": "[X]", "🔍": "[SEARCH]",
        "✨": "[STAR]", "📥": "[DOWNLOAD]", "📄": "[DOC]", "📊": "[CHART]",
        "💡": "[TIP]", "🛠️": "[TOOL]", "🛠": "[TOOL]", "📝": "[NOTE]",
        "🔒": "[LOCK]", "⚠️": "[WARNING]", "⚠": "[WARNING]",
    }
    
    for emoji, replacement in emoji_map.items():
        text = text.replace(emoji, replacement)
    
    # Basic Unicode cleanup
    text = text.replace('—', '-').replace('–', '-').replace(''', "'").replace(''', "'")
    text = text.replace('"', '"').replace('"', '"').replace('…', '...')
    
    # Remove any remaining non-ASCII
    text = ''.join(char if ord(char) < 128 else '' for char in text)
    
    # Remove extra whitespace
    text = ' '.join(text.split())
    
    return text

def safe_add_text(pdf, text, max_width=180):
    """Safely add text with automatic wrapping"""
    text = clean_text_for_pdf(str(text))
    
    # Split into chunks if too long
    chunk_size = 80
    if len(text) > chunk_size:
        words = text.split()
        current_line = []
        
        for word in words:
            current_line.append(word)
            line_text = ' '.join(current_line)
            if len(line_text) > chunk_size:
                if len(current_line) > 1:
                    current_line.pop()
                    pdf.cell(0, 6, ' '.join(current_line), ln=True)
                    current_line = [word]
                else:
                    # Single word too long, just print it
                    pdf.cell(0, 6, word[:chunk_size], ln=True)
                    current_line = []
        
        if current_line:
            pdf.cell(0, 6, ' '.join(current_line), ln=True)
    else:
        pdf.cell(0, 6, text, ln=True)

def generate_pdf_report(result, resume_filename="student"):
    try:
        # Initialize PDF with proper margins
        pdf = FPDF(orientation='P', unit='mm', format='A4')
        pdf.set_margins(left=15, top=15, right=15)
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)
        
        # =============== HEADER ===============
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 10, "ResumeBoost AI Report", ln=True, align="C")
        pdf.ln(5)
        
        # =============== ATS SCORE ===============
        pdf.set_font("Arial", "B", 14)
        score = result.get('ats_score', 0)
        color = (0, 100, 0) if score >= 70 else (180, 0, 0)
        pdf.set_text_color(*color)
        pdf.cell(0, 10, f"ATS Score: {score}/100", ln=True, align="C")
        pdf.set_text_color(0, 0, 0)
        pdf.ln(5)
        
        # =============== ROLE ===============
        pdf.set_font("Arial", "", 12)
        role = clean_text_for_pdf(str(result.get('detected_role', 'General')))
        pdf.cell(0, 8, f"Target Role: {role}", ln=True, align="C")
        pdf.ln(8)
        
        # =============== KEYWORD GAPS ===============
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 8, "Missing Keywords", ln=True)
        pdf.set_font("Arial", "", 10)
        
        missing = result.get('missing_keywords', [])
        if missing:
            for kw in missing[:8]:
                clean_kw = clean_text_for_pdf(str(kw))[:50]  # Limit length
                pdf.cell(0, 6, f"* {clean_kw}", ln=True)
        else:
            pdf.cell(0, 6, "[OK] None detected", ln=True)
        pdf.ln(5)
        
        # =============== SECTION SCORES ===============
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 8, "Section Scores", ln=True)
        pdf.set_font("Arial", "", 10)
        
        sections = result.get('section_scores', {})
        if sections:
            for sec, score_val in sections.items():
                status = "Good" if score_val >= 70 else "Needs Work"
                sec_clean = clean_text_for_pdf(str(sec))[:30]
                pdf.cell(0, 6, f"- {sec_clean}: {score_val}/100 ({status})", ln=True)
        else:
            pdf.cell(0, 6, "[INFO] No data", ln=True)
        pdf.ln(5)
        
        # =============== REWRITE SUGGESTION ===============
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 8, "Sample Rewrite", ln=True)
        pdf.set_font("Arial", "", 9)
        
        before_raw = result.get("weak_bullet", "Built a project")
        after_raw = result.get("rewrite_suggestion", "Improved project")
        
        before_clean = clean_text_for_pdf(str(before_raw))[:100]
        after_clean = clean_text_for_pdf(str(after_raw))[:100]
        
        pdf.cell(0, 6, "Before:", ln=True)
        safe_add_text(pdf, before_clean)
        pdf.ln(2)
        
        pdf.set_text_color(0, 100, 0)
        pdf.cell(0, 6, "After:", ln=True)
        safe_add_text(pdf, after_clean)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(5)
        
        # =============== SUGGESTIONS ===============
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 8, "Tips", ln=True)
        pdf.set_font("Arial", "", 9)
        
        suggestions = result.get('suggestions', [
            "Add metrics",
            "Use standard headers",
            "Expand descriptions"
        ])
        
        for i, sug in enumerate(suggestions[:5], 1):
            cleaned_sug = clean_text_for_pdf(str(sug))[:80]
            pdf.cell(0, 6, f"{i}. {cleaned_sug}", ln=True)
        
        # =============== FOOTER ===============
        pdf.ln(10)
        pdf.set_font("Arial", "I", 8)
        pdf.cell(0, 5, "Generated by ResumeBoost AI", ln=True, align="C")
        pdf.cell(0, 5, "Contact: bittukrazad652@gmail.com", ln=True, align="C")
        
        # =============== SAVE ===============
        filename = f"report_{score}.pdf"
        pdf.output(filename)
        return filename
        
    except Exception as e:
        # Absolute minimal fallback
        try:
            pdf = FPDF()
            pdf.set_margins(20, 20, 20)
            pdf.add_page()
            pdf.set_font("Arial", "B", 14)
            pdf.cell(0, 10, "ResumeBoost Report", ln=True)
            pdf.ln(5)
            
            pdf.set_font("Arial", "", 12)
            score = result.get('ats_score', 0)
            pdf.cell(0, 10, f"Score: {score}/100", ln=True)
            pdf.ln(5)
            
            pdf.set_font("Arial", "", 10)
            pdf.cell(0, 8, "Contact Support:", ln=True)
            pdf.cell(0, 8, "bittukrazad652@gmail.com", ln=True)
            
            filename = f"report_{score}.pdf"
            pdf.output(filename)
            return filename
            
        except:
            # Last resort
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            pdf.cell(0, 10, "Report Generated", ln=True)
            pdf.cell(0, 10, "Contact Support", ln=True)
            filename = "report.pdf"
            pdf.output(filename)
            return filename
        
