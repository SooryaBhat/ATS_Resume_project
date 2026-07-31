"""
backend/services/nlp_pipeline.py

Deterministic NLP Pipeline for Resume and Job Description Processing.
Implements notebook-derived NLP preprocessing, tokenization, text cleaning,
TF-IDF keyword extraction, spaCy/regex skill extraction, BERT embedding similarity,
and matching/missing skills calculations.

Gemini is strictly EXCLUDED from calculating ATS scores or extracting score inputs.
"""

import re
import logging
from typing import Dict, List, Set, Optional
import numpy as np
import spacy
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer

from backend.utils.matching import SKILL_ALIASES, normalize_skill, fuzzy_match_keywords

logger = logging.getLogger('ats_resume_scorer')

# Comprehensive taxonomy of technical, soft, and domain skills
TECH_SKILLS_TAXONOMY: Set[str] = {
    # Programming Languages
    'python', 'javascript', 'typescript', 'java', 'c++', 'c#', 'c', 'go', 'golang', 'rust',
    'ruby', 'php', 'swift', 'kotlin', 'r', 'matlab', 'scala', 'perl', 'shell', 'bash', 'powershell',
    'sql', 'html', 'css', 'html5', 'css3', 'sass', 'less', 'graphql',

    # Web & Backend Frameworks
    'fastapi', 'django', 'flask', 'react', 'react.js', 'reactjs', 'next.js', 'nextjs',
    'angular', 'angularjs', 'vue', 'vue.js', 'vuejs', 'express', 'express.js', 'node.js', 'nodejs',
    'spring', 'spring boot', 'springboot', 'asp.net', '.net', 'laravel', 'rails', 'ruby on rails',
    'bootstrap', 'tailwind', 'tailwindcss', 'redux', 'rxjs', 'nest.js', 'nestjs',

    # Databases & Caching
    'postgresql', 'postgres', 'mysql', 'sqlite', 'mongodb', 'redis', 'elasticsearch',
    'dynamodb', 'cassandra', 'oracle', 'sql server', 'mariadb', 'neo4j', 'couchdb', 'snowflake',

    # Cloud & DevOps / Infrastructure
    'aws', 'amazon web services', 'gcp', 'google cloud', 'azure', 'docker', 'kubernetes', 'k8s',
    'terraform', 'ansible', 'jenkins', 'gitlab', 'github actions', 'circleci', 'helm',
    'prometheus', 'grafana', 'nginx', 'apache', 'linux', 'unix', 'ci/cd', 'devops',

    # Data Science, ML & AI
    'machine learning', 'deep learning', 'artificial intelligence', 'ai', 'ml', 'nlp',
    'natural language processing', 'computer vision', 'cv', 'pytorch', 'tensorflow',
    'keras', 'scikit-learn', 'sklearn', 'pandas', 'numpy', 'scipy', 'spacy', 'nltk',
    'opencv', 'hugging face', 'huggingface', 'transformers', 'bert', 'llm', 'langchain',
    'data analysis', 'data modeling', 'tableau', 'power bi', 'spark', 'pyspark', 'hadoop',

    # Soft Skills & Business / Domain
    'agile', 'scrum', 'kanban', 'project management', 'product management', 'leadership',
    'stakeholder management', 'problem solving', 'communication', 'teamwork', 'collaboration',
    'time management', 'critical thinking', 'roadmapping', 'analytics', 'kpis',
    'rest api', 'restful apis', 'microservices', 'git', 'system design', 'pci-dss'
}

# Regex patterns for contact info & text cleaning
EMAIL_PATTERN = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
PHONE_PATTERN = r'\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'
LINKEDIN_PATTERN = r'(?:https?://)?(?:www\.)?linkedin\.com/in/[A-Za-z0-9_-]+/?'
GITHUB_PATTERN = r'(?:https?://)?(?:www\.)?github\.com/[A-Za-z0-9_-]+/?'

