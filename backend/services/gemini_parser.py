"""
gemini_parser.py — Google Gemini-powered resume and job description parser.

Replaces groq_parser.py. Maintains identical public interface so no other
module needs to change except its import line:

    parse_resume(raw_text: str)          -> Dict
    parse_job_description(raw_text: str) -> Dict

Key improvements over the Groq version:
  - Uses response_mime_type="application/json" so Gemini guarantees valid JSON
    output — eliminates the markdown-stripping hack and the inverted-logic bug
    that was present in groq_parser.py.
  - Cleaner single model-instance approach with system instructions.
  - No complex retry-on-bad-JSON needed (Gemini enforces JSON natively).
"""

import json
import logging
import os
from typing import Dict, Optional

logger = logging.getLogger('ats_resume_scorer')

# ── Model configuration ───────────────────────────────────────────────────────
GEMINI_MODEL = 'gemini-2.5-flash'

# ── Module-level singletons ───────────────────────────────────────────────────
_configured: bool = False
_resume_model = None   # lazy-loaded GenerativeModel for resume parsing
_jd_model     = None   # lazy-loaded GenerativeModel for JD parsing


def _ensure_configured() -> None:
    """Configure the google-generativeai SDK once (idempotent)."""
    global _configured
    if _configured:
        return
    api_key = os.getenv('GEMINI_API_KEY', '')
    if not api_key:
        raise ValueError(
            'GEMINI_API_KEY environment variable is not set. '
            'Obtain a key at https://aistudio.google.com/ and add it to your .env file.'
        )
    import google.generativeai as genai
    genai.configure(api_key=api_key)
    _configured = True


def _get_resume_model():
    """Return (and lazily initialise) the resume-parsing Gemini model."""
    global _resume_model
    if _resume_model is None:
        _ensure_configured()
        import google.generativeai as genai
        _resume_model = genai.GenerativeModel(
            model_name=GEMINI_MODEL,
            system_instruction=_RESUME_SYSTEM_PROMPT,
            generation_config=genai.types.GenerationConfig(
                temperature=0.0,
                response_mime_type='application/json',
            ),
        )
        logger.info(f'Gemini resume model initialised: {GEMINI_MODEL}')
    return _resume_model


def _get_jd_model():
    """Return (and lazily initialise) the JD-parsing Gemini model."""
    global _jd_model
    if _jd_model is None:
        _ensure_configured()
        import google.generativeai as genai
        _jd_model = genai.GenerativeModel(
            model_name=GEMINI_MODEL,
            system_instruction=_JD_SYSTEM_PROMPT,
            generation_config=genai.types.GenerationConfig(
                temperature=0.0,
                response_mime_type='application/json',
            ),
        )
        logger.info(f'Gemini JD model initialised: {GEMINI_MODEL}')
    return _jd_model


# ── System prompts ────────────────────────────────────────────────────────────

_RESUME_SYSTEM_PROMPT = (
    'You are an expert resume parser. '
    'Extract all structured information from the resume text provided by the user. '
    'Return ONLY a valid JSON object matching the exact schema given — '
    'no explanations, no markdown, no code fences.'
)

_JD_SYSTEM_PROMPT = (
    'You are an expert job description parser. '
    'Extract all structured information from the job description text provided by the user. '
    'Return ONLY a valid JSON object matching the exact schema given — '
    'no explanations, no markdown, no code fences.'
)

# ── User prompts ──────────────────────────────────────────────────────────────

