"""
supabase_db.py — Complete Supabase REST API database layer for TalentMatch AI.

Covers all tables:
  - profiles
  - analyses
  - job_descriptions / jd_matches
  - skill_gap_roadmaps
  - chat_sessions / chat_messages
  - notifications
  - activity_log
  - reports
  - comparisons
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import httpx

from backend.core.config import SUPABASE_KEY, SUPABASE_URL

logger = logging.getLogger('ats_resume_scorer')

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get_headers() -> Dict[str, str]:
    """Build standard service-role headers for Supabase REST API."""
    return {
        'apikey':        SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}',
        'Content-Type':  'application/json',
        'Prefer':        'return=representation',
    }


def _json_default(o: Any) -> str:
    if isinstance(o, datetime):
        return o.isoformat()
    return str(o)


def _rest(table: str) -> str:
    return f"{SUPABASE_URL.rstrip('/')}/rest/v1/{table}"


def _configured() -> bool:
    return bool(SUPABASE_URL and SUPABASE_KEY)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ══════════════════════════════════════════════════════════════════════════════
# ANALYSES
# ══════════════════════════════════════════════════════════════════════════════

# In-memory analysis cache for instant lookup & unconfigured fallback
_MEMORY_ANALYSES: Dict[str, Dict[str, Any]] = {}
_LAST_USER_ANALYSIS: Dict[str, str] = {}

_ANALYSES_DB_COLUMNS = {
    'id', 'user_id', 'filename', 'job_title', 'ats_score', 'keyword_match',
    'component_scores', 'matched_keywords', 'missing_keywords', 'issues_summary',
    'detailed_feedback', 'jd_match_analysis', 'skill_validation_details',
    'recommendations', 'strengths', 'interpretation', 'created_at'
}


async def save_analysis(
    user_id: str,
    analysis_result: Any,
    filename: Any = 'resume',
) -> Dict[str, Any]:
    """Save a full analysis result to public.analyses and in-memory cache."""
    # Handle flexible positional argument order: (user_id, filename, analysis_result) or (user_id, analysis_result, filename)
    if isinstance(analysis_result, str) and isinstance(filename, dict):
        filename, analysis_result = analysis_result, filename

    if not isinstance(analysis_result, dict):
        analysis_result = {}

    if not isinstance(filename, str) or not filename.strip():
        filename = 'resume'

    serializable = json.loads(json.dumps(analysis_result, default=_json_default))
    jd_data = (
        serializable.get('jd_comparison')
        or serializable.get('jd_match_analysis')
        or {}
    )
    job_title = serializable.get('job_title', '') or jd_data.get('job_title', '') or ''
    generated_id = str(uuid.uuid4())

    payload = {
        'id':                       generated_id,
        'user_id':                  user_id,
        'filename':                 filename,
        'job_title':                job_title,
        'ats_score':                serializable.get('ats_score', 0.0),
        'keyword_match':            serializable.get('keyword_match', 0.0),
        'component_scores':         serializable.get('component_scores', {}),
        'matched_keywords':         serializable.get('matched_keywords', []),
        'missing_keywords':         serializable.get('missing_keywords', []),
        'issues_summary':           serializable.get('issues_summary', []),
        'detailed_feedback':        serializable.get('detailed_feedback', []),
        'jd_match_analysis':        serializable.get('jd_match_analysis', {}),
        'skill_validation_details': serializable.get('skill_validation_details', {}),
        'recommendations':          serializable.get('recommendations', []),
        'strengths':                serializable.get('strengths', []),
        'interpretation':           serializable.get('interpretation', ''),
        'resume_text':              serializable.get('resume_text', ''),
        'skills':                   serializable.get('skills', []),
        'job_description':          serializable.get('job_description', ''),
        'jd_comparison':            serializable.get('jd_comparison', {}),
        'matching_skills':          serializable.get('matching_skills', []),
        'missing_skills':           serializable.get('missing_skills', []),
        'match_percentage':         serializable.get('match_percentage', 0.0),
        'resume_jd_similarity':    serializable.get('resume_jd_similarity', 0.0),
        'created_at':               _now(),
        'analysis_result':          serializable,
    }

    # Always cache in memory
    _MEMORY_ANALYSES[generated_id] = payload
    _LAST_USER_ANALYSIS[user_id]   = generated_id

    if not _configured():
        logger.info(f'Saved analysis in memory cache: id={generated_id}')
        return {'status': 'saved', 'id': generated_id}

    try:
        db_payload = {k: v for k, v in payload.items() if k in _ANALYSES_DB_COLUMNS}
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(_rest('analyses'), json=db_payload, headers=_get_headers())
            if resp.status_code in (200, 201):
                rows = resp.json()
                inserted_id = rows[0].get('id') if isinstance(rows, list) and rows else generated_id
                _MEMORY_ANALYSES[inserted_id] = payload
                _LAST_USER_ANALYSIS[user_id]   = inserted_id
                logger.info(f'Saved analysis to DB id={inserted_id}')
                return {'status': 'saved', 'id': inserted_id}
            logger.warning(f'Insert failed ({resp.status_code}): {resp.text} — using memory ID')
            return {'status': 'saved', 'id': generated_id}
    except Exception as exc:
        logger.warning(f'save_analysis DB exception: {exc} — using memory ID')
        return {'status': 'saved', 'id': generated_id}


async def update_analysis_context(analysis_id: str, user_id: str, updates: Dict[str, Any]) -> bool:
    """Enrich an existing analysis record with JD match and comparison details."""
    target_id = analysis_id
    if not target_id or target_id == 'latest':
        target_id = _LAST_USER_ANALYSIS.get(user_id)

    if not target_id:
        return False

    if target_id in _MEMORY_ANALYSES:
        item = _MEMORY_ANALYSES[target_id]
        item.update(updates)
        if 'analysis_result' in item and isinstance(item['analysis_result'], dict):
            item['analysis_result'].update(updates)
        else:
            item['analysis_result'] = dict(item)

    if _configured():
        try:
            url = f"{_rest('analyses')}?id=eq.{target_id}&user_id=eq.{user_id}"
            db_updates = {k: v for k, v in updates.items() if k in _ANALYSES_DB_COLUMNS}
            if db_updates:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    await client.patch(url, json=db_updates, headers=_get_headers())
        except Exception as exc:
            logger.warning(f'update_analysis_context DB warning: {exc}')

    return True


async def get_user_history(user_id: str) -> List[Dict[str, Any]]:
    """Fetch all analyses for a user, newest first."""
    if not _configured():
        user_mem = [
            _format_history_item(v) for v in _MEMORY_ANALYSES.values()
            if v.get('user_id') == user_id
        ]
        return sorted(user_mem, key=lambda x: x.get('created_at', ''), reverse=True)
    url = f"{_rest('analyses')}?user_id=eq.{user_id}&select=*&order=created_at.desc"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=_get_headers())
            if resp.status_code != 200:
                logger.error(f'History query failed ({resp.status_code}): {resp.text}')
                return []
            docs = resp.json()
            return [_format_history_item(doc) for doc in docs]
    except Exception as exc:
        logger.error(f'get_user_history exception: {exc}')
        return []


async def get_analysis_by_id(analysis_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a single analysis by ID or 'latest' (with ownership check)."""
    target_id = analysis_id
    if not target_id or target_id == 'latest':
        target_id = _LAST_USER_ANALYSIS.get(user_id)

    if target_id and target_id in _MEMORY_ANALYSES:
        return _format_history_item(_MEMORY_ANALYSES[target_id], full=True)

    if not _configured():
        return None

    if not target_id or target_id == 'latest':
        url = f"{_rest('analyses')}?user_id=eq.{user_id}&select=*&order=created_at.desc&limit=1"
    else:
        url = f"{_rest('analyses')}?id=eq.{target_id}&user_id=eq.{user_id}&select=*"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=_get_headers())
            if resp.status_code != 200 or not resp.json():
                return None
            doc = resp.json()[0]
            formatted = _format_history_item(doc, full=True)
            if doc.get('id'):
                _MEMORY_ANALYSES[doc.get('id')] = doc
                _LAST_USER_ANALYSIS[user_id] = doc.get('id')
            return formatted
    except Exception as exc:
        logger.error(f'get_analysis_by_id exception: {exc}')
        return None


