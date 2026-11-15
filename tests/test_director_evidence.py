"""Evidence-layer tests use user-uploaded film records; all motion is technical only.
No paid generation and no false movie reconstruction pass.
"""
import json,pathlib,sys,tempfile,threading,unittest,urllib.request
from http.server import ThreadingHTTPServer
import cv2,numpy as np
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import director_evidence as ev
import director as d
import studio_product as studio

class DirectorEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evidence=json.loads((ROOT/'output/evidence/director_evidence.json').read_text(encoding='utf-8'))
    def test_actual_film_all_shots_have_three_source_anchors(self):
        cards=self.evidence['cards'];self.assertEqual(len(cards),86)
        self.assertEqual(self.evidence['summary']['reference_anchors'],258)
        for c in cards:
            self.assertEqual(set(c['target_frames']),{'in','mid','out'})
            for p in c['target_frames'].values():self.assertTrue((ROOT/p).is_file())
            self.assertEqual(c['source_kind'],'ACTUAL_UPLOADED_FILM_REFERENCE_NOT_AI_GENERATED')
    def test_no_fake_generated_approval(self):
        s=self.evidence['summary'];self.assertEqual(s['current_generated_candidates'],0)
        self.assertEqual(s['fully_approved_shots'],0)
        self.assertFalse(s['film_recreation_accepted']);self.assertEqual(s['verified_3d_scene_models'],0)
        self.assertTrue(all(c['production_state']['gate']=='BLOCKED_UNVERIFIED' for c in self.evidence['cards']))
    def test_segment_is_contiguous_60_to_120_seconds_and_multi_shot(self):
        ch=self.evidence['challenge'];self.assertGreaterEqual(ch['duration_seconds'],60)
        self.assertLessEqual(ch['duration_seconds'],120);self.assertGreaterEqual(ch['shot_count'],5)
        idx={c['shot_id']:i for i,c in enumerate(self.evidence['cards'])}
        allidx=[idx[s] for s in ch['shot_ids']]
        self.assertEqual(allidx,list(range(min(allidx),max(allidx)+1)))
        self.assertAlmostEqual(self.evidence['cards'][allidx[0]]['start_sec'],ch['start_sec'])
        self.assertAlmostEqual(self.evidence['cards'][allidx[-1]]['end_sec'],ch['end_sec'])
    def test_observational_face_boxes_are_not_person_ids(self):
        count=0
        for c in self.evidence['cards']:
            self.assertFalse(c['asset_observations']['character_master_locked'])
            self.assertFalse(c['verified_3d_camera_path'])
            for o in c['asset_observations']['observations']:
                self.assertEqual(o['identity'],'UNKNOWN_UNVERIFIED');count+=1
        self.assertEqual(count,self.evidence['summary']['possible_face_observations_not_identity'])
    def test_computed_2d_motion_never_promotes_to_3d(self):
        found=[p for c in self.evidence['cards'] for p in c['apparent_motion'].values() if p['status']=='2D_ESTIMATE_AVAILABLE']
        self.assertGreater(len(found),20)
        self.assertEqual(len(found),self.evidence['summary']['motion_pairs_2d_computed'])
        self.assertTrue(all('3D' in p['warning'] for p in found))
    def test_known_synthetic_translation_is_measurable(self):
        rng=np.random.default_rng(4242);x=rng.integers(20,220,(240,480,3),dtype=np.uint8)
        # Textured cartoon-style visual primitives; offline measurement only.
        for i in range(40):cv2.circle(x,(int(rng.integers(15,465)),int(rng.integers(12,225))),4,(255,255,255),-1)
        y=cv2.warpAffine(x,np.float32([[1,0,11],[0,1,-7]]),(480,240),borderMode=cv2.BORDER_CONSTANT)
        with tempfile.TemporaryDirectory() as dtmp:
            a=pathlib.Path(dtmp)/'a.png';b=pathlib.Path(dtmp)/'b.png';cv2.imwrite(str(a),x);cv2.imwrite(str(b),y)
            m=ev.sparse_2d_motion(a,b)
            self.assertEqual(m['status'],'2D_ESTIMATE_AVAILABLE')
            self.assertAlmostEqual(m['dx_px_at_480w'],11,delta=2)
            self.assertAlmostEqual(m['dy_px_at_480w'],-7,delta=2)
            self.assertIn('Not a 3D',m['warning'])
    def test_black_frame_is_explicitly_uncertain(self):
        with tempfile.TemporaryDirectory() as dtmp:
            p=pathlib.Path(dtmp)/'b.png';cv2.imwrite(str(p),np.zeros((180,320,3),np.uint8))
            m=ev.sparse_2d_motion(p,p)
            self.assertEqual(m['status'],'LOW_TEXTURE_UNDETERMINED')
    def test_three_actual_film_technical_calibrations_are_not_model_outputs(self):
        results=self.evidence['calibration'];self.assertEqual(len(results),3)
        for r in results:
            self.assertEqual(r['grade'],'CALIBRATION_ONLY_NOT_GENERATION_OR_SEMANTIC_QA')
            self.assertTrue((ROOT/r['comparison_board']).is_file())
            self.assertTrue(r['technical_score_improved'])
            self.assertGreater(r['after']['technical_score'],r['before']['technical_score'])
        with d.connect() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM attempts').fetchone()[0],0)
    def test_new_http_dashboard_and_images_resolve(self):
        server=ThreadingHTTPServer(('127.0.0.1',0),studio.Handler)
        t=threading.Thread(target=server.serve_forever,daemon=True);t.start()
        try:
            origin=f'http://127.0.0.1:{server.server_port}'
            for path,needle in [('/evidence','镜头证据索引'),('/evidence-data','shot_candidates'),('/acceptance','八个工业生产阶段'),('/','打开导演证据')]:
                with urllib.request.urlopen(origin+path,timeout=10) as resp:
                    self.assertEqual(resp.status,200)
                    self.assertIn(needle,resp.read().decode('utf-8'))
            with urllib.request.urlopen(origin+'/file?path=output/evidence/calibration/SH_00003_QA_CALIBRATION.jpg',timeout=10) as resp:
                self.assertEqual(resp.headers['Content-Type'],'image/jpeg')
                self.assertGreater(len(resp.read()),20000)
        finally:server.shutdown();server.server_close()

if __name__=='__main__': unittest.main(verbosity=2)