_RESUME_USER_PROMPT = """\
Extract information from this resume and return a JSON object with exactly this structure:
{{
  "name": "full name of the candidate",
  "email": "email address or null",
  "phone": "phone number or null",
  "linkedin": "LinkedIn URL if present, otherwise null",
  "github": "GitHub URL if present, otherwise null",
  "professional_summary": "the complete text of the Summary / Profile / About Me / Objective section exactly as written, or empty string if absent",
  "skills": ["list", "of", "all", "technical", "and", "soft", "skills"],
  "experience": [
    {{
      "job_title": "role title",
      "company": "employer name",
      "start_date": "start date as written",
      "end_date": "end date as written, or 'Present' if current",
      "duration_months": 12,
      "description": "full text of responsibilities and achievements for this role"
    }}
  ],
  "education": [
    {{
      "degree": "degree name",
      "institution": "university or college name",
      "year": "graduation year or date range"
    }}
  ],
  "certifications": ["list of certifications"],
  "projects": [
    {{
      "title": "project name",
      "description": "what the project does and how it was built",
      "technologies": ["tech", "stack", "used"]
    }}
  ],
  "action_verbs": ["strong action verbs used in bullet points, e.g. developed, implemented, designed"],
  "keywords": ["important keywords and phrases for ATS keyword matching"]
}}

Important rules:
- duration_months: calculate the number of months between start_date and end_date. If end_date is "Present" or "Current", calculate to today.
- skills: extract ALL technical and soft skills mentioned anywhere in the resume.
- action_verbs: find verbs that start bullet points or describe achievements.
- keywords: extract noun phrases and technical terms relevant to ATS matching.

Resume Text:
{raw_text}"""


_JD_USER_PROMPT = """\
Extract information from this job description and return a JSON object with exactly this structure:
{{
  "job_title": "the role title being advertised",
  "required_skills": ["must-have skills explicitly stated"],
  "preferred_skills": ["nice-to-have or preferred skills"],
  "experience_required": "years or description of required experience",
  "education_required": "required degree or qualification",
  "key_responsibilities": ["list of main job responsibilities"],
  "keywords": ["all important terms for ATS keyword matching including skills, tools, certifications, and domain terms"]
}}

Important rules:
- required_skills: only skills explicitly marked as required or must-have.
- preferred_skills: skills described as preferred, nice-to-have, or bonus.
- keywords: comprehensive list — every term an ATS would scan for.

Job Description Text:
{raw_text}"""


# ── Core API call ─────────────────────────────────────────────────────────────

def _call_gemini(model, prompt: str) -> str:
    """Send a prompt to the Gemini model and return the raw response text."""
    response = model.generate_content(prompt)
    return response.text.strip()


# ── Validation helpers ────────────────────────────────────────────────────────

def _validate_resume_result(result: dict) -> dict:
    """Ensure all expected keys are present with correct types."""
    defaults = {
        'name':                 '',
        'email':                None,
        'phone':                None,
        'linkedin':             None,
        'github':               None,
        'professional_summary': '',
        'skills':               [],
        'experience':           [],
        'education':            [],
        'certifications':       [],
        'projects':             [],
        'action_verbs':         [],
        'keywords':             [],
    }
    for key, default in defaults.items():
        if key not in result or result[key] is None:
            result[key] = default
        if isinstance(default, list) and not isinstance(result[key], list):
            result[key] = default

    # Validate individual experience entries
    for exp in result.get('experience', []):
        if not isinstance(exp, dict):
            continue
        exp.setdefault('job_title',       '')
        exp.setdefault('company',         '')
        exp.setdefault('start_date',      '')
        exp.setdefault('end_date',        '')
        exp.setdefault('duration_months', 0)
        exp.setdefault('description',     '')
        try:
            exp['duration_months'] = int(exp['duration_months'])
        except (ValueError, TypeError):
            exp['duration_months'] = 0

    # Validate individual project entries
    for proj in result.get('projects', []):
        if not isinstance(proj, dict):
            continue
        proj.setdefault('title',        '')
        proj.setdefault('description',  '')
        proj.setdefault('technologies', [])

    return result


def _validate_jd_result(result: dict) -> dict:
    """Ensure all expected keys are present with correct types."""
    defaults = {
        'job_title':             '',
        'required_skills':       [],
        'preferred_skills':      [],
        'experience_required':   '',
        'education_required':    '',
        'key_responsibilities':  [],
        'keywords':              [],
    }
    for key, default in defaults.items():
        if key not in result or result[key] is None:
            result[key] = default
        if isinstance(default, list) and not isinstance(result[key], list):
            result[key] = default
    return result


# ── Public interface ──────────────────────────────────────────────────────────