# Common action verbs used in bullet points
ACTION_VERBS_TAXONOMY: Set[str] = {
    'accelerated', 'achieved', 'actioned', 'adapted', 'administered', 'advised', 'allocated',
    'analyzed', 'annotated', 'applied', 'approved', 'architected', 'arranged', 'assembled',
    'assessed', 'assigned', 'automated', 'authored', 'balanced', 'budgeted', 'built',
    'calculated', 'championed', 'clarified', 'coached', 'collaborated', 'collected', 'compiled',
    'completed', 'computed', 'conceptualized', 'conducted', 'configured', 'constructed',
    'consolidated', 'consulted', 'coordinating', 'coordinated', 'crafted', 'created', 'debugged',
    'decreased', 'defined', 'delegated', 'delivered', 'demonstrated', 'deployed', 'designed',
    'determined', 'developed', 'devised', 'diagnosed', 'directed', 'documented', 'drafted',
    'drove', 'edited', 'elevated', 'eliminated', 'engineered', 'enhanced', 'established',
    'evaluated', 'executed', 'expanded', 'expedited', 'facilitated', 'formulated', 'fostered',
    'generated', 'guided', 'headed', 'identified', 'implemented', 'improved', 'increased',
    'influenced', 'initiated', 'inspected', 'installed', 'instituted', 'instructed', 'integrated',
    'introduced', 'invented', 'investigated', 'launched', 'led', 'leveraged', 'managed',
    'maximized', 'mentored', 'merged', 'migrated', 'minimized', 'modeled', 'monitored',
    'negotiated', 'optimized', 'orchestrated', 'organized', 'overhauled', 'oversaw', 'performed',
    'pioneered', 'planned', 'prepared', 'presented', 'prioritized', 'processed', 'produced',
    'programmed', 'promoted', 'proposed', 'provided', 'published', 'quantified', 'reengineered',
    'refactored', 'refined', 'reorganized', 'researched', 'resolved', 'restructured', 'revamped',
    'reviewed', 'revitalized', 'scaled', 'scheduled', 'secured', 'selected', 'simplified',
    'spearheaded', 'standardized', 'steered', 'streamlined', 'strengthened', 'structured',
    'supervised', 'surpassed', 'systematized', 'tested', 'trained', 'transformed', 'troubleshot',
    'unified', 'updated', 'upgraded', 'utilized', 'validated', 'verified'
}


def clean_text(text: str) -> str:
    """
    Clean raw input text (Notebook 01 cleaning logic):
    - Strips unprintable control characters
    - Normalizes multi-spaces and Windows CRLF newlines
    - Standardizes bullet points
    """
    if not text:
        return ""
    cleaned = text.replace('\r\n', '\n').replace('\r', '\n').replace('\t', ' ')
    cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', cleaned)
    cleaned = re.sub(r'[\u2022\u2023\u25e6\u2043\u2219]', '• ', cleaned)
    cleaned = re.sub(r'[ ]{2,}', ' ', cleaned)
    return cleaned.strip()


def tokenize_text(text: str, nlp: Optional[spacy.Language] = None) -> List[str]:
    """
    Tokenize cleaned text using spaCy (Notebook 01 NLP preprocessing):
    - Lemmatizes tokens
    - Filters out stop words, punctuation, numbers, and short tokens
    """
    if not text or not text.strip():
        return []
    
    if nlp:
        doc = nlp(text.lower()[:50000])
        tokens = [
            token.lemma_.strip()
            for token in doc
            if not token.is_stop
            and not token.is_punct
            and not token.is_digit
            and len(token.text.strip()) > 1
            and re.match(r'^[a-z0-9#+.\-]+$', token.text)
        ]
        return tokens
    
    # Fallback basic split
    words = re.findall(r'\b[a-zA-Z0-9#+.\-]{2,}\b', text.lower())
    return words


