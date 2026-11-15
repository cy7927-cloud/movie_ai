"""Non-fiction acceptance: real film evidence / skill activation, not movie quality."""
import hashlib, http.client, json, threading, unittest
from http.server import HTTPServer
from pathlib import Path
import film_style_dense_study as v
import studio_product

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/dense_film_style_study'
SOURCE=Path('/mnt/data/妖猫传_全片段密集采样')

class DenseFilmResearchTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.d=json.loads((OUT/'film_study_data.json').read_text(encoding='utf8'))

 def test_actual_video_hash_and_scope(self):
  self.assertEqual(v.sha(ROOT/'data/source_video.mp4'),v.VIDEO_SHA)
  self.assertEqual(self.d['source']['duration_seconds'],776.477)
  self.assertIn('不是完整电影',self.d['source']['scope'])

 def test_52_windows_and_3106_frames_actual(self):
  x=self.d['windows_15sec'];self.assertEqual(len(x),52)
  self.assertEqual(sum(z['frame_count'] for z in x),3106)
  self.assertEqual(sum(z['sensitive_change_candidates'] for z in x),595)
  self.assertEqual(sum(z['strong_change_candidates'] for z in x),116)
  self.assertTrue(all(0 <= z['luma_mean_0_255'] <=255 for z in x))
  self.assertTrue(all(z['audio_rms']>=0 for z in x))
  self.assertTrue(all('艺术质量' in z['caution'] for z in x))

 def test_minute_and_deep_cards_cover_source(self):
  c=self.d['minutes'];self.assertEqual(len(c),13)
  self.assertEqual(len(self.d['deep_studies']),15)
  self.assertEqual(c[0]['id'],'MIN_00');self.assertEqual(c[-1]['id'],'MIN_12')
  for x in c:
   self.assertTrue(x['visible_facts'] and x['unknowns'] and x['filmmaking_hypothesis_unverified'])
   self.assertTrue((OUT/x['evidence_image']).is_file())
   for y in x['reference_frames']:
    self.assertTrue((OUT/y['path']).is_file())

 def test_frames_and_boards_are_exact_copies_of_user_supplied_material(self):
  manifest=json.loads((OUT/'evidence_manifest.json').read_text(encoding='utf-8'))
  self.assertEqual(manifest['source_film_sha256'],v.VIDEO_SHA)
  self.assertEqual(manifest['file_count'],117)
  for rel,entry in manifest['files'].items():
   self.assertEqual(v.sha(OUT/rel),entry['sha256'])
   if SOURCE.is_dir():
    self.assertEqual(v.sha(SOURCE/entry['origin_relative']),entry['sha256'])

 def test_not_claiming_native_skill_execution_or_film_completion(self):
  p=self.d['professional_skill_activation']
  self.assertTrue(p['upstream_skills_unchanged'])
  self.assertFalse(p['research_boundary']['skill_native_execution_verified'])
  self.assertFalse(p['research_boundary']['style_transfer_quality_proven'])
  self.assertFalse(p['research_boundary']['director_intent_verified'])
  self.assertEqual(self.d['counts']['transfer_films_completed'],0)
  self.assertEqual(self.d['counts']['source_audio_observed_semantically'],0)

 def test_original_professional_skills_unchanged(self):
  for name,gitblob in [('plan-camera-shots','c527ae79af43deec004f51fc52b0e94ba2eb7ffe'),('review-and-assemble','4c6e975e8977e8c6bb46cb89139069f4a1fbb2b9')]:
   p=ROOT/'external_skills/film-production-skills/skills'/name/'SKILL.md'
   b=p.read_bytes()
   git_hash=hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
   self.assertEqual(git_hash,gitblob)

 def test_web_viewer_and_media_without_traversal(self):
  server=HTTPServer(('127.0.0.1',0),studio_product.Handler)
  thread=threading.Thread(target=server.serve_forever,daemon=True)
  thread.start()
  try:
   base=server.server_address[1]
   def get(path):
    conn=http.client.HTTPConnection('127.0.0.1',base,timeout=10)
    conn.request('GET',path)
    r=conn.getresponse();status=r.status;body=r.read();headers=dict(r.getheaders());conn.close();return status,body,headers
   for path in ['/dense-style-study/','/dense-style-study/film_study_data.json','/dense-style-study/evidence_manifest.json','/dense-style-study/evidence/minute/minute_00.jpg','/dense-style-study/evidence/15sec/window_40.jpg','/dense-style-study/evidence/frames/0604s.jpg']:
    s,b,h=get(path)
    self.assertEqual(s,200,path)
    self.assertGreater(len(b),500,path)
    self.assertIn('nosniff',h.get('X-Content-Type-Options',''))
   for path in ['/dense-style-study/../../MANIFEST.sha256','/dense-style-study/private_gateway_bridge.py','/dense-style-study/evil.svg','/dense-style-study/evidence/15sec/window_99.jpg']:
    s,_,_=get(path)
    self.assertIn(s,[403,404],path)
  finally:
   server.shutdown();server.server_close();thread.join(timeout=2)

if __name__=='__main__': unittest.main()
