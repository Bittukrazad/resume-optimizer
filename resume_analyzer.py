import os
import re
import numpy as np
import traceback
from typing import Dict, List, Any, Tuple
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from utils import parse_resume_sections

_model = None


def get_model():
    """Lazy load model with caching"""
    global _model
    if _model is None:
        _model = SentenceTransformer(
            "all-MiniLM-L6-v2",
            cache_folder="./model_cache",
            device="cpu"
        )
    return _model


def normalize_score(value: float) -> int:
    """Normalize score to 0-100 range"""
    value = max(0, min(value, 100))
    return int(value)


def compute_similarity(model, text_a: str, text_b: str) -> float:
    """Compute semantic similarity between two texts"""
    try:
        if not text_a.strip() or not text_b.strip():
            return 0.0
        
        # Truncate to prevent memory issues
        text_a = text_a[:2000]
        text_b = text_b[:2000]
        
        embedding_a = model.encode([text_a])
        embedding_b = model.encode([text_b])
        
        similarity = float(cosine_similarity(embedding_a, embedding_b)[0][0])
        return max(0.0, min(1.0, similarity))
    except Exception as e:
        print(f"Similarity computation error: {e}")
        return 0.50


def extract_keywords(text: str) -> set:
    """Extract technical keywords from text"""
    tech_keywords = {
        # Programming Languages
        'python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'php', 
        'ruby', 'go', 'rust', 'kotlin', 'swift', 'r', 'matlab', 'scala',
        
        # Web Technologies
        'html', 'css', 'react', 'angular', 'vue', 'node', 'nodejs', 'express',
        'django', 'flask', 'fastapi', 'spring', 'asp.net', 'nextjs', 'nuxt',
        
        # Databases
        'sql', 'mysql', 'postgresql', 'mongodb', 'redis', 'cassandra', 
        'elasticsearch', 'oracle', 'sqlite', 'dynamodb', 'firebase',
        
        # Cloud & DevOps
        'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'jenkins', 'ci/cd',
        'terraform', 'ansible', 'git', 'github', 'gitlab', 'bitbucket',
        
        # AI/ML
        'tensorflow', 'pytorch', 'scikit-learn', 'keras', 'nlp', 'computer vision',
        'deep learning', 'machine learning', 'neural networks', 'pandas', 'numpy',
        'data analysis', 'data science', 'opencv', 'huggingface', 'transformers',
        
        # Mobile
        'android', 'ios', 'react native', 'flutter', 'xamarin',
        
        # Data Engineering
        'spark', 'hadoop', 'airflow', 'kafka', 'etl', 'data pipeline',
        'bigquery', 'snowflake', 'databricks',
        
        # Testing & Quality
        'pytest', 'junit', 'selenium', 'jest', 'cypress', 'unit testing',
        
        # Other
        'rest api', 'graphql', 'microservices', 'agile', 'scrum', 'jira',
        'linux', 'unix', 'bash', 'powershell', 'api', 'json', 'xml'
    }
    
    text_lower = text.lower()
    found = {keyword for keyword in tech_keywords if keyword in text_lower}
    
    return found


