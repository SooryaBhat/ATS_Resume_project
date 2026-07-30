"""
notification_service.py — Convenience wrappers for notification & activity creation.

Provides typed helper functions called from route handlers after key actions
(analysis complete, roadmap generated, JD matched, PDF exported, etc.).
"""

import logging
from typing import Any, Dict, Optional

from backend.database.supabase_db import (
    get_notifications,
    create_notification,
    mark_notification_read,
    log_activity,
    get_activity_feed,
)

logger = logging.getLogger('ats_resume_scorer')


# ── Notification fetch & update ───────────────────────────────────────────────

async def fetch_notifications(user_id: str, limit: int = 20):
    rows = await get_notifications(user_id, limit)
    return [_format_notif(r) for r in rows]


async def read_notification(notif_id: str, user_id: str) -> bool:
    return await mark_notification_read(notif_id, user_id)


def _format_notif(doc: Dict) -> Dict:
    return {
        'id':          str(doc.get('id')),
        'title':       doc.get('title', ''),
        'description': doc.get('description', ''),
        'icon':        doc.get('icon', 'fa-bell'),
        'type':        doc.get('type', 'info'),
        'is_read':     bool(doc.get('is_read', False)),
        'created_at':  doc.get('created_at', ''),
    }


# ── Activity feed ─────────────────────────────────────────────────────────────

async def fetch_activity_feed(user_id: str, limit: int = 10):
    rows = await get_activity_feed(user_id, limit)
    return [_format_activity(r) for r in rows]


def _format_activity(doc: Dict) -> Dict:
    return {
        'id':          str(doc.get('id')),
        'action':      doc.get('action', ''),
        'description': doc.get('description', ''),
        'icon':        doc.get('icon', 'fa-circle-check'),
        'metadata':    doc.get('metadata', {}),
        'created_at':  doc.get('created_at', ''),
    }


# ── Typed notification creators ───────────────────────────────────────────────

async def notify_analysis_complete(user_id: str, filename: str, score: float) -> None:
    await create_notification(
        user_id,
        title=f'Resume Analyzed: {filename}',
        description=f'Your resume scored {score}/100 — view detailed breakdown now.',
        icon='fa-circle-check',
        ntype='success',
    )
    await log_activity(
        user_id,
        action='analyzed_resume',
        description=f'Analyzed {filename} — ATS Score: {score}/100',
        icon='fa-file-circle-check',
        metadata={'filename': filename, 'score': score},
    )


async def notify_roadmap_generated(user_id: str, skill_count: int) -> None:
    await create_notification(
        user_id,
        title='Skill Roadmap Generated',
        description=f'{skill_count} skill gap items added to your learning roadmap.',
        icon='fa-road',
        ntype='info',
    )
    await log_activity(
        user_id,
        action='generated_roadmap',
        description=f'Generated skill roadmap with {skill_count} items',
        icon='fa-road',
        metadata={'skill_count': skill_count},
    )


async def notify_jd_matched(user_id: str, company: str, role: str, match_pct: float) -> None:
    await create_notification(
        user_id,
        title=f'JD Match: {role} at {company}',
        description=f'Resume matched at {match_pct}% against the job description.',
        icon='fa-bullseye',
        ntype='success' if match_pct >= 80 else 'info',
    )
    await log_activity(
        user_id,
        action='matched_jd',
        description=f'Matched resume against {role} @ {company} — {match_pct}% match',
        icon='fa-bullseye',
        metadata={'company': company, 'role': role, 'match_pct': match_pct},
    )


async def notify_pdf_exported(user_id: str, filename: str) -> None:
    await create_notification(
        user_id,
        title='PDF Report Ready',
        description=f'{filename} is ready for download.',
        icon='fa-file-pdf',
        ntype='info',
    )
    await log_activity(
        user_id,
        action='exported_pdf',
        description=f'Exported PDF report: {filename}',
        icon='fa-file-pdf',
        metadata={'filename': filename},
    )
