# -*- coding: utf-8 -*-
"""Actual-source director craft gatekeeping tests; no paid model or source-pixel regeneration."""
import json,shutil,sqlite3,tempfile,unittest,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import director_craft as craft
import director as director_db

class DirectorCraftTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.cards=json.loads((ROOT/'output/director_lab/director_cards.json').read_text(encoding='utf-8'))
  cls.summary=json.loads((ROOT/'output/director_lab/DIRECTOR_LAB_ACCEPTANCE.json').read_text(encoding='utf-8'))
  cls.timeline=json.loads((ROOT/'output/director_lab/reference_visual_timeline.json').read_text(encoding='utf-8'))
 def test_all_real_reference_cards_are_present(self):
  self.assertEqual(len(self.cards),86)
  self.assertEqual(sum(len(x['reference_images']) for x in self.cards),258)
  for x in self.cards:
   self.assertEqual(set(x['reference_images']),{'in','mid','out'})
   for anchor,p in x['reference_images'].items():
    self.assertTrue((ROOT/p).is_file())
    self.assertEqual(craft.sha(ROOT/p),x['anchor_source_shas'][anchor])
 def test_no_fabricated_director_approval_or_actor_identity(self):
  self.assertEqual(self.summary['confirmed_director_narrative_intents'],0)
  self.assertEqual(self.summary['verified_actor_identities'],0)
  self.assertEqual(self.summary['ai_recreated_stills_approved'],0)
  self.assertFalse(self.summary['real_model_api_used'])
  self.assertEqual(self.summary['cost_paid_video_generation'],0)
  for shot in self.cards:
   self.assertFalse(shot['production_gates']['director_approved'])
   self.assertFalse(shot['production_gates']['asset_identities_locked'])
   self.assertFalse(shot['camera_2d']['camera_3d_path_confirmed'])
 def test_internal_cut_is_proposed_not_auto_split(self):
  internal=self.timeline['internal_cut_warnings']
  self.assertGreaterEqual(len(internal),1)
  self.assertTrue(all(x['interpretation']=='POSSIBLE_UNDETECTED_CUT_NEEDS_REVIEW' for x in internal))
  suspicious=next(c for c in self.cards if c['shot_id']=='SH_00055')
  self.assertTrue(suspicious['cut_analysis']['is_contaminated'])
  self.assertEqual(suspicious['cut_analysis']['action'],'VERIFY_SPLIT_BEFORE_GENERATION')
  self.assertEqual(len(self.cards),86)
 def test_director_hypotheses_are_not_facts(self):
  mine=[c for c in self.cards if c['director_reading']['provenance'].startswith('assistant')]
  self.assertEqual(len(mine),20)
  self.assertTrue(all(not c['director_reading']['source_confirmed'] for c in mine))
 def test_director_edit_invalidates_spec_without_approving(self):
  import director as d
  old_db,old_data=d.DB,d.DATA
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);(root/'data/references').mkdir(parents=True)
   (root/'output/director_lab').mkdir(parents=True)
   shutil.copy2(ROOT/'data/project_manifest.json',root/'data/project_manifest.json')
   shutil.copy2(ROOT/'data/director.sqlite3',root/'data/director.sqlite3')
   sample=next(c for c in self.cards if c['shot_id']=='SH_00066')
   (root/'output/director_lab/director_cards.json').write_text(json.dumps([sample],ensure_ascii=False),encoding='utf-8')
   for pic in sample['reference_images'].values():shutil.copy2(ROOT/pic,root/pic)
   try:
    d.DB=root/'data/director.sqlite3';d.DATA=root/'data'
    out=craft.safe_notes('SH_00066',{'narrative_purpose':'猫的轮廓与运动关系；需要逐帧确认',
        'acting':'猫足接触点先审静态姿态','review_status':'REVIEWED_REFERENCE_ONLY'},root)
    self.assertEqual(out['revision'],1)
    self.assertFalse(out['reconstruction_approved'])
    with sqlite3.connect(d.DB) as con:
     statuses=con.execute("select status from tasks where shot_id='SH_00066'").fetchall()
     self.assertEqual(len(statuses),3)
     self.assertTrue(all(a[0]=='BLOCKED_SPEC_CHANGED' for a in statuses))
     self.assertEqual(con.execute("select count(*) from events where type='DIRECTOR_SPEC_EDITED' and task_id like 'SH_00066:%'").fetchone()[0],3)
    out2=craft.safe_notes('SH_00066',out['notes'],root)
    self.assertEqual(out2['revision'],1)
    with self.assertRaises(ValueError):craft.safe_notes('SH_00066',{'review_status':'APPROVED'},root)
   finally:d.DB=old_db;d.DATA=old_data
 def test_all_work_orders_keep_provenance(self):
  file=ROOT/'output/director_lab/director_shot_work_orders.jsonl'
  lines=[json.loads(v) for v in file.read_text(encoding='utf-8').splitlines()]
  self.assertEqual(len(lines),86)
  self.assertTrue(all(q['source_kind']=='ORIGINAL_REFERENCE_ONLY' for q in lines))
  self.assertEqual(sum(q['status']=='DRAFT_NOT_AUTHORIZED_FOR_GENERATION' for q in lines),self.summary['affected_current_shot_cards'])

if __name__=='__main__':unittest.main()
