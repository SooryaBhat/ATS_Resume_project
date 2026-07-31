"""
routes.py — Complete FastAPI router for TalentMatch AI.

Organised into logical sub-router groups:
  /api/v1/config          Public config
  /api/v1/health          Health check
  /api/v1/analyze-resume  Core analysis (POST)
  /api/v1/history         Analysis CRUD
  /api/v1/auth            Profile management
  /api/v1/dashboard       Aggregated stats
  /api/v1/chat            AI Chat sessions & messages
  /api/v1/job-descriptions JD CRUD + matching
  /api/v1/skill-gap       Roadmap CRUD
  /api/v1/compare         Resume comparison
  /api/v1/tailor          Resume tailoring
  /api/v1/reports         PDF report management
  /api/v1/notifications   Notification & activity feed
  /api/v1/generate-pdf    PDF generation (legacy)
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import Response

from backend.api.auth import get_current_user
from backend.core.config import SUPABASE_URL, SUPABASE_ANON_KEY
from backend.models.schemas import (
    # Core analysis
    AnalysisResponse, ComponentScores, JDComparison, SkillValidationDetails,
    # Profile
    ProfileResponse, ProfileUpdateRequest,
    # Dashboard
    DashboardStats,
    # History
    HistoryUpdateRequest, BulkDeleteRequest,
    # Chat
    ChatSessionCreate, ChatSessionResponse, ChatMessageRequest, ChatMessageResponse,
    # JD
    JobDescriptionCreate, JobDescriptionResponse, JDMatchRequest, JDMatchResult,
    # Skill Gap
    SkillRoadmapItem, SkillRoadmapUpdateRequest, RoadmapGenerateRequest,
    # Comparison
    ComparisonResponse,
    # Tailoring
    TailorRequest, TailoringResponse,
    # Notifications
    NotificationResponse, ActivityItem,
)

from backend.services.nlp_pipeline import is_nlp_loaded, is_embedder_loaded, get_nlp, get_embedder
from backend.services.resume_parser import parse_resume_file
from backend.services.resume_analyzer import analyze_full_resume
from backend.database.supabase_db import (
    save_analysis, get_user_history, delete_analysis,
    get_analysis_by_id, update_analysis_label, bulk_delete_analyses,
    get_user_reports, save_report_record, delete_report,
)
from backend.services.report_generator import generate_html_reports
from backend.services.pdf_export import generate_combined_pdf
from backend.services.profile_service import get_user_profile, update_user_profile, record_scan
from backend.services.dashboard_service import get_dashboard_stats
from backend.services.chat_service import (
    create_session, list_sessions, fetch_session_messages,
    send_message, remove_session,
)
from backend.services.jd_service import (
    create_job_description, list_job_descriptions,
    fetch_job_description, remove_job_description,
    match_analysis_with_jd, list_jd_matches,
)
from backend.services.skill_gap_service import (
    generate_roadmap, fetch_roadmap, set_item_status, remove_roadmap_item,
)
from backend.services.resume_comparison_service import (
    compare_analyses, fetch_comparisons, remove_comparison,
)
from backend.services.tailor_service import tailor_resume
from backend.services.storage_service import upload_pdf_report, download_file
from backend.services.notification_service import (
    fetch_notifications, read_notification, fetch_activity_feed,
    notify_analysis_complete, notify_roadmap_generated,
    notify_jd_matched, notify_pdf_exported,
)

logger = logging.getLogger('ats_resume_scorer')

router = APIRouter(prefix='/api/v1', tags=['TalentMatch AI'])


# ══════════════════════════════════════════════════════════════════════════════
# PUBLIC ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@router.get('/config')
async def get_frontend_config():
    """Return public Supabase config for the frontend Supabase JS SDK."""
    return {
        'supabase_url':      SUPABASE_URL,
        'supabase_anon_key': SUPABASE_ANON_KEY,
    }


@router.get('/health')
async def health_check(request: Request):
    """Confirm models status and API readiness without forcing heavy model load."""
    nlp_loaded = is_nlp_loaded() or getattr(request.app.state, 'nlp', None) is not None
    embedder_loaded = is_embedder_loaded() or getattr(request.app.state, 'embedder', None) is not None
    return {
        'status':          'healthy',
        'nlp_loaded':      nlp_loaded,
        'embedder_loaded': embedder_loaded,
        'version':         '2.0.0',
        'llm':             'gemini-2.5-flash',
    }


# ══════════════════════════════════════════════════════════════════════════════
# RESUME ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════

@router.post('/analyze-resume', response_model=AnalysisResponse)
async def analyze_resume(
    request:         Request,
    resume:          Optional[UploadFile] = File(None, description='Resume file — PDF or DOCX, max 5 MB'),
    resume_text:     str                  = Form('', description='Existing parsed resume text (optional)'),
    job_description: str                  = Form('', description='Job description text (optional)'),
    user_id:         str                  = Depends(get_current_user),
):
    """Parse, score, and analyse a resume. Optionally benchmark against a JD."""
    nlp      = getattr(request.app.state, 'nlp', None) or get_nlp()
    embedder = getattr(request.app.state, 'embedder', None) or get_embedder()


    filename = 'resume'
    target_resume_text = ''

    if resume is not None and resume.filename:
        try:
            file_bytes = await resume.read()
            filename   = resume.filename or 'resume'
            target_resume_text, _metadata = parse_resume_file(file_bytes, filename)
            logger.info(f"Parsed '{filename}': {len(target_resume_text)} chars")
        except Exception as exc:
            logger.error(f'File parsing failed: {exc}')
            raise HTTPException(status_code=422, detail=f'Could not parse resume: {exc}')
    elif resume_text and resume_text.strip():
        target_resume_text = resume_text.strip()
        filename = 'analyzed_resume.pdf'
    else:
        raise HTTPException(
            status_code=422,
            detail='Please select a resume file (PDF/DOCX) or run a resume analysis first.'
        )

    # Phase 2: Full analysis
    try:
        result = analyze_full_resume(
            resume_text=target_resume_text,
            nlp=nlp,
            embedder=embedder,
            job_description=job_description,
        )
        result['filename'] = filename
    except Exception as exc:
        logger.error(f'Analysis pipeline failed: {exc}')
        raise HTTPException(status_code=500, detail=f'Analysis failed: {exc}')

    # Build typed response
    jd_comparison_result = None
    if result.get('jd_comparison'):
        jd_comparison_result = JDComparison(
            match_percentage    = round(float(result['jd_comparison'].get('match_percentage',    0.0)), 1),
            semantic_similarity = round(float(result['jd_comparison'].get('semantic_similarity', 0.0)), 3),
            matched_keywords    = result['jd_comparison'].get('matched_keywords', [])[:20],
            missing_keywords    = result['jd_comparison'].get('missing_keywords', [])[:15],
            skills_gap          = result['jd_comparison'].get('skills_gap',       [])[:10],
        )

    svd_raw = result.get('skill_validation_details') or {}
    skill_val_details = SkillValidationDetails(
        validated       = svd_raw.get('validated',       []),
        unvalidated     = svd_raw.get('unvalidated',     []),
        total           = svd_raw.get('total',           0),
        validated_count = svd_raw.get('validated_count', 0),
        validation_pct  = svd_raw.get('validation_pct',  0.0),
    )

    response = AnalysisResponse(
        component_scores         = ComponentScores(**result['component_scores']),
        issues_summary           = result['issues_summary'],
        detailed_feedback        = result.get('detailed_feedback', []),
        jd_match_analysis        = jd_comparison_result,
        skill_validation_details = skill_val_details,
        ats_score                = result['ats_score'],
        keyword_match            = jd_comparison_result.match_percentage if jd_comparison_result else 0.0,
        missing_keywords         = result.get('missing_keywords', []),
        matched_keywords         = result.get('matched_keywords', []),
        skills                   = list(result.get('skills', [])[:20]),
        jd_comparison            = jd_comparison_result,
        interpretation           = result.get('interpretation', ''),
        strengths                = result.get('strengths', []),
        recommendations          = result.get('recommendations', []),
    )

    # Persist analysis (non-blocking)
    try:
        save_result = await save_analysis(user_id, filename, result)
        analysis_id = save_result.get('id')
    except Exception as exc:
        logger.warning(f'History save failed (non-blocking): {exc}')
        analysis_id = None

    # Fire-and-forget: record scan + notifications
    try:
        await record_scan(user_id)
        await notify_analysis_complete(user_id, filename, result['ats_score'])
    except Exception:
        pass

    return response


# ══════════════════════════════════════════════════════════════════════════════
# ANALYSIS HISTORY
# ══════════════════════════════════════════════════════════════════════════════

@router.get('/history')
async def get_history(user_id: str = Depends(get_current_user)):
    """List all analyses for the current user, newest first."""
    try:
        return await get_user_history(user_id)
    except Exception as exc:
        logger.error(f'History fetch failed: {exc}')
        raise HTTPException(status_code=500, detail=f'Could not load history: {exc}')


@router.get('/history/{analysis_id}')
async def get_history_item(
    analysis_id: str,
    user_id: str = Depends(get_current_user),
):
    """Fetch a single full analysis result with all nested fields."""
    item = await get_analysis_by_id(analysis_id, user_id)
    if not item:
        raise HTTPException(status_code=404, detail='Analysis not found.')
    return item


@router.patch('/history/{analysis_id}')
async def update_history_item(
    analysis_id: str,
    body:    HistoryUpdateRequest,
    user_id: str = Depends(get_current_user),
):
    """Rename the job_title label on a history entry."""
    if not body.job_title:
        raise HTTPException(status_code=422, detail='job_title is required.')
    ok = await update_analysis_label(analysis_id, user_id, body.job_title)
    if not ok:
        raise HTTPException(status_code=404, detail='Analysis not found or update failed.')
    return {'status': 'updated', 'id': analysis_id}


@router.delete('/history/{analysis_id}')
async def delete_history_entry(
    analysis_id: str,
    user_id: str = Depends(get_current_user),
):
    """Delete one analysis from the user's history."""
    ok = await delete_analysis(analysis_id, user_id)
    if not ok:
        raise HTTPException(status_code=404, detail='Analysis not found or not owned by user.')
    return {'status': 'deleted', 'id': analysis_id}


