"""Actual film-evidence / professional Skill activation; not a mock director model."""
import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np
import style_activation_engine as sty


class RealFilmStyleActivationTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.profile=sty.learn()
  cls.a=sty.apply(cls.profile,'audience_first_suspense')
  cls.b=sty.apply(cls.profile,'blocking_space_reveal')

 def test_actual_video_and_frame_hashes(self):
  p=self.profile
  self.assertEqual(p['reference_frame_count'],18)
  self.assertEqual(p['film_source']['sha256'],sty.sha256(sty.FILM))
  for mode in p['modes'].values():
   self.assertEqual(len(mode['frame_evidence']),len(mode['video_frame_authenticity_checks']))
   for f,check in zip(mode['frame_evidence'],mode['video_frame_authenticity_checks']):
    self.assertEqual(sty.sha256(sty.ROOT/f['path']),f['sha256'])
    self.assertEqual(check['authenticity_check'],'PASS')
    self.assertLess(check['comparison_mae_0_255'],15.0)

 def test_original_skill_texts_are_unchanged(self):
  st=self.profile['upstream_professional_skill_sources']
  self.assertTrue(st['plan-camera-shots']['local_original_instruction_available'])
  self.assertTrue(st['review-and-assemble']['local_original_instruction_available'])
  for name in ['plan-camera-shots','review-and-assemble']:
   f=sty.ROOT/st[name]['local_skill_path']
   before=sty.sha256(f)
   _=sty.apply(self.profile,'audience_first_suspense')
   self.assertEqual(sty.sha256(f),before)
  self.assertFalse(any(x['native_host_executed'] for x in st.values()))

 def test_modes_change_real_storyboard_and_camera_fields(self):
  comp=sty.compare(self.profile,self.a,self.b)
  self.assertTrue(comp['same_original_story'])
  self.assertTrue(comp['same_shot_time_ranges'])
  self.assertTrue(comp['same_actor_spatial_paths'])
  self.assertTrue(comp['style_changes_operational_not_label_only'])
  self.assertIn('S03',{x['shot_id'] for x in comp['changed_shots']})
  a3=next(x for x in self.a['shot_camera_handoff']['segments'] if x['id']=='S03')
  b3=next(x for x in self.b['shot_camera_handoff']['segments'] if x['id']=='S03')
  self.assertNotEqual(a3['focus_target'],b3['focus_target'])
  self.assertNotEqual(a3['lens_focal_length_mm'],b3['lens_focal_length_mm'])

 def test_b_plan_does_not_borrow_a_visual_proof(self):
  self.assertEqual(self.b['generation_status'],'B_HAS_NO_NEW_AI_IMAGES')
  self.assertEqual(self.b['external_media_reviews'],[])
  self.assertTrue(self.b['legacy_A_media_not_validated_for_new_style'])
  self.assertTrue(all('image_generation_ref' not in s for s in self.b['shot_camera_handoff']['segments']))
  self.assertTrue(all(s['new_visual_candidate_status']=='NOT_GENERATED_FOR_THIS_STYLE'
                      for s in self.b['shot_camera_handoff']['segments']))

 def test_independent_review_gate_cannot_be_self_approved(self):
  for result in (self.a,self.b):
   self.assertTrue(result['preflight']['pass'])
   self.assertFalse(result['media_final_approval'])
   self.assertTrue(result['film_export_blocked'])
   self.assertFalse(result['skill_native_execution_claimed'])
  self.assertTrue(any(x['status']=='REJECTED' for x in self.a['external_media_reviews']))

 def test_fake_film_claims_are_not_introduced(self):
  p=self.profile
  self.assertIn('NOT_MODEL_WEIGHT_FINETUNING',p['parameter_type'])
  self.assertEqual(p['film_source']['coverage'],'USER_PROVIDED_REFERENCE_VIDEO_NOT_ASSUMED_FULL_FEATURE')
  self.assertEqual(p['modes']['audience_first_suspense']['case'],'CASE_A')
  self.assertEqual(p['modes']['blocking_space_reveal']['case'],'CASE_B')
  self.assertFalse(self.a['story_audit']['film_director_intent_verified'])

 def test_new_script_packet_is_derived_from_same_script_bytes(self):
  with tempfile.TemporaryDirectory() as d:
   f=Path(d)/'new_script.txt';f.write_text('场景：车站夜里。A发现门外脚步声，B没有回应。',encoding='utf-8')
   a=sty.compile_for_script(self.profile,'audience_first_suspense',f)
   b=sty.compile_for_script(self.profile,'blocking_space_reveal',f)
   self.assertEqual(a['original_script'],b['original_script'])
   self.assertEqual(a['original_script']['sha256'],sty.sha256(f))
   self.assertNotEqual(a['film_style_cues_not_story_facts'],b['film_style_cues_not_story_facts'])
   self.assertEqual(a['ordered_original_skill_stages'][0]['stage'],'structure-screenplay')
   self.assertTrue(all(x['native_skill_available_in_this_environment']==False for x in a['ordered_original_skill_stages']))
   self.assertEqual(a['generated_shots'],0)

 def test_web_style_lab_and_reference_image_http(self):
  import threading
  import urllib.request
  from http.server import ThreadingHTTPServer
  from studio_product import Handler
  server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
  task=threading.Thread(target=server.serve_forever,daemon=True);task.start()
  try:
   base=f'http://127.0.0.1:{server.server_port}'
   for path,mime in [('/style-lab','text/html'),('/style-profile-json','application/json'),
                     ('/style-comparison-json','application/json'),
                     ('/gpt_director_study/source_frames/CASE_A_05_604.4s.jpg','image/jpeg')]:
    with urllib.request.urlopen(base+path,timeout=10) as r:
     self.assertEqual(r.status,200)
     self.assertIn(mime,r.headers['Content-Type'])
     self.assertGreater(len(r.read()),500)
  finally:
   server.shutdown();server.server_close();task.join(timeout=5)

 def test_bad_source_frame_is_rejected(self):
  with tempfile.TemporaryDirectory() as td:
   original=sty.FRAMES/'CASE_A_01_595.0s.jpg'
   fake=Path(td)/original.name
   cv2.imwrite(str(fake),np.zeros((534,1280,3),dtype=np.uint8))
   with self.assertRaisesRegex(ValueError,'does NOT match'):
    sty.verify_reference_frames(sty.FILM,[({'second':595.0},fake)])

 def test_changed_evidence_timestamp_requires_reanalysis(self):
  with tempfile.TemporaryDirectory() as td:
   j=json.loads(sty.CASES.read_text(encoding='utf-8'))
   j['cases'][0]['observations'][0]['second']=594.8
   f=Path(td)/'cases.json';f.write_text(json.dumps(j,ensure_ascii=False),encoding='utf-8')
   with self.assertRaisesRegex(ValueError,'re-analyse'):
    sty.learn(case_file=f)

 def test_different_movies_can_use_different_annotations_without_changing_skill_source(self):
  with tempfile.TemporaryDirectory() as td:
   work=Path(td)
   video=work/'other.mp4'
   writer=cv2.VideoWriter(str(video),cv2.VideoWriter_fourcc(*'mp4v'),10,(160,120))
   self.assertTrue(writer.isOpened())
   for i in range(20):
    frame=np.full((120,160,3),25+i,dtype=np.uint8)
    writer.write(frame)
   writer.release()
   frames=work/'frames';frames.mkdir()
   cap=cv2.VideoCapture(str(video))
   seconds=[0.2,0.9]
   for i,t in enumerate(seconds,1):
    cap.set(cv2.CAP_PROP_POS_MSEC,t*1000)
    ok,frame=cap.read();self.assertTrue(ok)
    cv2.imwrite(str(frames/f'CASE_X_{i:02d}_{t:.1f}s.jpg'),frame)
   cap.release()
   cases={'cases':[{'id':'CASE_X','observations':[{'second':x,'visible':'synthetic scene'} for x in seconds],
                     'hypotheses':[],'unverified':['acting','camera']}]}
   cf=work/'cases.json';cf.write_text(json.dumps(cases),encoding='utf-8')
   mode=copy.deepcopy(sty.load(sty.DEFAULT_STYLE_SPEC)['modes']['blocking_space_reveal'])
   mode['case']='CASE_X';mode['evidence_timestamps_s']=seconds
   sf=work/'spec.json'
   sf.write_text(json.dumps({'schema':'FILM_STYLE_EVIDENCE_ANNOTATIONS/1.0',
     'name':'Other Film','profile_id':'other_film_no_leak',
     'modes':{'custom_spatial':mode}}),encoding='utf-8')
   new=sty.learn(video,cf,frames,sf)
   self.assertEqual(new['profile_id'],'other_film_no_leak')
   self.assertEqual(new['reference_frame_count'],2)
   self.assertNotEqual(new['film_source']['sha256'],self.profile['film_source']['sha256'])
   self.assertEqual(new['film_source']['duration_seconds_technical_proxy'],2.0)
   self.assertTrue(all(z['authenticity_check']=='PASS'
               for z in new['modes']['custom_spatial']['video_frame_authenticity_checks']))
   script=work/'script.txt';script.write_text('另一个剧本，另一个地点',encoding='utf-8')
   pkt=sty.compile_for_script(new,'custom_spatial',script)
   self.assertEqual(pkt['selected_reference_profile_id'],'other_film_no_leak')
   self.assertNotIn('a6f7c66',json.dumps(pkt))


if __name__=='__main__':unittest.main()
