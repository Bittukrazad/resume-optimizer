import re
import io
import logging
from rapidfuzz import fuzz, process

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# ============================================================
# SECTION PARSER (Advanced Fuzzy Header Detection)
# ============================================================

SECTION_HEADERS = {
    "summary": ["summary", "professional summary", "career summary", "objective"],
    "skills": ["skills", "technical skills", "skills & tools", "core competencies"],
    "experience": ["experience", "work experience", "professional experience", "employment history"],
    "projects": ["projects", "academic projects", "personal projects"],
    "education": ["education", "academic background", "qualifications"],
    "certifications": ["certifications", "courses", "licenses"],
    "achievements": ["achievements", "awards", "accomplishments"],
}

def find_best_section(header_text):
    """
    Fuzzy match detected header to the canonical section name.
    """
    best_match = None
    best_score = 0

    for canonical, variations in SECTION_HEADERS.items():
        for v in variations:
            score = fuzz.ratio(header_text.lower(), v.lower())
            if score > best_score:
                best_match = canonical
                best_score = score

    return best_match if best_score >= 65 else None


def parse_resume_sections(text):
    """
    Bulletproof Resume Section Extractor.
    Works for variations like:
    - SKILLS:
    - Skills
    - SKILLS
    - Professional Experience
    - EXPERIENCE
    - Education :
    """
    sections = {
        "summary": "",
        "skills": "",
        "experience": "",
        "projects": "",
        "education": "",
        "certifications": "",
        "achievements": ""
    }

    clean = text.replace("\r", "\n")

    # Matches lines like:
    # "SKILLS", "Skills:", "Technical Skills", "Experience\n"
    pattern = r"\n\s*([A-Za-z ]{3,40})\s*\:\s*|\n\s*([A-Za-z ]{3,40})\s*\n"
    matches = list(re.finditer(pattern, clean))

    if not matches:
        return sections  # fallback

    for i, match in enumerate(matches):
        header = match.group(1) or match.group(2)
        start = match.end()

        end = matches[i+1].start() if i + 1 < len(matches) else len(clean)
        body = clean[start:end].strip()

        best_section = find_best_section(header)

        if best_section:
            sections[best_section] += "\n" + body

    return sections

def extract_text_from_pdf(file) -> str:
    """
    Robust PDF extraction with multiple fallback methods
    """
    text = ""
    
    # Method 1: Try PyPDF2 first (fast, works for most PDFs)
    try:
        from PyPDF2 import PdfReader
        file.seek(0)  # Reset file pointer
        pdf_reader = PdfReader(file)
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        
        if text.strip():
            logger.info("✅ PyPDF2 extraction successful")
            return clean_text(text)
    except Exception as e:
        logger.warning(f"⚠️ PyPDF2 failed: {str(e)[:100]}")
    
    # Method 2: Try pdfplumber (better for complex layouts)
    try:
        import pdfplumber
        file.seek(0)
        with pdfplumber.open(file) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        
        if text.strip():
            logger.info("✅ pdfplumber extraction successful")
            return clean_text(text)
    except ImportError:
        logger.warning("⚠️ pdfplumber not installed (optional)")
    except Exception as e:
        logger.warning(f"⚠️ pdfplumber failed: {str(e)[:100]}")
    
    # Method 3: Try pypdf (modern replacement for PyPDF2)
    try:
        from pypdf import PdfReader as PyPdfReader
        file.seek(0)
        pdf_reader = PyPdfReader(file)
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        
        if text.strip():
            logger.info("✅ pypdf extraction successful")
            return clean_text(text)
    except ImportError:
        pass
    except Exception as e:
        logger.warning(f"⚠️ pypdf failed: {str(e)[:100]}")
    
    # Method 4: Try PDFMiner (handles complex PDFs)
    try:
        from pdfminer.high_level import extract_text as pdfminer_extract
        file.seek(0)
        text = pdfminer_extract(file)
        
        if text.strip():
            logger.info("✅ pdfminer extraction successful")
            return clean_text(text)
    except ImportError:
        logger.warning("⚠️ pdfminer not installed (optional)")
    except Exception as e:
        logger.warning(f"⚠️ pdfminer failed: {str(e)[:100]}")
    
    # If all methods fail
    if not text.strip():
        logger.error("❌ All PDF extraction methods failed")
        raise ValueError(
            "Unable to extract text from PDF. Possible reasons:\n"
            "• PDF is password-protected\n"
            "• PDF contains only images (scanned document)\n"
            "• PDF is corrupted\n"
            "• Try converting to DOCX or use a different PDF"
        )
    
    return clean_text(text)


