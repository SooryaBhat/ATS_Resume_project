"""
test_pdf_export.py — Unit test for Phase 4 ReportLab PDF generation and PDF download route.
"""

import unittest
from backend.services.pdf_export import build_pdf_report


class TestPdfExport(unittest.TestCase):

    def test_pdf_report_generation(self):
        sample_analysis = {
            "id": "test-pdf-123",
            "filename": "Sample_Developer_Resume.pdf",
            "job_title": "Full Stack Engineer",
            "created_at": "2026-07-30T12:00:00Z",
            "ats_score": 85.0,
            "component_scores": {
                "formatting": 18,
                "keywords": 22,
                "content": 21,
                "skill_validation": 12,
                "ats_compatibility": 12,
            },
            "skills": ["Python", "JavaScript", "React", "FastAPI", "PostgreSQL"],
            "matched_keywords": ["python", "react", "fastapi"],
            "missing_keywords": ["graphql", "aws"],
            "job_description": "We need a Full Stack Engineer with React, Python, and AWS experience.",
            "match_percentage": 80.0,
            "resume_jd_similarity": 0.85,
            "matching_skills": ["Python", "React", "FastAPI"],
            "missing_skills": ["AWS", "GraphQL"],
            "recommendations": [
                {
                    "title": "Highlight AWS Projects",
                    "description": "Demonstrate cloud infrastructure experience.",
                    "action_items": ["Add AWS deployment details to work history."],
                }
            ],
            "interpretation": "Strong candidate matching core technical requirements.",
        }

        pdf_bytes = build_pdf_report(sample_analysis)
        self.assertIsNotNone(pdf_bytes)
        self.assertIsInstance(pdf_bytes, bytes)
        self.assertTrue(len(pdf_bytes) > 500)
        # Verify valid PDF binary header magic bytes (%PDF-1.)
        self.assertTrue(pdf_bytes.startswith(b'%PDF-1.'))


if __name__ == '__main__':
    unittest.main()
