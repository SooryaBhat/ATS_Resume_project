"""
pdf_export.py — PDF Report Export Engine powered by ReportLab 5.0.

Generates a professional, beautifully formatted PDF report containing:
- Candidate Overview & File Metadata
- Overall ATS Score & Grade Interpretation
- 5-Component ATS Score Breakdown Table
- Extracted Skills
- Target Job Description & JD Alignment (Match %, BERT Cosine Similarity %)
- Matching Skills & Missing Skills Gap
- Matched & Missing Keywords
- Actionable Recommendations & Action Items
"""

import io
import logging
from typing import Any, Dict

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT

logger = logging.getLogger('ats_resume_scorer')


def build_pdf_report(analysis_data: Dict[str, Any]) -> bytes:
    """
    Build a multi-section, publication-quality PDF report from an analysis record.
    Returns binary PDF bytes.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#1E293B'),
        alignment=TA_LEFT,
        spaceAfter=4,
    )
    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#64748B'),
        spaceAfter=12,
    )
    h2_style = ParagraphStyle(
        'SectionH2',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        textColor=colors.HexColor('#0F172A'),
        spaceBefore=12,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13.5,
        textColor=colors.HexColor('#334155'),
        spaceAfter=6,
    )
    bold_body = ParagraphStyle(
        'BoldBody',
        parent=body_style,
        fontName='Helvetica-Bold',
    )

    story = []

    # 1. Header Banner
    story.append(Paragraph("TALENTMATCH AI — ATS RESUME & JOB ALIGNMENT REPORT", title_style))
    story.append(Paragraph("Powered by spaCy NLP, SentenceTransformers BERT Embeddings & scikit-learn", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#3B82F6'), spaceAfter=12))

    # Extract fields from payload
    res = analysis_data.get('analysis_result') or analysis_data
    jd_analysis = res.get('jd_match_analysis') or res.get('jd_comparison') or analysis_data.get('jd_match_analysis') or {}

    filename    = analysis_data.get('filename') or res.get('filename') or 'Uploaded Resume'
    job_title   = res.get('job_title') or analysis_data.get('job_title') or 'Target Career Role'
    ats_score   = float(res.get('ats_score', analysis_data.get('ats_score', 0.0)))
    date_str    = analysis_data.get('created_at') or res.get('created_at') or 'Recent'
    interpretation = res.get('interpretation', 'Parsed resume analysis completed.')

    # Score color code
    score_color = colors.HexColor('#10B981') if ats_score >= 80 else colors.HexColor('#F59E0B') if ats_score >= 60 else colors.HexColor('#EF4444')

    # 2. Candidate Overview Table
    meta_data = [
        [
            Paragraph(f"<b>Candidate File:</b> {filename}", body_style),
            Paragraph(f"<b>Target Role:</b> {job_title}", body_style),
        ],
        [
            Paragraph(f"<b>Analysis Date:</b> {date_str[:10]}", body_style),
            Paragraph(f"<b>Overall ATS Score:</b> <font color='{score_color.hexval()}'><b>{Math_round(ats_score)}/100</b></font>", body_style),
        ],
    ]
    meta_table = Table(meta_data, colWidths=[270, 270])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
        ('PADDING', (0, 0), (-1, -1), 8),
        ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor('#E2E8F0')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 10))

    # Executive Summary Excerpt
    story.append(Paragraph("<b>Executive Summary & Evaluation:</b>", bold_body))
    story.append(Paragraph(interpretation, body_style))
    story.append(Spacer(1, 8))

    # 3. 5-Component ATS Score Breakdown Table
    story.append(Paragraph("5-Component ATS Score Breakdown", h2_style))
    cs = res.get('component_scores') or analysis_data.get('component_scores') or {}

    comp_rows = [
        [Paragraph("<b>Component Evaluation Layer</b>", bold_body), Paragraph("<b>Score Achieved</b>", bold_body), Paragraph("<b>Maximum Points</b>", bold_body), Paragraph("<b>Status</b>", bold_body)],
        [Paragraph("Formatting & Structural Health", body_style), f"{cs.get('formatting', 0)}", "20", _score_badge(cs.get('formatting', 0), 20)],
        [Paragraph("Keywords & Technical Skills", body_style), f"{cs.get('keywords', 0)}", "25", _score_badge(cs.get('keywords', 0), 25)],
        [Paragraph("Content Quality & Impact Metrics", body_style), f"{cs.get('content', 0)}", "25", _score_badge(cs.get('content', 0), 25)],
        [Paragraph("Skill Validation & Context", body_style), f"{cs.get('skill_validation', 0)}", "15", _score_badge(cs.get('skill_validation', 0), 15)],
        [Paragraph("ATS Parsing Compatibility", body_style), f"{cs.get('ats_compatibility', 0)}", "15", _score_badge(cs.get('ats_compatibility', 0), 15)],
    ]
    comp_table = Table(comp_rows, colWidths=[220, 100, 100, 120])
    comp_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F1F5F9')),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('ALIGN', (1, 0), (2, -1), 'CENTER'),
    ]))
    story.append(comp_table)
    story.append(Spacer(1, 12))

    # 4. Extracted Skills Section
    skills = res.get('skills') or analysis_data.get('skills') or []
    if skills:
        story.append(Paragraph("Top Extracted Technical & Professional Skills", h2_style))
        skills_text = ", ".join(skills[:30])
        story.append(Paragraph(skills_text, body_style))
        story.append(Spacer(1, 10))

    # 5. Job Description & Match Alignment Section (if available)
    jd_text = res.get('job_description') or jd_analysis.get('job_description') or ''
    match_pct = float(res.get('match_percentage') or jd_analysis.get('match_percentage') or 0.0)
    similarity = float(res.get('resume_jd_similarity') or jd_analysis.get('semantic_similarity') or 0.0)

    matching_skills = res.get('matching_skills') or jd_analysis.get('matching_skills') or []
    missing_skills  = res.get('missing_skills') or jd_analysis.get('missing_skills') or jd_analysis.get('skills_gap') or []

    if jd_text or match_pct > 0 or matching_skills or missing_skills:
        story.append(Paragraph("Resume ↔ Job Description Alignment Engine Results", h2_style))
        
        match_data = [
            [
                Paragraph(f"<b>Overall Resume ↔ JD Match:</b> {match_pct:.1f}%", bold_body),
                Paragraph(f"<b>BERT Cosine Similarity:</b> {(similarity * 100):.1f}%", bold_body),
            ]
        ]
        match_table = Table(match_data, colWidths=[270, 270])
        match_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#EFF6FF')),
            ('PADDING', (0, 0), (-1, -1), 8),
            ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor('#93C5FD')),
        ]))
        story.append(match_table)
        story.append(Spacer(1, 8))

        if matching_skills:
            story.append(Paragraph(f"<b><font color='#10B981'>✓ Validated Matching Skills ({len(matching_skills)}):</font></b>", bold_body))
            story.append(Paragraph(", ".join(matching_skills), body_style))
            story.append(Spacer(1, 4))

        if missing_skills:
            story.append(Paragraph(f"<b><font color='#EF4444'>✗ Missing Required Skills Gap ({len(missing_skills)}):</font></b>", bold_body))
            story.append(Paragraph(", ".join(missing_skills), body_style))
            story.append(Spacer(1, 8))

    # 6. Matched & Missing Keywords
    matched_kw = res.get('matched_keywords') or analysis_data.get('matched_keywords') or []
    missing_kw = res.get('missing_keywords') or analysis_data.get('missing_keywords') or []

    if matched_kw or missing_kw:
        story.append(Paragraph("ATS Keyword Optimization Breakdown", h2_style))
        if matched_kw:
            story.append(Paragraph(f"<b>Matched Keywords ({len(matched_kw)}):</b> {', '.join(matched_kw[:20])}", body_style))
        if missing_kw:
            story.append(Paragraph(f"<b>Missing Recommended Keywords ({len(missing_kw)}):</b> {', '.join(missing_kw[:15])}", body_style))
        story.append(Spacer(1, 10))

    # 7. Actionable Recommendations & Fixes
    recs = res.get('recommendations') or analysis_data.get('recommendations') or []
    if recs:
        story.append(Paragraph("Priority Resume Recommendations & Action Items", h2_style))
        for item in recs[:5]:
            title = item.get('title') or item.get('issue_title') or 'Recommendation'
            desc  = item.get('description') or item.get('explanation') or ''
            story.append(Paragraph(f"• <b>{title}</b>: {desc}", body_style))
            actions = item.get('action_items') or []
            if actions:
                for act in actions[:2]:
                    story.append(Paragraph(f"   - <i>Action:</i> {act}", body_style))
            story.append(Spacer(1, 3))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


def Math_round(val: float) -> int:
    return int(round(val))


def _score_badge(score: float, max_score: float) -> str:
    pct = (score / max_score) * 100 if max_score > 0 else 0
    if pct >= 80:
        return "<font color='#10B981'><b>Excellent</b></font>"
    elif pct >= 60:
        return "<font color='#F59E0B'><b>Needs Work</b></font>"
    else:
        return "<font color='#EF4444'><b>Critical</b></font>"


def generate_combined_pdf(data_or_html: Any) -> bytes:
    """
    Backward-compatible alias for build_pdf_report.
    Converts input analysis data/report dictionary into PDF bytes using ReportLab 5.0.
    """
    if isinstance(data_or_html, dict):
        return build_pdf_report(data_or_html)
    elif isinstance(data_or_html, list) and len(data_or_html) > 0 and isinstance(data_or_html[0], dict):
        return build_pdf_report(data_or_html[0])
    return build_pdf_report({})
