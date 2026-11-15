"""Evidence and manual cut review. No silent modification of user shot tables."""
import csv,json,pathlib,sys,tempfile,threading,subprocess,unittest,urllib.request,urllib.error
from unittest.mock import patch
from http.server import ThreadingHTTPServer
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import cut_review as c,studio_product as studio

class CutDisagreementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report=json.loads((ROOT/'output/cut_review/cut_disagreements.json').read_text())
    def test_fullfilm_two_detector_disagreements(self):
        x=self.report
        self.assertEqual(x['main_cut_count'],85)
        self.assertEqual(x['ffmpeg_cut_count'],94)
        self.assertEqual(x['two_detector_matches'],66)
        self.assertEqual(x['main_only'],19)
        self.assertEqual(x['ffmpeg_only'],28)
        self.assertEqual(x['disagreement_count'],47)
    def test_one_to_one_matching_does_not_double_count(self):
        a,b,f=c.compare_cuts([1.0,1.2,5],[1.1,5.1],.45)
        self.assertEqual(len(a),2);self.assertEqual(len(b),1);self.assertEqual(len(f),0)
    def test_all_disputed_boundaries_have_pair_images_and_unverified_state(self):
        for r in self.report['disputed']:
            self.assertTrue((ROOT/r['sheet']).is_file())
            self.assertIn(r['type'],('MAIN_ONLY','FFMPEG_ONLY'))
            self.assertIsNone(r['is_true_cut'])
            self.assertEqual(r['review_state'],'NOT_REVIEWED')
        self.assertEqual(self.report['confirmed_editorial_cuts'],0)
    def test_review_decision_is_only_a_note_and_is_source_bound(self):
        with tempfile.TemporaryDirectory() as dtmp:
            root=pathlib.Path(dtmp);(root/'data').mkdir();(root/'output/cut_review').mkdir(parents=True)
            (root/'data/project_manifest.json').write_text(json.dumps({'source_sha256':'sha_fake_for_unit_test'}))
            payload={'source_sha256':'sha_fake_for_unit_test','disputed':[{'id':'FFMPEG_ONLY_10.000','review_state':'NOT_REVIEWED','type':'FFMPEG_ONLY','time_sec':10.,'observation':{},'sheet':'output/cut_review/cut_disagreements_page_01.jpg','is_true_cut':None}],
                     'main_cut_count':0,'ffmpeg_cut_count':1,'two_detector_matches':0,'disagreement_count':1,'reviewed_count':0}
            (root/'output/cut_review/cut_disagreements.json').write_text(json.dumps(payload))
            with patch.object(c,'ROOT',root):
                with self.assertRaises(ValueError):c.mark('FFMPEG_ONLY_10.000','CONFIRMED_CUT','','')
                with self.assertRaises(KeyError):c.mark('unknown','CONFIRMED_CUT','director','reviewed')
                result=c.mark('FFMPEG_ONLY_10.000','CONFIRMED_CUT','director','visible hard cut')
                self.assertTrue(result['saved'])
                saved=json.loads((root/'data/cut_review_decisions.json').read_text())
                self.assertEqual(saved['reviews']['FFMPEG_ONLY_10.000']['decision'],'CONFIRMED_CUT')
                self.assertFalse((root/'data/director.sqlite3').exists())
                report=json.loads((root/'output/cut_review/cut_disagreements.json').read_text())
                self.assertEqual(report['reviewed_count'],1)
    def test_ui_cut_review_routes_and_auth(self):
        server=ThreadingHTTPServer(('127.0.0.1',0),studio.Handler)
        thr=threading.Thread(target=server.serve_forever,daemon=True);thr.start()
        try:
            site=f'http://127.0.0.1:{server.server_port}'
            with urllib.request.urlopen(site+'/cuts',timeout=10) as rsp:
                page=rsp.read().decode('utf-8');self.assertIn('分歧切镜',page)
                self.assertIn('submitReview',page)
            with urllib.request.urlopen(site+'/cut-image?name=cut_disagreements_page_01.jpg',timeout=10) as rsp:
                self.assertEqual(rsp.headers['Content-Type'],'image/jpeg')
                self.assertGreater(len(rsp.read()),30000)
            bad=urllib.request.Request(site+'/api/cut-decision',data=json.dumps({'id':'FFMPEG_ONLY_0.100','decision':'CONFIRMED_CUT','reviewer':'bad','reason':'no permission'}).encode(),headers={'Content-Type':'application/json'},method='POST')
            with self.assertRaises(urllib.error.HTTPError) as ctx:urllib.request.urlopen(bad,timeout=10)
            self.assertEqual(ctx.exception.code,403)
        finally:server.shutdown();server.server_close()
    def test_imported_second_movie_has_own_source_specific_evidence(self):
        """Full portable import on a DIFFERENT 9s synthetic movie, no cloud API."""
        with tempfile.TemporaryDirectory() as folder:
            dest=pathlib.Path(folder)/'new_film'
            import os
            env=dict(os.environ,OPENBLAS_NUM_THREADS='1')
            proc=subprocess.run([sys.executable,str(ROOT/'production_cli.py'),'import-film',
                 str(ROOT/'tests/fixtures/synthetic_second_movie.mp4'),'--out',str(dest)],
                 capture_output=True,text=True,timeout=160,env=env)
            self.assertEqual(proc.returncode,0,proc.stderr[-1800:])
            self.assertTrue((dest/'DIRECTOR_EVIDENCE.html').is_file())
            self.assertTrue((dest/'output/cut_review/index.html').is_file())
            source=json.loads((dest/'data/project_manifest.json').read_text())
            cut=json.loads((dest/'data/cut_detector_ffmpeg_times.json').read_text())
            self.assertEqual(cut['source_sha256'],source['source_sha256'])
            self.assertEqual(source['shot_count']*3,len(list((dest/'data/references').glob('*.jpg'))))
            self.assertEqual(json.loads((dest/'output/evidence/director_evidence.json').read_text())['summary']['current_generated_candidates'],0)

if __name__=='__main__':unittest.main(verbosity=2)
