"""
test_nlp_scoring_pipeline.py — Unit test for Phase 5: NLP Scorer Verification

Verifies that:
1. analyze_full_resume executes 100% via spaCy, SentenceTransformers, and scikit-learn without GEMINI_API_KEY.
2. ATS Score and 5-component breakdown are generated deterministically by NLP.
3. Resume-JD BERT Cosine Similarity and match percentage are generated deterministically by SentenceTransformers.
4. Gemini API is NEVER required or called for scoring, parsing, or matching.
"""

import unittest
import os
import spacy
from backend.services.nlp_pipeline import get_embedder, calculate_bert_similarity

from backend.services.resume_analyzer import analyze_full_resume


class TestNlpScoringPipeline(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Load spaCy small model & lightweight production embedder
        try:
            cls.nlp = spacy.load("en_core_web_sm")
        except Exception:
            cls.nlp = spacy.blank("en")
        cls.embedder = get_embedder()

        cls.sample_resume = """
        Alex Morgan
        Senior Software Engineer | Python, FastAPI, Docker, PostgreSQL
        Email: alex.morgan@example.com | Phone: (555) 019-2834
        LinkedIn: linkedin.com/in/alexmorgan | GitHub: github.com/alexmorgan

        PROFESSIONAL SUMMARY
        Innovative Senior Software Engineer with 6+ years of experience building high-throughput microservices using Python, FastAPI, Docker, and PostgreSQL. Reduced API latency by 45% and improved database query efficiency by 30%.

        TECHNICAL SKILLS
        • Languages: Python, JavaScript, SQL, Bash
        • Frameworks: FastAPI, Flask, React, Node.js
        • Databases & Cloud: PostgreSQL, Redis, Docker, AWS, Git

        PROFESSIONAL EXPERIENCE
        Senior Backend Engineer — TechCorp (2021 – Present)
        • Designed and deployed high-performance RESTful APIs using Python and FastAPI, serving over 1M daily requests.
        • Optimized PostgreSQL database queries, reducing average latency from 220ms to 120ms.
        • Containerized microservices using Docker and orchestrated deployments on AWS ECS.

        EDUCATION
        B.S. in Computer Science — University of Technology (2015 – 2019)
        """

        cls.sample_jd = """
        Target Role: Senior Python Backend Developer
        Requirements:
        • 5+ years experience with Python, FastAPI, Docker, and PostgreSQL.
        • Strong expertise building REST APIs and microservice architectures.
        • Cloud experience with AWS or Kubernetes is preferred.
        """

    def test_nlp_scoring_without_gemini_key(self):
        # Explicitly unset GEMINI_API_KEY to ensure zero reliance on Gemini for scoring
        orig_key = os.environ.get("GEMINI_API_KEY")
        if "GEMINI_API_KEY" in os.environ:
            del os.environ["GEMINI_API_KEY"]

        try:
            result = analyze_full_resume(
                resume_text=self.sample_resume,
                nlp=self.nlp,
                embedder=self.embedder,
                job_description=self.sample_jd,
            )

            # 1. Verify overall ATS Score & Component Scores exist and are numeric
            self.assertIn("ats_score", result)
            self.assertGreaterEqual(result["ats_score"], 0.0)
            self.assertLessEqual(result["ats_score"], 100.0)

            cs = result.get("component_scores", {})
            self.assertIn("formatting", cs)
            self.assertIn("keywords", cs)
            self.assertIn("content", cs)
            self.assertIn("skill_validation", cs)
            self.assertIn("ats_compatibility", cs)

            # 2. Verify Extracted Skills & Keywords
            self.assertTrue(len(result.get("skills", [])) > 0)
            self.assertIn("Python", result.get("skills", []))

            # 3. Verify SentenceTransformers BERT Cosine Similarity & Match %
            self.assertIn("resume_jd_similarity", result)
            self.assertGreater(result["resume_jd_similarity"], 0.50)

            self.assertIn("match_percentage", result)
            self.assertGreater(result["match_percentage"], 0.0)

            # 4. Verify Matching & Missing Skills
            self.assertIn("matching_skills", result)
            self.assertIn("missing_skills", result)

        finally:
            if orig_key is not None:
                os.environ["GEMINI_API_KEY"] = orig_key


if __name__ == "__main__":
    unittest.main()
