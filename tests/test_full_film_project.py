"""All tests use the ACTUAL user-supplied 776s video project's generated records.
No paid image/video API calls are made. Provider loops are tested separately by mock.
"""
import csv,hashlib,json,os,pathlib,sqlite3,subprocess,sys,tempfile,unittest
from unittest.mock import patch
import cv2,numpy as np
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import director as d,product_engine as eng,production_cli as cli,longform_engine as long,production_acceptance as acceptance

class FullFilmProject(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.meta=json.loads((ROOT/'data/project_manifest.json').read_text(encoding='utf-8'))
    with (ROOT/'data/shots_source.csv').open(encoding='utf-8') as f:
      cls.rows=list(csv.DictReader(f))
  def test_actual_uploaded_12minute_video_source(self):
    s=long.ffprobe(ROOT/'data/source_video.mp4')
    self.assertAlmostEqual(s['seconds'],776.477,delta=.2)
    self.assertTrue(len(s['streams'])>=2)
  def test_full_upload_sha256_provenance(self):
    self.assertEqual(long.hashfile(ROOT/'data/source_video.mp4'),self.meta['source_sha256'])
  def test_shot_timeline_covers_full_uploaded_clip(self):
    self.assertGreater(len(self.rows),40)
    self.assertAlmostEqual(float(self.rows[0]['start_sec']),0,places=2)
    prev=0
    for row in self.rows:
      self.assertAlmostEqual(float(row['start_sec']),prev,delta=.003)
      prev=float(row['start_sec'])+float(row['duration_sec'])
    self.assertAlmostEqual(prev,self.meta['duration_seconds'],delta=.01)
  def test_full_resolution_real_reference_images(self):
    self.assertEqual(self.meta['reference_resolution'],'1280x534')
    self.assertEqual(self.meta['reference_upscaled'],False)
    for row in (self.rows[0],self.rows[len(self.rows)//2],self.rows[-1]):
      for a in ('in','mid','out'):
        im=cv2.imread(str(ROOT/'data/references'/row[a]));self.assertIsNotNone(im)
        self.assertEqual(tuple(im.shape[:2]),(534,1280))
  def test_database_tracks_three_anchors_without_fake_candidates(self):
    with d.connect() as c:
      for row in (self.rows[0],self.rows[-1]):
        for anchor in d.ANCHORS:
          task=c.execute('SELECT * FROM tasks WHERE id=?',(row['shot_id']+':'+anchor,)).fetchone()
          self.assertIsNotNone(task)
          self.assertEqual(d.sha(ROOT/task['reference']),task['reference_sha'])
      self.assertEqual(c.execute('SELECT count(*) FROM attempts').fetchone()[0],0)
  def test_audit_does_not_autopass_source_frame(self):
    a=eng.project_audit()
    self.assertEqual(a['stats']['shots'],len(self.rows))
    self.assertEqual(a['stats']['frames'],len(self.rows)*3)
    self.assertEqual(a['stats']['anchors_with_candidates'],0)
    self.assertEqual(a['stats']['shots_fully_approved'],0)
  def test_final_export_refused_without_verified_generation(self):
    result=eng.export_cut()
    self.assertEqual(result['result'],'BLOCKED')
  def test_complete_real_reference_continuity_but_no_generation(self):
    o=json.loads((ROOT/'data/continuity_reference.json').read_text(encoding='utf-8'))
    self.assertEqual(o['intra_shot_pairs'],len(self.rows)*2)
    self.assertEqual(o['adjacent_shot_pairs'],len(self.rows)-1)
    self.assertIn('NOT_MEASURABLE',o['reconstructed_content_continuity_status'])
  def test_assets_do_not_claim_character_identification(self):
    a=json.loads((ROOT/'data/asset_bible_observations.json').read_text(encoding='utf-8'))
    self.assertEqual(len(a['verified_costume_states']),0)
    self.assertEqual(len(a['3d_scene_geometry']),0)
    self.assertTrue(all(s['identity']=='UNKNOWN_UNVERIFIED' for s in a['face_observations']))
  def test_second_scene_detector_marks_boundaries_unverified(self):
    x=json.loads((ROOT/'data/cut_detector_crosscheck.json').read_text(encoding='utf-8'))
    self.assertTrue(x['human_boundary_review_required'])
    self.assertGreater(x['ffmpeg_candidate_cut_count'],20)
  def test_production_jobs_match_reference_cards(self):
    p=ROOT/'output/shot_work_orders.jsonl';jobs=[json.loads(x) for x in p.read_text(encoding='utf-8').splitlines()]
    self.assertEqual(len(jobs),len(self.rows)*3)
    self.assertTrue(all(not x['video_model_required_for_still_stage'] for x in jobs))
    self.assertTrue(all(x['approval']=='NOT_APPROVED' for x in jobs))
  def test_workbench_and_preview_have_no_false_success_claim(self):
    s=(ROOT/'PROJECT_STORYBOARD_REPORT.html').read_text(encoding='utf-8')
    self.assertIn('候选镜头',s)
    self.assertIn('AI独立生成',s)
    r=(ROOT/'output/FINAL_ACCEPTANCE.json').read_text(encoding='utf-8')
    self.assertIn('NOT_ACCEPTED_FOR_AI_FILM_RECONSTRUCTION',r)
  def test_technical_metrics_do_not_auto_pass_semantic_identity(self):
    scores={'technical_score':.999,'same_file_sha':False,'reference_texture_std':50}
    self.assertEqual(d.final_gate(scores,None,'manual'),'BLOCKED_NO_SEMANTIC_REVIEW')
  def test_local_provider_never_runs_without_model_config(self):
    import local_model_bridge as b
    with patch.object(b,'CONFIG',ROOT/'this_file_does_not_exist.json'):
      self.assertFalse(b.get_status()['available'])
  def test_imported_reference_image_cannot_be_faked_as_new_generation(self):
    q={'technical_score':1.,'same_file_sha':True,'reference_texture_std':50}
    vision={'scores':{k:1. for k in d.ISSUES if k not in ('continuity',)},'identity_verified':True,'confidence':1,'director_ready':True,'issues':[]}
    self.assertEqual(d.final_gate(q,vision,'openai'),'REJECTED_REFERENCE_COPY')
  def test_reconstructed_character_or_3d_asset_not_falsely_reported(self):
    summary=acceptance.report()
    self.assertEqual(summary['verified_actor_identities'],0)
    self.assertEqual(summary['verified_3d_assets'],0)
    self.assertEqual(summary['model_verified_video_shots'],0)
  def test_hash_stream_does_not_hang_at_EOF(self):
    with tempfile.TemporaryDirectory() as root:
      p=pathlib.Path(root)/'x';p.write_bytes(b'hello')
      self.assertEqual(long.hashfile(p),hashlib.sha256(b'hello').hexdigest())

if __name__=='__main__':unittest.main(verbosity=2)
