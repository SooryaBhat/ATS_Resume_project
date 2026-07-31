"""
schemas.py — All Pydantic request/response models for TalentMatch AI API.

Organised by feature area:
  1. Core Analysis
  2. Authentication & Profile
  3. Dashboard
  4. History
  5. Chat / AI Assistant
  6. Job Descriptions & Matching
  7. Skill Gap Roadmap
  8. Resume Comparison
  9. Resume Tailoring
  10. Reports
  11. Notifications & Activity
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel


# ══════════════════════════════════════════════════════════════════════════════
# 1. Core Analysis Models
# ══════════════════════════════════════════════════════════════════════════════

class ComponentScores(BaseModel):
    formatting: float
    keywords: float
    content: float
    skill_validation: float
    ats_compatibility: float


class JDComparison(BaseModel):
    match_percentage: float = 0.0
    semantic_similarity: float = 0.0
    matching_skills: List[str] = []
    missing_skills: List[str] = []
    matched_keywords: List[str] = []
    missing_keywords: List[str] = []
    skills_gap: List[str] = []


class SkillValidationDetails(BaseModel):
    validated: List[Dict[str, Any]] = []       # [{'skill': str, 'projects': [str]}]
    unvalidated: List[str] = []                # ['Flask', 'A/B Testing', ...]
    total: int = 0
    validated_count: int = 0
    validation_pct: float = 0.0


class IssueDetail(BaseModel):
    issue_title: str
    severity_level: str
    ats_impact: str
    explanation: str
    where_it_appears: str
    how_to_fix: str
    action_items: List[str] = []
    example_improvement: str = ""


class AnalysisResponse(BaseModel):
    # ── Primary structured fields ──────────────────────────────────────────
    component_scores: ComponentScores
    issues_summary: List[str]
    detailed_feedback: List[IssueDetail]
    jd_match_analysis: Optional[JDComparison] = None
    skill_validation_details: Optional[SkillValidationDetails] = None

    # ── Flat convenience fields (backward-compatible) ──────────────────────
    ats_score: float
    job_title: str = ""
    keyword_match: float = 0.0
    resume_jd_similarity: float = 0.0
    match_percentage: float = 0.0
    matching_skills: List[str] = []
    missing_skills: List[str] = []
    missing_keywords: List[str] = []
    matched_keywords: List[str] = []
    suggestions: List[str] = []
    strengths: List[str] = []
    critical_issues: List[str] = []
    skills: List[str] = []
    jd_comparison: Optional[JDComparison] = None
    warnings: List[str] = []
    interpretation: str = ""

    # ── Recommendation engine output ──────────────────────────────────────
    recommendations: List[Dict[str, Any]] = []


# ══════════════════════════════════════════════════════════════════════════════
# 2. Authentication & Profile
# ══════════════════════════════════════════════════════════════════════════════

class ProfileResponse(BaseModel):
    id: str
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    target_role: str = "Software Engineer"
    primary_tech_stack: List[str] = []
    plan: str = "free"
    scans_used: int = 0
    scans_limit: int = 30
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ProfileUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    target_role: Optional[str] = None
    primary_tech_stack: Optional[List[str]] = None
    avatar_url: Optional[str] = None


# ══════════════════════════════════════════════════════════════════════════════
# 3. Dashboard
# ══════════════════════════════════════════════════════════════════════════════

class ScoreTrendPoint(BaseModel):
    label: str          # e.g. "Resume v1.0", or filename
    score: float
    date: str


class DashboardStats(BaseModel):
    avg_ats_score: float = 0.0
    health_index: float = 0.0
    scans_used: int = 0
    scans_limit: int = 30
    top_match_pct: float = 0.0
    total_analyses: int = 0
    score_trend: List[ScoreTrendPoint] = []
    latest_component_scores: Optional[Dict[str, float]] = None
    latest_ats_score: Optional[float] = None
    improvement_pct: float = 0.0   # change vs previous scan


# ══════════════════════════════════════════════════════════════════════════════
# 4. History (extended)
# ══════════════════════════════════════════════════════════════════════════════

class HistoryItem(BaseModel):
    id: str
    filename: str
    job_title: str = ""
    ats_score: float
    keyword_match: float = 0.0
    matched_keywords: List[str] = []
    missing_keywords: List[str] = []
    created_at: str
    component_scores: Dict[str, float] = {}
    recommendations: List[Dict[str, Any]] = []


class HistoryItemDetail(HistoryItem):
    """Full analysis with all nested fields — for single-item fetch."""
    issues_summary: List[str] = []
    detailed_feedback: List[Dict[str, Any]] = []
    jd_match_analysis: Optional[Dict[str, Any]] = None
    skill_validation_details: Optional[Dict[str, Any]] = None
    strengths: List[str] = []
    interpretation: str = ""
    skills: List[str] = []


class HistoryUpdateRequest(BaseModel):
    job_title: Optional[str] = None
    filename: Optional[str] = None     # label rename


class BulkDeleteRequest(BaseModel):
    ids: List[str]


# ══════════════════════════════════════════════════════════════════════════════
# 5. AI Chat / Resume Assistant
# ══════════════════════════════════════════════════════════════════════════════

class ChatSessionCreate(BaseModel):
    title: Optional[str] = "New AI Resume Session"
    analysis_id: Optional[str] = None   # attach resume context


class ChatSessionResponse(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str
    analysis_id: Optional[str] = None


class ChatMessageRequest(BaseModel):
    message: str
    analysis_id: Optional[str] = None   # optional — provides context if not set at session level


class ChatMessageResponse(BaseModel):
    id: str
    role: str           # 'user' or 'assistant'
    content: str
    created_at: str


class ChatSessionWithMessages(BaseModel):
    session: ChatSessionResponse
    messages: List[ChatMessageResponse]


# ══════════════════════════════════════════════════════════════════════════════
# 6. Job Descriptions & JD Matching
# ══════════════════════════════════════════════════════════════════════════════

class JobDescriptionCreate(BaseModel):
    company_name: str
    job_title: str
    jd_text: str


class JobDescriptionResponse(BaseModel):
    id: str
    company_name: str
    job_title: str
    jd_text: str
    created_at: str
    last_match_score: Optional[float] = None
    last_matched_at: Optional[str] = None


class JDMatchRequest(BaseModel):
    analysis_id: str     # which resume analysis to compare against


class JDMatchResult(BaseModel):
    id: str
    jd_id: str
    analysis_id: str
    company_name: str
    job_title: str
    match_percentage: float
    semantic_similarity: float
    matched_keywords: List[str]
    missing_keywords: List[str]
    skills_gap: List[str]
    created_at: str


# ══════════════════════════════════════════════════════════════════════════════
# 7. Skill Gap Roadmap
# ══════════════════════════════════════════════════════════════════════════════

class RoadmapStep(BaseModel):
    step: str
    resource: Optional[str] = None


class SkillRoadmapItem(BaseModel):
    id: str
    skill_name: str
    category: str = "General"
    priority: str = "Medium"         # Critical / High / Medium / Low
    estimated_hours: str = "10 Hours"
    status: str = "Not Started"      # Not Started / In Progress / Completed
    roadmap_steps: List[str] = []
    analysis_id: Optional[str] = None
    created_at: str


class SkillRoadmapUpdateRequest(BaseModel):
    status: Optional[str] = None     # "Not Started" | "In Progress" | "Completed"
    estimated_hours: Optional[str] = None


class RoadmapGenerateRequest(BaseModel):
    analysis_id: str


# ══════════════════════════════════════════════════════════════════════════════
# 8. Resume Comparison
# ══════════════════════════════════════════════════════════════════════════════

class ComparisonEntry(BaseModel):
    filename: str
    ats_score: float
    component_scores: Dict[str, float]
    matched_keywords: List[str]
    missing_keywords: List[str]
    skills_count: int
    verdict: str


class ComparisonResponse(BaseModel):
    id: str
    name: str
    entries: List[ComparisonEntry]
    winner_filename: str
    created_at: str


# ══════════════════════════════════════════════════════════════════════════════
# 9. Resume Tailoring
# ══════════════════════════════════════════════════════════════════════════════

class TailorRequest(BaseModel):
    analysis_id: str
    jd_id: str


class TailoringSuggestion(BaseModel):
    section: str              # "summary" | "experience" | "skills"
    original: str
    improved: str
    explanation: str
    keywords_added: List[str] = []


class TailoringResponse(BaseModel):
    analysis_id: str
    jd_id: str
    company_name: str
    job_title: str
    suggestions: List[TailoringSuggestion]
    summary_rewrite: str = ""
    new_keywords_to_add: List[str] = []


# ══════════════════════════════════════════════════════════════════════════════
# 10. Reports
# ══════════════════════════════════════════════════════════════════════════════

class ReportResponse(BaseModel):
    id: str
    analysis_id: Optional[str] = None
    filename: str
    storage_path: str
    created_at: str


# ══════════════════════════════════════════════════════════════════════════════
# 11. Notifications & Activity
# ══════════════════════════════════════════════════════════════════════════════

class NotificationResponse(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    icon: str = "fa-bell"
    type: str = "info"           # info | success | warning | error
    is_read: bool = False
    created_at: str


class ActivityItem(BaseModel):
    id: str
    action: str
    description: Optional[str] = None
    icon: str = "fa-circle-check"
    metadata: Dict[str, Any] = {}
    created_at: str
