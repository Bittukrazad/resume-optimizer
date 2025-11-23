from fpdf import FPDF
import re
from datetime import datetime
from typing import Dict, Any


def clean_text_for_pdf(text: str) -> str:
    """Remove emojis and unsupported Unicode for PDF"""
    if not isinstance(text, str):
        text = str(text)
    
    # Emoji replacements
    emoji_map = {
        "🎯": "[TARGET]", "✅": "[OK]", "❌": "[X]", "🔍": "[SEARCH]",
        "✨": "[STAR]", "📥": "[DOWNLOAD]", "📄": "[DOC]", "📊": "[CHART]",
        "💡": "[TIP]", "🛠️": "[TOOL]", "🛠": "[TOOL]", "📌": "[NOTE]",
        "🔐": "[LOCK]", "⚠️": "[WARNING]", "⚠": "[WARNING]",
    }
    
    for emoji, replacement in emoji_map.items():
        text = text.replace(emoji, replacement)
    
    # Unicode cleanup
    text = text.replace('–', '-').replace('—', '-').replace(''', "'")
    text = text.replace(''', "'").replace('"', '"').replace('"', '"')
    text = text.replace('…', '...')
    
    # Remove remaining non-ASCII
    text = ''.join(char if ord(char) < 128 else '' for char in text)
    
    # Normalize whitespace
    text = ' '.join(text.split())
    
    return text


class EnhancedPDF(FPDF):
    """Enhanced PDF with custom header and footer"""
    
    def __init__(self):
        super().__init__(orientation='P', unit='mm', format='A4')
        self.set_margins(left=15, top=20, right=15)
        self.set_auto_page_break(auto=True, margin=20)
    
    def header(self):
        """Custom header for each page"""
        if self.page_no() == 1:
            # Title page header
            self.set_font('Arial', 'B', 20)
            self.set_text_color(51, 51, 51)
            self.cell(0, 10, 'ResumeBoost AI Report', ln=True, align='C')
            self.ln(2)
            
            # Subtitle
            self.set_font('Arial', '', 10)
            self.set_text_color(100, 100, 100)
            self.cell(0, 5, f'Generated on {datetime.now().strftime("%B %d, %Y at %I:%M %p")}', ln=True, align='C')
            self.ln(5)
        else:
            # Subsequent pages
            self.set_font('Arial', 'I', 8)
            self.set_text_color(150, 150, 150)
            self.cell(0, 5, 'ResumeBoost AI Report', ln=True, align='L')
            self.ln(2)
    
    def footer(self):
        """Custom footer for each page"""
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f'Page {self.page_no()}', align='C')
    
    def section_header(self, title: str):
        """Add a section header"""
        self.ln(5)
        self.set_font('Arial', 'B', 14)
        self.set_text_color(51, 51, 51)
        
        # Background
        self.set_fill_color(240, 240, 245)
        self.cell(0, 10, title, ln=True, fill=True)
        self.ln(2)
    
    def add_score_badge(self, score: int, x: int, y: int):
        """Add a circular score badge"""
        # Determine color based on score
        if score >= 80:
            r, g, b = 5, 150, 105  # Green
        elif score >= 70:
            r, g, b = 16, 185, 129
        elif score >= 50:
            r, g, b = 245, 158, 11  # Orange
        else:
            r, g, b = 220, 38, 38  # Red
        
        # Draw circle
        self.set_fill_color(r, g, b)
        self.ellipse(x, y, 30, 30, 'F')
        
        # Add score text
        self.set_xy(x, y + 7)
        self.set_font('Arial', 'B', 20)
        self.set_text_color(255, 255, 255)
        self.cell(30, 10, str(score), align='C')
        
        self.set_xy(x, y + 17)
        self.set_font('Arial', '', 8)
        self.cell(30, 5, '/100', align='C')
    
    def add_progress_bar(self, value: int, max_value: int = 100):
        """Add a progress bar"""
        bar_width = 170
        bar_height = 6
        fill_width = (value / max_value) * bar_width
        
        # Background
        self.set_fill_color(230, 230, 230)
        self.rect(self.get_x(), self.get_y(), bar_width, bar_height, 'F')
        
        # Fill
        if value >= 70:
            self.set_fill_color(59, 130, 246)
        elif value >= 50:
            self.set_fill_color(245, 158, 11)
        else:
            self.set_fill_color(220, 38, 38)
        
        self.rect(self.get_x(), self.get_y(), fill_width, bar_height, 'F')
        self.ln(bar_height + 3)


