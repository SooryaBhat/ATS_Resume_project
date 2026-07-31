from typing import List, Dict
import numpy as np
import spacy
from sentence_transformers import SentenceTransformer

from typing import List, Dict
import numpy as np
import spacy
from sentence_transformers import SentenceTransformer

from backend.utils.matching import fuzzy_match_keywords, normalize_skill
from rapidfuzz import fuzz


def calculate_semantic_similarity(
    resume_text: str, jd_text: str, embedder: SentenceTransformer
) -> float:
    resume_emb = embedder.encode(resume_text[:5000], convert_to_tensor=False)
    jd_emb     = embedder.encode(jd_text[:5000], convert_to_tensor=False)

    similarity = np.dot(resume_emb, jd_emb) / (
        np.linalg.norm(resume_emb) * np.linalg.norm(jd_emb)
    )
    return float(np.clip(similarity, 0.0, 1.0))


def identify_matched_keywords(
    resume_keywords: List[str], jd_keywords: List[str]
) -> List[str]:
    result = fuzzy_match_keywords(resume_keywords, jd_keywords, threshold=80)
    return result['matched']


def identify_missing_keywords(
    resume_keywords: List[str], jd_keywords: List[str], top_n: int = 15
) -> List[str]:

    result = fuzzy_match_keywords(resume_keywords, jd_keywords, threshold=80)
    return result['missing'][:top_n]


def analyze_skills_gap(
    resume_skills: List[str], jd_text: str, nlp: spacy.Language
) -> List[str]:
    doc       = nlp(jd_text[:5000])
    jd_skills = set()

    for ent in doc.ents:
        if ent.label_ in ['PRODUCT', 'ORG', 'LANGUAGE']:
            jd_skills.add(ent.text.lower())

    for chunk in doc.noun_chunks:
        ct = chunk.text.lower().strip()
        if 1 <= len(ct.split()) <= 4:
            jd_skills.add(ct)

    # Normalize resume skills for comparison
    resume_normalized = {normalize_skill(s) for s in resume_skills}

    gap = []
    for jd_skill in jd_skills:
        jd_norm = normalize_skill(jd_skill)

        # Check canonical match first
        if jd_norm in resume_normalized:
            continue

        # Then try fuzzy match against all resume skills
        best_score = max(
            (fuzz.token_sort_ratio(jd_norm, rs) for rs in resume_normalized),
            default=0,
        )
        if best_score < 75:
            gap.append(jd_skill)

    return sorted(gap)[:20]


def calculate_match_percentage(
    resume_keywords: List[str],
    jd_keywords: List[str],
    semantic_similarity: float,
) -> float:
    if not jd_keywords:
        return 0.0
    matched = identify_matched_keywords(resume_keywords, jd_keywords)
    keyword_overlap = len(matched) / len(jd_keywords)
    match_pct = (keyword_overlap * 0.6 + semantic_similarity * 0.4) * 100
    return float(np.clip(match_pct, 0.0, 100.0))


def identify_skills_breakdown(
    resume_skills: List[str], jd_keywords: List[str]
) -> Dict[str, List[str]]:
    """Identify matching skills and missing skills between resume and JD target."""
    resume_norm_map = {normalize_skill(s): s for s in resume_skills if s}
    jd_norm_map = {normalize_skill(s): s for s in jd_keywords if s}

    matching_skills = []
    missing_skills = []

    for jd_norm, original_jd_skill in jd_norm_map.items():
        if not jd_norm:
            continue
        if jd_norm in resume_norm_map:
            matching_skills.append(original_jd_skill)
        else:
            best_score = max(
                (fuzz.token_sort_ratio(jd_norm, rs) for rs in resume_norm_map.keys()),
                default=0,
            )
            if best_score >= 75:
                matching_skills.append(original_jd_skill)
            else:
                missing_skills.append(original_jd_skill)

    return {
        'matching_skills': sorted(list(set(matching_skills))),
        'missing_skills': sorted(list(set(missing_skills))),
    }


def compare_resume_with_jd(
    resume_text: str,
    resume_keywords: List[str],
    resume_skills: List[str],
    jd_text: str,
    jd_keywords: List[str],
    embedder: SentenceTransformer,
    nlp: spacy.Language,
) -> Dict:
    semantic_similarity = calculate_semantic_similarity(resume_text, jd_text, embedder)
    matched_keywords    = identify_matched_keywords(resume_keywords, jd_keywords)
    missing_keywords    = identify_missing_keywords(resume_keywords, jd_keywords)
    skills_gap          = analyze_skills_gap(resume_skills, jd_text, nlp)
    match_percentage    = calculate_match_percentage(
        resume_keywords, jd_keywords, semantic_similarity
    )
    skills_breakdown    = identify_skills_breakdown(resume_skills, jd_keywords)

    # Notebook 03 Cell 14: Match tier classification rules
    if semantic_similarity >= 0.70 or match_percentage >= 70.0:
        match_tier = 'HIGH'
    elif semantic_similarity >= 0.45 or match_percentage >= 45.0:
        match_tier = 'MEDIUM'
    else:
        match_tier = 'LOW'

    return {
        'match_percentage':    round(float(match_percentage), 1),
        'semantic_similarity': round(float(semantic_similarity), 3),
        'match_tier':          match_tier,
        'matching_skills':     skills_breakdown['matching_skills'],
        'missing_skills':      skills_breakdown['missing_skills'],
        'matched_keywords':    matched_keywords,
        'missing_keywords':    missing_keywords,
        'skills_gap':          skills_gap,
    }

