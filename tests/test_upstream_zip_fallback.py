"""Archive fallback tests: no live GitHub required or untrusted code execution."""
import io
import base64
import hashlib
import json
import tempfile
import urllib.error
import unittest
import zipfile
from pathlib import Path
from unittest import mock

import professional_skill_adapter as up


def archive(repo, *, malformed=None):
    stem = '62656456-ai-film-skills-abc' if repo == 'open-film-skills' else 'film-production-skills-main'
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr(stem+'/', b'')
        z.writestr(stem+'/LICENSE','License text')
        for skill in up.UPSTREAMS[repo]['skills']:
            z.writestr(stem+'/skills/'+skill+'/SKILL.md',
                       '---\nname: '+skill+'\ndescription: Original skill\n---\n'+
                       'See [reference](references/field-guide.md)\n')
            if not malformed or malformed != 'missing-reference':
                z.writestr(stem+'/skills/'+skill+'/references/field-guide.md','Original reference')
        if malformed=='traversal':z.writestr(stem+'/../escape.txt','attack')
    return stream.getvalue()


class TestOfficialZipInstall(unittest.TestCase):
    def test_full_offline_archive_can_install_all_targets(self):
        for repo in up.UPSTREAMS:
            with self.subTest(repo=repo), tempfile.TemporaryDirectory() as t:
                root=Path(t)
                f=root/'package.zip';f.write_bytes(archive(repo))
                with mock.patch.object(up,'SKILLS_ROOT',root/'external'):
                    result=up.install(repo,archive_path=f)
                    self.assertEqual(result['status'],'DOWNLOADED_READ_ONLY_NO_UPSTREAM_CODE_EXECUTED',result)
                    self.assertEqual(result['transport'],'verified_user_supplied_zip')
                    self.assertTrue(up.status()[repo]['ready_for_native_skill_invocation'])
                    self.assertEqual(up.install(repo,archive_path=f)['status'],'ALREADY_INSTALLED')

    def test_block_traversal_and_clean_partial_tree(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);f=root/'bad.zip';f.write_bytes(archive('film-production-skills',malformed='traversal'))
            with mock.patch.object(up,'SKILLS_ROOT',root/'external'):
                result=up.install('film-production-skills',archive_path=f)
                self.assertEqual(result['reason'],'archive_validation_failed')
                self.assertFalse((root/'external'/'film-production-skills').exists())
                self.assertFalse((root/'external'/'escape.txt').exists())

    def test_block_incomplete_skill_references(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);f=root/'bad.zip';f.write_bytes(archive('open-film-skills',malformed='missing-reference'))
            with mock.patch.object(up,'SKILLS_ROOT',root/'external'):
                result=up.install('open-film-skills',archive_path=f)
                self.assertEqual(result['reason'],'archive_validation_failed')
                self.assertFalse((root/'external'/'open-film-skills').exists())

    def test_official_api_fallback_without_git(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            with mock.patch.object(up,'SKILLS_ROOT',root/'external'), \
                 mock.patch.object(up.shutil,'which',return_value=None), \
                 mock.patch.object(up,'_fetch_official_zip',return_value=(archive('film-production-skills'),'https://api.github.com/repos/zhangzhangco/film-production-skills/zipball/main',[])):
                result=up.install('film-production-skills')
                self.assertEqual(result['transport'],'official_github_archive')
                self.assertTrue(up.status()['film-production-skills']['ready_for_native_skill_invocation'])

    def test_official_network_failure_reports_offline_path(self):
        with tempfile.TemporaryDirectory() as t:
            with mock.patch.object(up,'SKILLS_ROOT',Path(t)/'external'), \
                 mock.patch.object(up.shutil,'which',return_value=None), \
                 mock.patch.object(up,'_fetch_official_zip',return_value=(None,None,[{'source':'github','error':'blocked'}])), \
                 mock.patch.object(up,'_fetch_official_files_via_api',return_value=(None,None,[{'source':'api','error':'blocked'}])):
                result=up.install('open-film-skills')
                self.assertEqual(result['status'],'BLOCKED')
                self.assertIn('--archive',result['offline_fallback'])

    def test_blob_hash_verification(self):
        self.assertEqual(up._git_blob_sha1(b'hello\n'), 'ce013625030ba8dba906f756967f9e9ca394464a')

    def test_subset_rejects_unsafe_paths_and_only_includes_selected_skills(self):
        entries=[{'path':'LICENSE','type':'blob','sha':'a','size':1},
                 {'path':'skills/plan-camera-shots/SKILL.md','type':'blob','sha':'b','size':10},
                 {'path':'skills/unrelated/SKILL.md','type':'blob','sha':'c','size':10},
                 {'path':'../evil','type':'blob','sha':'d','size':10}]
        found=up._repo_api_subset('film-production-skills',entries)
        self.assertEqual([x['path'] for x in found],['LICENSE','skills/plan-camera-shots/SKILL.md'])

    def test_api_fallback_without_zip(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            with mock.patch.object(up,'SKILLS_ROOT',root/'external'), \
                 mock.patch.object(up.shutil,'which',return_value=None), \
                 mock.patch.object(up,'_fetch_official_zip',return_value=(None,None,[{'error':'blocked'}])), \
                 mock.patch.object(up,'_fetch_official_files_via_api',return_value=(archive('film-production-skills'),'github-api',[])):
                result=up.install('film-production-skills')
                self.assertEqual(result['transport'],'github_git_blob_api_sha_verified')
                self.assertTrue(up.status()['film-production-skills']['ready_for_native_skill_invocation'])

    def test_git_api_fetch_reconstructs_exact_official_blobs(self):
        repo='film-production-skills'
        files={'LICENSE':b'MIT',
               'skills/structure-screenplay/SKILL.md':b'---\nname: structure-screenplay\n---\n',
               'skills/plan-camera-shots/SKILL.md':b'---\nname: plan-camera-shots\n---\n',
               'skills/review-and-assemble/SKILL.md':b'---\nname: review-and-assemble\n---\n'}
        entries=[{'path':path,'type':'blob','sha':up._git_blob_sha1(raw),'size':len(raw)}
                 for path,raw in files.items()]
        table={x['sha']:files[x['path']] for x in entries}
        class Result(io.BytesIO):
            def geturl(self):return 'https://api.github.com/fake'
        def fake_urlopen(req,timeout):
            url=req.full_url
            if '/git/trees/' in url:
                return Result(json.dumps({'truncated':False,'tree':entries}).encode('utf-8'))
            if 'raw.githubusercontent.com' in url:
                raise urllib.error.URLError('raw blocked in this test')
            sha=url.split('/git/blobs/')[-1]
            raw=table[sha]
            return Result(json.dumps({'encoding':'base64','content':base64.b64encode(raw).decode()}).encode())
        with mock.patch.object(up.urllib.request,'urlopen',side_effect=fake_urlopen):
            data, source, errors=up._fetch_official_files_via_api(repo)
        self.assertEqual(errors,[])
        self.assertTrue(source.startswith('https://api.github.com/'))
        with tempfile.TemporaryDirectory() as t:
            up._safe_unpack_repo_zip(repo,data,Path(t)/'out')
            for path,raw in files.items():
                self.assertEqual((Path(t)/'out'/path).read_bytes(),raw)

    def test_git_api_rejects_mismatched_blob(self):
        raw=b'original'
        sha=up._git_blob_sha1(raw)
        class Result(io.BytesIO):
            def geturl(self):return 'https://api.github.com/fake'
        def fake_urlopen(req,timeout):
            if '/git/trees/' in req.full_url:
                paths=['LICENSE']+['skills/'+n+'/SKILL.md' for n in up.UPSTREAMS['film-production-skills']['skills']]
                return Result(json.dumps({'truncated':False,'tree':[{'path':p,'type':'blob','sha':sha,'size':8} for p in paths]}).encode())
            if 'raw.githubusercontent.com' in req.full_url:
                raise urllib.error.URLError('raw blocked in this test')
            return Result(json.dumps({'encoding':'base64','content':base64.b64encode(b'tampered').decode()}).encode())
        with mock.patch.object(up.urllib.request,'urlopen',side_effect=fake_urlopen):
            data, source, errors=up._fetch_official_files_via_api('film-production-skills')
        self.assertIsNone(data)
        self.assertTrue('SHA' in errors[0]['detail'])

    def test_reject_wrong_repository_archive(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);f=root/'wrong.zip';f.write_bytes(archive('film-production-skills'))
            with mock.patch.object(up,'SKILLS_ROOT',root/'external'):
                result=up.install('open-film-skills',archive_path=f)
                self.assertEqual(result['reason'],'archive_validation_failed')

if __name__=='__main__': unittest.main()
