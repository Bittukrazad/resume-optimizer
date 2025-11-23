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
        "🎯": "[TARGET]",
        "✅": "[OK]",
        "❌": "[X]",
        "🔍": "[SEARCH]",
        "✨": "[STAR]",
        "📥": "[DOWNLOAD]",
        "📄": "[DOC]",
        "📊": "[CHART]",
        "💡": "[TIP]",
        "🛠️": "[TOOL]",
        "🛠": "[TOOL]",
        "📝": "[NOTE]",
        "🔒": "[LOCK]",
        "⚠️": "[WARNING]",
        "⚠": "[WARNING]",
        "🚀": "[ROCKET]",
        "💰": "[MONEY]",
        "💳": "[CARD]",
        "📞": "[PHONE]",
        "📧": "[EMAIL]",
        "📍": "[LOCATION]",
        "🎓": "[GRADUATE]",
        "🏆": "[TROPHY]",
        "⭐": "[STAR]",
        "➡️": "->",
        "➡": "->",
        "✔️": "[OK]",
        "✔": "[OK]",
    }
    
    # Replace emojis first
    for emoji, replacement in emoji_map.items():
        text = text.replace(emoji, replacement)
    
    # Comprehensive Unicode cleanup for Latin-1 compatibility
    replacements = {
        # Dashes
        '\u2013': '-',    # en-dash
        '\u2014': '-',    # em-dash
        '\u2015': '-',    # horizontal bar
        '\u2212': '-',    # minus sign
        
        # Quotes
        '\u2018': "'",    # left single quote
        '\u2019': "'",    # right single quote
        '\u201A': "'",    # single low quote
        '\u201B': "'",    # single high reversed quote
        '\u201C': '"',    # left double quote
        '\u201D': '"',    # right double quote
        '\u201E': '"',    # double low quote
        '\u201F': '"',    # double high reversed quote
        '\u2039': '<',    # single left-pointing angle quote
        '\u203A': '>',    # single right-pointing angle quote
        '\u00AB': '<<',   # left-pointing double angle quote
        '\u00BB': '>>',   # right-pointing double angle quote
        
        # Ellipsis
        '\u2026': '...',  # horizontal ellipsis
        
        # Spaces
        '\u00A0': ' ',    # non-breaking space
        '\u2000': ' ',    # en quad
        '\u2001': ' ',    # em quad
        '\u2002': ' ',    # en space
        '\u2003': ' ',    # em space
        '\u2009': ' ',    # thin space
        '\u200A': ' ',    # hair space
        '\u200B': '',     # zero-width space
        '\u200C': '',     # zero-width non-joiner
        '\u200D': '',     # zero-width joiner
        '\uFEFF': '',     # zero-width no-break space (BOM)
        
        # Bullets
        '\u2022': '*',    # bullet
        '\u2023': '>',    # triangular bullet
        '\u2043': '-',    # hyphen bullet
        '\u25E6': 'o',    # white bullet
        '\u2219': '*',    # bullet operator
        
        # Special characters
        '\u00D7': 'x',    # multiplication sign
        '\u00F7': '/',    # division sign
        '\u00B1': '+/-',  # plus-minus
        '\u2260': '!=',   # not equal
        '\u2264': '<=',   # less than or equal
        '\u2265': '>=',   # greater than or equal
        '\u2192': '->',   # rightwards arrow
        '\u2190': '<-',   # leftwards arrow
    }
    
    # Apply all replacements
    for unicode_char, ascii_char in replacements.items():
        text = text.replace(unicode_char, ascii_char)
    
    # Remove any remaining non-Latin-1 characters (keep only ASCII + Latin-1 supplement)
    # This ensures compatibility with FPDF's default fonts
    text = ''.join(char if ord(char) < 256 else '?' for char in text)
    
    return text