@router.delete('/history')
async def bulk_delete_history(
    body:    BulkDeleteRequest,
    user_id: str = Depends(get_current_user),
):
    """Delete multiple analyses by ID."""
    if not body.ids:
        raise HTTPException(status_code=422, detail='ids list cannot be empty.')
    deleted = await bulk_delete_analyses(body.ids, user_id)
    return {'status': 'deleted', 'count': deleted}


# ══════════════════════════════════════════════════════════════════════════════
# PDF GENERATION & REPORTS
# ══════════════════════════════════════════════════════════════════════════════

@router.post('/generate-pdf')
async def generate_pdf(
    data:    AnalysisResponse,
    user_id: str = Depends(get_current_user),
):
    """Generate a multi-page PDF report from analysis data and optionally persist it."""
    try:
        pdf_bytes = generate_combined_pdf(data.model_dump())
    except Exception as exc:
        logger.error(f'PDF generation failed: {exc}')
        raise HTTPException(status_code=500, detail=f'PDF generation failed: {exc}')

    # Persist PDF to storage (non-blocking)
    try:
        filename     = 'talentmatch_report.pdf'
        storage_path = await upload_pdf_report(user_id, pdf_bytes, filename)
        if storage_path:
            await save_report_record(user_id, None, filename, storage_path, len(pdf_bytes))
            await notify_pdf_exported(user_id, filename)
    except Exception:
        pass

    return Response(
        content    = pdf_bytes,
        media_type = 'application/pdf',
        headers    = {'Content-Disposition': 'attachment; filename=talentmatch_report.pdf'},
    )


