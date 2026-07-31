"""
test_chat_context.py — Unit test suite for Phase 3 Context-Aware AI Chat Assistant.

Verifies:
1. _build_resume_context_prompt formats resume text, ATS score breakdown, extracted skills, JD text, BERT similarity, missing skills, and recommendations.
2. In-memory analysis cache in supabase_db stores and retrieves full analysis context by ID and 'latest'.
3. Chat system instruction contains candidate's actual resume data.
"""

import unittest
import asyncio
from backend.services.chat_service import _build_resume_context_prompt
from backend.database.supabase_db import save_analysis, get_analysis_by_id


class TestChatContext(unittest.TestCase):

    def test_build_resume_context_prompt_formatting(self):
        sample_analysis = {
            'id': 'test-analysis-123',
            'job_title': 'Senior Python Developer',
            'ats_score': 85.5,
            'interpretation': 'Great! Your resume should perform well.',
            'resume_text': 'Alex Morgan\nSenior Python developer with 5+ years experience building REST APIs with FastAPI.',
            'job_description': 'We need a Senior Python Developer with FastAPI, PostgreSQL, and Docker.',
            'skills': ['Python', 'FastAPI', 'PostgreSQL', 'Docker', 'AWS'],
            'component_scores': {
                'formatting': 18.0,
                'keywords': 22.0,
                'content': 21.0,
                'skill_validation': 12.0,
                'ats_compatibility': 12.5,
            },
            'resume_jd_similarity': 0.88,
            'match_percentage': 84.5,
            'matching_skills': ['Python', 'FastAPI', 'PostgreSQL'],
            'missing_skills': ['Docker', 'Kubernetes'],
            'matched_keywords': ['Python', 'FastAPI', 'REST APIs'],
            'missing_keywords': ['Docker', 'Kubernetes', 'Helm'],
            'strengths': ['Clear Skills section', 'Quantified achievements'],
            'issues_summary': ['Missing Kubernetes experience'],
            'recommendations': [
                {
                    'title': 'Add Kubernetes Projects',
                    'description': 'Target JD requires Kubernetes experience.',
                    'action_items': ['Deploy a sample app on Minikube', 'Add K8s to skills']
                }
            ]
        }

        prompt = _build_resume_context_prompt(sample_analysis)

        # Verify all Phase 3 context requirements are present in the prompt
        self.assertIn("=== CANDIDATE RESUME & ATS ANALYSIS CONTEXT ===", prompt)
        self.assertIn("Senior Python Developer", prompt)
        self.assertIn("85.5/100", prompt)
        self.assertIn("Formatting Score: 18.0 / 20", prompt)
        self.assertIn("Keywords & Skills Score: 22.0 / 25", prompt)
        self.assertIn("Content Quality Score: 21.0 / 25", prompt)
        self.assertIn("Skill Validation Score: 12.0 / 15", prompt)
        self.assertIn("ATS Compatibility Score: 12.5 / 15", prompt)
        self.assertIn("CANDIDATE RESUME TEXT", prompt)
        self.assertIn("Alex Morgan", prompt)
        self.assertIn("EXTRACTED SKILLS", prompt)
        self.assertIn("Python, FastAPI, PostgreSQL", prompt)
        self.assertIn("JOB DESCRIPTION & RESUME-JD COMPARISON", prompt)
        self.assertIn("Overall Match Percentage: 84.5%", prompt)
        self.assertIn("88.0%", prompt)
        self.assertIn("Matching Skills: Python, FastAPI, PostgreSQL", prompt)
        self.assertIn("Missing Required Skills: Docker, Kubernetes", prompt)
        self.assertIn("Add Kubernetes Projects", prompt)

    def test_in_memory_analysis_lookup(self):
        user_id = "test-user-456"
        analysis_payload = {
            'ats_score': 92.0,
            'job_title': 'AI Systems Lead',
            'resume_text': 'AI Research Engineer with PyTorch and Transformers experience.',
            'skills': ['Python', 'PyTorch', 'Transformers', 'FastAPI'],
            'component_scores': {'formatting': 20.0, 'keywords': 24.0, 'content': 23.0, 'skill_validation': 13.0, 'ats_compatibility': 12.0},
        }

        # Run async save and fetch
        async def run_async_test():
            res = await save_analysis(user_id, "test_resume.pdf", analysis_payload)
            aid = res.get('id')
            self.assertIsNotNone(aid)

            # Fetch by explicit ID
            fetched = await get_analysis_by_id(aid, user_id)
            self.assertIsNotNone(fetched)
            self.assertEqual(fetched.get('ats_score'), 92.0)

            # Fetch by 'latest'
            latest_fetched = await get_analysis_by_id('latest', user_id)
            self.assertIsNotNone(latest_fetched)
            self.assertEqual(latest_fetched.get('ats_score'), 92.0)

        asyncio.run(run_async_test())


if __name__ == '__main__':
    unittest.main()
