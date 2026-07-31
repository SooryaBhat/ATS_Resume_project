"""
test_context_sharing.py — Verification test for Phase 2: Connect Application Context

Tests that:
1. save_analysis stores resume text, skills, ATS score, and component breakdown.
2. update_analysis_context enriches the analysis record with JD text, similarity, match %, matching skills, and missing skills.
3. _build_resume_context_prompt in chat_service formats both candidate resume details AND target job description details into Gemini prompts.
"""

import unittest
import asyncio
from backend.database.supabase_db import (
    save_analysis,
    update_analysis_context,
    get_analysis_by_id,
    _MEMORY_ANALYSES,
)
from backend.services.chat_service import _build_resume_context_prompt


class TestContextSharing(unittest.TestCase):

    def setUp(self):
        self.user_id = "test-user-context-123"
        self.sample_analysis_payload = {
            "ats_score": 88.5,
            "job_title": "Senior Python Backend Developer",
            "resume_text": "Experienced Python Backend Developer skilled in FastAPI, spaCy, PostgreSQL, Docker, and REST APIs. Built scalable microservices.",
            "skills": ["Python", "FastAPI", "spaCy", "PostgreSQL", "Docker", "REST APIs"],
            "component_scores": {
                "formatting": 18,
                "keywords": 23,
                "content": 22,
                "skill_validation": 13,
                "ats_compatibility": 12.5,
            },
            "matched_keywords": ["python", "fastapi", "docker", "postgresql"],
            "missing_keywords": ["kubernetes", "redis", "celery"],
            "recommendations": [
                {"title": "Add Caching Experience", "description": "Highlight Redis or Memcached usage."}
            ],
            "strengths": ["Strong Python & API experience"],
            "interpretation": "Strong candidate for backend engineering roles.",
        }

    def test_end_to_end_context_sharing(self):
        async def run_test():
            # Step 1: Save initial Resume Analysis
            save_res = await save_analysis(
                user_id=self.user_id,
                analysis_result=self.sample_analysis_payload,
                filename="Senior_Python_Developer.pdf",
            )
            analysis_id = save_res["id"]
            self.assertIsNotNone(analysis_id)

            # Verify initial retrieval has resume text & skills
            record1 = await get_analysis_by_id(analysis_id, self.user_id)
            self.assertIsNotNone(record1)
            self.assertIn("FastAPI", record1.get("resume_text", ""))
            self.assertIn("Python", record1.get("skills", []))

            # Step 2: Simulate JD Match Analysis & update_analysis_context
            jd_updates = {
                "job_description": "Looking for a Senior Backend Developer proficient in Python, FastAPI, Docker, and Kubernetes for cloud deployment.",
                "jd_comparison": {
                    "match_percentage": 82.5,
                    "semantic_similarity": 0.87,
                    "matching_skills": ["Python", "FastAPI", "Docker"],
                    "missing_skills": ["Kubernetes"],
                },
                "matching_skills": ["Python", "FastAPI", "Docker"],
                "missing_skills": ["Kubernetes"],
                "match_percentage": 82.5,
                "resume_jd_similarity": 0.87,
            }
            updated_ok = await update_analysis_context(analysis_id, self.user_id, jd_updates)
            self.assertTrue(updated_ok)

            # Step 3: Fetch enriched analysis record
            record2 = await get_analysis_by_id(analysis_id, self.user_id)
            self.assertEqual(record2.get("match_percentage"), 82.5)
            self.assertEqual(record2.get("missing_skills"), ["Kubernetes"])

            # Step 4: Build AI Assistant Context Prompt
            prompt = _build_resume_context_prompt(record2)

            # Verify prompt contains Resume details
            self.assertIn("Senior Python Backend Developer", prompt)
            self.assertIn("88.5/100", prompt)
            self.assertIn("FastAPI, spaCy, PostgreSQL", prompt)

            # Verify prompt contains JD & Match details
            self.assertIn("Overall Match Percentage: 82.5%", prompt)
            self.assertIn("SentenceTransformers BERT Cosine Similarity: 87.0%", prompt)
            self.assertIn("Matching Skills: Python, FastAPI, Docker", prompt)
            self.assertIn("Missing Required Skills: Kubernetes", prompt)

        asyncio.run(run_test())


if __name__ == "__main__":
    unittest.main()
