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
        # Try to encode as ASCII, replacing errors
        text = text.encode('ascii', 'ignore').decode('ascii')
    except:
        pass
    
    # Emoji replacements → plain text
    emoji_map = {
        "🎯": "[TARGET]", "✅": "[OK]", "❌": "[X]", "🔍": "[SEARCH]",
        "✨": "[STAR]", "📥": "[DOWNLOAD]", "📄": "[DOC]", "📊": "[CHART]",
        "💡": "[TIP]", "🛠️": "[TOOL]", "🛠": "[TOOL]", "📝": "[NOTE]",
        "🔒": "[LOCK]", "⚠️": "[WARNING]", "⚠": "[WARNING]", "🚀": "[ROCKET]",
        "💰": "[MONEY]", "💳": "[CARD]", "📞": "[PHONE]", "📧": "[EMAIL]",
        "📍": "[LOCATION]", "🎓": "[GRADUATE]", "🏆": "[TROPHY]", "⭐": "[STAR]",
        "➡️": "->", "➡": "->", "✔️": "[OK]", "✔": "[OK]",
    }
    
    # Replace emojis first
    for emoji, replacement in emoji_map.items():
        text = text.replace(emoji, replacement)
    
    # Comprehensive Unicode cleanup
    replacements = {
        '\u2013': '-', '\u2014': '-', '\u2015': '-', '\u2212': '-',
        '\u2018': "'", '\u2019': "'", '\u201A': "'", '\u201B': "'",
        '\u201C': '"', '\u201D': '"', '\u201E': '"', '\u201F': '"',
        '\u2039': '<', '\u203A': '>', '\u00AB': '<<', '\u00BB': '>>',
        '\u2026': '...', '\u00A0': ' ', '\u2000': ' ', '\u2001': ' ',
        '\u2002': ' ', '\u2003': ' ', '\u2009': ' ', '\u200A': ' ',
        '\u200B': '', '\u200C': '', '\u200D': '', '\uFEFF': '',
        '\u2022': '*', '\u2023': '>', '\u2043': '-', '\u25E6': 'o',
        '\u2219': '*', '\u00D7': 'x', '\u00F7': '/', '\u00B1': '+/-',
        '\u2260': '!=', '\u2264': '<=', '\u2265': '>=',
        '\u2192': '->', '\u2190': '<-',
    }
    
    # Apply all replacements
    for unicode_char, ascii_char in replacements.items():
        text = text.replace(unicode_char, ascii_char)
    
    # Remove any remaining non-Latin-1 characters
    text = ''.join(char if ord(char) < 256 else '?' for char in text)
    
    # Limit length to prevent overflow (optional safety)
    if len(text) > 1000:
        text = text[:997] + "..."
    
    return text