async def delete_analysis(analysis_id: str, user_id: str) -> bool:
    """Delete one analysis owned by user_id."""
    if not _configured():
        return False
    url = f"{_rest('analyses')}?id=eq.{analysis_id}&user_id=eq.{user_id}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.delete(url, headers=_get_headers())
            return resp.status_code in (200, 204)
    except Exception as exc:
        logger.error(f'delete_analysis exception: {exc}')
        return False


async def bulk_delete_analyses(ids: List[str], user_id: str) -> int:
    """Delete multiple analyses. Returns count deleted."""
    deleted = 0
    for aid in ids:
        if await delete_analysis(aid, user_id):
            deleted += 1
    return deleted


async def update_analysis_label(analysis_id: str, user_id: str, job_title: str) -> bool:
    """Rename the job_title label on an analysis."""
    if not _configured():
        return False
    url = f"{_rest('analyses')}?id=eq.{analysis_id}&user_id=eq.{user_id}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.patch(url, json={'job_title': job_title}, headers=_get_headers())
            return resp.status_code in (200, 204)
    except Exception as exc:
        logger.error(f'update_analysis_label exception: {exc}')
        return False


def _format_history_item(doc: Dict, full: bool = False) -> Dict[str, Any]:
    res = doc.get('analysis_result') or {}
    base = {
        'id':                       str(doc.get('id')),
        'filename':                 doc.get('filename', 'resume'),
        'resume_name':              doc.get('filename', 'resume'),
        'job_title':                doc.get('job_title', ''),
        'ats_score':                float(doc.get('ats_score', 0.0)),
        'keyword_match':            float(doc.get('keyword_match', 0.0)),
        'missing_keywords':         doc.get('missing_keywords', []),
        'matched_keywords':         doc.get('matched_keywords', []),
        'date':                     doc.get('created_at', ''),
        'created_at':               doc.get('created_at', ''),
        'component_scores':         doc.get('component_scores', {}),
        'recommendations':          doc.get('recommendations', []),
        'resume_text':              doc.get('resume_text') or res.get('resume_text', ''),
        'skills':                   doc.get('skills') or res.get('skills', []),
        'job_description':          doc.get('job_description') or res.get('job_description', ''),
        'jd_comparison':            doc.get('jd_comparison') or res.get('jd_comparison', {}),
        'matching_skills':          doc.get('matching_skills') or res.get('matching_skills', []),
        'missing_skills':           doc.get('missing_skills') or res.get('missing_skills', []),
        'match_percentage':         float(doc.get('match_percentage') or res.get('match_percentage', 0.0)),
        'resume_jd_similarity':    float(doc.get('resume_jd_similarity') or res.get('resume_jd_similarity', 0.0)),
        'analysis_result': {
            'ats_score':                doc.get('ats_score', 0.0),
            'job_title':                doc.get('job_title', ''),
            'component_scores':         doc.get('component_scores', {}),
            'issues_summary':           doc.get('issues_summary', []),
            'detailed_feedback':        doc.get('detailed_feedback', []),
            'matched_keywords':         doc.get('matched_keywords', []),
            'missing_keywords':         doc.get('missing_keywords', []),
            'recommendations':          doc.get('recommendations', []),
            'strengths':                doc.get('strengths', []),
            'interpretation':           doc.get('interpretation', ''),
            'skill_validation_details': doc.get('skill_validation_details', {}),
            'resume_text':              doc.get('resume_text') or res.get('resume_text', ''),
            'skills':                   doc.get('skills') or res.get('skills', []),
            'job_description':          doc.get('job_description') or res.get('job_description', ''),
            'jd_comparison':            doc.get('jd_comparison') or res.get('jd_comparison', {}),
            'matching_skills':          doc.get('matching_skills') or res.get('matching_skills', []),
            'missing_skills':           doc.get('missing_skills') or res.get('missing_skills', []),
            'match_percentage':         float(doc.get('match_percentage') or res.get('match_percentage', 0.0)),
            'resume_jd_similarity':    float(doc.get('resume_jd_similarity') or res.get('resume_jd_similarity', 0.0)),
        },
    }
    if full:
        base.update({
            'issues_summary':           doc.get('issues_summary', []),
            'detailed_feedback':        doc.get('detailed_feedback', []),
            'jd_match_analysis':        doc.get('jd_match_analysis', {}),
            'skill_validation_details': doc.get('skill_validation_details', {}),
            'strengths':                doc.get('strengths', []),
            'interpretation':           doc.get('interpretation', ''),
        })
    return base


