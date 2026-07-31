"""
jd_service.py — Job Description CRUD and matching service.

Provides:
  - CRUD for saved job descriptions (public.job_descriptions)
  - Standalone JD matching against an existing analysis record
  - Result persistence to public.jd_matches
"""

import logging
from typing import Any, Dict, List, Optional

from backend.database.supabase_db import (
    save_job_description,
    get_job_descriptions,
    get_job_description,
    delete_job_description,
    get_analysis_by_id,
    save_jd_match,
    get_jd_matches,
)

logger = logging.getLogger('ats_resume_scorer')


async def create_job_description(user_id: str, company_name: str, job_title: str, jd_text: str) -> Optional[Dict]:
    """Persist a new job description for the user."""
    if not company_name.strip() or not job_title.strip() or not jd_text.strip():
        raise ValueError('company_name, job_title, and jd_text are all required.')
    result = await save_job_description(user_id, company_name.strip(), job_title.strip(), jd_text.strip())
    if result:
        logger.info(f"Saved JD '{job_title}' @ '{company_name}' for user={user_id}")
    return result


async def list_job_descriptions(user_id: str) -> List[Dict]:
    return await get_job_descriptions(user_id)


async def fetch_job_description(jd_id: str, user_id: str) -> Optional[Dict]:
    return await get_job_description(jd_id, user_id)


async def remove_job_description(jd_id: str, user_id: str) -> bool:
    ok = await delete_job_description(jd_id, user_id)
    if ok:
        logger.info(f'Deleted JD id={jd_id} for user={user_id}')
    return ok


async def match_analysis_with_jd(
    analysis_id: str,
    jd_id: str,
    user_id: str,
    nlp,
    embedder,
) -> Dict[str, Any]:
    """
    Run the JD comparison pipeline on a stored analysis record vs a saved JD.

    1. Fetch analysis from DB
    2. Fetch JD from DB
    3. Re-run jd_matcher.compare_resume_with_jd on the stored text/keywords
    4. Persist result to jd_matches table
    5. Return structured match result
    """
    from backend.services.jd_matcher import compare_resume_with_jd
    from backend.services.nlp_pipeline import nlp_parse_job_description

    # 1. Fetch analysis
    analysis = await get_analysis_by_id(analysis_id, user_id)
    if not analysis:
        raise ValueError(f'Analysis {analysis_id} not found or not owned by user.')

    # 2. Fetch JD
    jd = await get_job_description(jd_id, user_id)
    if not jd:
        raise ValueError(f'Job description {jd_id} not found.')

    jd_text = jd.get('jd_text', '')

    # 3. Run matching — use stored keywords from analysis
    analysis_result = analysis.get('analysis_result', {})
    resume_keywords = analysis_result.get('matched_keywords', []) + analysis_result.get('missing_keywords', [])
    resume_skills   = []  # skills not stored separately — use keywords as proxy

    # Parse JD to extract structured keywords using deterministic NLP pipeline
    try:
        parsed_jd = nlp_parse_job_description(jd_text, nlp)
        jd_keywords = list(set(
            parsed_jd.get('keywords', []) +
            parsed_jd.get('required_skills', []) +
            parsed_jd.get('preferred_skills', [])
        ))
    except Exception as exc:
        logger.warning(f'NLP JD parsing failed, falling back to raw text: {exc}')
        jd_keywords = jd_text.split()[:50]

    match_result = compare_resume_with_jd(
        resume_text=analysis_result.get('interpretation', '') or analysis_result.get('filename', ''),
        resume_keywords=resume_keywords,
        resume_skills=resume_skills,
        jd_text=jd_text,
        jd_keywords=jd_keywords,
        embedder=embedder,
        nlp=nlp,
    )

    from backend.database.supabase_db import update_analysis_context

    # 4. Persist
    match_payload = {
        **match_result,
        'company_name': jd.get('company_name', ''),
        'job_title':    jd.get('job_title', ''),
    }
    await save_jd_match(user_id, jd_id, analysis_id, match_payload)

    # Enrich active analysis record with JD match context
    await update_analysis_context(analysis_id, user_id, {
        'job_description':       jd_text,
        'jd_comparison':          match_result,
        'matching_skills':        match_result.get('matching_skills', []),
        'missing_skills':         match_result.get('missing_skills', match_result.get('skills_gap', [])),
        'match_percentage':       match_result.get('match_percentage', 0.0),
        'resume_jd_similarity':  match_result.get('semantic_similarity', 0.0),
    })

    # 5. Return
    return {
        'jd_id':              jd_id,
        'analysis_id':        analysis_id,
        'company_name':       jd.get('company_name', ''),
        'job_title':          jd.get('job_title', ''),
        'match_percentage':   round(float(match_result.get('match_percentage', 0)), 1),
        'semantic_similarity': round(float(match_result.get('semantic_similarity', 0)), 3),
        'matched_keywords':   match_result.get('matched_keywords', []),
        'missing_keywords':   match_result.get('missing_keywords', []),
        'skills_gap':         match_result.get('skills_gap', []),
    }


async def list_jd_matches(user_id: str) -> List[Dict]:
    return await get_jd_matches(user_id)