@router.get('/history/{analysis_id}/pdf')
async def generate_history_pdf(
    analysis_id: str,
    user_id:     str = Depends(get_current_user),
):
    """Re-generate the PDF for a saved history entry."""
    item = await get_analysis_by_id(analysis_id, user_id)
    if not item:
        raise HTTPException(status_code=404, detail='Analysis not found.')

    try:
        pdf_bytes = generate_combined_pdf(item)
    except Exception as exc:
        logger.error(f'History PDF generation failed: {exc}')
        raise HTTPException(status_code=500, detail=f'PDF generation failed: {exc}')

    # Persist (non-blocking)
    try:
        fname        = f'talentmatch_report_{analysis_id}.pdf'
        storage_path = await upload_pdf_report(user_id, pdf_bytes, fname)
        if storage_path:
            await save_report_record(user_id, analysis_id, fname, storage_path, len(pdf_bytes))
    except Exception:
        pass

    return Response(
        content    = pdf_bytes,
        media_type = 'application/pdf',
        headers    = {'Content-Disposition': f'attachment; filename=talentmatch_report_{analysis_id}.pdf'},
    )


@router.get('/reports')
async def list_reports(user_id: str = Depends(get_current_user)):
    """List all stored PDF reports for the current user."""
    rows = await get_user_reports(user_id)
    return [
        {
            'id':          str(r.get('id')),
            'analysis_id': str(r.get('analysis_id')) if r.get('analysis_id') else None,
            'filename':    r.get('filename', ''),
            'storage_path': r.get('storage_path', ''),
            'created_at':  r.get('created_at', ''),
        }
        for r in rows
    ]


