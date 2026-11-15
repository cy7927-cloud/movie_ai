from __future__ import annotations
import json, unittest, hashlib, subprocess, sys
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import production_skill_handoff as pilot

class ProductionPilot(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.camera,cls.review=pilot.produce()

    def test_original_generated_images_are_not_reference_frames(self):
        src=pilot.SOURCE
        assert src.is_file() and src.stat().st_size>100000
        assert src.resolve()!=(ROOT/'data/source_video.mp4').resolve()
        film_hashes={r['sha256'] for r in json.loads((ROOT/'output/gpt_director_study/study_and_rehearsal.json').read_text())['frame_references']['CASE_A']}
        assert pilot.digest(src) not in film_hashes
        self.assertEqual(self.review['candidate_count'],7)
        self.assertEqual(self.review['generation_run_count'],1)
        self.assertEqual(len({x['candidate_sha256'] for x in self.review['reviews']}),7)

    def test_complete_production_handoff(self):
        p=self.camera
        self.assertTrue(p['preflight']['pass'])
        self.assertEqual(len(p['segments']),7)
        self.assertEqual(p['segments'][-1]['end_s'],32)
        self.assertEqual({x['upstream_beat_id'] for x in p['segments']},{'BEAT_S%02d'%i for i in range(1,8)})
        for s in p['segments']:
            for f in ('camera_position','camera_target','focus_target','asset_bindings','upstream_beat_id','props_at_start','props_at_end','positions_at_start','positions_at_end','sound','cut_reason'):
                self.assertTrue(s[f],(s['id'],f))
            self.assertEqual(s['camera_geometry_provenance'],'director_proposed_local_stage_not_measured_from_film')

    def test_media_provenance_verified_from_disk(self):
        for r in self.review['reviews']:
            p=ROOT/r['candidate_path']
            self.assertEqual(pilot.digest(p),r['candidate_sha256'])
            with Image.open(p) as im:
                im.verify()
            self.assertGreater(r['technical']['width'],400)
            self.assertGreater(r['technical']['height'],400)

    def test_independent_rejection_and_no_fake_approval(self):
        self.assertEqual(self.review['human_approved_count'],0)
        self.assertEqual(self.review['editorial_export']['status'],'BLOCKED')
        self.assertFalse(any(x['human_approved'] for x in self.review['reviews']))
        rejected=[x for x in self.review['reviews'] if x['status']=='REJECTED']
        self.assertEqual([x['shot_id'] for x in rejected],['S07'])
        self.assertTrue(all(x['notes'] for x in rejected))

    def test_original_film_is_untouched(self):
        self.assertTrue((ROOT/'data/source_video.mp4').is_file())
        status=__import__('production_cli').table_status()
        self.assertEqual(status['candidate_versions_total'],0) # source film shot task set separate

    def test_animatic_has_true_32_seconds(self):
        media=pilot.OUT/'AI分镜静帧预演_非成片.mp4'
        self.assertTrue(media.is_file())
        ffprobe=subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(media)],capture_output=True,text=True,check=True)
        self.assertAlmostEqual(float(ffprobe.stdout),32.0,places=1)

if __name__=='__main__':unittest.main()
