# coding: utf-8
"""True-source and falsifiable original-screenplay QA; no claim of film artistry pass."""
import copy, json, sys, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import gpt_director_study as g

class FilmDirectorStudyTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.data=g.load(g.SCENE);cls.scene=cls.data['scene']
  cls.good=cls.data['revised_shots']
  cls.results=g.load(g.OUT/'study_and_rehearsal.json')
 def test_video_matches_uploaded_segment_sha(self):
  r=g.verify_source();self.assertEqual(r['duration_s'],776.477)
  self.assertEqual(r['source_scope'],'UPLOADED_776_SECOND_EXCERPT_NOT_THE_FULL_FEATURE')
 def test_18_real_frames_match_saved_provenance(self):
  study=self.results
  self.assertEqual(sum(len(x) for x in study['frame_references'].values()),18)
  for recs in study['frame_references'].values():
   for r in recs:
    self.assertTrue((ROOT/r['path']).is_file())
    self.assertEqual(g.digest(ROOT/r['path']),r['sha256'])
 def test_source_film_not_scored_as_flawed(self):
  self.assertFalse(self.results['director_intent_verified'])
  self.assertFalse(self.results['new_ai_image_generated'])
  self.assertTrue(all(c['unverified'] and c['hypotheses'] for c in self.results['study_cases']))
 def test_source_film_study_separates_knowledge_and_blocking(self):
  cases=self.results['study_cases'];self.assertEqual([x['id'] for x in cases],['CASE_A','CASE_B'])
  self.assertIn('猫',cases[0]['narrative_core']);self.assertIn('行动',cases[1]['title'])
 def test_initial_rehearsal_fails_for_real_reasons(self):
  defects={x['type'] for x in g.audit(self.scene,self.data['initial_draft'])['issues']}
  for key in ('UNSUPPORTED_CHARACTER_KNOWLEDGE','TELEPORTATION_UNEXPLAINED',
              'MULTI_SETUP_IN_SINGLE_SHOT','GAP_OR_OVERLAP','MISSING_SOUND_PLAN'):
   self.assertIn(key,defects)
 def test_revision_passes_structure_only_not_art(self):
  r=g.audit(self.scene,self.good)
  self.assertEqual(r['issues'],[])
  self.assertFalse(r['artistic_quality_verified'])
  self.assertFalse(r['spatial_3d_verified'])
  self.assertFalse(r['film_director_intent_verified'])
 def test_audience_information_not_leaked_to_character(self):
  r=g.audit(self.scene,self.good)
  self.assertIn('REMOTE_LOGIN',r['audience_knowledge_final'])
  self.assertNotIn('REMOTE_LOGIN',r['character_knowledge_final']['A'])
  self.assertIn('BADGE_HIDDEN',r['audience_knowledge_final'])
  self.assertNotIn('BADGE_HIDDEN',r['character_knowledge_final']['A'])
 def test_injected_errors_independently_detected(self):
  r=g.negative_tests(self.scene,self.good)
  self.assertEqual(r['detected_count'],r['total'])
  self.assertEqual(r['total'],6)
 def test_director_study_is_real_page_not_source_copy(self):
  html=(ROOT/'GPT_DIRECTOR_FILM_STUDY.html').read_text('utf8')
  self.assertIn('导演学习系统',html)
  self.assertIn('617–653',html)
  self.assertIn('output/gpt_director_study/CASE_A_',html)
  self.assertNotIn('新AI视频已生成',html)

if __name__=='__main__':unittest.main()
