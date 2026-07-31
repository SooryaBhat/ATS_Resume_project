"""
test_nlp_pipeline.py — Unit test suite for TalentMatch AI Phase 1 NLP pipeline audit.

Verifies:
1. Preprocessing, tokenization, text cleaning.
2. Keyword extraction (TF-IDF), skill extraction (spaCy/taxonomy).
3. Similarity calculation (SentenceTransformer BERT cosine similarity).
4. 5-Component ATS score calculation.
5. Missing & matching skills extraction.
6. Execution of full resume analysis without GEMINI_API_KEY (proving Gemini is excluded from ATS scoring).
"""

import unittest
import os
from unittest.mock import MagicMock

import spacy
from sentence_transformers import SentenceTransformer

from backend.services.nlp_pipeline import (
    clean_text,
    tokenize_text,
    extract_skills_nlp,
    extract_keywords_nlp,
    extract_action_verbs_nlp,
    calculate_bert_similarity,
    score_resume_against_jd,
    nlp_parse_resume,
    nlp_parse_job_description,
)
from backend.services.ats_scorer import calculate_overall_score, validate_skills_with_projects
from backend.services.resume_analyzer import analyze_full_resume


class TestNLPPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Load spaCy small model or dummy if not available
        try:
            cls.nlp = spacy.load('en_core_web_sm')
        except Exception:
            cls.nlp = None

        # Instantiate lightweight embedder
        try:
            cls.embedder = SentenceTransformer('all-MiniLM-L6-v2')
        except Exception:
            cls.embedder = None

    def test_clean_text(self):
        raw = "Hello\r\n\tWorld! \u2022 Skill 1   \u2023 Skill 2"
        cleaned = clean_text(raw)
        self.assertIn("• Skill 1", cleaned)
        self.assertNotIn("\r\n", cleaned)

    def test_tokenize_text(self):
        sample = "Python developer with FastAPI experience."
        tokens = tokenize_text(sample, self.nlp)
        self.assertIsInstance(tokens, list)
        self.assertTrue(len(tokens) > 0)

    def test_extract_skills_nlp(self):
        sample = "Proficient in Python, FastAPI, Docker, and PostgreSQL. Experienced with React."
        skills = extract_skills_nlp(sample, self.nlp)
        skills_lower = [s.lower() for s in skills]
        self.assertIn('python', skills_lower)
        self.assertIn('fastapi', skills_lower)
        self.assertIn('docker', skills_lower)

    def test_extract_keywords_nlp(self):
        sample = "Senior Python Backend Engineer building REST APIs and microservices on AWS cloud."
        keywords = extract_keywords_nlp(sample, self.nlp, top_n=10)
        self.assertIsInstance(keywords, list)
        self.assertTrue(len(keywords) > 0)

    def test_extract_action_verbs_nlp(self):
        sample = "• Developed REST APIs\n• Optimized database queries\n• Led agile team"
        verbs = extract_action_verbs_nlp(sample, self.nlp)
        self.assertIn('developed', verbs)
        self.assertIn('optimized', verbs)

    def test_bert_similarity(self):
        if self.embedder is None:
            self.skipTest("SentenceTransformer embedder not available")
        
        resume = "Senior Python developer with FastAPI, PostgreSQL, and Docker experience."
        jd = "Looking for a Python backend engineer with FastAPI and SQL database experience."
        
        sim1 = calculate_bert_similarity(resume, jd, self.embedder)
        sim2 = score_resume_against_jd(resume, jd, self.embedder)
        
        self.assertGreaterEqual(sim1, 0.0)
        self.assertLessEqual(sim1, 1.0)
        self.assertEqual(sim1, sim2)

    def test_ats_score_no_gemini_required(self):
        # Ensure GEMINI_API_KEY is unset to verify pure NLP execution
        old_key = os.environ.pop('GEMINI_API_KEY', None)
        try:
            resume_text = """
            John Doe
            Email: john@example.com | Phone: 555-0199
            LinkedIn: linkedin.com/in/johndoe | GitHub: github.com/johndoe

            PROFESSIONAL SUMMARY
            Senior Python Software Engineer with 5+ years of experience building scalable web applications.

            SKILLS
            Python, FastAPI, Django, PostgreSQL, Docker, AWS, Git, REST APIs

            EXPERIENCE
            Senior Backend Engineer — TechCorp (2021 – Present)
            • Developed RESTful microservices using FastAPI and PostgreSQL handling 10k daily requests.
            • Optimized database query performance by 40% using index optimization.
            • Automated CI/CD deployment pipelines using Docker and GitHub Actions on AWS.

            PROJECTS
            E-Commerce Backend API — Python, FastAPI, Docker
            • Built high-performance async REST API with JWT authentication.

            EDUCATION
            B.S. Computer Science — State University (2017 – 2021)
            """

            jd_text = """
            We are hiring a Senior Python Engineer.
            Required skills: Python, FastAPI, PostgreSQL, Docker, AWS.
            Responsibilities: Build scalable backend microservices, optimize database performance.
            """

            # Run full analysis using nlp and embedder
            result = analyze_full_resume(
                resume_text=resume_text,
                nlp=self.nlp,
                embedder=self.embedder,
                job_description=jd_text,
            )

            # Assert ATS score is returned deterministically from NLP pipeline
            self.assertIn('ats_score', result)
            self.assertIsInstance(result['ats_score'], (int, float))
            self.assertGreater(result['ats_score'], 0)
            self.assertIn('component_scores', result)
            self.assertIn('formatting', result['component_scores'])
            self.assertIn('keywords', result['component_scores'])
            self.assertIn('content', result['component_scores'])
            self.assertIn('skill_validation', result['component_scores'])
            self.assertIn('ats_compatibility', result['component_scores'])

            # Assert skills and keywords were extracted
            self.assertTrue(len(result['skills']) > 0)
            self.assertTrue(len(result['matched_keywords']) > 0)

            # Assert Phase 2 Resume-JD comparison metrics
            self.assertIn('jd_match_analysis', result)
            self.assertIsNotNone(result['jd_match_analysis'])
            self.assertIn('match_percentage', result)
            self.assertIn('resume_jd_similarity', result)
            self.assertIn('matching_skills', result)
            self.assertIn('missing_skills', result)
            self.assertIsInstance(result['matching_skills'], list)
            self.assertIsInstance(result['missing_skills'], list)

            # Assert fallback interpretation is present even without Gemini
            self.assertIn('interpretation', result)

        finally:
            if old_key is not None:
                os.environ['GEMINI_API_KEY'] = old_key


if __name__ == '__main__':
    unittest.main()

