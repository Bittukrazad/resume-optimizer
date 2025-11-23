import os
import re
import numpy as np
import traceback
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from utils import parse_resume_sections

_model = None


def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(
            "all-MiniLM-L6-v2",
            cache_folder="./model_cache",
            device="cpu"
        )
    return _model


def normalize_score(value):
    value = max(0, min(value, 100))
    return int(value)


def compute_similarity(model, a, b):
    try:
        a_emb = model.encode([a])
        b_emb = model.encode([b])
        return float(cosine_similarity(a_emb, b_emb)[0][0])
    except:
        return 0.50


def analyze_resume(resume_text, job_desc):
    try:
        model = get_model()

        if not resume_text.strip():
            resume_text = "No resume text"
        if not job_desc.strip():
            job_desc = "No job description"

        # ---------- GLOBAL ATS SCORE ----------
        global_sim = compute_similarity(model, resume_text, job_desc)
        ats_score = normalize_score(global_sim * 100)

        # ---------- SECTION EXTRACTION ----------
        sections = parse_resume_sections(resume_text)

        # ---------- SECTION-WISE SCORE ----------
        section_weights = {
            "skills": 0.30,
            "experience": 0.40,
            "projects": 0.20,
            "education": 0.10,
        }

        section_scores = {}
        weighted_total = 0

        for sec, weight in section_weights.items():
            content = sections.get(sec, "").strip()

            if not content:
                section_scores[sec] = 0
                continue

            sim = compute_similarity(model, content[:600], job_desc)
            sec_score = normalize_score(sim * 100)
            section_scores[sec] = sec_score

            weighted_total += sec_score * weight

        final_ats = int((ats_score + weighted_total) / 2)

        # ---------- KEYWORD ANALYSIS ----------
        tech_keywords = {
            'python', 'java', 'javascript', 'c++', 'c#', 'php', 'html', 'css',
            'react', 'node', 'django', 'flask', 'sql', 'mysql', 'mongodb',
            'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'tensorflow',
            'pytorch', 'scikit-learn', 'nlp', 'computer vision', 'data analysis'
        }

        resume_low = resume_text.lower()
        jd_low = job_desc.lower()

        jd_keys = {k for k in tech_keywords if k in jd_low}
        resume_keys = {k for k in tech_keywords if k in resume_low}

        missing = sorted(list(jd_keys - resume_keys))
        extra = sorted(list(resume_keys - jd_keys))

        # ---------- ROLE DETECTION ----------
        role_patterns = {
            "Data Scientist": ["data science", "machine learning", "ml engineer", "deep learning"],
            "AI/ML Engineer": ["deep learning", "neural networks", "nlp"],
            "Software Engineer": ["software engineer", "developer", "backend", "frontend"],
            "Data Analyst": ["data analyst", "tableau", "power bi", "sql"],
            "DevOps Engineer": ["ci/cd", "docker", "kubernetes", "aws"],
            "Web Developer": ["html", "css", "react", "node"]
        }

        detected_role = "General"
        max_hits = 0

        for role, keywords in role_patterns.items():
            hits = sum(1 for k in keywords if k in jd_low)
            if hits > max_hits:
                detected_role = role
                max_hits = hits

        # ---------- WEAK BULLET DETECTION ----------
        bullets = re.split(r"[\n•·\-*]\s*", resume_text)
        weak_bullets = []

        for b in bullets:
            b = b.strip()
            if len(b) < 20:
                continue

            has_metrics = bool(re.search(r"\d+%|\d+x|\d+\+|\$", b.lower()))
            weak_actions = ["worked on", "helped", "involved", "participated", "did", "made"]

            if any(a in b.lower() for a in weak_actions) and not has_metrics:
                weak_bullets.append(b)

        weak_bullet = weak_bullets[0] if weak_bullets else "Worked on a project but need to add metrics."

        # ---------- AUTO-REWRITE ----------
        rewrite = f"Developed a {detected_role.lower()} solution using modern tools, improving performance by 20%+."

        # ---------- SUGGESTIONS ----------
        suggestions = []

        if missing:
            suggestions.append(f"Add missing keywords: {', '.join(missing[:5])}")

        if section_scores["experience"] < 60:
            suggestions.append("Add impact-driven bullet points with metrics in Experience section.")

        if section_scores["skills"] < 60:
            suggestions.append("Skills section should be more aligned with the job description.")

        if not re.search(r"\d+%|\d+x|\$", resume_text):
            suggestions.append("Add measurable metrics like % improvements, time saved, or revenue impact.")

        if final_ats < 70:
            suggestions.append("Add 3–5 more job-specific keywords for better ATS ranking.")

        # ---------- FINAL RETURN ----------
        return {
            "ats_score": final_ats,
            "section_scores": section_scores,
            "missing_keywords": missing,
            "extra_keywords": extra,
            "detected_role": detected_role,
            "weak_bullet": weak_bullet,
            "rewrite_suggestion": rewrite,
            "suggestions": suggestions[:6],
            "tech_stack": list(resume_keys)[:6]
        }

    except Exception as e:
        traceback.print_exc()
        return {
            "ats_score": 50,
            "section_scores": {"skills": 40, "experience": 40, "projects": 30, "education": 30},
            "missing_keywords": [],
            "extra_keywords": [],
            "detected_role": "General",
            "weak_bullet": "",
            "rewrite_suggestion": "",
            "suggestions": ["Error analyzing resume"]
        }
