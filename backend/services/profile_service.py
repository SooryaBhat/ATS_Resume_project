"""
profile_service.py — User profile management for TalentMatch AI.

Wraps the Supabase DB layer for profile reads/writes and scan-count enforcement.
"""

import logging
from typing import Any, Dict, List, Optional

from backend.database.supabase_db import (
    get_profile,
    update_profile,
    increment_scans_used,
)

logger = logging.getLogger('ats_resume_scorer')


async def get_user_profile(user_id: str) -> Optional[Dict[str, Any]]:
    """Return the user's profile row, or None if not found."""
    return await get_profile(user_id)


async def update_user_profile(user_id: str, full_name: Optional[str] = None,
                               target_role: Optional[str] = None,
                               primary_tech_stack: Optional[List[str]] = None,
                               avatar_url: Optional[str] = None) -> bool:
    """
    Update editable profile fields.
    Only non-None values are sent to Supabase to allow partial updates.
    primary_tech_stack is stored as a Postgres TEXT[] array.
    """
    updates: Dict[str, Any] = {}

    if full_name is not None:
        updates['full_name'] = full_name.strip()

    if target_role is not None:
        updates['target_role'] = target_role.strip()

    if primary_tech_stack is not None:
        # Accept both List[str] and comma-separated string
        if isinstance(primary_tech_stack, str):
            primary_tech_stack = [s.strip() for s in primary_tech_stack.split(',') if s.strip()]
        updates['primary_tech_stack'] = primary_tech_stack

    if avatar_url is not None:
        updates['avatar_url'] = avatar_url

    if not updates:
        return True   # nothing to do

    ok = await update_profile(user_id, updates)
    if ok:
        logger.info(f'Profile updated for user={user_id}: fields={list(updates.keys())}')
    else:
        logger.warning(f'Profile update failed for user={user_id}')
    return ok


async def record_scan(user_id: str) -> None:
    """
    Increment the user's scans_used counter after a successful analysis.
    This is fire-and-forget — failure should not block the analysis response.
    """
    try:
        await increment_scans_used(user_id)
    except Exception as exc:
        logger.warning(f'increment_scans_used failed for user={user_id}: {exc}')


async def check_scan_limit(user_id: str) -> Dict[str, Any]:
    """
    Returns { allowed: bool, scans_used: int, scans_limit: int }.
    'allowed' is True unless the user is on a paid plan AND has exhausted their quota.
    Free-plan users are always allowed (limit enforcement is lenient for now).
    """
    profile = await get_profile(user_id)
    if not profile:
        return {'allowed': True, 'scans_used': 0, 'scans_limit': 30}

    scans_used  = profile.get('scans_used', 0)
    scans_limit = profile.get('scans_limit', 30)
    plan        = profile.get('plan', 'free')

    # Enforce limits only for paid plans (free plan is unlimited for now)
    if plan != 'free' and scans_used >= scans_limit:
        return {'allowed': False, 'scans_used': scans_used, 'scans_limit': scans_limit}

    return {'allowed': True, 'scans_used': scans_used, 'scans_limit': scans_limit}
