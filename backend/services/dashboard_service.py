"""
dashboard_service.py — Computes live dashboard stats from the analyses table.

Aggregates:
  - Average ATS score across all user analyses
  - Score improvement trend (latest N scans)
  - Health index (% of analyses scoring >= 80)
  - Latest component breakdown
  - Top JD match percentage
  - Scan quota from profile
"""

import logging
from typing import Any, Dict, List, Optional

from backend.database.supabase_db import get_user_history, get_profile

logger = logging.getLogger('ats_resume_scorer')


async def get_dashboard_stats(user_id: str) -> Dict[str, Any]:
    """
    Return aggregated dashboard statistics for the given user.
    All computation is done in Python over the fetched history rows —
    no raw SQL aggregation needed.
    """
    history   = await get_user_history(user_id)
    profile   = await get_profile(user_id)

    total     = len(history)
    if total == 0:
        return _empty_stats(profile)

    scores = [item.get('ats_score', 0.0) for item in history]

    avg_score   = round(sum(scores) / total, 1)
    health_idx  = round(sum(1 for s in scores if s >= 80) / total * 100, 1)

    # Improvement vs previous scan
    improvement = 0.0
    if len(scores) >= 2:
        improvement = round(scores[0] - scores[1], 1)   # newest - previous

    # Score trend — last 10 scans (oldest first for chart)
    trend_items = list(reversed(history[:10]))
    score_trend = [
        {
            'label': _short_label(item.get('filename', ''), item.get('job_title', '')),
            'score': item.get('ats_score', 0.0),
            'date':  item.get('created_at', ''),
        }
        for item in trend_items
    ]

    # Latest component scores & ATS score
    latest             = history[0]
    latest_components  = latest.get('component_scores', {}) or {}
    latest_ats         = latest.get('ats_score', 0.0)

    # Top JD match — scan all analyses for the highest keyword_match
    top_match = max((item.get('keyword_match', 0.0) for item in history), default=0.0)

    scans_used  = profile.get('scans_used', total) if profile else total
    scans_limit = profile.get('scans_limit', 30)   if profile else 30

    return {
        'avg_ats_score':          avg_score,
        'health_index':           health_idx,
        'scans_used':             scans_used,
        'scans_limit':            scans_limit,
        'top_match_pct':          round(top_match, 1),
        'total_analyses':         total,
        'score_trend':            score_trend,
        'latest_component_scores': _normalise_components(latest_components),
        'latest_ats_score':       latest_ats,
        'improvement_pct':        improvement,
    }


def _empty_stats(profile: Optional[Dict]) -> Dict[str, Any]:
    return {
        'avg_ats_score':          0.0,
        'health_index':           0.0,
        'scans_used':             profile.get('scans_used', 0)  if profile else 0,
        'scans_limit':            profile.get('scans_limit', 30) if profile else 30,
        'top_match_pct':          0.0,
        'total_analyses':         0,
        'score_trend':            [],
        'latest_component_scores': None,
        'latest_ats_score':       None,
        'improvement_pct':        0.0,
    }


def _short_label(filename: str, job_title: str) -> str:
    """Create a short chart label from filename or job_title."""
    if job_title and job_title.strip():
        words = job_title.strip().split()
        return ' '.join(words[:3])
    name = filename.replace('.pdf', '').replace('.docx', '').replace('.doc', '')
    parts = name.split('_')
    return '_'.join(parts[:2]) if len(parts) >= 2 else name[:20]


def _normalise_components(raw: Dict) -> Dict[str, float]:
    """Ensure all 5 component keys are present as floats."""
    keys = ['formatting', 'keywords', 'content', 'skill_validation', 'ats_compatibility']
    return {k: float(raw.get(k, 0.0)) for k in keys}