def extract_text_from_docx(file) -> str:
    """
    Robust DOCX extraction with fallback methods
    """
    text = ""
    
    # Method 1: Try python-docx (standard method)
    try:
        from docx import Document
        file.seek(0)
        doc = Document(file)
        
        # Extract from paragraphs
        paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
        text = "\n".join(paragraphs)
        
        # Also extract from tables
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    if cell.text.strip():
                        text += "\n" + cell.text
        
        if text.strip():
            logger.info("✅ python-docx extraction successful")
            return clean_text(text)
    except Exception as e:
        logger.warning(f"⚠️ python-docx failed: {str(e)[:100]}")
    
    # Method 2: Try docx2txt (simpler, more robust)
    try:
        import docx2txt
        file.seek(0)
        text = docx2txt.process(file)
        
        if text.strip():
            logger.info("✅ docx2txt extraction successful")
            return clean_text(text)
    except ImportError:
        logger.warning("⚠️ docx2txt not installed (optional)")
    except Exception as e:
        logger.warning(f"⚠️ docx2txt failed: {str(e)[:100]}")
    
    # Method 3: Try converting to text using zipfile (DOCX is a zip)
    try:
        import zipfile
        from xml.etree import ElementTree as ET
        
        file.seek(0)
        with zipfile.ZipFile(file, 'r') as docx_zip:
            xml_content = docx_zip.read('word/document.xml')
            tree = ET.fromstring(xml_content)
            
            # Extract text from XML
            namespaces = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
            paragraphs = tree.findall('.//w:p', namespaces)
            
            for para in paragraphs:
                texts = para.findall('.//w:t', namespaces)
                para_text = ''.join([t.text for t in texts if t.text])
                if para_text.strip():
                    text += para_text + "\n"
        
        if text.strip():
            logger.info("✅ XML extraction successful")
            return clean_text(text)
    except Exception as e:
        logger.warning(f"⚠️ XML extraction failed: {str(e)[:100]}")
    
    # If all methods fail
    if not text.strip():
        logger.error("❌ All DOCX extraction methods failed")
        raise ValueError(
            "Unable to extract text from DOCX. Possible reasons:\n"
            "• File is corrupted\n"
            "• File is password-protected\n"
            "• File is not a valid DOCX format\n"
            "• Try saving as a new DOCX or convert to PDF"
        )
    
    return clean_text(text)


def clean_text(text: str) -> str:
    """
    Clean extracted text while preserving important structure
    LESS AGGRESSIVE - keeps more original content
    """
    if not text:
        return ""
    
    # Keep original case for better matching
    original_text = text
    
    # Remove URLs but keep the context
    text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', ' [URL] ', text)
    
    # Replace email with placeholder to preserve structure
    text = re.sub(r'\S+@\S+\.\S+', ' [EMAIL] ', text)
    
    # Keep most special characters - only remove truly problematic ones
    # DON'T convert to lowercase here - preserve original case
    text = re.sub(r'[^\w\s\.\,\-\(\)\[\]\+\#\:\;\/\&\%\@\*\'\"]', ' ', text)
    
    # Normalize whitespace but keep line breaks
    text = re.sub(r' +', ' ', text)  # Multiple spaces to single
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)  # Multiple newlines to double
    
    # DON'T remove short lines - they might be headers
    
    return text.strip()

def validate_resume_content(text: str) -> tuple[bool, str]:
    """
    Validate if extracted text is actually a resume
    Returns (is_valid, error_message)
    """
    if not text or len(text.strip()) < 50:
        return False, "Extracted text is too short (less than 50 characters). File may be empty or corrupted."
    
    # Check for common resume keywords (much more comprehensive)
    resume_indicators = [
        # Section headers
        'experience', 'education', 'skills', 'project', 'summary', 
        'objective', 'profile', 'qualification', 'certification',
        'achievement', 'internship', 'training', 'award',
        
        # Educational terms
        'bachelor', 'master', 'degree', 'university', 'college',
        'school', 'graduate', 'undergraduate', 'btech', 'mtech',
        'bsc', 'msc', 'diploma', 'cgpa', 'gpa', 'percentage',
        
        # Work terms
        'work', 'intern', 'job', 'role', 'position', 'responsibilities',
        'company', 'organization', 'team', 'developed', 'managed',
        'led', 'designed', 'implemented', 'built', 'created',
        
        # Technical terms
        'python', 'java', 'javascript', 'react', 'node', 'sql',
        'html', 'css', 'programming', 'software', 'developer',
        'engineer', 'data', 'analysis', 'machine learning', 'ai',
        
        # Time/date indicators
        'january', 'february', 'march', 'april', 'may', 'june',
        'july', 'august', 'september', 'october', 'november', 'december',
        '2020', '2021', '2022', '2023', '2024', '2025',
        'present', 'current', 'ongoing',
        
        # Contact info indicators
        'email', 'phone', 'linkedin', 'github', 'portfolio',
        
        # Common resume words
        'professional', 'technical', 'leadership', 'communication',
        'problem solving', 'teamwork', 'analytical'
    ]
    
    text_lower = text.lower()
    found_indicators = sum(1 for indicator in resume_indicators if indicator in text_lower)
    
    # Very lenient check - just need ANY indicator
    if found_indicators < 1:
        return False, "File doesn't appear to be a resume. Please upload a valid resume with sections like Education, Experience, Skills, or Projects."
    
    # Check if it's mostly gibberish (too many numbers or special chars)
    alpha_chars = sum(c.isalpha() for c in text)
    total_chars = len(text.replace(' ', ''))
    
    if total_chars > 0 and alpha_chars / total_chars < 0.3:
        return False, "Extracted text appears corrupted. Try converting the file to a different format."
    
    return True, ""