# ══════════════════════════════════════════════════════════════════════════════
# PROFILES
# ══════════════════════════════════════════════════════════════════════════════

async def get_profile(user_id: str) -> Optional[Dict[str, Any]]:
    if not _configured():
        return None
    url = f"{_rest('profiles')}?id=eq.{user_id}&select=*"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=_get_headers())
            if resp.status_code != 200 or not resp.json():
                return None
            doc = resp.json()[0]
            stack = doc.get('primary_tech_stack') or []
            return {
                'id':                str(doc.get('id')),
                'full_name':         doc.get('full_name', ''),
                'avatar_url':        doc.get('avatar_url', ''),
                'target_role':       doc.get('target_role', 'Software Engineer'),
                'primary_tech_stack': stack if isinstance(stack, list) else [],
                'plan':              doc.get('plan', 'free'),
                'scans_used':        int(doc.get('scans_used', 0)),
                'scans_limit':       int(doc.get('scans_limit', 30)),
                'created_at':        doc.get('created_at', ''),
                'updated_at':        doc.get('updated_at', ''),
            }
    except Exception as exc:
        logger.error(f'get_profile exception: {exc}')
        return None


async def update_profile(user_id: str, updates: Dict[str, Any]) -> bool:
    if not _configured():
        return False
    payload = {k: v for k, v in updates.items() if v is not None}
    payload['updated_at'] = _now()
    url = f"{_rest('profiles')}?id=eq.{user_id}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.patch(url, json=payload, headers=_get_headers())
            return resp.status_code in (200, 204)
    except Exception as exc:
        logger.error(f'update_profile exception: {exc}')
        return False