def parse_resume(raw_text: str) -> Dict:
    """
    Parse a resume using Gemini and return a validated structured dict.

    With response_mime_type='application/json', Gemini guarantees valid JSON
    output, so no retry-on-bad-JSON logic is required.

    Raises:
        ValueError:   if GEMINI_API_KEY is not configured.
        RuntimeError: if the Gemini API call fails or returns invalid JSON.
    """
    model  = _get_resume_model()
    prompt = _RESUME_USER_PROMPT.format(raw_text=raw_text)

    try:
        raw_response = _call_gemini(model, prompt)
    except Exception as exc:
        logger.error(f'Gemini API call failed during resume parsing: {exc}')
        raise RuntimeError(f'Gemini resume parsing failed: {exc}') from exc

    # response_mime_type="application/json" ensures valid JSON; wrap in
    # try/except as a defensive measure.
    try:
        result = json.loads(raw_response)
    except json.JSONDecodeError as exc:
        logger.error(
            f'Gemini returned non-JSON for resume (first 300 chars): '
            f'{raw_response[:300]}'
        )
        raise RuntimeError(
            f'Gemini returned a non-JSON response for resume parsing. '
            f'Raw (first 300 chars): {raw_response[:300]}'
        ) from exc

    logger.info(
        f"Gemini resume parse OK — "
        f"{len(result.get('skills', []))} skills, "
        f"{len(result.get('experience', []))} experience entries, "
        f"{len(result.get('projects', []))} projects"
    )
    return _validate_resume_result(result)


def parse_job_description(raw_text: str) -> Dict:
    """
    Parse a job description using Gemini and return a validated structured dict.

    Raises:
        ValueError:   if GEMINI_API_KEY is not configured.
        RuntimeError: if the Gemini API call fails or returns invalid JSON.
    """
    model  = _get_jd_model()
    prompt = _JD_USER_PROMPT.format(raw_text=raw_text)

    try:
        raw_response = _call_gemini(model, prompt)
    except Exception as exc:
        logger.error(f'Gemini API call failed during JD parsing: {exc}')
        raise RuntimeError(f'Gemini JD parsing failed: {exc}') from exc

    try:
        result = json.loads(raw_response)
    except json.JSONDecodeError as exc:
        logger.error(
            f'Gemini returned non-JSON for JD (first 300 chars): '
            f'{raw_response[:300]}'
        )
        raise RuntimeError(
            f'Gemini returned a non-JSON response for JD parsing. '
            f'Raw (first 300 chars): {raw_response[:300]}'
        ) from exc

    logger.info(
        f"Gemini JD parse OK — "
        f"job_title='{result.get('job_title', '')}', "
        f"{len(result.get('keywords', []))} keywords, "
        f"{len(result.get('required_skills', []))} required skills"
    )
    return _validate_jd_result(result)


def explain_results_with_gemini(nlp_results: Dict) -> str:
    """
    Use Gemini ONLY to generate a natural language executive explanation of the
    already calculated NLP ATS score and recommendations.
    Gemini does NOT compute or alter scores.
    """
    try:
        model = _get_resume_model()
        ats_score = nlp_results.get('ats_score', 0)
        interpretation = nlp_results.get('interpretation', '')
        missing_kw = nlp_results.get('missing_keywords', [])[:5]
        strengths = nlp_results.get('strengths', [])[:3]

        prompt = (
            f"You are an expert career consultant. Explain these deterministic NLP ATS analysis results to the candidate.\n"
            f"ATS Score: {ats_score}/100\n"
            f"Interpretation: {interpretation}\n"
            f"Strengths: {', '.join(strengths)}\n"
            f"Missing Keywords: {', '.join(missing_kw)}\n\n"
            f"Write a concise 2-sentence executive summary explaining the candidate's ATS performance "
            f"and 2 actionable improvement tips."
        )
        return _call_gemini(model, prompt)
    except Exception as exc:
        logger.warning(f"Gemini explanation generation skipped/fallback: {exc}")
        return nlp_results.get('interpretation', 'Analysis completed successfully by NLP pipeline.')