def calculate_dynamic_section_score(section_content: str, job_desc: str, model, section_type: str) -> Tuple[int, Dict[str, Any]]:
    """
    Calculate dynamic score for a section based on:
    1. Content quality
    2. Relevance to job description
    3. Keyword density
    4. Quantifiable metrics presence
    """
    
    if not section_content.strip():
        return 0, {"reason": "Empty section", "suggestions": ["Add content to this section"]}
    
    # Base similarity score (0-100)
    similarity = compute_similarity(model, section_content, job_desc)
    base_score = similarity * 100
    
    # Quality metrics
    quality_score = 0
    suggestions = []
    details = {}
    
    # 1. Length check
    word_count = len(section_content.split())
    details['word_count'] = word_count
    
    if section_type == "summary":
        if word_count >= 50 and word_count <= 150:
            quality_score += 20
        elif word_count < 30:
            suggestions.append("Summary too short (aim for 50-150 words)")
        else:
            suggestions.append("Summary too long (keep it concise)")
    
    elif section_type == "skills":
        if word_count >= 20:
            quality_score += 25
        else:
            suggestions.append("Add more skills relevant to the job")
    
    elif section_type == "experience":
        if word_count >= 100:
            quality_score += 25
        else:
            suggestions.append("Expand experience descriptions with more details")
    
    elif section_type == "projects":
        if word_count >= 80:
            quality_score += 20
        else:
            suggestions.append("Add more project details and outcomes")
    
    elif section_type == "education":
        if word_count >= 30:
            quality_score += 15
        else:
            suggestions.append("Include GPA/CGPA and relevant coursework")
    
    # 2. Check for quantifiable metrics
    metrics_patterns = [
        r'\d+%',  # Percentages
        r'\d+x',  # Multipliers
        r'\$\d+', # Money
        r'\d+\+', # Plus numbers
        r'\d+k',  # Thousands
        r'\d+ (users|customers|projects|hours|days|months)',  # Counts
    ]
    
    has_metrics = any(re.search(pattern, section_content.lower()) for pattern in metrics_patterns)
    
    if has_metrics:
        quality_score += 15
        details['has_metrics'] = True
    else:
        if section_type in ["experience", "projects"]:
            suggestions.append("Add quantifiable metrics (%, numbers, impact)")
        details['has_metrics'] = False
    
    # 3. Check for action verbs (for experience/projects)
    if section_type in ["experience", "projects"]:
        strong_verbs = [
            'developed', 'built', 'created', 'designed', 'implemented',
            'engineered', 'architected', 'optimized', 'improved', 'increased',
            'reduced', 'managed', 'led', 'coordinated', 'established',
            'launched', 'delivered', 'achieved', 'spearheaded', 'pioneered'
        ]
        
        verb_count = sum(1 for verb in strong_verbs if verb in section_content.lower())
        
        if verb_count >= 3:
            quality_score += 10
            details['strong_verbs'] = verb_count
        else:
            suggestions.append("Use more strong action verbs")
            details['strong_verbs'] = verb_count
    
    # 4. Keyword alignment with job description
    section_keywords = extract_keywords(section_content)
    jd_keywords = extract_keywords(job_desc)
    
    if jd_keywords:
        keyword_overlap = len(section_keywords & jd_keywords)
        keyword_match_ratio = keyword_overlap / len(jd_keywords)
        
        quality_score += int(keyword_match_ratio * 30)
        details['keyword_overlap'] = keyword_overlap
        details['keyword_match_ratio'] = f"{keyword_match_ratio:.2%}"
    
    # 5. Check for weak phrases
    weak_phrases = [
        'worked on', 'helped with', 'assisted in', 'was responsible for',
        'duties included', 'tasks included', 'involved in'
    ]
    
    has_weak_phrases = any(phrase in section_content.lower() for phrase in weak_phrases)
    
    if has_weak_phrases:
        quality_score -= 10
        suggestions.append("Replace weak phrases with strong action verbs")
        details['has_weak_phrases'] = True
    
    # Calculate final score
    final_score = int((base_score * 0.6) + (quality_score * 0.4))
    final_score = normalize_score(final_score)
    
    details['base_similarity'] = f"{similarity:.2%}"
    details['quality_bonus'] = quality_score
    details['final_score'] = final_score
    
    return final_score, {"details": details, "suggestions": suggestions}


