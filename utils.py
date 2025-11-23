import re
import io
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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


def parse_resume_sections(text: str):
    """
    Split resume into sections: Skills, Projects, Experience, Education
    Handles multiple header formats including ALL CAPS, Title Case, etc.
    Returns dict: {section_name: text}
    """
    sections = {
        "skills": "",
        "projects": "",
        "experience": "",
        "education": ""
    }
    
    # More comprehensive section patterns - matches various formats
    patterns = {
        "skills": r"(?i)^[\s]*(?:technical[\s]+)?skills?(?:[\s]+and[\s]+(?:competencies|expertise))?[\s]*$|^[\s]*core[\s]+competencies[\s]*$|^[\s]*expertise[\s]*$|^[\s]*proficiencies[\s]*$|^[\s]*technologies[\s]*$",
        
        "projects": r"(?i)^[\s]*projects?(?:[\s]+(?:and[\s]+)?(?:achievements?|portfolio))?[\s]*$|^[\s]*(?:personal|academic|key)[\s]+projects?[\s]*$|^[\s]*portfolio[\s]*$",
        
        "experience": r"(?i)^[\s]*(?:work[\s]+)?experience[\s]*$|^[\s]*professional[\s]+experience[\s]*$|^[\s]*(?:work[\s]+)?history[\s]*$|^[\s]*employment(?:[\s]+history)?[\s]*$|^[\s]*internships?[\s]*$|^[\s]*career[\s]+(?:summary|history)[\s]*$",
        
        "education": r"(?i)^[\s]*education(?:al[\s]+(?:background|qualifications?))?[\s]*$|^[\s]*academic[\s]+(?:background|details|qualifications?)[\s]*$|^[\s]*qualifications?[\s]*$"
    }
    
    lines = text.split('\n')
    current_section = None
    section_content = []
    
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        if not line_stripped:
            continue
        
        # Check if line is a section header
        matched = False
        
        # IMPORTANT: Check if it's a SHORT line (likely a header)
        # Most section headers are under 40 characters
        if len(line_stripped) < 40:
            for sec, pattern in patterns.items():
                if re.match(pattern, line_stripped):
                    # Save previous section
                    if current_section and section_content:
                        sections[current_section] = '\n'.join(section_content)
                    
                    current_section = sec
                    section_content = []
                    matched = True
                    break
        
        # Add content to current section (skip the header line itself)
        if not matched and current_section:
            section_content.append(line_stripped)
    
    # Save last section
    if current_section and section_content:
        sections[current_section] = '\n'.join(section_content)
    
    # Fallback: If no sections detected, try simpler keyword search
    if all(not content.strip() for content in sections.values()):
        text_lower = text.lower()
        
        # Split by common section indicators
        if 'skills' in text_lower:
            skills_start = text_lower.find('skills')
            skills_end = min([text_lower.find(keyword, skills_start + 6) 
                            for keyword in ['experience', 'education', 'projects', 'work', 'employment'] 
                            if text_lower.find(keyword, skills_start + 6) > skills_start] or [len(text)])
            sections['skills'] = text[skills_start:skills_end]
        
        if 'experience' in text_lower or 'work' in text_lower:
            exp_start = min([pos for pos in [text_lower.find('experience'), text_lower.find('work experience'), text_lower.find('employment')] if pos >= 0] or [0])
            if exp_start > 0:
                exp_end = min([text_lower.find(keyword, exp_start + 10) 
                             for keyword in ['education', 'skills', 'projects'] 
                             if text_lower.find(keyword, exp_start + 10) > exp_start] or [len(text)])
                sections['experience'] = text[exp_start:exp_end]
        
        if 'education' in text_lower:
            edu_start = text_lower.find('education')
            edu_end = min([text_lower.find(keyword, edu_start + 9) 
                         for keyword in ['skills', 'experience', 'projects', 'certifications'] 
                         if text_lower.find(keyword, edu_start + 9) > edu_start] or [len(text)])
            sections['education'] = text[edu_start:edu_end]
        
        if 'project' in text_lower:
            proj_start = text_lower.find('project')
            proj_end = min([text_lower.find(keyword, proj_start + 7) 
                          for keyword in ['experience', 'education', 'skills'] 
                          if text_lower.find(keyword, proj_start + 7) > proj_start] or [len(text)])
            sections['projects'] = text[proj_start:proj_end]
    
    return sections


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
