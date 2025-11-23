import os as os_module
import re
import numpy as np
import torch
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from utils import parse_resume_sections

_model = None

def get_model():
    global _model
    if _model is None:
        os_module.makedirs("./model_cache", exist_ok=True)
        device = "cpu"
        _model = SentenceTransformer(
            'all-MiniLM-L6-v2',
            cache_folder="./model_cache",
            device=device
        )
    return _model

def analyze_resume(resume_text, job_desc):
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
            # Clean section content
            clean_content = content[:500]  # Limit to avoid token issues
            sec_emb = model.encode([clean_content])
            sec_sim = cosine_similarity(sec_emb, jd_emb)[0][0]
            section_scores[sec] = max(0, min(100, int(sec_sim * 100)))
        else:
            section_scores[sec] = 0
    
    # If no sections detected, give default scores based on overall
    if all(score == 0 for score in section_scores.values()):
        base_score = ats_score
        section_scores = {
            "skills": min(100, base_score + 5),
            "experience": base_score,
            "projects": max(0, base_score - 10),
            "education": max(0, base_score - 5)
        }
    
    # 3. Enhanced Keyword Analysis
    tech_keywords = {
        # Programming Languages
        'python', 'java', 'javascript', 'c++', 'c#', 'ruby', 'php', 'swift', 'kotlin', 'go', 'rust', 'r',
        
        # Data Science & ML
        'numpy', 'pandas', 'scikit-learn', 'sklearn', 'keras', 'tensorflow', 'pytorch', 'xgboost',
        'machine learning', 'deep learning', 'ai', 'nlp', 'cv', 'computer vision', 'neural networks',
        'data science', 'data analysis', 'statistics', 'forecasting', 'time series',
        
        # Web Development
        'html', 'css', 'react', 'angular', 'vue', 'nodejs', 'node', 'express', 'flask', 'django',
        'rest', 'api', 'graphql', 'frontend', 'backend', 'full stack', 'fullstack',
        
        # Databases
        'sql', 'mysql', 'postgresql', 'postgres', 'mongodb', 'redis', 'oracle', 'nosql',
        
        # Cloud & DevOps
        'aws', 'azure', 'gcp', 'cloud', 'docker', 'kubernetes', 'k8s', 'jenkins', 'ci/cd',
        'terraform', 'ansible', 'devops',
        
        # Tools & Others
        'git', 'github', 'gitlab', 'linux', 'bash', 'tableau', 'power bi', 'excel',
        'jira', 'agile', 'scrum',
        
        # CS Fundamentals
        'dsa', 'algorithms', 'data structures', 'system design', 'oops', 'oop',
        'dbms', 'operating system', 'os', 'networking', 'distributed systems'
    }
    
    # Extract keywords from both texts
    resume_lower = resume_text.lower()
    jd_lower = job_desc.lower()
    
    # Find keywords present in job description
    jd_keywords = set()
    for keyword in tech_keywords:
        if keyword in jd_lower:
            jd_keywords.add(keyword)
    
    # Find keywords present in resume
    resume_keywords = set()
    for keyword in tech_keywords:
        if keyword in resume_lower:
            resume_keywords.add(keyword)
    
    # Calculate gaps
    missing = sorted(jd_keywords - resume_keywords)
    extra_keywords = sorted(resume_keywords - jd_keywords)
    
    # 4. Enhanced Role Detection
    role_keywords = {
        "Data Scientist": {
            "primary": ["data scientist", "data science", "ml engineer", "machine learning"],
            "secondary": ["pandas", "numpy", "scikit-learn", "statistics", "forecasting", "modeling"]
        },
        "AI/ML Engineer": {
            "primary": ["ai engineer", "ml engineer", "machine learning engineer", "deep learning"],
            "secondary": ["pytorch", "tensorflow", "keras", "nlp", "computer vision", "neural"]
        },
        "Software Engineer": {
            "primary": ["software engineer", "sde", "software developer", "developer"],
            "secondary": ["dsa", "algorithms", "system design", "oops", "coding"]
        },
        "Data Analyst": {
            "primary": ["data analyst", "business analyst", "analytics"],
            "secondary": ["sql", "tableau", "power bi", "excel", "reporting", "dashboard"]
        },
        "DevOps Engineer": {
            "primary": ["devops", "site reliability", "sre", "cloud engineer"],
            "secondary": ["docker", "kubernetes", "aws", "azure", "ci/cd", "jenkins"]
        },
        "Web Developer": {
            "primary": ["web developer", "frontend", "backend", "full stack"],
            "secondary": ["react", "node", "javascript", "html", "css", "api"]
        }
    }
    
    detected_role = "General"
    max_score = 0
    
    for role, keywords in role_keywords.items():
        score = 0
        # Check primary keywords (higher weight)
        for kw in keywords["primary"]:
            if kw in jd_lower:
                score += 5
        # Check secondary keywords
        for kw in keywords["secondary"]:
            if kw in jd_lower:
                score += 1
        
        if score > max_score:
            max_score = score
            detected_role = role
    
    # 5. Extract Weak Bullet Points
    weak_bullets = []
    
    # Try to get content from experience or projects section
    experience_text = sections.get("experience", "") + " " + sections.get("projects", "")
    
    if not experience_text.strip():
        experience_text = resume_text
    
    # Split by common bullet point markers
    bullets = re.split(r'[•◦▪\-]\s*|\n\s*\d+\.\s*|\n\s*[-*]\s*', experience_text)
    
    for bullet in bullets:
        bullet = bullet.strip()
        if not bullet or len(bullet) < 20:
            continue
        
        # Identify weak phrases
        weak_phrases = [
            "built ", "worked on", "did ", "made ", "created ", 
            "developed a", "implemented a", "designed a", "helped with",
            "participated in", "assisted with", "involved in"
        ]
        
        # Check if bullet is weak AND short (no metrics)
        has_metric = bool(re.search(r'\d+%|\d+x|\$\d+|\d+\+|increased|improved|reduced|saved', bullet.lower()))
        is_weak = any(phrase in bullet.lower() for phrase in weak_phrases)
        
        if is_weak and not has_metric and len(bullet) < 150:
            tech_in_bullet = [kw for kw in tech_keywords if kw in bullet.lower()]
            weak_bullets.append({
                "original": bullet,
                "tech": tech_in_bullet[:3]
            })
    
    # 6. Generate Dynamic Rewrite
    if weak_bullets:
        bullet = weak_bullets[0]
        tech_str = ", ".join(bullet["tech"][:2]) if bullet["tech"] else "relevant technologies"
        
        action_verbs = {
            "Data Scientist": "Developed",
            "AI/ML Engineer": "Engineered",
            "Software Engineer": "Architected",
            "Data Analyst": "Analyzed",
            "DevOps Engineer": "Automated",
            "Web Developer": "Built"
        }
        action = action_verbs.get(detected_role, "Developed")
        
        # Generate contextual metrics
        if "data" in detected_role.lower() or "analyst" in detected_role.lower():
            metric = "improving accuracy by 15% and reducing processing time by 30%"
        elif "ml" in detected_role.lower() or "ai" in detected_role.lower():
            metric = "achieving 92% accuracy and reducing inference time by 40%"
        elif "web" in detected_role.lower() or "frontend" in detected_role.lower():
            metric = "improving load time by 35% and user engagement by 25%"
        elif "devops" in detected_role.lower():
            metric = "reducing deployment time by 50% and downtime by 80%"
        else:
            metric = "delivering measurable improvements in performance and efficiency"
        
        rewrite = f"{action} a {detected_role.lower()}-focused solution using {tech_str}, {metric}"
    else:
        top_tech = list(resume_keywords)[:2]
        tech_str = ", ".join(top_tech) if top_tech else "industry-standard tools"
        rewrite = f"Designed and deployed a {detected_role.lower()} solution using {tech_str} with quantifiable business impact"
    
    # 7. Generate Smart Suggestions
    suggestions = []
    
    if len(missing) > 0:
        suggestions.append(f"✅ Add these keywords: {', '.join(missing[:4])}")
    
    if section_scores.get("experience", 0) < 60:
        suggestions.append("💼 Experience section needs strengthening - add metrics and impact")
    
    if section_scores.get("skills", 0) < 70:
        suggestions.append(f"🔧 Skills section needs keywords: {', '.join(missing[:3])}")
    
    if section_scores.get("projects", 0) < 50 and "projects" in sections:
        suggestions.append("🛠️ Projects need metrics - add 'Improved X by Y%' statements")
    
    if ats_score < 70:
        suggestions.append(f"🎯 Target ATS Score: 80+ → Add {len(missing[:5])} keywords + 2 metrics")
    
    if not any(re.search(r'\d+%|\d+x', resume_text)):
        suggestions.append("📊 Add quantifiable metrics (%, $, time saved) to every bullet point")

    return {
        "ats_score": ats_score,
        "section_scores": section_scores,
        "missing_keywords": missing[:10],  # Limit to top 10
        "extra_keywords": extra_keywords[:5],
        "detected_role": detected_role,
        "suggestions": suggestions[:5],  # Limit to 5 suggestions
        "weak_bullet": weak_bullets[0]["original"] if weak_bullets else "Built a project with relevant technologies",
        "rewrite_suggestion": rewrite,
        "tech_stack": list(resume_keywords)[:5],
        "metric": metric if 'metric' in locals() else "measurable impact"
    }
