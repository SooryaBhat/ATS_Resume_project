"""
resume_comparison_service.py — Multi-resume differential comparison engine.

Accepts 2–5 resume analysis results and produces a side-by-side comparison
matrix with scoring differentials, skill overlaps, and a winner recommendation.

Does NOT re-run the full analysis pipeline — it works on already-scored
analyses fetched from the database, which makes it fast.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from backend.database.supabase_db import (
    get_analysis_by_id,
    save_comparison,
)

logger = logging.getLogger('ats_resume_scorer')


async def compare_analyses(
    analysis_ids: List[str],
    user_id: str,
    comparison_name: str = 'Resume Comparison',
) -> Dict[str, Any]:
    """
    Fetch each analysis from DB, build the comparison matrix, persist the
    result, and return a ComparisonResponse-compatible dict.
    """
    if len(analysis_ids) < 2:
        raise ValueError('At least 2 analysis IDs are required for comparison.')
    if len(analysis_ids) > 5:
        raise ValueError('Maximum 5 analyses can be compared at once.')

    # Fetch all analyses
    entries: List[Dict] = []
    for aid in analysis_ids:
        analysis = await get_analysis_by_id(aid, user_id)
        if analysis:
            entries.append(analysis)

    if len(entries) < 2:
        raise ValueError('Could not retrieve enough analyses. Ensure all IDs belong to you.')

    # Build comparison matrix
    comparison_entries, winner = _build_matrix(entries)

    # Persist
    result_payload = {'entries': comparison_entries, 'winner': winner}
    comparison_id = await save_comparison(
        user_id, comparison_name, analysis_ids, result_payload, winner
    )

    return {
        'id':              comparison_id or 'local',
        'name':            comparison_name,
        'entries':         comparison_entries,
        'winner_filename': winner,
        'created_at':      _now_str(),
    }


async def fetch_comparisons(user_id: str) -> List[Dict]:
    from backend.database.supabase_db import get_comparisons
    return await get_comparisons(user_id)


async def remove_comparison(comparison_id: str, user_id: str) -> bool:
    from backend.database.supabase_db import delete_comparison
    return await delete_comparison(comparison_id, user_id)


# ── Internal helpers ──────────────────────────────────────────────────────────

def _build_matrix(entries: List[Dict]) -> Tuple[List[Dict], str]:
    """Build a structured list of comparison entries and determine winner."""
    formatted: List[Dict] = []
    best_score  = -1.0
    winner_name = ''

    for entry in entries:
        ar      = entry.get('analysis_result', {}) or {}
        score   = float(entry.get('ats_score', 0))
        fname   = entry.get('filename', 'Unknown')
        comps   = entry.get('component_scores', {}) or ar.get('component_scores', {})
        matched = entry.get('matched_keywords', []) or ar.get('matched_keywords', [])
        missing = entry.get('missing_keywords', []) or ar.get('missing_keywords', [])

        # Estimate skills count — count unique items in matched_keywords as proxy
        skills_count = len(set(matched))

        # Generate verdict
        verdict = _make_verdict(score, comps)

        formatted.append({
            'filename':        fname,
            'ats_score':       score,
            'component_scores': _normalise_components(comps),
            'matched_keywords': matched[:15],
            'missing_keywords': missing[:10],
            'skills_count':    skills_count,
            'verdict':         verdict,
        })

        if score > best_score:
            best_score  = score
            winner_name = fname

    return formatted, winner_name


def _make_verdict(score: float, components: Dict) -> str:
    if score >= 90:
        return 'Top ATS Grade — Ready to Apply'
    if score >= 80:
        return 'Excellent — Minor Tweaks Needed'
    if score >= 70:
        return 'Good — Keyword Boost Recommended'
    if score >= 60:
        return 'Average — Significant Improvements Needed'
    return 'Needs Work — Major Revision Required'


def _normalise_components(raw: Dict) -> Dict[str, float]:
    keys = ['formatting', 'keywords', 'content', 'skill_validation', 'ats_compatibility']
    return {k: float(raw.get(k, 0.0)) for k in keys}


def _now_str() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()
