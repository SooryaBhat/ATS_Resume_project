"""
skill_gap_service.py — AI-generated skill roadmap service using Gemini.

Generates a personalised learning roadmap by:
  1. Extracting unvalidated skills + missing JD keywords from an analysis
  2. Calling Gemini to generate structured skill roadmap items
  3. Persisting roadmap items to public.skill_gap_roadmaps
  4. Supporting status updates (Not Started → In Progress → Completed)
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional

from backend.database.supabase_db import (
    get_analysis_by_id,
    save_skill_roadmap_items,
    get_skill_roadmap,
    update_roadmap_item,
    delete_roadmap_item,
)

logger = logging.getLogger('ats_resume_scorer')

GEMINI_MODEL = 'gemini-2.5-flash'

_ROADMAP_SYSTEM_PROMPT = """You are a world-class technical career coach generating personalised skill 
learning roadmaps for software engineers. Given a list of skill gaps, output a JSON array of roadmap 
items — one per skill — that provides a realistic, actionable learning path.

Output ONLY valid JSON with this exact schema (no markdown, no explanation):
[
  {
    "skill_name": "Kubernetes",
    "category": "DevOps",
    "priority": "Critical",
    "estimated_hours": "15 Hours",
    "status": "Not Started",
    "roadmap_steps": [
      "Step 1: Understand container orchestration concepts and Kubernetes architecture",
      "Step 2: Set up a local cluster with minikube and deploy a simple FastAPI app",
      "Step 3: Learn Services, Ingress, ConfigMaps, and Secrets",
      "Step 4: Write a Helm chart for a microservice deployment"
    ]
  }
]

Priority must be one of: Critical / High / Medium / Low
Category must be one of: DevOps / Backend / Frontend / AI/ML / Database / API Architecture / Cloud / General
Estimated hours should be a realistic estimate string like "8 Hours" or "20 Hours".
Provide 3–5 concrete roadmap_steps per skill."""


def _extract_skill_gaps(analysis: Dict) -> List[str]:
    """Pull skill gaps from analysis — unvalidated skills + missing keywords."""
    analysis_result = analysis.get('analysis_result', {})
    skill_details   = analysis_result.get('skill_validation_details') or {}
    unvalidated     = skill_details.get('unvalidated', [])
    missing_kw      = analysis_result.get('missing_keywords', [])

    # Combine and deduplicate
    all_gaps = list(dict.fromkeys(unvalidated + missing_kw))
    return all_gaps[:15]   # cap at 15 items for Gemini token efficiency


async def generate_roadmap(user_id: str, analysis_id: str) -> List[Dict[str, Any]]:
    """
    Generate a personalised skill roadmap for the user based on an analysis.
    Clears any existing roadmap items for the same analysis before inserting new ones.
    Returns the list of created roadmap item dicts.
    """
    analysis = await get_analysis_by_id(analysis_id, user_id)
    if not analysis:
        raise ValueError(f'Analysis {analysis_id} not found or not owned by user.')

    skill_gaps = _extract_skill_gaps(analysis)
    if not skill_gaps:
        logger.info(f'No skill gaps found for analysis={analysis_id} — returning empty roadmap')
        return []

    # Call Gemini to generate roadmap
    try:
        roadmap_items = await _call_gemini_roadmap(skill_gaps)
    except Exception as exc:
        logger.error(f'Gemini roadmap generation failed: {exc}')
        # Fallback: generate basic items without Gemini
        roadmap_items = _generate_fallback_roadmap(skill_gaps)

    # Persist to DB
    saved_ids = await save_skill_roadmap_items(user_id, analysis_id, roadmap_items)
    logger.info(f'Saved {len(saved_ids)} roadmap items for user={user_id}')

    # Return items with IDs attached
    saved = await get_skill_roadmap(user_id)
    # Filter to items from this analysis
    return [
        _format_roadmap_item(item)
        for item in saved
        if str(item.get('analysis_id')) == str(analysis_id)
    ]


async def fetch_roadmap(user_id: str) -> List[Dict[str, Any]]:
    """Fetch all skill roadmap items for a user."""
    items = await get_skill_roadmap(user_id)
    return [_format_roadmap_item(item) for item in items]


async def set_item_status(roadmap_id: str, user_id: str, status: str) -> bool:
    """Update the status of a roadmap item."""
    valid_statuses = {'Not Started', 'In Progress', 'Completed'}
    if status not in valid_statuses:
        raise ValueError(f'Invalid status. Must be one of: {valid_statuses}')
    updates: Dict[str, Any] = {'status': status}
    if status == 'Completed':
        from datetime import datetime, timezone
        updates['completed_at'] = datetime.now(timezone.utc).isoformat()
    return await update_roadmap_item(roadmap_id, user_id, updates)


async def remove_roadmap_item(roadmap_id: str, user_id: str) -> bool:
    return await delete_roadmap_item(roadmap_id, user_id)


# ── Internal helpers ──────────────────────────────────────────────────────────

async def _call_gemini_roadmap(skill_gaps: List[str]) -> List[Dict]:
    api_key = os.getenv('GEMINI_API_KEY', '')
    if not api_key:
        raise ValueError('GEMINI_API_KEY not set.')

    import google.generativeai as genai
    genai.configure(api_key=api_key)

    model = genai.GenerativeModel(
        model_name=GEMINI_MODEL,
        system_instruction=_ROADMAP_SYSTEM_PROMPT,
        generation_config=genai.types.GenerationConfig(
            temperature=0.3,
            max_output_tokens=4096,
            response_mime_type='application/json',
        ),
    )

    prompt = (
        f"Generate a personalised skill learning roadmap for the following skill gaps "
        f"identified from a resume analysis:\n\n{', '.join(skill_gaps)}"
    )
    response = model.generate_content(prompt)
    items = json.loads(response.text)
    return items if isinstance(items, list) else []


def _generate_fallback_roadmap(skill_gaps: List[str]) -> List[Dict]:
    """Basic fallback when Gemini is unavailable."""
    return [
        {
            'skill_name':       skill,
            'category':         'General',
            'priority':         'Medium',
            'estimated_hours':  '10 Hours',
            'status':           'Not Started',
            'roadmap_steps':    [
                f'Research {skill} fundamentals and official documentation',
                f'Complete an introductory {skill} course or tutorial',
                f'Build a small project demonstrating {skill} in practice',
            ],
        }
        for skill in skill_gaps
    ]


def _format_roadmap_item(doc: Dict) -> Dict[str, Any]:
    steps = doc.get('roadmap_steps', [])
    if isinstance(steps, str):
        try:
            steps = json.loads(steps)
        except Exception:
            steps = [steps]
    return {
        'id':              str(doc.get('id')),
        'skill_name':      doc.get('skill_name', ''),
        'category':        doc.get('category', 'General'),
        'priority':        doc.get('priority', 'Medium'),
        'estimated_hours': doc.get('estimated_hours', '10 Hours'),
        'status':          doc.get('status', 'Not Started'),
        'roadmap_steps':   steps,
        'analysis_id':     str(doc.get('analysis_id')) if doc.get('analysis_id') else None,
        'created_at':      doc.get('created_at', ''),
    }