def generate_pdf_report(result, resume_filename="student"):
    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)
        
        # =============== HEADER ===============
        pdf.set_font("Arial", "B", 16)
        header_text = "ResumeBoost AI - Full Report"
        header_text = header_text.replace("—", "-").replace("–", "-")
        pdf.cell(0, 10, clean_text_for_pdf(header_text), ln=True, align="C")
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
        pdf.cell(0, 10, f"Target Role: {role}", ln=True, align="C")
        pdf.ln(10)
        
        # =============== KEYWORD GAPS ===============
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "Missing Keywords", ln=True)
        pdf.set_font("Arial", "", 10)
        
        missing = result.get('missing_keywords', [])
        if missing:
            for kw in missing[:8]:
                clean_kw = clean_text_for_pdf(str(kw))
                # Use multi_cell for safety
                pdf.multi_cell(0, 6, f"* {clean_kw}")
        else:
            pdf.multi_cell(0, 6, "[OK] None detected - great job!")
        pdf.ln(3)
        
        # =============== SECTION SCORES ===============
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "Section-wise Feedback", ln=True)
        pdf.set_font("Arial", "", 10)
        
        sections = result.get('section_scores', {})
        if sections:
            for sec, score_val in sections.items():
                status = "[OK] Good" if score_val >= 70 else "[X] Needs Work"
                sec_clean = clean_text_for_pdf(str(sec))
                line = f"- {sec_clean.title()}: {score_val}/100 ({status})"
                # Use multi_cell instead of cell
                pdf.multi_cell(0, 6, line)
        else:
            pdf.multi_cell(0, 6, "[INFO] Section analysis unavailable")
        pdf.ln(5)
        
        # =============== REWRITE SUGGESTION ===============
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "Personalized Rewrite", ln=True)
        pdf.set_font("Arial", "", 10)
        
        # Get and clean rewrite data
        before_raw = result.get("weak_bullet", "Built a project.")
        after_raw = result.get("rewrite_suggestion", 
                         f"Developed a {role} solution with results.")
        
        before_clean = clean_text_for_pdf(str(before_raw))
        after_clean = clean_text_for_pdf(str(after_raw))
        
        # Truncate if too long
        if len(before_clean) > 200:
            before_clean = before_clean[:197] + "..."
        if len(after_clean) > 200:
            after_clean = after_clean[:197] + "..."
        
        pdf.multi_cell(0, 6, f"Before: {before_clean}")
        pdf.ln(2)
        pdf.set_font("Arial", "B", 10)
        pdf.set_text_color(0, 100, 0)
        pdf.multi_cell(0, 6, f"After: {after_clean}")
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Arial", "", 10)
        pdf.ln(5)
        
        # =============== SUGGESTIONS ===============
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "Actionable Tips", ln=True)
        pdf.set_font("Arial", "", 10)
        
        suggestions = result.get('suggestions', [
            "Add quantifiable metrics",
            "Use standard section headers",
            "Expand project descriptions"
        ])
        
        for i, sug in enumerate(suggestions[:5], 1):
            cleaned_sug = clean_text_for_pdf(str(sug))
            # Truncate long suggestions
            if len(cleaned_sug) > 150:
                cleaned_sug = cleaned_sug[:147] + "..."
            pdf.multi_cell(0, 6, f"{i}. {cleaned_sug}")
        
        # =============== FOOTER ===============
        pdf.ln(10)
        pdf.set_font("Arial", "I", 9)
        pdf.multi_cell(0, 5, "Generated by ResumeBoost AI - Made for AIML Students", align="C")
        pdf.multi_cell(0, 5, "No resume data stored - Payment verified via Razorpay", align="C")
        
        # =============== SAVE ===============
        filename = f"report_{clean_text_for_pdf(resume_filename)}_{score}.pdf"
        # Remove any problematic characters from filename
        filename = "".join(c for c in filename if c.isalnum() or c in "._-")
        pdf.output(filename)
        return filename
        
    except Exception as e:
        # Enhanced fallback with better formatting
        try:
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", "B", 14)
            pdf.multi_cell(0, 10, "ResumeBoost AI Report")
            pdf.ln(5)
            
            pdf.set_font("Arial", "", 11)
            pdf.multi_cell(0, 8, "Your report encountered a formatting issue.")
            pdf.ln(3)
            
            pdf.set_font("Arial", "B", 11)
            pdf.multi_cell(0, 8, "Your ATS Score:")
            pdf.set_font("Arial", "", 11)
            score = result.get('ats_score', 0)
            pdf.multi_cell(0, 8, f"{score}/100")
            pdf.ln(5)
            
            pdf.set_font("Arial", "", 10)
            pdf.multi_cell(0, 7, "For full report details, please contact support:")
            pdf.multi_cell(0, 7, "Email: bittukrazad652@gmail.com")
            pdf.multi_cell(0, 7, "Phone: +918233659229")
            
            filename = f"report_fallback_{score}.pdf"
            pdf.output(filename)
            return filename
        except:
            # Last resort: create absolute minimal PDF
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            pdf.multi_cell(0, 10, "Report Error")
            pdf.multi_cell(0, 8, "Contact: bittukrazad652@gmail.com")
            filename = "report_error.pdf"
            pdf.output(filename)
            return filename
