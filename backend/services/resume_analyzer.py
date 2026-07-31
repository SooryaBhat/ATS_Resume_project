import logging
from typing import Dict, List, Optional, Any

from backend.models.schemas import IssueDetail
from backend.services.nlp_pipeline import (
    get_nlp,
    get_embedder,
    nlp_parse_resume,
    nlp_parse_job_description,
    calculate_bert_similarity,
    clean_text,
)
from backend.services.gemini_parser import explain_results_with_gemini
from backend.services.jd_matcher import compare_resume_with_jd
from backend.services.feedback_engine import analyze_issues, generate_issues_summary
from backend.services.ats_scorer import calculate_overall_score, validate_skills_with_projects
from backend.services.recommendation_engine import (
    generate_all_recommendations,
    format_recommendations_for_api,
)

logger = logging.getLogger('ats_resume_scorer')


def analyze_full_resume(
    resume_text: str,
    nlp: Optional[Any] = None,
    embedder: Optional[Any] = None,
    job_description: Optional[str] = None,
) -> Dict:
    """
    Full ATS Analysis Pipeline driven 100% by spaCy, scikit-learn, SentenceTransformers, and deterministic NLP.

    Pipeline steps:
    1. Preprocess & Parse resume deterministically with NLP (spaCy + TF-IDF + Regex)
    2. Validate skills against projects/experience using SentenceTransformer embeddings
    3. If JD is provided, extract JD terms via NLP and compute BERT embedding cosine similarity
    4. Calculate 5-component deterministic ATS score (Gemini does NOT compute ATS scores)
    5. Detect issues & generate detailed rule-based feedback
    6. Generate prioritized recommendations
    7. Optionally call Gemini ONLY for generating a narrative explanation of the NLP score
    """
    if nlp is None:
        nlp = get_nlp()
    if embedder is None:
        embedder = get_embedder()


    # ── Step 1: Preprocessing & Deterministic NLP Parse ───────────────────────
    cleaned_resume_text = clean_text(resume_text)
    nlp_parsed = nlp_parse_resume(cleaned_resume_text, nlp)

    # Deterministic NLP extraction outputs
    skills            = nlp_parsed['skills']
    keywords          = nlp_parsed['keywords']
    action_verbs      = nlp_parsed['action_verbs']
    experience_months = nlp_parsed['experience_months']
    contact_info      = {
        'email':     nlp_parsed.get('email'),
        'phone':     nlp_parsed.get('phone'),
        'linkedin':  nlp_parsed.get('linkedin'),
        'github':    nlp_parsed.get('github'),
        'portfolio': None,
    }

    # Build base parsed_resume structure for scoring components strictly from NLP
    parsed_resume = {
        'professional_summary': nlp_parsed.get('professional_summary', ''),
        'skills':               skills,
        'keywords':             keywords,
        'action_verbs':         action_verbs,
        'experience':           nlp_parsed.get('experience', []),
        'projects':             nlp_parsed.get('projects', []),
        'education':            nlp_parsed.get('education', []),
        'email':                nlp_parsed.get('email'),
        'phone':                nlp_parsed.get('phone'),
        'linkedin':             nlp_parsed.get('linkedin'),
        'github':               nlp_parsed.get('github'),
    }

    projects = parsed_resume.get('projects', [])

    logger.info(f"NLP Extracted Skills ({len(skills)}): {skills[:10]}")
    logger.info(f"NLP Extracted Keywords ({len(keywords)}): {keywords[:10]}")
    logger.info(f"NLP Action Verbs ({len(action_verbs)}): {action_verbs[:10]}")

    # ── Step 2: Skill validation with SentenceTransformers ─────────────────────
    skill_validation = validate_skills_with_projects(
        skills=skills,
        projects=projects,
        experience_entries=parsed_resume.get('experience', []),
        embedder=embedder,
    )

    # ── Step 3: JD comparison & BERT embedding similarity ─────────────────────
    jd_comparison_result = None
    jd_keywords          = None
    job_title            = ''

    if job_description and job_description.strip():
        cleaned_jd = clean_text(job_description.strip())
        nlp_jd = nlp_parse_job_description(cleaned_jd, nlp)
        job_title = nlp_jd.get('job_title', 'Target Position')

        jd_keywords = list(set(nlp_jd.get('keywords', []) + nlp_jd.get('required_skills', [])))

        # BERT Cosine Similarity calculation (Notebook 02 & 03)
        bert_sim = calculate_bert_similarity(cleaned_resume_text, cleaned_jd, embedder)

        jd_comparison_result = compare_resume_with_jd(
            resume_text=cleaned_resume_text,
            resume_keywords=keywords,
            resume_skills=skills,
            jd_text=cleaned_jd,
            jd_keywords=jd_keywords,
            embedder=embedder,
            nlp=nlp,
        )
        # Override / attach BERT embedding similarity
        jd_comparison_result['bert_similarity'] = bert_sim
        jd_comparison_result['semantic_similarity'] = bert_sim

    # ── Step 4: Deterministic ATS scoring ─────────────────────────────────────
    from backend.utils.file_utils import get_default_grammar_results, get_default_location_results
    grammar_results  = get_default_grammar_results()
    location_results = get_default_location_results()

    scores = calculate_overall_score(
        text=cleaned_resume_text,
        parsed_resume=parsed_resume,
        skills=skills,
        keywords=keywords,
        action_verbs=action_verbs,
        skill_validation_results=skill_validation,
        grammar_results=grammar_results,
        location_results=location_results,
        jd_keywords=jd_keywords,
        experience_months=experience_months,
    )

    # ── Step 5: Detailed feedback (issue detection) ───────────────────────────
    detailed_feedback = analyze_issues(
        resume_text=cleaned_resume_text,
        parsed_resume=parsed_resume,
        skills=skills,
        projects=projects,
        action_verbs=action_verbs,
        skill_validation=skill_validation,
        scores=scores,
        contact_info=contact_info,
    )

    issues_summary = generate_issues_summary(detailed_feedback)

    # ── Step 6: Recommendation engine ──────────────────────────────────────────
    exp_entries  = [e for e in parsed_resume.get('experience', []) if isinstance(e, dict)]
    edu_entries  = [e for e in parsed_resume.get('education',  []) if isinstance(e, dict)]
    proj_entries = [p for p in parsed_resume.get('projects',   []) if isinstance(p, dict)]

    sections = {
        'experience': ' '.join(e.get('description', '') for e in exp_entries),
        'education':  ' '.join(
            f"{e.get('degree', '')} {e.get('institution', '')}" for e in edu_entries
        ),
        'skills':     ' '.join(skills),
        'summary':    parsed_resume.get('professional_summary', ''),
        'projects':   ' '.join(p.get('description', '') for p in proj_entries),
    }

    recommendations_result = generate_all_recommendations(
        skill_validation_results=skill_validation,
        grammar_results=grammar_results,
        location_results=location_results,
        score_results=scores,
        sections=sections,
        keyword_analysis=jd_comparison_result,
        resume_keywords=keywords,
    )
    recommendations_api = format_recommendations_for_api(recommendations_result)

    # ── Step 7: Build skill validation details ────────────────────────────────
    validated_raw   = skill_validation.get('validated_skills',   [])
    unvalidated_raw = skill_validation.get('unvalidated_skills', [])
    total_skills    = len(validated_raw) + len(unvalidated_raw)
    val_pct         = round((len(validated_raw) / total_skills * 100) if total_skills > 0 else 0, 1)

    skill_validation_details = {
        'validated': [
            {'skill': item['skill'], 'projects': item.get('projects', [])}
            for item in validated_raw
        ],
        'unvalidated':     unvalidated_raw,
        'total':           total_skills,
        'validated_count': len(validated_raw),
        'validation_pct':  val_pct,
    }

    # ── Step 8: Build unified result dict ────────────────────────────────────
    result_dict = {
        'ats_score':            scores['overall_score'],
        'job_title':            job_title,
        'resume_text':          cleaned_resume_text,
        'job_description':      cleaned_jd if (job_description and job_description.strip()) else '',
        'component_scores': {
            'formatting':        scores['formatting_score'],
            'keywords':          scores['keywords_score'],
            'content':           scores['content_score'],
            'skill_validation':  scores['skill_validation_score'],
            'ats_compatibility': scores['ats_compatibility_score'],
        },
        'issues_summary':            issues_summary,
        'detailed_feedback':         detailed_feedback,
        'jd_match_analysis':         jd_comparison_result,
        'jd_comparison':             jd_comparison_result,
        'resume_jd_similarity': (
            jd_comparison_result['semantic_similarity']
            if jd_comparison_result else 0.0
        ),
        'match_percentage': (
            jd_comparison_result['match_percentage']
            if jd_comparison_result else 0.0
        ),
        'skills':                    skills,
        'matching_skills': (
            jd_comparison_result['matching_skills']
            if jd_comparison_result else []
        ),
        'missing_skills': (
            jd_comparison_result['missing_skills']
            if jd_comparison_result else []
        ),
        'matched_keywords': (
            jd_comparison_result['matched_keywords']
            if jd_comparison_result else list(keywords[:20])
        ),
        'missing_keywords': (
            jd_comparison_result['missing_keywords']
            if jd_comparison_result else []
        ),
        'strengths':                 _generate_strengths(
            parsed_resume, skills, projects, action_verbs, skill_validation, scores
        ),
        'interpretation':            scores.get('overall_interpretation', ''),
        'skill_validation_details':  skill_validation_details,
        'experience_months':         experience_months,
        'recommendations':           recommendations_api,
    }

    # Step 9: Optional Gemini Narrative Explanation (does NOT alter scores)
    try:
        explanation = explain_results_with_gemini(result_dict)
        if explanation:
            result_dict['ai_explanation'] = explanation
    except Exception:
        pass

    return result_dict


