import numpy as np
import torch
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from utils import parse_resume_sections
import re

_model = None

def get_model():
    global _model
    if _model is None:
        # Ensure cache dir exists
        os.makedirs("./model_cache", exist_ok=True)
        device = "cpu"
        _model = SentenceTransformer(
            'all-MiniLM-L6-v2',
            cache_folder="./model_cache",
            device=device
        )
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
    
    # 3. Keyword Analysis
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
        "SDE": {"sde", "software engineer", "coding", "dsa", "algorithms", "oops", "system design"},
        "Data Scientist": {"data scientist", "ml", "ai", "analytics", "model", "pandas", "numpy", "statistics"},
        "AI/ML Engineer": {"ai", "ml", "deep learning", "pytorch", "tensorflow", "nlp", "cv", "bert"},
        "DevOps": {"devops", "docker", "kubernetes", "ci/cd", "cloud", "jenkins", "terraform"},
        "Web Developer": {"web", "react", "node", "html", "css", "javascript", "frontend", "backend"}
    }
    detected_role = "General"
    for role, keywords in role_keywords.items():
        if any(k in job_desc.lower() for k in keywords):
            detected_role = role
            break
    
    # 5. Extract Weak Bullet Points (for dynamic rewrites)
    weak_bullets = []
    projects_text = sections.get("projects", "")
    
    # Split by common bullet separators
    bullets = re.split(r'[•●-]\s*|\n\s*\d+\.\s*|\n\s*[-*]\s*', projects_text)
    
    for bullet in bullets:
        bullet = bullet.strip()
        if not bullet or len(bullet) < 20:
            continue
            
        # Detect weak patterns
        weak_phrases = [
            "built ", "worked on", "did ", "made ", "created ", 
            "developed a", "implemented a", "designed a"
        ]
        if any(phrase in bullet.lower() for phrase in weak_phrases) and len(bullet) < 80:
            # Extract tech stack from this bullet
            tech_in_bullet = [kw for kw in tech_keywords if kw in bullet.lower()]
            weak_bullets.append({
                "original": bullet,
                "tech": tech_in_bullet[:3]  # Top 3 tech from bullet
            })
    
    # 6. Generate Dynamic Rewrite
    if weak_bullets:
        bullet = weak_bullets[0]
        tech_str = ", ".join(bullet["tech"]) if bullet["tech"] else "relevant technologies"
        
        # Role-specific action verbs
        action_verbs = {
            "SDE": "Engineered",
            "Data Scientist": "Developed",
            "AI/ML Engineer": "Designed",
            "DevOps": "Automated",
            "Web Developer": "Built"
        }
        action = action_verbs.get(detected_role, "Developed")
        
        # Smart metric selection
        if "ml" in job_desc.lower() or "ai" in job_desc.lower() or "nlp" in job_desc.lower():
            metric = "92% accuracy"
        elif "web" in job_desc.lower() or "react" in job_desc.lower():
            metric = "30% faster load times"
        elif "devops" in job_desc.lower():
            metric = "50% faster deployments"
        else:
            metric = "measurable improvement"
            
        rewrite = f"{action} a {detected_role} solution using {tech_str}, achieving {metric}."
    else:
        # Fallback for minimal resumes
        top_tech = list(resume_keywords)[:2]
        tech_str = ", ".join(top_tech) if top_tech else "Python and relevant tools"
        rewrite = f"Designed and implemented a {detected_role}-aligned solution using {tech_str} with quantifiable results."
    
    # 7. Suggestions
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
        "suggestions": suggestions,
        "weak_bullet": weak_bullets[0]["original"] if weak_bullets else "Built a project.",
        "rewrite_suggestion": rewrite
    }