async def increment_scans_used(user_id: str) -> None:
    """Increment the scans_used counter for the user. Best-effort, non-blocking."""
    if not _configured():
        return
    # Fetch current count first
    profile = await get_profile(user_id)
    if not profile:
        return
    new_count = profile.get('scans_used', 0) + 1
    await update_profile(user_id, {'scans_used': new_count})


# ══════════════════════════════════════════════════════════════════════════════
# JOB DESCRIPTIONS
# ══════════════════════════════════════════════════════════════════════════════

async def save_job_description(user_id: str, company_name: str, job_title: str, jd_text: str) -> Optional[Dict]:
    if not _configured():
        return None
    payload = {
        'user_id':      user_id,
        'company_name': company_name,
        'job_title':    job_title,
        'jd_text':      jd_text,
        'created_at':   _now(),
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(_rest('job_descriptions'), json=payload, headers=_get_headers())
            if resp.status_code in (200, 201):
                rows = resp.json()
                return rows[0] if rows else None
            logger.error(f'save_jd failed ({resp.status_code}): {resp.text}')
            return None
    except Exception as exc:
        logger.error(f'save_job_description exception: {exc}')
        return None


async def get_job_descriptions(user_id: str) -> List[Dict]:
    if not _configured():
        return []
    url = f"{_rest('job_descriptions')}?user_id=eq.{user_id}&select=*&order=created_at.desc"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=_get_headers())
            if resp.status_code != 200:
                return []
            return resp.json()
    except Exception as exc:
        logger.error(f'get_job_descriptions exception: {exc}')
        return []


