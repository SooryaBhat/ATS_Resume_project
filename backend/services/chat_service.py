"""
chat_service.py — Gemini-powered conversational AI Resume Assistant.

Architecture:
  - Uses google-generativeai with multi-turn chat history
  - System prompt injects resume context (scores, skills, issues) from an
    analysis record when an analysis_id is provided
  - Persists messages to public.chat_messages via supabase_db
  - Supports session-level context (attach analysis at session creation)
    and per-message context injection (if no session-level context)
"""

import logging
import os
from typing import Any, Dict, List, Optional

from backend.database.supabase_db import (
    create_chat_session,
    get_chat_sessions,
    get_chat_session,
    get_chat_messages,
    save_chat_message,
    delete_chat_session,
    get_analysis_by_id,
)

logger = logging.getLogger('ats_resume_scorer')

GEMINI_MODEL = 'gemini-2.5-flash'

# ── Lazy Gemini singleton ─────────────────────────────────────────────────────
_configured: bool = False
_chat_model = None


def _ensure_configured() -> None:
    global _configured
    if _configured:
        return
    api_key = os.getenv('GEMINI_API_KEY', '')
    if not api_key:
        raise ValueError('GEMINI_API_KEY not set — cannot initialise chat service.')
    import google.generativeai as genai
    genai.configure(api_key=api_key)
    _configured = True


# ── System prompts ─────────────────────────────────────────────────────────────

_BASE_SYSTEM_PROMPT = """You are TalentMatch AI Assistant — a world-class resume optimization expert
and career coach. You specialise in:
  • ATS (Applicant Tracking System) resume formatting and keyword optimization
  • Rewriting bullet points with strong action verbs and quantified impact metrics
  • Crafting professional summaries tailored for specific job descriptions
  • Identifying and addressing skill gaps for target roles
  • Providing actionable, specific career advice

Guidelines:
  - Be concise, professional, and highly specific — avoid generic advice
  - When rewriting content, always provide the improved version directly
  - Reference specific details from the user's resume when available
  - Use Markdown formatting (bold, bullet lists) for clarity
  - Keep responses focused and actionable (max 300 words unless asked for more)"""


def _build_resume_context_prompt(analysis: Dict[str, Any]) -> str:
    """
    Build a comprehensive context injection prompt from an analysis record.
    Injects:
      - Candidate Resume Text
      - ATS Results (overall score + 5 component score breakdown + grade interpretation)
      - Extracted Skills & Validation Details
      - Target Job Description & Role Title
      - Similarity Results (SentenceTransformers BERT Cosine Similarity % & Match %)
      - Matching & Missing Skills
      - Matched & Missing Keywords
      - Priority Recommendations & Issues Summary
    """
    res = analysis.get('analysis_result', analysis)
    jd_analysis = res.get('jd_match_analysis') or res.get('jd_comparison') or analysis.get('jd_match_analysis') or {}

    ats_score  = res.get('ats_score', analysis.get('ats_score', 0))
    job_title  = res.get('job_title') or analysis.get('job_title', 'Target Role')
    
    resume_text = res.get('resume_text') or analysis.get('resume_text') or res.get('professional_summary', '')
    jd_text     = res.get('job_description') or jd_analysis.get('job_description') or ''

    components  = res.get('component_scores') or analysis.get('component_scores') or {}

    skills          = res.get('skills', [])
    matching_skills = res.get('matching_skills') or jd_analysis.get('matching_skills') or []
    missing_skills  = res.get('missing_skills') or jd_analysis.get('missing_skills') or jd_analysis.get('skills_gap') or []
    
    matched_kw = res.get('matched_keywords') or jd_analysis.get('matched_keywords') or []
    missing_kw = res.get('missing_keywords') or jd_analysis.get('missing_keywords') or []

    similarity = res.get('resume_jd_similarity') or jd_analysis.get('semantic_similarity') or jd_analysis.get('bert_similarity') or 0.0
    match_pct  = res.get('match_percentage') or jd_analysis.get('match_percentage') or 0.0

    recommendations = res.get('recommendations', [])
    strengths       = res.get('strengths', [])
    issues          = res.get('issues_summary', [])
    interpretation  = res.get('interpretation', '')

    ctx_lines = [
        "=== CANDIDATE RESUME & ATS ANALYSIS CONTEXT ===",
        f"Target Role / Job Title: {job_title}",
        f"Overall ATS Score: {ats_score}/100 ({interpretation})",
        "",
        "--- 5-COMPONENT ATS SCORE BREAKDOWN ---",
        f"• Formatting Score: {components.get('formatting', 0)} / 20",
        f"• Keywords & Skills Score: {components.get('keywords', 0)} / 25",
        f"• Content Quality Score: {components.get('content', 0)} / 25",
        f"• Skill Validation Score: {components.get('skill_validation', 0)} / 15",
        f"• ATS Compatibility Score: {components.get('ats_compatibility', 0)} / 15",
    ]

    if resume_text:
        ctx_lines.extend([
            "",
            "--- CANDIDATE RESUME TEXT ---",
            resume_text[:3000]
        ])

    if skills:
        ctx_lines.extend([
            "",
            "--- EXTRACTED SKILLS ---",
            ", ".join(skills[:30])
        ])

    if jd_text or match_pct > 0 or similarity > 0 or matching_skills or missing_skills:
        ctx_lines.extend([
            "",
            "--- JOB DESCRIPTION & RESUME-JD COMPARISON ---",
            f"Overall Match Percentage: {match_pct}%",
            f"SentenceTransformers BERT Cosine Similarity: {(similarity * 100):.1f}%",
        ])
        if jd_text:
            ctx_lines.append(f"Job Description Requirements: {jd_text[:1500]}")
        if matching_skills:
            ctx_lines.append(f"Matching Skills: {', '.join(matching_skills)}")
        if missing_skills:
            ctx_lines.append(f"Missing Required Skills: {', '.join(missing_skills)}")
        if matched_kw:
            ctx_lines.append(f"Matched Keywords: {', '.join(matched_kw[:15])}")
        if missing_kw:
            ctx_lines.append(f"Missing Keywords: {', '.join(missing_kw[:15])}")

    if strengths:
        ctx_lines.extend([
            "",
            "--- CANDIDATE STRENGTHS ---",
            "\n".join(f"• {s}" for s in strengths[:5])
        ])

    if issues:
        ctx_lines.extend([
            "",
            "--- TOP ATS ISSUES IDENTIFIED ---",
            "\n".join(f"• {issue}" for issue in issues[:5])
        ])

    if recommendations:
        ctx_lines.extend([
            "",
            "--- PRIORITY RECOMMENDATIONS ---"
        ])
        for rec in recommendations[:5]:
            title = rec.get('title') or rec.get('issue_title') or 'Recommendation'
            desc  = rec.get('description') or rec.get('explanation') or ''
            actions = rec.get('action_items', [])
            ctx_lines.append(f"• {title}: {desc}")
            if actions:
                ctx_lines.append(f"  Actions: {'; '.join(actions[:3])}")

    ctx_lines.append("=== END CANDIDATE CONTEXT ===")
    ctx_lines.append(
        "\nInstruction: You MUST use the candidate's exact resume text, skills, ATS score breakdown, "
        "Job Description comparison, missing skills, and recommendations provided above to answer user questions. "
        "Provide direct, highly tailored, specific answers referencing their actual resume data."
    )

    return "\n".join(ctx_lines)