def _generate_strengths(
    parsed_resume: Dict, skills: List, projects: List,
    action_verbs: List, skill_validation: Dict, scores: Dict,
) -> List[str]:
    """Generate a list of things the resume does well, based on actual structured data."""
    strengths = []

    if parsed_resume.get('experience'):
        strengths.append('Has a dedicated Experience section')
    if parsed_resume.get('projects') or len(projects) > 0:
        strengths.append('Includes a Projects section showcasing applied skills')
    if parsed_resume.get('education'):
        strengths.append('Education section is present')
    if parsed_resume.get('skills'):
        strengths.append('Clear Skills section with listed technologies')
    if parsed_resume.get('professional_summary', '').strip():
        strengths.append('Professional Summary provides a quick overview')

    if len(skills) >= 8:
        strengths.append(f'Strong skill set — {len(skills)} skills detected')
    if len(action_verbs) >= 5:
        strengths.append(f'Uses {len(action_verbs)} strong action verbs in bullet points')

    validated = skill_validation.get('validated_skills', [])
    if len(validated) >= 3:
        strengths.append(f'{len(validated)} skills are backed by project/experience evidence')

    if scores.get('formatting_score', 0) >= 16:
        strengths.append('Well-formatted and ATS-friendly structure')
    if scores.get('content_score', 0) >= 20:
        strengths.append('Content quality is high with measurable achievements')

    return strengths