async def get_job_description(jd_id: str, user_id: str) -> Optional[Dict]:
    if not _configured():
        return None
    url = f"{_rest('job_descriptions')}?id=eq.{jd_id}&user_id=eq.{user_id}&select=*"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=_get_headers())
            if resp.status_code != 200 or not resp.json():
                return None
            return resp.json()[0]
    except Exception as exc:
        logger.error(f'get_job_description exception: {exc}')
        return None


async def delete_job_description(jd_id: str, user_id: str) -> bool:
    if not _configured():
        return False
    url = f"{_rest('job_descriptions')}?id=eq.{jd_id}&user_id=eq.{user_id}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.delete(url, headers=_get_headers())
            return resp.status_code in (200, 204)
    except Exception as exc:
        logger.error(f'delete_job_description exception: {exc}')
        return False


async def save_jd_match(user_id: str, jd_id: str, analysis_id: str, match_result: Dict) -> Optional[str]:
    if not _configured():
        return None
    payload = {
        'user_id':      user_id,
        'jd_id':        jd_id,
        'analysis_id':  analysis_id,
        'match_result': match_result,
        'created_at':   _now(),
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(_rest('jd_matches'), json=payload, headers=_get_headers())
            if resp.status_code in (200, 201) and resp.json():
                inserted_id = resp.json()[0].get('id')
                # Update last_match_score on job_descriptions
                await _update_jd_last_match(jd_id, match_result.get('match_percentage', 0))
                return inserted_id
            return None
    except Exception as exc:
        logger.error(f'save_jd_match exception: {exc}')
        return None


async def get_jd_matches(user_id: str) -> List[Dict]:
    if not _configured():
        return []
    url = f"{_rest('jd_matches')}?user_id=eq.{user_id}&select=*&order=created_at.desc"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=_get_headers())
            return resp.json() if resp.status_code == 200 else []
    except Exception as exc:
        logger.error(f'get_jd_matches exception: {exc}')
        return []


async def _update_jd_last_match(jd_id: str, score: float) -> None:
    if not _configured():
        return
    url = f"{_rest('job_descriptions')}?id=eq.{jd_id}"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.patch(
                url,
                json={'last_match_score': round(score, 2), 'last_matched_at': _now()},
                headers=_get_headers(),
            )
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════════════════════
# SKILL GAP ROADMAPS
# ══════════════════════════════════════════════════════════════════════════════

async def save_skill_roadmap_items(user_id: str, analysis_id: str, items: List[Dict]) -> List[str]:
    """Bulk-insert skill roadmap items. Returns list of inserted IDs."""
    if not _configured() or not items:
        return []
    ids = []
    for item in items:
        payload = {
            'user_id':        user_id,
            'analysis_id':    analysis_id,
            'skill_name':     item.get('skill_name', item.get('skill', '')),
            'category':       item.get('category', 'General'),
            'priority':       item.get('priority', 'Medium'),
            'estimated_hours': item.get('estimated_hours', '10 Hours'),
            'status':         item.get('status', 'Not Started'),
            'roadmap_steps':  item.get('roadmap_steps', item.get('roadmap', [])),
            'created_at':     _now(),
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(_rest('skill_gap_roadmaps'), json=payload, headers=_get_headers())
                if resp.status_code in (200, 201) and resp.json():
                    ids.append(resp.json()[0].get('id'))
        except Exception as exc:
            logger.error(f'save_skill_roadmap_item exception: {exc}')
    return ids


async def get_skill_roadmap(user_id: str) -> List[Dict]:
    if not _configured():
        return []
    url = f"{_rest('skill_gap_roadmaps')}?user_id=eq.{user_id}&select=*&order=created_at.desc"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=_get_headers())
            return resp.json() if resp.status_code == 200 else []
    except Exception as exc:
        logger.error(f'get_skill_roadmap exception: {exc}')
        return []


