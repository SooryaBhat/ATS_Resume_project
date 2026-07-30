"""
tailor_service.py — Gemini-powered resume tailoring service.

Given a stored analysis and a saved job description, uses Gemini to:
  - Rewrite the professional summary optimised for the specific JD
  - Suggest specific bullet point improvements to highlight relevant experience
  - Recommend new keywords to inject naturally
  - Flag skills to emphasise or add
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional

from backend.database.supabase_db import (
    get_analysis_by_id,
    get_job_description,
)

logger = logging.getLogger('ats_resume_scorer')

GEMINI_MODEL = 'gemini-2.5-flash'

_TAILOR_SYSTEM_PROMPT = """You are an expert resume writer specialising in tailoring resumes for 
specific job descriptions. Given a resume analysis summary and a target job description, output 
specific, actionable rewriting suggestions.

Output ONLY valid JSON (no markdown, no explanation) with this exact schema:
{
  "summary_rewrite": "A complete rewritten professional summary paragraph optimised for this JD",
  "new_keywords_to_add": ["keyword1", "keyword2", "keyword3"],
  "suggestions": [
    {
      "section": "experience",
      "original": "Developed APIs using Python",
      "improved": "Architected high-throughput REST APIs using FastAPI and Python, reducing response latency by 45% — aligned with role's microservices scaling requirements",
      "explanation": "Added quantified impact and explicitly tied the technology to the JD requirement",
      "keywords_added": ["FastAPI", "microservices", "latency optimization"]
    }
  ]
}

Guidelines:
- summary_rewrite should be 3–4 sentences, using exact keywords from the JD where naturally appropriate
- Provide 3–5 bullet point suggestions in 'suggestions'
- new_keywords_to_add should contain 5–10 missing keywords from the JD
- section must be one of: summary / experience / skills / education / projects
- Be specific — reference actual content from the resume and actual requirements from the JD"""


async def tailor_resume(analysis_id: str, jd_id: str, user_id: str) -> Dict[str, Any]:
    """
    Generate tailoring suggestions for a resume against a specific JD.
    Returns a TailoringResponse-compatible dict.
    """
    # Fetch analysis
    analysis = await get_analysis_by_id(analysis_id, user_id)
    if not analysis:
        raise ValueError(f'Analysis {analysis_id} not found or not owned by user.')

    # Fetch JD
    jd = await get_job_description(jd_id, user_id)
    if not jd:
        raise ValueError(f'Job description {jd_id} not found.')

    # Build prompt context from analysis
    analysis_result = analysis.get('analysis_result', {}) or {}
    resume_context  = _build_resume_summary(analysis_result)
    jd_text         = jd.get('jd_text', '')
    company         = jd.get('company_name', '')
    job_title       = jd.get('job_title', '')

    # Call Gemini
    try:
        result = await _call_gemini_tailor(resume_context, jd_text, company, job_title)
    except Exception as exc:
        logger.error(f'Gemini tailoring failed: {exc}')
        result = _fallback_tailor(analysis_result, jd)

    return {
        'analysis_id':        analysis_id,
        'jd_id':              jd_id,
        'company_name':       company,
        'job_title':          job_title,
        'summary_rewrite':    result.get('summary_rewrite', ''),
        'new_keywords_to_add': result.get('new_keywords_to_add', []),
        'suggestions':        result.get('suggestions', []),
    }


def _build_resume_summary(ar: Dict) -> str:
    """Build a compact resume summary string for the Gemini prompt."""
    skills       = ', '.join(ar.get('skills', ar.get('matched_keywords', []))[:15])
    missing      = ', '.join(ar.get('missing_keywords', [])[:10])
    strengths    = '; '.join(ar.get('strengths', [])[:3])
    interpretation = ar.get('interpretation', '')

    return (
        f"ATS Score: {ar.get('ats_score', 0)}/100\n"
        f"Detected Skills: {skills}\n"
        f"Missing Keywords: {missing}\n"
        f"Strengths: {strengths}\n"
        f"Summary: {interpretation}"
    )


async def _call_gemini_tailor(resume_context: str, jd_text: str, company: str, job_title: str) -> Dict:
    api_key = os.getenv('GEMINI_API_KEY', '')
    if not api_key:
        raise ValueError('GEMINI_API_KEY not set.')

    import google.generativeai as genai
    genai.configure(api_key=api_key)

    model = genai.GenerativeModel(
        model_name=GEMINI_MODEL,
        system_instruction=_TAILOR_SYSTEM_PROMPT,
        generation_config=genai.types.GenerationConfig(
            temperature=0.4,
            max_output_tokens=3000,
            response_mime_type='application/json',
        ),
    )

    prompt = (
        f"TARGET ROLE: {job_title} at {company}\n\n"
        f"RESUME ANALYSIS SUMMARY:\n{resume_context}\n\n"
        f"JOB DESCRIPTION:\n{jd_text[:3000]}"
    )
    response = model.generate_content(prompt)
    return json.loads(response.text)


def _fallback_tailor(ar: Dict, jd: Dict) -> Dict:
    """Minimal fallback when Gemini is unavailable."""
    missing = ar.get('missing_keywords', [])[:8]
    return {
        'summary_rewrite':    (
            f"Experienced software engineer targeting the {jd.get('job_title', 'role')} position "
            f"at {jd.get('company_name', 'your company')}. Please try again for AI-powered rewrites."
        ),
        'new_keywords_to_add': missing,
        'suggestions':        [
            {
                'section':      'skills',
                'original':     'Current skills section',
                'improved':     f'Add the following missing keywords: {", ".join(missing)}',
                'explanation':  'These keywords appear in the JD but not in your resume.',
                'keywords_added': missing,
            }
        ],
    }
