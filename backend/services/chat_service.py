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
    """Build context injection from an analysis record to prime the assistant."""
    ats_score  = analysis.get('ats_score', 0)
    job_title  = analysis.get('job_title', 'Not specified')
    strengths  = analysis.get('strengths', [])
    missing_kw = analysis.get('missing_keywords', [])
    components = analysis.get('component_scores', {})
    issues     = analysis.get('issues_summary', [])

    ctx = f"""
--- RESUME CONTEXT (user's latest analysis) ---
ATS Score: {ats_score}/100
Target Role: {job_title}
Component Scores:
  - Formatting: {components.get('formatting', 0)}/20
  - Keywords: {components.get('keywords', 0)}/25
  - Content Quality: {components.get('content', 0)}/25
  - Skill Validation: {components.get('skill_validation', 0)}/15
  - ATS Compatibility: {components.get('ats_compatibility', 0)}/15

Strengths: {', '.join(strengths[:4]) if strengths else 'None identified'}
Missing Keywords: {', '.join(missing_kw[:10]) if missing_kw else 'None'}
Top Issues: {'; '.join(issues[:3]) if issues else 'None'}
--- END RESUME CONTEXT ---

Use the above context to give personalised, specific advice when helping the user."""
    return ctx


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

    # Resolve analysis_id (session-level wins, then per-message, then None)
    ctx_analysis_id = session.get('analysis_id') or analysis_id

    # Build Gemini history from DB messages (excluding the message we just saved)
    # Gemini format: [{'role': 'user'|'model', 'parts': [text]}]
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

    # Build system instruction — base + optional resume context
    system_instruction = _BASE_SYSTEM_PROMPT
    if analysis_id:
        analysis = await get_analysis_by_id(analysis_id, user_id)
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
