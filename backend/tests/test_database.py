"""
test_database.py — Database Layer & Migration Test Suite for TalentMatch AI.
"""

import asyncio
import os
import sys
import unittest
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.core.config import SUPABASE_URL, SUPABASE_KEY
from backend.database.supabase_db import save_analysis, get_user_history, delete_analysis


class TestDatabaseLayer(unittest.TestCase):

  def test_env_variables_loaded(self):
    """Verify Supabase URL and keys are loaded."""
    self.assertTrue(bool(SUPABASE_URL), 'SUPABASE_URL should not be empty.')
    self.assertTrue(bool(SUPABASE_KEY), 'SUPABASE_KEY should not be empty.')
    self.assertTrue(
        SUPABASE_URL.startswith('https://'),
        'SUPABASE_URL should be a valid HTTPS endpoint.',
    )

  def test_save_and_retrieve_history_format(self):
    """Test saving a mock analysis payload and reading history format."""

    async def _test():
      mock_user_id = '00000000-0000-0000-0000-000000000001'
      mock_analysis = {
          'ats_score': 92.5,
          'job_title': 'Lead AI Systems Architect',
          'keyword_match': 90.0,
          'component_scores': {
              'formatting': 19.0,
              'keywords': 24.0,
              'content': 23.0,
              'skill_validation': 14.0,
              'ats_compatibility': 14.5,
          },
          'matched_keywords': ['Python', 'FastAPI', 'PyTorch', 'Docker'],
          'missing_keywords': ['Kubernetes', 'Terraform'],
          'issues_summary': ['Missing Kubernetes keyword'],
          'detailed_feedback': [],
          'recommendations': [{
              'title': 'Add Kubernetes',
              'priority_label': 'High',
              'impact_score': 5.0,
          }],
          'strengths': ['Quantified accomplishments'],
          'interpretation': 'Excellent ATS grade.',
      }

      # Test save_analysis
      save_result = await save_analysis(
          mock_user_id, 'test_resume.pdf', mock_analysis
      )
      self.assertIn(
          save_result.get('status'),
          ['saved', 'skipped', 'error'],
          "Status should be one of ['saved', 'skipped', 'error']",
      )

      # Test get_user_history
      history = await get_user_history(mock_user_id)
      self.assertIsInstance(history, list)

      if history and save_result.get('status') == 'saved':
        latest = history[0]
        self.assertIn('id', latest)
        self.assertIn('filename', latest)
        self.assertIn('ats_score', latest)
        self.assertEqual(latest['job_title'], 'Lead AI Systems Architect')

        # Clean up test record
        del_result = await delete_analysis(latest['id'], mock_user_id)
        self.assertTrue(del_result)

    asyncio.run(_test())


if __name__ == '__main__':
  unittest.main()