async def update_roadmap_item(roadmap_id: str, user_id: str, updates: Dict) -> bool:
    if not _configured():
        return False
    url = f"{_rest('skill_gap_roadmaps')}?id=eq.{roadmap_id}&user_id=eq.{user_id}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.patch(url, json=updates, headers=_get_headers())
            return resp.status_code in (200, 204)
    except Exception as exc:
        logger.error(f'update_roadmap_item exception: {exc}')
        return False


async def delete_roadmap_item(roadmap_id: str, user_id: str) -> bool:
    if not _configured():
        return False
    url = f"{_rest('skill_gap_roadmaps')}?id=eq.{roadmap_id}&user_id=eq.{user_id}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.delete(url, headers=_get_headers())
            return resp.status_code in (200, 204)
    except Exception as exc:
        logger.error(f'delete_roadmap_item exception: {exc}')
        return False


# ══════════════════════════════════════════════════════════════════════════════
# CHAT SESSIONS & MESSAGES
# ══════════════════════════════════════════════════════════════════════════════

# In-memory chat stores for unconfigured / fallback mode
_MEMORY_CHAT_SESSIONS: Dict[str, Dict[str, Any]] = {}
_MEMORY_CHAT_MESSAGES: Dict[str, List[Dict[str, Any]]] = {}


async def create_chat_session(user_id: str, title: str, analysis_id: Optional[str] = None) -> Optional[Dict]:
    session_id = str(uuid.uuid4())
    now_str = _now()
    fallback_session = {
        'id':          session_id,
        'user_id':     user_id,
        'title':       title,
        'analysis_id': analysis_id,
        'created_at':  now_str,
        'updated_at':  now_str,
    }
    _MEMORY_CHAT_SESSIONS[session_id] = fallback_session

    if not _configured():
        return fallback_session

    payload = {
        'id':          session_id,
        'user_id':     user_id,
        'title':       title,
        'created_at':  now_str,
        'updated_at':  now_str,
    }
    if analysis_id:
        payload['analysis_id'] = analysis_id

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(_rest('chat_sessions'), json=payload, headers=_get_headers())
            if resp.status_code in (200, 201) and resp.json():
                res_obj = resp.json()[0]
                _MEMORY_CHAT_SESSIONS[res_obj.get('id', session_id)] = res_obj
                return res_obj
            logger.warning(f"Supabase chat_sessions insert returned status {resp.status_code} — using memory fallback")
            return fallback_session
    except Exception as exc:
        logger.error(f'create_chat_session exception: {exc} — using memory fallback')
        return fallback_session


async def get_chat_sessions(user_id: str) -> List[Dict]:
    if _configured():
        url = f"{_rest('chat_sessions')}?user_id=eq.{user_id}&select=*&order=updated_at.desc"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers=_get_headers())
                if resp.status_code == 200:
                    return resp.json()
        except Exception as exc:
            logger.error(f'get_chat_sessions exception: {exc}')

    user_sessions = [s for s in _MEMORY_CHAT_SESSIONS.values() if s.get('user_id') == user_id]
    return sorted(user_sessions, key=lambda x: x.get('updated_at', ''), reverse=True)


async def get_chat_session(session_id: str, user_id: str) -> Optional[Dict]:
    if _configured():
        url = f"{_rest('chat_sessions')}?id=eq.{session_id}&user_id=eq.{user_id}&select=*"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers=_get_headers())
                if resp.status_code == 200 and resp.json():
                    return resp.json()[0]
        except Exception as exc:
            logger.error(f'get_chat_session exception: {exc}')

    session = _MEMORY_CHAT_SESSIONS.get(session_id)
    if session and session.get('user_id') == user_id:
        return session
    return None


