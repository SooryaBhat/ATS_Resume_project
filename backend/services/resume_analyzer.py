import logging
import spacy
from sentence_transformers import SentenceTransformer
from typing import Dict, List, Optional

from backend.models.schemas import IssueDetail
from backend.services.gemini_parser import parse_resume, parse_job_description   # Gemini replaces Groq
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
    nlp: spacy.Language,
    embedder: SentenceTransformer,
    job_description: Optional[str] = None,
) -> Dict:
    """
    Full analysis pipeline:
    1. Parse resume with Gemini
    2. Optionally parse JD with Gemini and compare
    3. Validate skills against projects/experience
    4. Score across 5 ATS components
    5. Generate detailed feedback (issues)
    6. Generate prioritised recommendations (now wired in)
    7. Return a unified result dict
    """

    # ── Step 1: Parse resume ──────────────────────────────────────────────────
    parsed_resume = parse_resume(resume_text)
    logger.info(f"Gemini parsed summary: {parsed_resume.get('professional_summary', '')[:100]!r}")
    logger.info(f"Gemini parsed skills count: {len(parsed_resume.get('skills', []))}")
    logger.info(f"Gemini parsed experience count: {len(parsed_resume.get('experience', []))}")

    skills       = parsed_resume.get('skills',       [])
    projects     = parsed_resume.get('projects',     [])
    keywords     = parsed_resume.get('keywords',     [])
    action_verbs = parsed_resume.get('action_verbs', [])

    experience_months = sum(
        int(e.get('duration_months', 0))
        for e in parsed_resume.get('experience', [])
        if isinstance(e, dict)
    )

    contact_info = {
        'email':     parsed_resume.get('email'),
        'phone':     parsed_resume.get('phone'),
        'linkedin':  parsed_resume.get('linkedin'),
        'github':    parsed_resume.get('github'),
        'portfolio': None,
    }

    # ── Step 2: Skill validation ──────────────────────────────────────────────
    skill_validation = validate_skills_with_projects(
        skills=skills,
        projects=projects,
        experience_entries=parsed_resume.get('experience', []),
        embedder=embedder,
    )

    # ── Step 3: JD comparison (optional) ─────────────────────────────────────
    jd_comparison_result = None
    jd_keywords          = None
    job_title            = ''

    if job_description and job_description.strip():
        parsed_jd = parse_job_description(job_description.strip())
        job_title = parsed_jd.get('job_title', '')
        jd_keywords = list(set(
            parsed_jd.get('keywords',          []) +
            parsed_jd.get('required_skills',   []) +
            parsed_jd.get('preferred_skills',  [])
        ))
        jd_comparison_result = compare_resume_with_jd(
            resume_text=resume_text,
            resume_keywords=keywords,
            resume_skills=skills,
            jd_text=job_description.strip(),
            jd_keywords=jd_keywords,
            embedder=embedder,
            nlp=nlp,
        )

    # ── Step 4: ATS scoring ───────────────────────────────────────────────────
    from backend.utils.file_utils import get_default_grammar_results, get_default_location_results
    grammar_results  = get_default_grammar_results()
    location_results = get_default_location_results()

    scores = calculate_overall_score(
        text=resume_text,
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
        resume_text=resume_text,
        parsed_resume=parsed_resume,
        skills=skills,
        projects=projects,
        action_verbs=action_verbs,
        skill_validation=skill_validation,
        scores=scores,
        contact_info=contact_info,
    )

    issues_summary = generate_issues_summary(detailed_feedback)

    # ── Step 6: Recommendation engine (now wired in) ──────────────────────────
    # Build resume section texts for the formatting generator
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

    # ── Step 8: Assemble final result dict ────────────────────────────────────
    return {
        'ats_score':        scores['overall_score'],
        'job_title':        job_title,          # extracted from JD (no longer hardcoded)
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
        'skills':                    skills,
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
        'recommendations':           recommendations_api,   # Now populated
    }


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
