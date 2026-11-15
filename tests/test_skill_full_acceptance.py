"""Regression gates for real product acceptance and truthful Skill status."""
import json, subprocess, sys, threading, unittest, urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
import studio_product as studio

class SkillProductE2ETests(unittest.TestCase):
    def test_acceptance_report_is_explicit_about_unfinished_product(self):
        r=json.loads((ROOT/'output/skill_end_to_end_acceptance/acceptance.json').read_text(encoding='utf-8'))
        self.assertEqual(r['summary']['stages_tested'],12)
        self.assertEqual(r['summary']['failure_count'],0)
        self.assertFalse(r['summary']['release_ready'])
        self.assertEqual(r['summary']['native_professional_skills_executed'],0)
        self.assertEqual(r['summary']['original_ai_stills_accepted'],0)
        self.assertIn('原版专业Skill安装与调用',r['summary']['blocked_stages'])
        self.assertEqual(r['summary']['original_ai_stills_generated'],7)
        self.assertEqual(r['summary']['original_ai_generation_runs'],1)
        self.assertEqual(r['summary']['blocked_stages'],['原版专业Skill安装与调用'])
        done={x['stage']:x['result'] for x in r['stages']}
        self.assertEqual(done['真实原创AI分镜图生成'],'PASS')
        self.assertEqual(done['摄影Skill生成级镜头交接合同'],'PASS')
    def test_acceptance_page_is_actually_served_by_studio(self):
        server=ThreadingHTTPServer(('127.0.0.1',0),studio.Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        try:
            base=f'http://127.0.0.1:{server.server_port}'
            with urllib.request.urlopen(base+'/skill-acceptance',timeout=8) as r:
                body=r.read().decode('utf-8')
                self.assertEqual(r.status,200)
                self.assertIn('《妖猫传》整套成品功能验收',body)
            with urllib.request.urlopen(base+'/skill-acceptance-json',timeout=8) as r:
                data=json.load(r)
                self.assertFalse(data['summary']['release_ready'])
            with urllib.request.urlopen(base+'/skill-acceptance-report',timeout=8) as r:
                self.assertIn('NOT PRODUCTION READY',r.read().decode('utf-8'))
        finally:
            server.shutdown();server.server_close();thread.join(timeout=5)
    def test_cli_exposes_one_command_for_real_acceptance(self):
        cli=(ROOT/'production_cli.py').read_text(encoding='utf-8')
        self.assertIn('skill-acceptance',cli)
        self.assertTrue((ROOT/'skill_product_acceptance.py').is_file())

if __name__=='__main__':unittest.main()