async def save_chat_message(session_id: str, user_id: str, role: str, content: str) -> Optional[Dict]:
    msg_id = str(uuid.uuid4())
    now_str = _now()
    fallback_msg = {
        'id':         msg_id,
        'session_id': session_id,
        'user_id':    user_id,
        'role':       role,
        'content':    content,
        'created_at': now_str,
    }
    _MEMORY_CHAT_MESSAGES.setdefault(session_id, []).append(fallback_msg)
    if session_id in _MEMORY_CHAT_SESSIONS:
        _MEMORY_CHAT_SESSIONS[session_id]['updated_at'] = now_str

    if not _configured():
        return fallback_msg

    payload = {
        'id':         msg_id,
        'session_id': session_id,
        'user_id':    user_id,
        'role':       role,
        'content':    content,
        'created_at': now_str,
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(_rest('chat_messages'), json=payload, headers=_get_headers())
            if resp.status_code in (200, 201) and resp.json():
                await _touch_chat_session(session_id)
                return resp.json()[0]
            return fallback_msg
    except Exception as exc:
        logger.error(f'save_chat_message exception: {exc}')
        return fallback_msg


async def get_chat_messages(session_id: str, user_id: str) -> List[Dict]:
    if _configured():
        url = (
            f"{_rest('chat_messages')}"
            f"?session_id=eq.{session_id}&user_id=eq.{user_id}&select=*&order=created_at.asc"
        )
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers=_get_headers())
                if resp.status_code == 200 and resp.json():
                    return resp.json()
        except Exception as exc:
            logger.error(f'get_chat_messages exception: {exc}')

    return _MEMORY_CHAT_MESSAGES.get(session_id, [])


async def delete_chat_session(session_id: str, user_id: str) -> bool:
    _MEMORY_CHAT_SESSIONS.pop(session_id, None)
    _MEMORY_CHAT_MESSAGES.pop(session_id, None)

    if not _configured():
        return True

    url = f"{_rest('chat_sessions')}?id=eq.{session_id}&user_id=eq.{user_id}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.delete(url, headers=_get_headers())
            return resp.status_code in (200, 204)
    except Exception as exc:
        logger.error(f'delete_chat_session exception: {exc}')
        return True


async def _touch_chat_session(session_id: str) -> None:
    if not _configured():
        return
    url = f"{_rest('chat_sessions')}?id=eq.{session_id}"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.patch(url, json={'updated_at': _now()}, headers=_get_headers())
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════════════════════
# NOTIFICATIONS
# ══════════════════════════════════════════════════════════════════════════════

async def get_notifications(user_id: str, limit: int = 20) -> List[Dict]:
    if not _configured():
        return []
    url = (
        f"{_rest('notifications')}"
        f"?user_id=eq.{user_id}&select=*&order=created_at.desc&limit={limit}"
    )
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=_get_headers())
            return resp.json() if resp.status_code == 200 else []
    except Exception as exc:
        logger.error(f'get_notifications exception: {exc}')
        return []


async def create_notification(user_id: str, title: str, description: str = '', icon: str = 'fa-bell', ntype: str = 'info') -> None:
    """Fire-and-forget notification insert."""
    if not _configured():
        return
    payload = {
        'user_id':     user_id,
        'title':       title,
        'description': description,
        'icon':        icon,
        'type':        ntype,
        'created_at':  _now(),
    }
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(_rest('notifications'), json=payload, headers=_get_headers())
    except Exception:
        pass


async def mark_notification_read(notif_id: str, user_id: str) -> bool:
    if not _configured():
        return False
    url = f"{_rest('notifications')}?id=eq.{notif_id}&user_id=eq.{user_id}"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.patch(url, json={'is_read': True}, headers=_get_headers())
            return resp.status_code in (200, 204)
    except Exception as exc:
        logger.error(f'mark_notification_read exception: {exc}')
        return False


# ══════════════════════════════════════════════════════════════════════════════
# ACTIVITY LOG
# ══════════════════════════════════════════════════════════════════════════════