def detect_role_from_jd(job_desc: str) -> str:
    """Enhanced role detection from job description"""
    jd_lower = job_desc.lower()
    
    role_patterns = {
        "Data Scientist": [
            "data scien", "machine learning", "ml engineer", "statistical analysis",
            "predictive model", "data mining"
        ],
        "AI/ML Engineer": [
            "ai engineer", "ml engineer", "deep learning", "neural network",
            "nlp", "computer vision", "artificial intelligence"
        ],
        "Software Engineer": [
            "software engineer", "software developer", "backend", "frontend",
            "full stack", "application developer"
        ],
        "Data Analyst": [
            "data analyst", "business analyst", "tableau", "power bi",
            "data visualization", "reporting"
        ],
        "DevOps Engineer": [
            "devops", "site reliability", "ci/cd", "docker", "kubernetes",
            "infrastructure", "cloud engineer"
        ],
        "Web Developer": [
            "web developer", "frontend developer", "react developer",
            "html", "css", "javascript developer"
        ],
        "Mobile Developer": [
            "mobile developer", "android developer", "ios developer",
            "flutter", "react native"
        ],
        "Data Engineer": [
            "data engineer", "etl", "data pipeline", "spark", "hadoop",
            "data warehouse"
        ],
        "Product Manager": [
            "product manager", "product owner", "product management",
            "roadmap", "stakeholder"
        ],
        "UI/UX Designer": [
            "ui designer", "ux designer", "user experience", "figma",
            "user interface", "wireframe"
        ]
    }
    
    best_role = "General"
    max_hits = 0
    
    for role, keywords in role_patterns.items():
        hits = sum(1 for keyword in keywords if keyword in jd_lower)
        if hits > max_hits:
            best_role = role
            max_hits = hits
    
    return best_role


def find_weak_bullets(resume_text: str) -> List[str]:
    """Find weak bullet points that need improvement"""
    
    # Split into potential bullet points
    bullets = re.split(r'[\n•·\-\*]\s*', resume_text)
    
    weak_bullets = []
    weak_actions = [
        'worked on', 'helped', 'involved', 'participated', 'did',
        'made', 'was responsible', 'handled', 'dealt with'
    ]
    
    for bullet in bullets:
        bullet = bullet.strip()
        
        # Skip short lines
        if len(bullet) < 20 or len(bullet) > 200:
            continue
        
        # Check for weak action words
        has_weak_action = any(action in bullet.lower() for action in weak_actions)
        
        # Check for lack of metrics
        has_metrics = bool(re.search(r'\d+%|\d+x|\d+\+|\$\d+', bullet.lower()))
        
        if has_weak_action and not has_metrics:
            weak_bullets.append(bullet)
    
    return weak_bullets


def generate_rewrite_suggestion(weak_bullet: str, detected_role: str, tech_stack: List[str]) -> str:
    """Generate improved version of weak bullet point"""
    
    # Extract any existing numbers/metrics
    numbers = re.findall(r'\d+', weak_bullet)
    
    # Use role-specific action verbs
    role_verbs = {
        "Data Scientist": "Developed",
        "AI/ML Engineer": "Engineered",
        "Software Engineer": "Built",
        "Data Analyst": "Analyzed",
        "DevOps Engineer": "Automated",
        "Web Developer": "Designed",
        "Data Engineer": "Architected"
    }
    
    verb = role_verbs.get(detected_role, "Developed")
    
    # Select relevant tech
    tech = ", ".join(tech_stack[:2]) if len(tech_stack) >= 2 else (tech_stack[0] if tech_stack else "modern tools")
    
    # Generate metric if none exists
    metric = numbers[0] + "%" if numbers else "25%"
    
    suggestion = f"{verb} a {detected_role.lower()} solution using {tech}, improving performance by {metric} and reducing processing time by 30%."
    
    return suggestion


