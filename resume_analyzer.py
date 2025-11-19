# resume_analyzer.py — REPLACE ENTIRE FILE

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from utils import parse_resume_sections

_model = None

def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer('all-MiniLM-L6-v2', cache_folder="./model_cache")
    return _model

def analyze_resume(resume_text: str, job_desc: str):
    model = get_model()
    
    # 1. Overall ATS Score
    resume_emb = model.encode([resume_text])
    jd_emb = model.encode([job_desc])
    similarity = cosine_similarity(resume_emb, jd_emb)[0][0]
    ats_score = max(0, min(100, int(similarity * 100)))
    
    # 2. Section-wise Analysis
    sections = parse_resume_sections(resume_text)
    section_scores = {}
    for sec, content in sections.items():
        if content.strip():
            sec_emb = model.encode([content])
            sec_sim = cosine_similarity(sec_emb, jd_emb)[0][0]
            section_scores[sec] = max(0, min(100, int(sec_sim * 100)))
        else:
            section_scores[sec] = 0
    
    # 3. Keyword Gap (Expanded CSE Bank)
    tech_keywords = {
        # Core CS
        'python', 'java', 'c++', 'sql', 'linux', 'git', 'github', 'docker', 'aws', 'azure', 'gcp',
        # Web
        'html', 'css', 'javascript', 'react', 'nodejs', 'flask', 'django', 'rest', 'api',
        # AIML
        'machine learning', 'deep learning', 'ai', 'nlp', 'cv', 'tensorflow', 'pytorch', 'scikit-learn',
        'pandas', 'numpy', 'matplotlib', 'seaborn', 'bert', 'transformers',
        # DSA/System Design
        'dsa', 'algorithms', 'data structures', 'system design', 'oops', 'dbms', 'os', 'networking'
    }
    
    resume_words = set(resume_text.lower().split())
    jd_words = set(job_desc.lower().split())
    jd_keywords = jd_words & tech_keywords
    resume_keywords = resume_words & tech_keywords
    missing = sorted(jd_keywords - resume_keywords)
    
    # 4. Role Detection
    role_keywords = {
        "SDE": {"sde", "software engineer", "coding", "dsa", "algorithms", "oops"},
        "Data Scientist": {"data scientist", "ml", "ai", "analytics", "model", "pandas", "numpy"},
        "AI/ML Engineer": {"ai", "ml", "deep learning", "pytorch", "tensorflow", "nlp", "cv"},
        "DevOps": {"devops", "docker", "kubernetes", "ci/cd", "cloud"}
    }
    detected_role = "General"
    for role, keywords in role_keywords.items():
        if any(k in job_desc.lower() for k in keywords):
            detected_role = role
            break
    
    # 5. Suggestions
    suggestions = []
    if len(missing) > 0:
        suggestions.append(f"✅ Add top keywords: {', '.join(missing[:3])}")
    if section_scores.get("projects", 0) < 60:
        suggestions.append("🛠️ Projects need metrics! Add: 'Improved X by Y%'")
    if ats_score < 70:
        suggestions.append("🎯 Target ATS Score: 80+ → add 2–3 keywords + 1 metric")

    return {
        "ats_score": ats_score,
        "section_scores": section_scores,
        "missing_keywords": missing,
        "detected_role": detected_role,
        "suggestions": suggestions
    }