def generate_pdf_report(result: Dict[str, Any], resume_filename: str = "student") -> str:
    """Generate comprehensive PDF report"""
    
    try:
        pdf = EnhancedPDF()
        pdf.add_page()
        
        # =============== TITLE PAGE ===============
        score = result.get('ats_score', 0)
        
        # Score badge in center
        pdf.add_score_badge(score, 90, 40)
        
        pdf.ln(45)
        
        # Score interpretation
        pdf.set_font('Arial', 'B', 14)
        pdf.set_text_color(51, 51, 51)
        
        if score >= 80:
            interpretation = "Excellent! ATS-Ready"
            color = (5, 150, 105)
        elif score >= 70:
            interpretation = "Good - Minor Improvements Needed"
            color = (16, 185, 129)
        elif score >= 50:
            interpretation = "Average - Improvements Recommended"
            color = (245, 158, 11)
        else:
            interpretation = "Needs Work - Follow Suggestions"
            color = (220, 38, 38)
        
        pdf.set_text_color(*color)
        pdf.cell(0, 8, interpretation, ln=True, align='C')
        
        pdf.ln(10)
        
        # Key metrics
        pdf.set_font('Arial', '', 11)
        pdf.set_text_color(51, 51, 51)
        
        role = clean_text_for_pdf(result.get('detected_role', 'General'))
        word_count = result.get('word_count', 0)
        sections_found = len(result.get('sections_found', []))
        
        pdf.cell(0, 7, f"Target Role: {role}", ln=True, align='C')
        pdf.cell(0, 7, f"Word Count: {word_count} | Sections: {sections_found}/12", ln=True, align='C')
        
        # =============== SECTION SCORES ===============
        pdf.section_header("Section-wise Performance")
        
        pdf.set_font('Arial', '', 10)
        pdf.set_text_color(51, 51, 51)
        
        section_scores = result.get('section_scores', {})
        
        for sec, sec_score in section_scores.items():
            # Section name
            pdf.set_font('Arial', 'B', 11)
            pdf.cell(120, 8, sec.title(), ln=0)
            
            # Score
            if sec_score >= 70:
                color = (5, 150, 105)
                status = "Good"
            elif sec_score >= 50:
                color = (245, 158, 11)
                status = "Average"
            else:
                color = (220, 38, 38)
                status = "Poor"
            
            pdf.set_text_color(*color)
            pdf.set_font('Arial', 'B', 11)
            pdf.cell(0, 8, f"{sec_score}/100 - {status}", ln=True)
            
            # Progress bar
            pdf.set_text_color(51, 51, 51)
            pdf.add_progress_bar(sec_score)
            
            # Section details
            details = result.get('section_details', {}).get(sec, {}).get('details', {})
            
            if details:
                pdf.set_font('Arial', '', 9)
                pdf.set_text_color(100, 100, 100)
                
                info_parts = []
                
                if 'word_count' in details:
                    info_parts.append(f"Words: {details['word_count']}")
                
                if 'has_metrics' in details:
                    info_parts.append("Metrics: " + ("Yes" if details['has_metrics'] else "No"))
                
                if 'keyword_match_ratio' in details:
                    info_parts.append(f"Match: {details['keyword_match_ratio']}")
                
                if info_parts:
                    pdf.cell(0, 5, " | ".join(info_parts), ln=True)
            
            pdf.ln(3)
        
        # =============== KEYWORD ANALYSIS ===============
        pdf.section_header("Keyword Gap Analysis")
        
        pdf.set_font('Arial', '', 10)
        pdf.set_text_color(51, 51, 51)
        
        missing = result.get('missing_keywords', [])
        
        if missing:
            pdf.set_font('Arial', 'B', 11)
            pdf.cell(0, 7, f"Missing Keywords ({len(missing)}):", ln=True)
            
            pdf.set_font('Arial', '', 10)
            
            # Display in rows
            keywords_per_row = 3
            for i in range(0, len(missing), keywords_per_row):
                row_keywords = missing[i:i+keywords_per_row]
                
                for kw in row_keywords:
                    clean_kw = clean_text_for_pdf(str(kw))[:25]
                    
                    # Box style
                    pdf.set_fill_color(254, 226, 226)
                    pdf.set_text_color(220, 38, 38)
                    pdf.cell(60, 7, clean_kw, ln=0, align='C', fill=True)
                    pdf.cell(3, 7, '', ln=0)  # Spacing
                
                pdf.ln(9)
        else:
            pdf.set_text_color(5, 150, 105)
            pdf.cell(0, 7, "[OK] No missing keywords - Perfect alignment!", ln=True)
        
        pdf.ln(5)
        
        # Found keywords
        extra = result.get('extra_keywords', [])
        
        if extra:
            pdf.set_font('Arial', 'B', 11)
            pdf.set_text_color(51, 51, 51)
            pdf.cell(0, 7, f"Your Strong Keywords ({len(extra)}):", ln=True)
            
            pdf.set_font('Arial', '', 9)
            
            for i in range(0, min(len(extra), 12), 3):
                row_keywords = extra[i:i+3]
                
                for kw in row_keywords:
                    clean_kw = clean_text_for_pdf(str(kw))[:25]
                    
                    pdf.set_fill_color(209, 250, 229)
                    pdf.set_text_color(5, 150, 105)
                    pdf.cell(60, 6, clean_kw, ln=0, align='C', fill=True)
                    pdf.cell(3, 6, '', ln=0)
                
                pdf.ln(8)
        
        # =============== RECOMMENDATIONS ===============
        pdf.add_page()
        pdf.section_header("Key Recommendations")
        
        pdf.set_font('Arial', '', 10)
        pdf.set_text_color(51, 51, 51)
        
        suggestions = result.get('suggestions', [])
        
        for i, suggestion in enumerate(suggestions[:8], 1):
            clean_sug = clean_text_for_pdf(str(suggestion))[:150]
            
            pdf.set_font('Arial', 'B', 10)
            pdf.cell(10, 7, f"{i}.", ln=0)
            
            pdf.set_font('Arial', '', 10)
            pdf.multi_cell(0, 7, clean_sug)
            pdf.ln(2)
        
        # =============== SAMPLE REWRITE ===============
        pdf.section_header("AI-Powered Rewrite Example")
        
        weak_bullet = result.get('weak_bullet', '')
        rewrite = result.get('rewrite_suggestion', '')
        
        if weak_bullet:
            # Before
            pdf.set_font('Arial', 'B', 11)
            pdf.set_text_color(220, 38, 38)
            pdf.cell(0, 7, "Before (Weak):", ln=True)
            
            pdf.set_font('Arial', '', 9)
            pdf.set_text_color(100, 100, 100)
            clean_before = clean_text_for_pdf(weak_bullet)[:150]
            pdf.multi_cell(0, 6, clean_before)
            
            pdf.ln(3)
            
            # After
            pdf.set_font('Arial', 'B', 11)
            pdf.set_text_color(5, 150, 105)
            pdf.cell(0, 7, "After (Strong):", ln=True)
            
            pdf.set_font('Arial', '', 9)
            pdf.set_text_color(51, 51, 51)
            clean_after = clean_text_for_pdf(rewrite)[:150]
            pdf.multi_cell(0, 6, clean_after)
        
        # =============== FOOTER INFO ===============
        pdf.ln(10)
        pdf.set_font('Arial', 'I', 9)
        pdf.set_text_color(100, 100, 100)
        pdf.multi_cell(0, 5, 
            "This report was generated by ResumeBoost AI using advanced NLP and "
            "machine learning algorithms. For support, contact: bittukrazad652@gmail.com"
        )
        
        # =============== SAVE PDF ===============
        filename = f"ResumeBoost_Report_{score}.pdf"
        pdf.output(filename)
        
        return filename
    
    except Exception as e:
        print(f"PDF generation error: {e}")
        
        # Minimal fallback
        try:
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", "B", 16)
            pdf.cell(0, 10, "ResumeBoost AI Report", ln=True, align='C')
            pdf.ln(10)
            
            pdf.set_font("Arial", "", 12)
            score = result.get('ats_score', 0)
            pdf.cell(0, 10, f"ATS Score: {score}/100", ln=True)
            pdf.ln(5)
            
            role = clean_text_for_pdf(result.get('detected_role', 'General'))
            pdf.cell(0, 8, f"Target Role: {role}", ln=True)
            pdf.ln(10)
            
            pdf.set_font("Arial", "I", 10)
            pdf.cell(0, 8, "For full report, contact: bittukrazad652@gmail.com", ln=True)
            
            filename = f"ResumeBoost_Report_{score}.pdf"
            pdf.output(filename)
            return filename
        
        except:
            # Absolute last resort
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            pdf.cell(0, 10, "ResumeBoost AI", ln=True)
            pdf.cell(0, 10, "Report Generated", ln=True)
            filename = "report.pdf"
            pdf.output(filename)
            return filename
