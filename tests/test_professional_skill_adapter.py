import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import gpt_director_study as base
import professional_skill_adapter as upstream
import professional_skill_experiment as experiment

class ProfessionalSkillsFilmTest(unittest.TestCase):
    def test_actual_source_frames_verified(self):
        source, cases, frames = upstream.validate_film_evidence()
        self.assertEqual(len(cases), 2)
        self.assertEqual(sum(map(len,frames.values())),18)
        self.assertEqual(len(source['sha256']),64)

    def test_external_skill_source_is_not_fabricated(self):
        status = upstream.status()
        self.assertIn('open-film-skills',status)
        self.assertIn('film-production-skills',status)
        for repo in status.values():
            self.assertEqual(repo['ready_for_native_skill_invocation'], all(x['installed'] for x in repo['skills']))
        for repo_name, repo in status.items():
            for skill in repo['skills']:
                if skill['installed']:
                    self.assertEqual(len(skill['sha256']),64)
                    self.assertTrue((upstream.ROOT/skill['upstream_file']).is_file())

    def test_native_packet_blocked_without_original_skill(self):
        packets = upstream.create_packets()
        self.assertEqual(packets['verified_frames'],18)
        self.assertEqual(len(packets['packets']),8)
        for packet in packets['packets']:
            self.assertEqual(packet['status'], 'READY_WITH_ORIGINAL_SKILL_TEXT' if packet['upstream_skill_loaded'] else 'BLOCKED_SKILL_NOT_INSTALLED')
        self.assertFalse(packets['director_artistic_quality_verified'])

    def test_existing_original_script_not_invented(self):
        result = upstream.build_original_scene_handoff()
        expected='READY_FOR_UPSTREAM_INVOCATION' if upstream.status()['film-production-skills']['ready_for_native_skill_invocation'] else 'BLOCKED_UPSTREAM_SKILLS_NOT_INSTALLED'
        self.assertEqual(result['preparation_state'],expected)
        self.assertEqual(len(result['request']['payload']['beats']),7)
        self.assertFalse(result['video_generated'])
        self.assertEqual(result['review_and_assemble_status'],'BLOCKED_NO_GENERATED_TAKES')

    def test_two_visual_strategies_are_not_identical(self):
        scene_data = base.load(upstream.ROOT/'data/gpt_director_scene.json')
        scene=scene_data['scene'];first=scene_data['revised_shots']
        second=experiment.make_alternate(first)
        self.assertEqual(base.audit(scene,first)['issue_count'],0)
        self.assertEqual(base.audit(scene,second)['issue_count'],0)
        self.assertEqual([s['id'] for s in first],[s['id'] for s in second])
        p1=experiment.audience_track(scene,first)
        p2=experiment.audience_track(scene,second)
        self.assertIn('REMOTE_LOGIN',p1[2]['audience_advantage_over_A'])
        self.assertNotIn('REMOTE_LOGIN',p2[2]['audience_advantage_over_A'])
        self.assertFalse('REMOTE_LOGIN' in p2[-1]['character_known']['A'])

    def test_research_result_does_not_pretend_native_execution(self):
        result=experiment.run()
        self.assertTrue(result['film_source_verified'])
        self.assertEqual(result['public_professional_methods_applied'],4)
        self.assertFalse(result['artistic_quality_verified'])
        count=sum(x['installed'] for repo in upstream.status().values() for x in repo['skills'])
        self.assertEqual(result['upstream_native_skills_installed'],count)
        data=json.loads((upstream.OUT/'film_skill_audit_experiment.json').read_text(encoding='utf-8'))
        self.assertFalse(data['native_upstream_skill_execution'])
        self.assertEqual(data['original_scene']['actual_generated_original_video'],0)

    def test_bad_repo_rejected_before_network(self):
        with self.assertRaises(ValueError):upstream.install('unknown')
        with self.assertRaises(ValueError):upstream.skill_file('open-film-skills','nonexistent')

if __name__ == '__main__':unittest.main()
