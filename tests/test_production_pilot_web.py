from __future__ import annotations
import json,sys,threading,unittest,urllib.request,urllib.error,urllib.parse
from http.server import ThreadingHTTPServer
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import studio_product as studio
import official_skill_source_audit as source

class PilotWebTest(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.srv=ThreadingHTTPServer(('127.0.0.1',0),studio.Handler)
  cls.url='http://127.0.0.1:'+str(cls.srv.server_port)
  cls.thread=threading.Thread(target=cls.srv.serve_forever,daemon=True)
  cls.thread.start()
 @classmethod
 def tearDownClass(cls):
  cls.srv.shutdown();cls.srv.server_close();cls.thread.join(timeout=2)
 def test_real_artifacts_servable(self):
  paths=['/production-pilot','/production-pilot-json','/production-pilot-review',
   '/production-pilot/generated_stills/S07_AI_CANDIDATE.png',
   '/production-pilot/'+urllib.parse.quote('AI分镜静帧预演_非成片.mp4')]
  for p in paths:
   with self.subTest(p=p),urllib.request.urlopen(self.url+p,timeout=12) as r:
    self.assertEqual(r.status,200)
    self.assertGreater(len(r.read()),300)
 def test_no_arbitrary_file_read(self):
  for p in ['/production-pilot/../../data/source_video.mp4','/production-pilot/MANIFEST.sha256',
            '/production-pilot/generated_stills/S01_AI_CANDIDATE.png/../secret.txt']:
   req=urllib.request.Request(self.url+p)
   with self.subTest(p=p),self.assertRaises(urllib.error.HTTPError) as context:
    urllib.request.urlopen(req,timeout=4)
   self.assertIn(context.exception.code,(403,404))
 def test_official_skill_docs_are_real_not_fabricated(self):
  s=source.verify()
  self.assertGreaterEqual(s['authentic_original_files_verified'],6)
  self.assertEqual(len(s['original_skill_texts_verified']),2)
  self.assertFalse(s['native_skill_host_installed'])
  self.assertFalse(s['full_pipeline_ready'])

if __name__=='__main__':unittest.main()