def extract_skills_nlp(text: str, nlp: Optional[spacy.Language] = None) -> List[str]:
    """
    Extract skills deterministically using spaCy and regex matching against taxonomy.
    Does NOT depend on Gemini or any external API.
    """
    if not text:
        return []

    text_lower = text.lower()
    found_skills: Set[str] = set()

    # 1. Match skills from taxonomy
    for skill in TECH_SKILLS_TAXONOMY:
        pattern = r'\b' + re.escape(skill) + r'\b'
        if re.search(pattern, text_lower):
            found_skills.add(normalize_skill(skill))

    # 2. Extract skills via spaCy NER and section parsing if nlp is available
    if nlp:
        try:
            doc = nlp(text[:20000])
            for ent in doc.ents:
                if ent.label_ in ['PRODUCT', 'ORG', 'LANGUAGE']:
                    ent_text = ent.text.strip().lower()
                    if len(ent_text) >= 2 and ent_text in TECH_SKILLS_TAXONOMY:
                        found_skills.add(normalize_skill(ent_text))

            # Check explicit "Skills:" section if present
            skills_section_match = re.search(
                r'(?:skills|technical skills|skills & expertise|technologies)[\s:]+([^\n]+(?:\n[^\n]+){0,5})',
                text_lower,
                re.IGNORECASE
            )
            if skills_section_match:
                section_text = skills_section_match.group(1)
                raw_items = re.split(r'[,|•;\n]', section_text)
                for item in raw_items:
                    cleaned_item = item.strip().lower()
                    cleaned_item = re.sub(r'^[:\-•\s]+', '', cleaned_item)
                    if cleaned_item and len(cleaned_item) <= 40:
                        norm = normalize_skill(cleaned_item)
                        if len(norm) >= 2:
                            found_skills.add(norm)
        except Exception as e:
            logger.warning(f"spaCy skill extraction fallback warning: {e}")

    result = sorted(list(found_skills))
    return [s.capitalize() if len(s) > 3 else s.upper() for s in result]


def extract_keywords_nlp(text: str, nlp: Optional[spacy.Language] = None, top_n: int = 25) -> List[str]:
    """
    Extract top N keywords using scikit-learn TF-IDF Vectorizer and spaCy noun chunks.
    Does NOT depend on Gemini.
    """
    if not text or not text.strip():
        return []

    cleaned = clean_text(text)
    keywords: Set[str] = set()

    # 1. TF-IDF extraction via scikit-learn
    try:
        vectorizer = TfidfVectorizer(
            stop_words='english',
            ngram_range=(1, 2),
            max_features=100,
            token_pattern=r'(?u)\b[a-zA-Z0-9#+.\-]{2,}\b'
        )
        tfidf_matrix = vectorizer.fit_transform([cleaned])
        feature_names = vectorizer.get_feature_names_out()
        scores = tfidf_matrix.toarray()[0]

        top_indices = np.argsort(scores)[::-1][:top_n]
        for idx in top_indices:
            if scores[idx] > 0:
                kw = feature_names[idx].strip()
                if len(kw) >= 2 and not kw.isdigit():
                    keywords.add(kw)
    except Exception as e:
        logger.warning(f"TF-IDF keyword extraction warning: {e}")

    # 2. Extract noun chunks via spaCy if available
    if nlp:
        try:
            doc = nlp(cleaned[:20000])
            for chunk in doc.noun_chunks:
                ct = chunk.text.strip().lower()
                ct_clean = re.sub(r'^(the|a|an|my|our|their|his|her|this|that)\s+', '', ct)
                if 2 <= len(ct_clean) <= 35 and len(ct_clean.split()) <= 3:
                    if not any(stop in ct_clean for stop in ['experience', 'years', 'month', 'duty', 'role']):
                        keywords.add(ct_clean)
        except Exception as e:
            logger.warning(f"spaCy noun chunk extraction warning: {e}")

    return sorted(list(keywords))[:top_n]


