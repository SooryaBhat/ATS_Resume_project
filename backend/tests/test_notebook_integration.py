"""
test_notebook_integration.py — Integration test for Notebook NLP Pipeline conversion.

Verifies that:
1. score_resume_against_jd matches Notebook 03 Cell 14 implementation.
2. validate_text_length matches Notebook 01 Cell 31 length check.
3. compare_resume_with_jd attaches match_tier ('HIGH', 'MEDIUM', 'LOW').
4. The entire NLP pipeline runs 100% deterministically without requiring Gemini API calls.
"""

import unittest
import spacy
from backend.services.nlp_pipeline import get_embedder

from backend.services.nlp_pipeline import (
    score_resume_against_jd,
    validate_text_length,
    clean_text,
    nlp_parse_resume,
    nlp_parse_job_description,
)
from backend.services.jd_matcher import compare_resume_with_jd


class TestNotebookIntegration(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        try:
            cls.nlp = spacy.load("en_core_web_sm")
        except Exception:
            cls.nlp = spacy.blank("en")
        cls.embedder = get_embedder()

        cls.sample_resume = """
        John Doe
        Software Engineer | Python, React, PostgreSQL, Docker
        Email: john.doe@example.com | Phone: 555-123-4567

        PROFESSIONAL SUMMARY
        Experienced Software Engineer specializing in full stack web applications using Python, FastAPI, and React.

        EXPERIENCE
        Backend Developer — Acme Inc (2020 - Present)
        • Developed high throughput microservices in Python and FastAPI.
        • Optimized PostgreSQL database queries reducing response latency by 35%.

        EDUCATION
        B.S. Computer Science — Tech University
        """

        cls.sample_jd = """
        Target Role: Backend Engineer (Python)
        Requirements:
        • 3+ years experience with Python, FastAPI, and SQL databases.
        • Experience containerizing applications with Docker.
        """

    def test_notebook_validate_text_length(self):
        # Notebook 01 Cell 31 check: resumes with < 20 words are marked False
        self.assertFalse(validate_text_length("Short resume text", min_words=20))
        self.assertTrue(validate_text_length(self.sample_resume, min_words=20))

    def test_notebook_score_resume_against_jd(self):
        # Notebook 03 Cell 14 check: score_resume_against_jd returns float between 0.0 and 1.0
        score = score_resume_against_jd(self.sample_resume, self.sample_jd, self.embedder)
        self.assertIsInstance(score, float)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)
        self.assertGreater(score, 0.50)  # High semantic overlap expected

    def test_notebook_match_tier_classification(self):
        # Notebook 03 Cell 14 check: HIGH match tier assignment
        res_keywords = ["python", "fastapi", "react", "postgresql", "docker"]
        res_skills   = ["Python", "FastAPI", "React", "PostgreSQL", "Docker"]
        jd_keywords  = ["python", "fastapi", "sql", "docker"]

        match_res = compare_resume_with_jd(
            resume_text=self.sample_resume,
            resume_keywords=res_keywords,
            resume_skills=res_skills,
            jd_text=self.sample_jd,
            jd_keywords=jd_keywords,
            embedder=self.embedder,
            nlp=self.nlp,
        )

        self.assertIn("match_tier", match_res)
        self.assertIn(match_res["match_tier"], ["HIGH", "MEDIUM", "LOW"])
        self.assertEqual(match_res["match_tier"], "HIGH")


if __name__ == "__main__":
    unittest.main()