async def log_activity(user_id: str, action: str, description: str = '', icon: str = 'fa-circle-check', metadata: Optional[Dict] = None) -> None:
    """Fire-and-forget activity log insert."""
    if not _configured():
        return
    payload = {
        'user_id':     user_id,
        'action':      action,
        'description': description,
        'icon':        icon,
        'metadata':    metadata or {},
        'created_at':  _now(),
    }
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(_rest('activity_log'), json=payload, headers=_get_headers())
    except Exception:
        pass


async def get_activity_feed(user_id: str, limit: int = 10) -> List[Dict]:
    if not _configured():
        return []
    url = (
        f"{_rest('activity_log')}"
        f"?user_id=eq.{user_id}&select=*&order=created_at.desc&limit={limit}"
    )
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=_get_headers())
            return resp.json() if resp.status_code == 200 else []
    except Exception as exc:
        logger.error(f'get_activity_feed exception: {exc}')
        return []


# ══════════════════════════════════════════════════════════════════════════════
# COMPARISONS
# ══════════════════════════════════════════════════════════════════════════════

async def save_comparison(user_id: str, name: str, analysis_ids: List[str], result: Dict, winner: str) -> Optional[str]:
    if not _configured():
        return None
    payload = {
        'user_id':           user_id,
        'name':              name,
        'analysis_ids':      analysis_ids,
        'comparison_result': result,
        'winner_filename':   winner,
        'created_at':        _now(),
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(_rest('comparisons'), json=payload, headers=_get_headers())
            if resp.status_code in (200, 201) and resp.json():
                return resp.json()[0].get('id')
            return None
    except Exception as exc:
        logger.error(f'save_comparison exception: {exc}')
        return None


async def get_comparisons(user_id: str) -> List[Dict]:
    if not _configured():
        return []
    url = f"{_rest('comparisons')}?user_id=eq.{user_id}&select=*&order=created_at.desc"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=_get_headers())
            return resp.json() if resp.status_code == 200 else []
    except Exception as exc:
        logger.error(f'get_comparisons exception: {exc}')
        return []


async def delete_comparison(comparison_id: str, user_id: str) -> bool:
    if not _configured():
        return False
    url = f"{_rest('comparisons')}?id=eq.{comparison_id}&user_id=eq.{user_id}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.delete(url, headers=_get_headers())
            return resp.status_code in (200, 204)
    except Exception as exc:
        logger.error(f'delete_comparison exception: {exc}')
        return False


# ══════════════════════════════════════════════════════════════════════════════
# REPORTS
# ══════════════════════════════════════════════════════════════════════════════

async def save_report_record(user_id: str, analysis_id: Optional[str], filename: str, storage_path: str, file_size: int = 0) -> Optional[str]:
    if not _configured():
        return None
    payload = {
        'user_id':        user_id,
        'analysis_id':    analysis_id,
        'filename':       filename,
        'storage_path':   storage_path,
        'file_size_bytes': file_size,
        'created_at':     _now(),
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(_rest('reports'), json=payload, headers=_get_headers())
            if resp.status_code in (200, 201) and resp.json():
                return resp.json()[0].get('id')
            return None
    except Exception as exc:
        logger.error(f'save_report_record exception: {exc}')
        return None


async def get_user_reports(user_id: str) -> List[Dict]:
    if not _configured():
        return []
    url = f"{_rest('reports')}?user_id=eq.{user_id}&select=*&order=created_at.desc"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=_get_headers())
            return resp.json() if resp.status_code == 200 else []
    except Exception as exc:
        logger.error(f'get_user_reports exception: {exc}')
        return []


async def delete_report(report_id: str, user_id: str) -> bool:
    if not _configured():
        return False
    url = f"{_rest('reports')}?id=eq.{report_id}&user_id=eq.{user_id}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.delete(url, headers=_get_headers())
            return resp.status_code in (200, 204)
    except Exception as exc:
        logger.error(f'delete_report exception: {exc}')
        return False