def extract_action_verbs_nlp(text: str, nlp: Optional[spacy.Language] = None) -> List[str]:
    """
    Extract action verbs from bullet points using spaCy POS tagging and verb taxonomy.
    """
    if not text:
        return []

    found_verbs: Set[str] = set()
    text_lower = text.lower()

    for verb in ACTION_VERBS_TAXONOMY:
        if re.search(r'\b' + re.escape(verb) + r'\b', text_lower):
            found_verbs.add(verb)

    lines = text.split('\n')
    for line in lines:
        stripped = line.strip()
        if re.match(r'^\s*[•\-\*\◦\d+\.]', stripped):
            words = re.findall(r'\b[A-Za-z]+\b', stripped)
            if words:
                first_word = words[0].lower()
                if first_word in ACTION_VERBS_TAXONOMY:
                    found_verbs.add(first_word)

    if nlp:
        try:
            doc = nlp(text[:20000])
            for token in doc:
                if token.pos_ == 'VERB' and token.lemma_.lower() in ACTION_VERBS_TAXONOMY:
                    found_verbs.add(token.lemma_.lower())
        except Exception as e:
            logger.warning(f"spaCy POS verb extraction warning: {e}")

    return sorted(list(found_verbs))


def extract_contact_info_nlp(text: str, nlp: Optional[spacy.Language] = None) -> Dict:
    """Extract email, phone, LinkedIn, and GitHub from raw text using regex & spaCy."""
    email_match = re.search(EMAIL_PATTERN, text)
    phone_match = re.search(PHONE_PATTERN, text)
    linkedin_match = re.search(LINKEDIN_PATTERN, text, re.IGNORECASE)
    github_match = re.search(GITHUB_PATTERN, text, re.IGNORECASE)

    name = ""
    if nlp:
        try:
            doc = nlp(text[:1000])
            for ent in doc.ents:
                if ent.label_ == 'PERSON':
                    name = ent.text.strip()
                    break
        except Exception:
            pass

    if not name:
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        if lines:
            first_line = lines[0]
            if len(first_line) < 40 and not re.search(r'resume|cv|curriculum', first_line, re.IGNORECASE):
                name = first_line

    return {
        'name': name or 'Candidate',
        'email': email_match.group(0) if email_match else None,
        'phone': phone_match.group(0) if phone_match else None,
        'linkedin': linkedin_match.group(0) if linkedin_match else None,
        'github': github_match.group(0) if github_match else None,
    }


def extract_sections_nlp(text: str) -> Dict[str, str]:
    """Segment text into standard resume sections using regex section headers."""
    sections = {
        'summary': '',
        'experience': '',
        'education': '',
        'skills': '',
        'projects': ''
    }

    patterns = {
        'summary': r'(?:summary|profile|about me|objective)',
        'experience': r'(?:experience|work history|employment|work experience|professional experience)',
        'education': r'(?:education|academic|qualifications)',
        'skills': r'(?:skills|technical skills|technologies|expertise)',
        'projects': r'(?:projects|personal projects|key projects)'
    }

    found_headers = []
    for section_key, pattern in patterns.items():
        matches = re.finditer(r'^\s*(?:[0-9\.\#\-\*]*\s*)(' + pattern + r')[\s:]*$', text, re.IGNORECASE | re.MULTILINE)
        for m in matches:
            found_headers.append((m.start(), section_key))

    found_headers.sort(key=lambda x: x[0])

    if not found_headers:
        sections['experience'] = text
        return sections

    for i in range(len(found_headers)):
        start_idx, sec_key = found_headers[i]
        end_idx = found_headers[i + 1][0] if i + 1 < len(found_headers) else len(text)
        sections[sec_key] += text[start_idx:end_idx] + "\n"

    return sections


def calculate_bert_similarity(
    resume_text: str, jd_text: str, embedder: SentenceTransformer
) -> float:
    """
    Calculate BERT / SentenceTransformer cosine similarity between resume and JD.
    Identical to notebook 02 & notebook 03 logic.
    """
    if not resume_text or not jd_text:
        return 0.0

    try:
        emb_resume = embedder.encode(resume_text[:5000], convert_to_numpy=True)
        emb_jd = embedder.encode(jd_text[:5000], convert_to_numpy=True)

        norm_resume = np.linalg.norm(emb_resume)
        norm_jd = np.linalg.norm(emb_jd)

        if norm_resume == 0 or norm_jd == 0:
            return 0.0

        similarity = np.dot(emb_resume, emb_jd) / (norm_resume * norm_jd)
        return float(np.clip(similarity, 0.0, 1.0))
    except Exception as e:
        logger.error(f"Error calculating BERT similarity: {e}")
        return 0.0