def analyze_resume(resume_text: str, job_desc: str) -> Dict[str, Any]:
    """
    Comprehensive resume analysis with dynamic section scoring
    """
    try:
        model = get_model()
        
        # Validate inputs
        if not resume_text.strip():
            resume_text = "No resume text provided"
        if not job_desc.strip():
            job_desc = "No job description provided"
        
        # ========== GLOBAL ATS SCORE ==========
        global_similarity = compute_similarity(model, resume_text, job_desc)
        global_ats_score = normalize_score(global_similarity * 100)
        
        # ========== SECTION EXTRACTION ==========
        sections = parse_resume_sections(resume_text)
        
        # ========== DYNAMIC SECTION SCORING ==========
        section_weights = {
            "summary": 0.10,
            "skills": 0.25,
            "experience": 0.35,
            "projects": 0.20,
            "education": 0.10,
        }
        
        section_scores = {}
        section_details = {}
        weighted_total = 0
        
        for sec, weight in section_weights.items():
            content = sections.get(sec, "").strip()
            
            score, details = calculate_dynamic_section_score(
                content, job_desc, model, sec
            )
            
            section_scores[sec] = score
            section_details[sec] = details
            weighted_total += score * weight
        
        # Calculate final ATS score (weighted average)
        final_ats = int((global_ats_score * 0.3) + (weighted_total * 0.7))
        final_ats = normalize_score(final_ats)
        
        # ========== KEYWORD ANALYSIS ==========
        resume_keywords = extract_keywords(resume_text)
        jd_keywords = extract_keywords(job_desc)
        
        missing_keywords = sorted(list(jd_keywords - resume_keywords))
        extra_keywords = sorted(list(resume_keywords - jd_keywords))
        
        # ========== ROLE DETECTION ==========
        detected_role = detect_role_from_jd(job_desc)
        
        # ========== WEAK BULLET DETECTION ==========
        weak_bullets = find_weak_bullets(resume_text)
        weak_bullet = weak_bullets[0] if weak_bullets else "Worked on a project without metrics"
        
        # ========== REWRITE SUGGESTION ==========
        rewrite = generate_rewrite_suggestion(
            weak_bullet, detected_role, list(resume_keywords)[:3]
        )
        
        # ========== SUGGESTIONS ==========
        suggestions = []
        
        # Missing keywords
        if len(missing_keywords) > 0:
            suggestions.append(f"Add {len(missing_keywords)} missing keywords: {', '.join(missing_keywords[:5])}")
        
        # Section-specific suggestions
        for sec, score in section_scores.items():
            if score < 60:
                sec_suggestions = section_details[sec].get('suggestions', [])
                if sec_suggestions:
                    suggestions.append(f"{sec.title()}: {sec_suggestions[0]}")
        
        # Metrics check
        if not re.search(r'\d+%|\d+x|\$\d+', resume_text):
            suggestions.append("Add quantifiable metrics (%, $, numbers) to demonstrate impact")
        
        # Action verbs check
        if len(weak_bullets) > 3:
            suggestions.append("Replace weak phrases with strong action verbs")
        
        # ATS formatting
        if final_ats < 70:
            suggestions.append("Use standard section headers (Experience, Education, Skills)")
        
        # Length check
        word_count = len(resume_text.split())
        if word_count < 300:
            suggestions.append("Resume is too short - aim for 400-600 words")
        elif word_count > 800:
            suggestions.append("Resume is too long - keep it concise (1-2 pages)")
        
        # ========== RETURN RESULTS ==========
        return {
            "ats_score": final_ats,
            "global_similarity": f"{global_similarity:.2%}",
            "section_scores": section_scores,
            "section_details": section_details,
            "missing_keywords": missing_keywords[:10],
            "extra_keywords": extra_keywords[:10],
            "detected_role": detected_role,
            "weak_bullet": weak_bullet,
            "weak_bullets": weak_bullets[:3],
            "rewrite_suggestion": rewrite,
            "suggestions": suggestions[:8],
            "tech_stack": list(resume_keywords)[:10],
            "word_count": word_count,
            "sections_found": [k for k, v in sections.items() if v.strip()]
        }
    
    except Exception as e:
        traceback.print_exc()
        
        # Return safe fallback
        return {
            "ats_score": 50,
            "global_similarity": "0%",
            "section_scores": {
                "skills": 40,
                "experience": 40,
                "projects": 30,
                "education": 30,
                "summary": 40
            },
            "section_details": {},
            "missing_keywords": [],
            "extra_keywords": [],
            "detected_role": "General",
            "weak_bullet": "",
            "weak_bullets": [],
            "rewrite_suggestion": "",
            "suggestions": [f"Error analyzing resume: {str(e)[:100]}"],
            "tech_stack": [],
            "word_count": 0,
            "sections_found": []
        }