# ── Public API ────────────────────────────────────────────────────────────────

async def create_session(user_id: str, title: str, analysis_id: Optional[str] = None) -> Optional[Dict]:
    """Create a new chat session record."""
    session = await create_chat_session(user_id, title, analysis_id)
    return session


async def list_sessions(user_id: str) -> List[Dict]:
    return await get_chat_sessions(user_id)


async def fetch_session_messages(session_id: str, user_id: str) -> List[Dict]:
    # Verify ownership
    session = await get_chat_session(session_id, user_id)
    if not session:
        return []
    return await get_chat_messages(session_id, user_id)


async def send_message(
    session_id: str,
    user_id: str,
    user_message: str,
    analysis_id: Optional[str] = None,
) -> Optional[str]:
    """
    Persist the user's message, call Gemini with full conversation history,
    persist the assistant reply, and return the reply text.
    """
    # Verify session ownership
    session = await get_chat_session(session_id, user_id)
    if not session:
        raise ValueError('Chat session not found or access denied.')

    # Persist user message
    await save_chat_message(session_id, user_id, 'user', user_message)

    # Fetch full conversation history for multi-turn context
    db_messages = await get_chat_messages(session_id, user_id)

    # Resolve analysis_id (session-level wins, then per-message, then latest fallback)
    ctx_analysis_id = session.get('analysis_id') or analysis_id or 'latest'

    # Build Gemini history from DB messages (excluding the message we just saved)
    gemini_history = []
    for msg in db_messages[:-1]:   # exclude last message (current user input)
        role = 'model' if msg.get('role') == 'assistant' else 'user'
        gemini_history.append({'role': role, 'parts': [msg.get('content', '')]})

    # Call Gemini
    try:
        ai_reply = await _call_gemini(
            user_message=user_message,
            history=gemini_history,
            user_id=user_id,
            analysis_id=ctx_analysis_id,
        )
    except Exception as exc:
        logger.error(f'Gemini chat call failed: {exc}')
        ai_reply = (
            "I'm sorry, I encountered an issue processing your request. "
            "Please try again in a moment."
        )

    # Persist assistant reply
    await save_chat_message(session_id, user_id, 'assistant', ai_reply)
    return ai_reply


async def remove_session(session_id: str, user_id: str) -> bool:
    return await delete_chat_session(session_id, user_id)


# ── Gemini call ───────────────────────────────────────────────────────────────

async def _call_gemini(
    user_message: str,
    history: List[Dict],
    user_id: str,
    analysis_id: Optional[str],
) -> str:
    """Make a multi-turn Gemini chat call and return the text response."""
    _ensure_configured()
    import google.generativeai as genai

    # Build system instruction — base + full resume context
    system_instruction = _BASE_SYSTEM_PROMPT
    target_aid = analysis_id or 'latest'
    
    analysis = await get_analysis_by_id(target_aid, user_id)
    if analysis:
        system_instruction += '\n\n' + _build_resume_context_prompt(analysis)

    model = genai.GenerativeModel(
        model_name=GEMINI_MODEL,
        system_instruction=system_instruction,
        generation_config=genai.types.GenerationConfig(
            temperature=0.7,
            max_output_tokens=1024,
        ),
    )

    chat = model.start_chat(history=history)
    response = chat.send_message(user_message)
    return response.text.strip()
