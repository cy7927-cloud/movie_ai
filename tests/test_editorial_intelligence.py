# -*- coding: utf-8 -*-
"""No paid provider; verifies reference editing relationships and rule-based iteration."""
import json,shutil,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import editorial_intelligence as e

class EditorialIntelligenceTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.pairs=e.read_json(ROOT/'output/editorial_language/transitions.json',[])
  cls.lessons=e.read_json(ROOT/'output/editorial_language/director_lessons.json',[])
  cls.audit=e.read_json(ROOT/'output/editorial_language/acceptance.json',{})
 def test_real_source_has_85_transition_records_no_penalties(self):
  self.assertEqual(len(self.pairs),85)
  self.assertTrue(all(not z['film_quality_fault'] and not z['visual_change_is_defect'] for z in self.pairs))
  self.assertTrue(all(z['cut_boundary_status']=='AUTO_PROPOSED_NOT_EDITORIALLY_CONFIRMED' for z in self.pairs))
  self.assertEqual(self.audit['film_cut_visual_change_quality_penalty'],0)
 def test_each_pair_carries_original_frames_with_hash(self):
  for p in self.pairs:
   self.assertTrue((ROOT/p['out_frame']).is_file())
   self.assertTrue((ROOT/p['in_frame']).is_file())
   self.assertEqual(e.hash_file(ROOT/p['out_frame']),p['out_sha256'])
   self.assertEqual(e.hash_file(ROOT/p['in_frame']),p['in_sha256'])
 def test_real_film_grammar_lessons_stay_hypotheses(self):
  self.assertEqual(len(self.lessons),3)
  self.assertEqual([x['id'] for x in self.lessons],['LESSON_01','LESSON_02','LESSON_03'])
  self.assertTrue(all(not x['narrative_approved'] for x in self.lessons))
  self.assertTrue(all(len(x['shots'])==len(x['reference_sha256'])==len(x['reference_mid_frames']) for x in self.lessons))
  self.assertEqual(self.audit['verified_cut_intentions'],0)
  self.assertEqual(self.audit['director_grade_recreation_approvals'],0)
 def test_9_pair_readings_not_asserted_as_verified(self):
  known=[x for x in self.pairs if x['director_interpretation']['type']!='UNKNOWN']
  self.assertEqual(len(known),9)
  self.assertTrue(all(not x['director_interpretation']['verified'] for x in known))
  self.assertEqual(next(x for x in known if x['from']=='SH_00065')['director_interpretation']['type'],'INSERT_SHOT')
 def test_original_storyboard_structural_self_revision_three_modes(self):
  for mode in e.PATTERNS:
   z=e.design_scene('科考队发现海面发出不明光信号，决定是否靠近。',mode)
   before=z['iteration_trace'][0]['technical_review']
   after=z['iteration_trace'][1]['technical_review']
   self.assertLess(before['structural_check_passed'],after['structural_check_passed'])
   self.assertEqual(after['structural_check_passed'],after['structural_check_total'])
   self.assertFalse(after['director_quality_verified'])
   self.assertFalse(z['real_image_model_called'])
   self.assertFalse(z['paid_video_model_called'])
   self.assertIn('科考队',z['iteration_trace'][1]['shots'][0]['source_story_brief'])
   self.assertTrue(z['iteration_trace'][1]['shots'][0]['shootable_director_prompt_draft'])
 def test_invalid_brief_and_mode_rejected(self):
  for brief in ('', 'x', 'a'*1600):
   with self.assertRaises(ValueError):e.design_scene(brief)
  with self.assertRaises(ValueError):e.design_scene('一场真实原创戏份', 'invalid')
 def test_editorial_notes_reference_binding_and_no_signoff(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);(root/'output/editorial_language').mkdir(parents=True)
   (root/'data/references').mkdir(parents=True)
   first=self.pairs[0]
   for path in (first['out_frame'],first['in_frame']):shutil.copy2(ROOT/path,root/path)
   e.write_json(root/'output/editorial_language/transitions.json',[first])
   out=e.save_director_edit(root,first['id'],'OTHER','为观众呈现新的情绪信息，需要查证原片','后续核对音轨与角色目光','测试复核')
   self.assertEqual(out['revision'],1)
   self.assertFalse(out['director_approval'])
   self.assertTrue(out['reference_only'])
   out2=e.save_director_edit(root,first['id'],'OTHER','为观众呈现新的情绪信息，需要查证原片','后续核对音轨与角色目光','测试复核')
   self.assertEqual(out2['revision'],1)
   with self.assertRaises(ValueError):e.save_director_edit(root,first['id'],'FILM_IS_WRONG','电影出现画面不连贯必须修复','','')
   with open(root/first['in_frame'],'ab') as f:f.write(b'modified')
   with self.assertRaisesRegex(ValueError,'Source frame changed'):
    e.save_director_edit(root,first['id'],'OTHER','电影空间关系待查证','','')
 def test_ready_for_offline_and_local_browser(self):
  p=ROOT/'EDITORIAL_DIRECTOR_LAB.html'
  self.assertTrue(p.is_file())
  src=p.read_text('utf-8')
  self.assertIn('切镜不是错误',src)
  self.assertIn('LESSON_03',src)
  self.assertIn('真实影片仅为导演语法参考样本',src)
  self.assertTrue((ROOT/self.audit['board_path']).is_file())

if __name__=='__main__':unittest.main()
