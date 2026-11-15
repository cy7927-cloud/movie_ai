"""Real program components, explicitly mocked LOCAL model only (no cloud or paid API)."""
import base64,io,json,pathlib,sys,threading,unittest,urllib.request,urllib.error
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from unittest.mock import patch
import cv2,numpy as np
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import director_intent_model as intent
import studio_product as studio

class FakeLocalVisualModel(BaseHTTPRequestHandler):
    seen_images=0
    def log_message(self,*args):pass
    def do_POST(self):
        if self.path!='/api/chat':self.send_error(404);return
        body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        FakeLocalVisualModel.seen_images=len(body['messages'][-1]['images'])
        obj={'visible_subjects':['one dark cat; identity unknown'],'visible_actions':['static frame sequence'],
             'blocking_foreground_background':'unknown','shot_size_hypothesis':'wide shot',
             'camera_direction_hypothesis':'unknown','art_and_costume_observations':['stone court'],
             'lighting_and_palette':'warm daylight','narrative_intent_hypothesis':'possibly introduces a cat',
             'uncertainties':['subject identity not verified'], 'confidence':0.63}
        raw=json.dumps({'message':{'content':json.dumps(obj)}}).encode()
        self.send_response(200);self.send_header('Content-Type','application/json')
        self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)

class NewLocalIntegration(unittest.TestCase):
  def test_local_vision_host_restriction(self):
    with self.assertRaises(ValueError):intent.local_url('https://public.example.com/api/chat')
    with self.assertRaises(ValueError):intent.local_url('http://127.0.0.1:11434/unsafe')
    self.assertEqual(intent.local_url('http://localhost:11434'),'http://localhost:11434/api/chat')
  def test_local_visual_director_uses_real_3_anchors_but_stays_unverified(self):
    server=ThreadingHTTPServer(('127.0.0.1',0),FakeLocalVisualModel)
    thr=threading.Thread(target=server.serve_forever,daemon=True);thr.start()
    try:
      images=[ROOT/'data/references'/('SH_00003_'+s+'.jpg') for s in ['in','mid','out']]
      r=intent.request_model(images,model='mock_local_vision',url=f'http://127.0.0.1:{server.server_port}')
      self.assertEqual(FakeLocalVisualModel.seen_images,3)
      self.assertFalse(r['identity_verified']);self.assertFalse(r['camera_3d_verified'])
      self.assertEqual(r['status'],'UNVERIFIED_VISION_MODEL_DRAFT')
    finally:server.shutdown();server.server_close()
  def test_web_can_serve_real_fullfilm_dashboard_without_external_network(self):
    server=ThreadingHTTPServer(('127.0.0.1',0),studio.Handler)
    thr=threading.Thread(target=server.serve_forever,daemon=True);thr.start()
    try:
      with urllib.request.urlopen(f'http://127.0.0.1:{server.server_port}/longform',timeout=10) as r:
        content=r.read().decode();self.assertIn('86',content);self.assertIn('IN',content)
      with urllib.request.urlopen(f'http://127.0.0.1:{server.server_port}/file?path=data/references/SH_00001_mid.jpg',timeout=10) as r:
        self.assertEqual(r.headers['Content-Type'],'image/jpeg');self.assertGreater(len(r.read()),10000)
    finally:server.shutdown();server.server_close()
  def test_web_cannot_mutate_without_local_session_token(self):
    server=ThreadingHTTPServer(('127.0.0.1',0),studio.Handler)
    thr=threading.Thread(target=server.serve_forever,daemon=True);thr.start()
    try:
      req=urllib.request.Request(f'http://127.0.0.1:{server.server_port}/api/annotate',
          data=json.dumps({'task_id':'SH_00001:MID','intent':'unauthorized'}).encode(),
          headers={'Content-Type':'application/json'},method='POST')
      with self.assertRaises(urllib.error.HTTPError) as x:urllib.request.urlopen(req,timeout=10)
      self.assertEqual(x.exception.code,403)
    finally:server.shutdown();server.server_close()
  def test_reference_preview_visibly_watermarked_and_not_fake_movie(self):
    p=ROOT/'output/REFERENCE_previs_NOT_AI_MOVIE.mp4'
    c=cv2.VideoCapture(str(p));ok,f=c.read();c.release()
    self.assertTrue(ok);self.assertEqual(f.shape[:2],(360,640))
    self.assertGreater(float(np.std(f[0:34])),5.0)

if __name__=='__main__':unittest.main(verbosity=2)