# Direct alias matching Notebook 03 production test function signature
score_resume_against_jd = calculate_bert_similarity



def nlp_parse_resume(raw_text: str, nlp: Optional[spacy.Language] = None) -> Dict:
    """
    Pure NLP Resume Parser.
    Extracts all score components (skills, keywords, verbs, contact info, sections)
    deterministically using spaCy, scikit-learn, and regex without LLM dependencies.
    """
    cleaned = clean_text(raw_text)
    tokens = tokenize_text(cleaned, nlp)
    skills = extract_skills_nlp(cleaned, nlp)
    keywords = extract_keywords_nlp(cleaned, nlp)
    action_verbs = extract_action_verbs_nlp(cleaned, nlp)
    contact_info = extract_contact_info_nlp(cleaned, nlp)
    sections = extract_sections_nlp(cleaned)

    years_match = re.findall(r'(\d+)\+?\s*(?:years|yrs)', cleaned, re.IGNORECASE)
    exp_months = max([int(y) * 12 for y in years_match], default=24)

    return {
        'name': contact_info['name'],
        'email': contact_info['email'],
        'phone': contact_info['phone'],
        'linkedin': contact_info['linkedin'],
        'github': contact_info['github'],
        'professional_summary': sections['summary'].strip(),
        'skills': skills,
        'keywords': keywords,
        'action_verbs': action_verbs,
        'tokens_count': len(tokens),
        'experience_months': exp_months,
        'sections': sections,
        'experience': [{'description': sections['experience'], 'duration_months': exp_months}],
        'projects': [{'description': sections['projects']}] if sections['projects'] else [],
        'education': [{'description': sections['education']}] if sections['education'] else []
    }


def nlp_parse_job_description(raw_text: str, nlp: Optional[spacy.Language] = None) -> Dict:
    """
    Pure NLP Job Description Parser.
    Extracts skills, keywords, and job title without calling Gemini.
    """
    cleaned = clean_text(raw_text)
    skills = extract_skills_nlp(cleaned, nlp)
    keywords = extract_keywords_nlp(cleaned, nlp)

    lines = [l.strip() for l in cleaned.split('\n') if l.strip()]
    job_title = lines[0] if lines and len(lines[0]) < 60 else "Target Position"

    return {
        'job_title': job_title,
        'required_skills': skills,
        'preferred_skills': [],
        'keywords': keywords
    }


# ══════════════════════════════════════════════════════════════════════════════
# NOTEBOOK PIPELINE FUNCTIONS (01_EDA, 02_BERT_EMBEDDINGS, 03_BERT_FINETUNE)
# ══════════════════════════════════════════════════════════════════════════════

def validate_text_length(text: str, min_words: int = 20) -> bool:
    """
    Notebook 01 (Cell 31): Text Length Validation.
    A short text (< 20 words for resume) is flagged as incomplete for analysis.
    """
    if not text or not text.strip():
        return False
    word_count = len(text.strip().split())
    return word_count >= min_words


def score_resume_against_jd(resume_text: str, jd_text: str, embedder: SentenceTransformer) -> float:
    """
    Notebook 03 (Cell 14): score_resume_against_jd.
    Computes SentenceTransformer embedding cosine similarity between resume and job description.
    Returns float score between 0.0 and 1.0.
    """
    if not resume_text or not jd_text:
        return 0.0
    clean_r = clean_text(resume_text)
    clean_j = clean_text(jd_text)
    emb_resume = embedder.encode(clean_r, convert_to_numpy=True)
    emb_jd     = embedder.encode(clean_j, convert_to_numpy=True)
    score      = cosine_similarity([emb_resume], [emb_jd])[0][0]
    return float(max(0.0, min(1.0, score)))


def calculate_bert_similarity(resume_text: str, jd_text: str, embedder: SentenceTransformer) -> float:
    """
    Notebook 02 (Cell 6): BERT Cosine Similarity alias.
    """
    return score_resume_against_jd(resume_text, jd_text, embedder)
