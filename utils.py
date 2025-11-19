import re
from PyPDF2 import PdfReader
from docx import Document
import io

def extract_text_from_pdf(file) -> str:
    pdf_reader = PdfReader(file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text() or ""
    return clean_text(text)

def extract_text_from_docx(file) -> str:
    doc = Document(file)
    text = "\n".join([para.text for para in doc.paragraphs])
    return clean_text(text)

def clean_text(text: str) -> str:
    # Remove URLs, emails, extra spaces, non-ASCII
    text = re.sub(r'http\S+|www\S+|mailto:\S+', '', text)
    text = re.sub(r'\S+@\S+', '', text)
    text = re.sub(r'[^a-zA-Z0-9\s\.\,\-\(\)\[\]]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text.lower()

# ADD THIS FUNCTION

def parse_resume_sections(text: str):
    """
    Split resume into sections: Skills, Projects, Experience, Education
    Returns dict: {section_name: text}
    """
    sections = {
        "skills": "",
        "projects": "",
        "experience": "",
        "education": ""
    }
    
    # Normalize headings (case-insensitive, flexible)
    patterns = {
        "skills": r"(?i)(skills|technical skills|expertise)",
        "projects": r"(?i)(projects|personal projects|academic projects)",
        "experience": r"(?i)(experience|internships|work experience)",
        "education": r"(?i)(education|academic background|qualifications)"
    }
    
    lines = text.split('\n')
    current_section = None
    
    for line in lines:
        line_clean = line.strip().lower()
        # Check if line matches a section header
        for sec, pattern in patterns.items():
            if re.search(pattern, line_clean):
                current_section = sec
                break
        # Accumulate content
        if current_section:
            sections[current_section] += line + " "
    
    return sections