@router.delete('/reports/{report_id}')
async def delete_report_entry(
    report_id: str,
    user_id:   str = Depends(get_current_user),
):
    ok = await delete_report(report_id, user_id)
    if not ok:
        raise HTTPException(status_code=404, detail='Report not found.')
    return {'status': 'deleted', 'id': report_id}


# ══════════════════════════════════════════════════════════════════════════════
# AUTH / PROFILE
# ══════════════════════════════════════════════════════════════════════════════

@router.get('/auth/me')
async def get_me(user_id: str = Depends(get_current_user)):
    """Return the current user's profile from public.profiles."""
    profile = await get_user_profile(user_id)
    if not profile:
        # Profile may not exist yet (e.g. trigger didn't fire) — return minimal stub
        return {
            'id': user_id,
            'full_name': '',
            'avatar_url': '',
            'target_role': 'Software Engineer',
            'primary_tech_stack': [],
            'plan': 'free',
            'scans_used': 0,
            'scans_limit': 30,
        }
    return profile


@router.patch('/auth/profile')
async def update_profile(
    body:    ProfileUpdateRequest,
    user_id: str = Depends(get_current_user),
):
    """Update the user's target role, tech stack, full name, or avatar."""
    ok = await update_user_profile(
        user_id,
        full_name           = body.full_name,
        target_role         = body.target_role,
        primary_tech_stack  = body.primary_tech_stack,
        avatar_url          = body.avatar_url,
    )
    if not ok:
        raise HTTPException(status_code=500, detail='Profile update failed.')
    return {'status': 'updated'}


# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD STATS
# ══════════════════════════════════════════════════════════════════════════════

@router.get('/dashboard/stats')
async def dashboard_stats(user_id: str = Depends(get_current_user)):
    """Aggregated dashboard statistics computed from the user's analysis history."""
    try:
        stats = await get_dashboard_stats(user_id)
        return stats
    except Exception as exc:
        logger.error(f'Dashboard stats failed: {exc}')
        raise HTTPException(status_code=500, detail=f'Could not compute dashboard stats: {exc}')


# ══════════════════════════════════════════════════════════════════════════════
# AI CHAT ASSISTANT
# ══════════════════════════════════════════════════════════════════════════════

@router.post('/chat/sessions')
async def create_chat_session_route(
    body:    ChatSessionCreate,
    user_id: str = Depends(get_current_user),
):
    """Create a new AI chat session, optionally linked to an analysis for resume context."""
    session = await create_session(
        user_id     = user_id,
        title       = body.title or 'New AI Resume Session',
        analysis_id = body.analysis_id,
    )
    if not session:
        raise HTTPException(status_code=500, detail='Failed to create chat session.')
    return session


@router.get('/chat/sessions')
async def list_chat_sessions(user_id: str = Depends(get_current_user)):
    """List all chat sessions for the current user."""
    return await list_sessions(user_id)


@router.get('/chat/sessions/{session_id}/messages')
async def get_session_messages(
    session_id: str,
    user_id:    str = Depends(get_current_user),
):
    """Fetch all messages in a chat session."""
    messages = await fetch_session_messages(session_id, user_id)
    return messages


@router.post('/chat/sessions/{session_id}/message')
async def send_chat_message(
    session_id: str,
    body:       ChatMessageRequest,
    user_id:    str = Depends(get_current_user),
):
    """
    Send a message to the AI assistant.
    Returns the assistant's Gemini-powered reply.
    """
    if not body.message or not body.message.strip():
        raise HTTPException(status_code=422, detail='message cannot be empty.')
    try:
        reply = await send_message(
            session_id  = session_id,
            user_id     = user_id,
            user_message= body.message.strip(),
            analysis_id = body.analysis_id,
        )
        return {'role': 'assistant', 'content': reply}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.error(f'Chat send failed: {exc}')
        raise HTTPException(status_code=500, detail=f'Chat error: {exc}')


@router.delete('/chat/sessions/{session_id}')
async def delete_chat_session_route(
    session_id: str,
    user_id:    str = Depends(get_current_user),
):
    """Delete a chat session and all its messages."""
    ok = await remove_session(session_id, user_id)
    if not ok:
        raise HTTPException(status_code=404, detail='Session not found.')
    return {'status': 'deleted', 'id': session_id}