def generate_pdf_report(result, resume_filename="student"):
    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.set_font("Arial", size=12)
        
        # =============== HEADER ===============
        pdf.set_font("Arial", "B", 16)
        header_text = "ResumeBoost AI - Full Report"
        # Extra safety: manually replace known problematic chars
        header_text = header_text.replace("—", "-").replace("–", "-")
        pdf.cell(0, 10, clean_text_for_pdf(header_text), ln=True, align="C")
        pdf.ln(5)
        
        # =============== ATS SCORE ===============
        pdf.set_font("Arial", "B", 14)
        score = result.get('ats_score', 0)
        color = (0, 100, 0) if score >= 70 else (180, 0, 0)
        pdf.set_text_color(*color)
        pdf.cell(0, 10, clean_text_for_pdf(f"ATS Score: {score}/100"), ln=True, align="C")
        pdf.set_text_color(0, 0, 0)
        pdf.ln(5)
        
        # =============== ROLE ===============
        pdf.set_font("Arial", "", 12)
        role = clean_text_for_pdf(str(result.get('detected_role', 'General')))
        role_text = f"Target Role: {role}"
        pdf.cell(0, 10, clean_text_for_pdf(role_text), ln=True, align="C")
        pdf.ln(10)
        
        # =============== KEYWORD GAPS ===============
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "Missing Keywords", ln=True)
        pdf.set_font("Arial", "", 11)
        
        missing = result.get('missing_keywords', [])
        if missing:
            for kw in missing[:8]:
                # Clean each keyword individually
                clean_kw = clean_text_for_pdf(str(kw))
                pdf.cell(0, 8, f"* {clean_kw}", ln=True)
        else:
            pdf.cell(0, 8, "[OK] None detected - great job!", ln=True)
        pdf.ln(5)
        
        # =============== SECTION SCORES ===============
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "Section-wise Feedback", ln=True)
        pdf.set_font("Arial", "", 11)
        
        sections = result.get('section_scores', {})
        if sections:
            for sec, score_val in sections.items():
                status = "[OK] Good" if score_val >= 70 else "[X] Needs Work"
                # Clean section name and entire line
                sec_clean = clean_text_for_pdf(str(sec))
                line = f"- {sec_clean.title()}: {score_val}/100 ({status})"
                pdf.cell(0, 8, clean_text_for_pdf(line), ln=True)
        else:
            pdf.cell(0, 8, "[INFO] Section analysis unavailable", ln=True)
        pdf.ln(10)
        
        # =============== REWRITE SUGGESTION ===============
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "Personalized Rewrite", ln=True)
        pdf.set_font("Arial", "", 11)
        
        # Get rewrite data
        before = result.get("weak_bullet", "Built a project.")
        after = result.get("rewrite_suggestion", 
                         f"Developed a {role} solution with quantifiable results.")
        
        # Clean and wrap text if too long
        before_clean = clean_text_for_pdf(before)
        after_clean = clean_text_for_pdf(after)
        
        pdf.set_font("Arial", "", 10)
        pdf.multi_cell(0, 6, f"Before: {before_clean}")
        pdf.ln(2)
        pdf.set_font("Arial", "B", 10)
        pdf.set_text_color(0, 100, 0)
        pdf.multi_cell(0, 6, f"After:  {after_clean}")
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Arial", "", 11)
        pdf.ln(5)
        
        # =============== SUGGESTIONS ===============
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "Actionable Tips", ln=True)
        pdf.set_font("Arial", "", 11)
        
        suggestions = result.get('suggestions', [
            "[OK] Add quantifiable metrics (e.g., 'Improved accuracy by 12%')",
            "[TOOL] Use standard section headers (Skills, Projects, Education)",
            "[NOTE] Expand project descriptions with technologies used"
        ])
        
        for i, sug in enumerate(suggestions[:5], 1):
            cleaned_sug = clean_text_for_pdf(sug)
            pdf.multi_cell(0, 7, f"{i}. {cleaned_sug}")
        
        # =============== FOOTER ===============
        pdf.ln(15)
        pdf.set_font("Arial", "I", 10)
        pdf.cell(0, 5, "Generated by ResumeBoost AI - Made for AIML Students", ln=True, align="C")
        pdf.cell(0, 5, "No resume data stored - Payment verified via Razorpay", ln=True, align="C")
        
        # =============== SAVE ===============
        filename = f"report_{resume_filename}_{score}.pdf"
        pdf.output(filename)
        return filename
        
    except Exception as e:
        # Fallback: Generate minimal PDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(0, 10, "ResumeBoost AI Report (Fallback)", ln=True)
        pdf.cell(0, 10, clean_text_for_pdf(f"Error: {str(e)}"), ln=True)
        pdf.cell(0, 10, "Contact support: bittukrazad652@gmail.com", ln=True)
        
        filename = f"report_error_{resume_filename}.pdf"
        pdf.output(filename)
        return filename
      