# ══════════════════════════════════════════════════════════════════════════════
# JOB DESCRIPTIONS
# ══════════════════════════════════════════════════════════════════════════════

@router.post('/job-descriptions')
async def create_jd(
    body:    JobDescriptionCreate,
    user_id: str = Depends(get_current_user),
):
    """Save a new job description for repeated matching."""
    try:
        jd = await create_job_description(
            user_id      = user_id,
            company_name = body.company_name,
            job_title    = body.job_title,
            jd_text      = body.jd_text,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    if not jd:
        raise HTTPException(status_code=500, detail='Failed to save job description.')
    return jd


@router.get('/job-descriptions')
async def list_jds(user_id: str = Depends(get_current_user)):
    """List all saved job descriptions for the current user."""
    return await list_job_descriptions(user_id)


@router.get('/job-descriptions/matches')
async def get_jd_matches_route(user_id: str = Depends(get_current_user)):
    """List all past JD match results for the current user."""
    return await list_jd_matches(user_id)


@router.get('/job-descriptions/{jd_id}')
async def get_jd(
    jd_id:   str,
    user_id: str = Depends(get_current_user),
):
    jd = await fetch_job_description(jd_id, user_id)
    if not jd:
        raise HTTPException(status_code=404, detail='Job description not found.')
    return jd


@router.delete('/job-descriptions/{jd_id}')
async def delete_jd(
    jd_id:   str,
    user_id: str = Depends(get_current_user),
):
    ok = await remove_job_description(jd_id, user_id)
    if not ok:
        raise HTTPException(status_code=404, detail='Job description not found.')
    return {'status': 'deleted', 'id': jd_id}


@router.post('/job-descriptions/{jd_id}/match')
async def match_jd(
    jd_id:   str,
    body:    JDMatchRequest,
    request: Request,
    user_id: str = Depends(get_current_user),
):
    """Match a saved JD against a stored resume analysis."""
    try:
        nlp      = getattr(request.app.state, 'nlp', None) or get_nlp()
        embedder = getattr(request.app.state, 'embedder', None) or get_embedder()
        result = await match_analysis_with_jd(
            analysis_id = body.analysis_id,
            jd_id       = jd_id,
            user_id     = user_id,
            nlp         = nlp,
            embedder    = embedder,
        )

        # Fire-and-forget notification
        try:
            await notify_jd_matched(
                user_id, result['company_name'], result['job_title'], result['match_percentage']
            )
        except Exception:
            pass
        return result
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.error(f'JD match failed: {exc}')
        raise HTTPException(status_code=500, detail=f'JD matching failed: {exc}')




# ══════════════════════════════════════════════════════════════════════════════
# SKILL GAP ROADMAP
# ══════════════════════════════════════════════════════════════════════════════

@router.post('/skill-gap/generate')
async def generate_skill_gap_roadmap(
    body:    RoadmapGenerateRequest,
    user_id: str = Depends(get_current_user),
):
    """Generate an AI-powered skill learning roadmap from a resume analysis."""
    try:
        items = await generate_roadmap(user_id, body.analysis_id)
        # Fire-and-forget notification
        try:
            await notify_roadmap_generated(user_id, len(items))
        except Exception:
            pass
        return {'status': 'generated', 'count': len(items), 'items': items}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.error(f'Roadmap generation failed: {exc}')
        raise HTTPException(status_code=500, detail=f'Roadmap generation failed: {exc}')


@router.get('/skill-gap')
async def get_skill_gap_roadmap(user_id: str = Depends(get_current_user)):
    """Fetch all skill roadmap items for the current user."""
    items = await fetch_roadmap(user_id)
    return items


@router.patch('/skill-gap/{roadmap_id}')
async def update_skill_gap_item(
    roadmap_id: str,
    body:       SkillRoadmapUpdateRequest,
    user_id:    str = Depends(get_current_user),
):
    """Update the status (or estimated hours) of a roadmap item."""
    if not body.status and not body.estimated_hours:
        raise HTTPException(status_code=422, detail='Provide status or estimated_hours to update.')
    try:
        if body.status:
            ok = await set_item_status(roadmap_id, user_id, body.status)
        else:
            from backend.database.supabase_db import update_roadmap_item
            ok = await update_roadmap_item(roadmap_id, user_id, {'estimated_hours': body.estimated_hours})
        if not ok:
            raise HTTPException(status_code=404, detail='Roadmap item not found.')
        return {'status': 'updated', 'id': roadmap_id}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.delete('/skill-gap/{roadmap_id}')
async def delete_skill_gap_item(
    roadmap_id: str,
    user_id:    str = Depends(get_current_user),
):
    ok = await remove_roadmap_item(roadmap_id, user_id)
    if not ok:
        raise HTTPException(status_code=404, detail='Roadmap item not found.')
    return {'status': 'deleted', 'id': roadmap_id}


# ══════════════════════════════════════════════════════════════════════════════
# RESUME COMPARISON
# ══════════════════════════════════════════════════════════════════════════════

@router.post('/compare')
async def compare_resumes(
    analysis_ids: List[str] = Body(..., embed=True),
    name:         str        = Body('Resume Comparison', embed=True),
    user_id:      str        = Depends(get_current_user),
):
    """
    Compare 2–5 existing analysis records side-by-side.
    Pass a list of analysis IDs already stored in the database.
    """
    try:
        result = await compare_analyses(analysis_ids, user_id, name)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        logger.error(f'Comparison failed: {exc}')
        raise HTTPException(status_code=500, detail=f'Comparison failed: {exc}')


@router.get('/compare')
async def list_comparisons_route(user_id: str = Depends(get_current_user)):
    """List all past comparison sessions."""
    return await fetch_comparisons(user_id)


@router.delete('/compare/{comparison_id}')
async def delete_comparison_route(
    comparison_id: str,
    user_id:       str = Depends(get_current_user),
):
    ok = await remove_comparison(comparison_id, user_id)
    if not ok:
        raise HTTPException(status_code=404, detail='Comparison not found.')
    return {'status': 'deleted', 'id': comparison_id}


# ══════════════════════════════════════════════════════════════════════════════
# RESUME TAILORING
# ══════════════════════════════════════════════════════════════════════════════

@router.post('/tailor')
async def tailor_resume_route(
    body:    TailorRequest,
    user_id: str = Depends(get_current_user),
):
    """
    Generate Gemini-powered tailoring suggestions for a resume vs a specific JD.
    Requires both an analysis_id and a jd_id already saved in the database.
    """
    try:
        result = await tailor_resume(body.analysis_id, body.jd_id, user_id)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.error(f'Tailoring failed: {exc}')
        raise HTTPException(status_code=500, detail=f'Tailoring failed: {exc}')


# ══════════════════════════════════════════════════════════════════════════════
# NOTIFICATIONS & ACTIVITY
# ══════════════════════════════════════════════════════════════════════════════

@router.get('/notifications')
async def get_notifications_route(
    limit:   int = Query(20, ge=1, le=50),
    user_id: str = Depends(get_current_user),
):
    """Fetch the user's latest notifications."""
    return await fetch_notifications(user_id, limit)


@router.patch('/notifications/{notif_id}/read')
async def mark_notification_read_route(
    notif_id: str,
    user_id:  str = Depends(get_current_user),
):
    ok = await read_notification(notif_id, user_id)
    if not ok:
        raise HTTPException(status_code=404, detail='Notification not found.')
    return {'status': 'read', 'id': notif_id}


@router.get('/activity')
async def get_activity_route(
    limit:   int = Query(10, ge=1, le=50),
    user_id: str = Depends(get_current_user),
):
    """Fetch the user's recent activity feed."""
    return await fetch_activity_feed(user_id, limit)


# ══════════════════════════════════════════════════════════════════════════════
# PDF REPORT EXPORT
# ══════════════════════════════════════════════════════════════════════════════

@router.get('/analyses/{analysis_id}/pdf')
@router.get('/reports/{analysis_id}/pdf')
async def download_analysis_pdf(
    analysis_id: str,
    user_id:     str = Depends(get_current_user),
):
    """Generate and stream a professional PDF report for an analysis record."""
    from backend.services.pdf_export import build_pdf_report

    analysis = await get_analysis_by_id(analysis_id, user_id)
    if not analysis:
        raise HTTPException(status_code=404, detail='Analysis record not found.')

    try:
        pdf_bytes = build_pdf_report(analysis)
        clean_fn = (analysis.get('filename') or 'resume').replace(' ', '_')
        filename = f"talentmatch_report_{clean_fn}.pdf"
        return Response(
            content=pdf_bytes,
            media_type='application/pdf',
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"',
                'Access-Control-Expose-Headers': 'Content-Disposition',
            }
        )
    except Exception as exc:
        logger.error(f'PDF generation failed: {exc}')
        raise HTTPException(status_code=500, detail=f'PDF report generation failed: {exc}')