#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Connect *real upstream* cinematic Agent Skills to the existing user-film evidence.

This is a thin provenance/transport adapter, not a replacement for professional
skills.  `install` fetches unmodified upstream source via git when network access
is available.  In offline environments, packets are clearly marked BLOCKED.
No untrusted downloaded executable code is ever run by this module.
"""
from __future__ import annotations

import argparse
import base64
import io
import tempfile
import urllib.error
import urllib.request
import urllib.parse
import zipfile
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "professional_skills"
SKILLS_ROOT = ROOT / "external_skills"

UPSTREAMS = {
    "open-film-skills": {
        "url": "https://github.com/62656456/ai-film-skills.git",
        "project": "Open Film Skills",
        "license": "Apache-2.0",
        "skills": ["director-agent", "ai-storyboard-director"],
        "purpose": "导演判断、人物行动、观众信息顺序、电影摄影与分镜",
    },
    "film-production-skills": {
        "url": "https://github.com/zhangzhangco/film-production-skills.git",
        "project": "Film Production Skills",
        "license": "MIT",
        "skills": ["structure-screenplay", "plan-camera-shots", "review-and-assemble"],
        "purpose": "以稳定剧本/镜头 ID 连接可执行摄影方案、连续性与审片结果",
    },
}


def file_hash(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def skill_file(repo, skill):
    if repo not in UPSTREAMS or skill not in UPSTREAMS[repo]["skills"]:
        raise ValueError("Unknown professional upstream or skill")
    return SKILLS_ROOT / repo / "skills" / skill / "SKILL.md"


def status():
    results = {}
    for repo, meta in UPSTREAMS.items():
        root = SKILLS_ROOT / repo
        rows = []
        for name in meta["skills"]:
            p = skill_file(repo, name)
            rows.append({
                "name": name,
                "upstream_file": str(p.relative_to(ROOT) if p.is_relative_to(ROOT) else p),
                "installed": p.is_file(),
                "sha256": file_hash(p) if p.is_file() else None,
            })
        validation_errors=[]
        if all(x['installed'] for x in rows):
            try:
                _validate_installed_tree(repo, root)
            except (ValueError, UnicodeError) as e:
                validation_errors.append(str(e))
        results[repo] = {
            "repository": meta["url"],
            "license_declared_upstream": meta["license"],
            "git_checkout_present": (root/".git").is_dir(),
            "license_file_present": (root/"LICENSE").is_file(),
            "skills": rows,
            "ready_for_native_skill_invocation": all(x["installed"] for x in rows) and not validation_errors,
            "validation_errors": validation_errors,
        }
    return results


def _repo_zip_urls(repo):
    """Only two official GitHub download hosts; no arbitrary mirror is trusted."""
    meta = UPSTREAMS[repo]
    slug = meta["url"].removeprefix("https://github.com/").removesuffix(".git")
    return [
        "https://api.github.com/repos/" + slug + "/zipball/main",
        "https://codeload.github.com/" + slug + "/zip/refs/heads/main",
    ]


def _fetch_official_zip(repo, timeout_s=45, max_zip_bytes=64*1024*1024):
    """GitHub API first (can work when github.com/git blocked), then codeload."""
    errors = []
    for url in _repo_zip_urls(repo):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "GPTDirector-SkillFetcher/1.0",
                "Accept": "application/vnd.github+json" if "api.github.com" in url else "application/zip",
            })
            with urllib.request.urlopen(req, timeout=timeout_s) as resp:
                resolved = resp.geturl()
                if not resolved.startswith("https://") or not any(
                    resolved.split("/", 3)[2] == hostname
                    for hostname in ("api.github.com", "codeload.github.com", "github.com")
                ):
                    raise ValueError("Unexpected archive redirect host: " + resolved[:160])
                buf = resp.read(max_zip_bytes + 1)
                if len(buf) > max_zip_bytes:
                    raise ValueError("Downloaded archive exceeds safety limit")
                if not zipfile.is_zipfile(io.BytesIO(buf)):
                    raise ValueError("Not a ZIP archive")
                return buf, url, errors
        except (OSError, ValueError, zipfile.BadZipFile) as e:
            errors.append({"source": url, "error": type(e).__name__, "detail": str(e)[:180]})
    return None, None, errors


def _git_blob_sha1(data):
    return hashlib.sha1(b'blob '+str(len(data)).encode('ascii')+b'\0'+data).hexdigest()


def _repo_api_subset(repo, entries):
    """Select each full upstream Skill directory and the shared schema tree."""
    prefixes=['skills/'+n+'/' for n in UPSTREAMS[repo]['skills']]
    if repo == 'film-production-skills':
        prefixes.extend(['schemas/common/', 'docs/'])
    fixed={'LICENSE','README.md','workflow.yaml'}
    result=[]
    for x in entries:
        path=x.get('path','')
        if x.get('type') == 'blob' and (path in fixed or any(path.startswith(pr) for pr in prefixes)):
            if path.startswith('/') or '..' in Path(path).parts or '\\' in path:
                raise ValueError('Unsafe remote Git tree path')
            if x.get('size',0)>16*1024*1024:
                raise ValueError('Oversized upstream blob')
            result.append(x)
    return sorted(result,key=lambda x:x['path'])


def _fetch_official_files_via_api(repo, timeout_s=25):
    """Fallback for hosts that can reach api.github.com but not Git/codeload.

    Git tree + Git Blob API; every file is checked against its advertised
    Git object SHA. Produces a complete snapshot of selected Skill folders.
    No downloaded Python/Node/bash files are executed.
    """
    slug=UPSTREAMS[repo]['url'].removeprefix('https://github.com/').removesuffix('.git')
    prefix='https://api.github.com/repos/'+slug
    token=os.environ.get('GITHUB_TOKEN','')
    headers={'User-Agent':'GPTDirector-SkillFetcher/1.0','Accept':'application/vnd.github+json'}
    if token:headers['Authorization']='Bearer '+token
    def get_json(url):
        with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=timeout_s) as r:
            if r.geturl().split('/',3)[2]!='api.github.com':
                raise ValueError('Unexpected GitHub API redirect')
            body=r.read(16*1024*1024+1)
            if len(body)>16*1024*1024:raise ValueError('Oversized API response')
            return json.loads(body)
    try:
        tree=get_json(prefix+'/git/trees/main?recursive=1')
        if tree.get('truncated'):raise ValueError('Git tree was truncated')
        files=_repo_api_subset(repo,tree.get('tree',[]))
        if not files or not any(x['path']=='LICENSE' for x in files):
            raise ValueError('No LICENSE or requested files listed in Git tree')
        for skill in UPSTREAMS[repo]['skills']:
            if 'skills/'+skill+'/SKILL.md' not in {x['path'] for x in files}:
                raise ValueError('Missing '+skill+' SKILL.md in Git tree')
        if len(files)>300:raise ValueError('Too many selected Skill files for API fallback')
        root=slug.split('/')[-1]+'-api-snapshot'
        io_buf=io.BytesIO()
        with zipfile.ZipFile(io_buf,'w',zipfile.ZIP_DEFLATED) as zip_out:
            for index,f in enumerate(files):
                sha=f['sha']
                raw=None
                # Raw GitHub is not rate-limited like REST Git Blobs. Verify
                # every retrieved file against the commit tree's object SHA.
                raw_url='https://raw.githubusercontent.com/'+slug+'/main/'+urllib.parse.quote(f['path'],safe='/')
                try:
                    req=urllib.request.Request(raw_url,headers={'User-Agent':'GPTDirector-SkillFetcher/1.0'})
                    with urllib.request.urlopen(req,timeout=timeout_s) as r:
                        if r.geturl().split('/',3)[2]=='raw.githubusercontent.com':
                            candidate=r.read(16*1024*1024+1)
                            if len(candidate)<=16*1024*1024 and _git_blob_sha1(candidate)==sha:
                                raw=candidate
                except (OSError,ValueError):
                    pass
                if raw is None:
                    payload=get_json(prefix+'/git/blobs/'+sha)
                    if payload.get('encoding')!='base64':
                        raise ValueError('Unsupported blob encoding: '+f['path'])
                    raw=base64.b64decode(payload['content'],validate=False)
                    if _git_blob_sha1(raw)!=sha:
                        raise ValueError('Git blob SHA mismatch: '+f['path'])
                zip_out.writestr(root+'/'+f['path'],raw)
        return io_buf.getvalue(), prefix+'/git/trees/main?recursive=1', []
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as e:
        return None, None, [{'source':prefix+'/git/trees/main?recursive=1',
                             'error':type(e).__name__,'detail':str(e)[:220]}]


def _safe_unpack_repo_zip(repo, zip_bytes, dest):
    """Transactional, path-safe unpacking; never executes any downloaded code."""
    if repo not in UPSTREAMS:
        raise ValueError("Unrecognized repository")
    dest = Path(dest)
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
        records = z.infolist()
        if len(records) > 4500:
            raise ValueError("Too many files")
        if sum(x.file_size for x in records) > 150 * 1024 * 1024:
            raise ValueError("Unpacked files exceed safety limit")
        dirs = {x.filename.split('/')[0] for x in records if '/' in x.filename}
        if len(dirs) != 1:
            raise ValueError("Ambiguous ZIP root")
        folder = next(iter(dirs))
        # Official codeload: repo-main; GitHub API: owner-repo-<sha>.
        slug = UPSTREAMS[repo]['url'].rsplit('/', 1)[-1].removesuffix('.git').lower()
        name = folder.lower()
        if not (name.startswith(slug+'-') or ('-'+slug+'-') in name):
            raise ValueError('Archive root does not match expected repository: ' + folder)
        dest.mkdir(parents=True, exist_ok=False)
        try:
            seen = set()
            for item in records:
                n = item.filename
                if item.is_dir() and n.rstrip('/') == folder:
                    continue
                if n in seen:
                    raise ValueError('Duplicate archive member: '+n[:160])
                seen.add(n)
                path = Path(n)
                if n.startswith('/') or '\\' in n or '\x00' in n or '..' in path.parts or len(path.parts) < 2:
                    raise ValueError("Unsafe archive path: " + n[:160])
                # Reject symbolic links and special file types.
                mode = (item.external_attr >> 16) & 0o170000
                if mode not in (0, 0o100000, 0o040000):
                    raise ValueError("Unsupported archive member type")
                local = dest.joinpath(*path.parts[1:])
                if item.is_dir():
                    local.mkdir(parents=True, exist_ok=True)
                else:
                    local.parent.mkdir(parents=True, exist_ok=True)
                    if item.file_size > 16*1024*1024:
                        raise ValueError("Oversized individual file")
                    with z.open(item) as inp, local.open('wb') as out:
                        shutil.copyfileobj(inp, out)
            _validate_installed_tree(repo, dest)
        except BaseException:
            shutil.rmtree(dest, ignore_errors=True)
            raise


def _validate_installed_tree(repo, root):
    if not (root/'LICENSE').is_file():
        raise ValueError('Repository LICENSE missing')
    for skill in UPSTREAMS[repo]['skills']:
        skill_dir = root/'skills'/skill
        p = skill_dir/'SKILL.md'
        if not p.is_file():
            raise ValueError('Missing original SKILL.md: ' + skill)
        text = p.read_text(encoding='utf-8')
        if not text.startswith('---\n') or ('name: '+skill) not in text.split('---',2)[1]:
            raise ValueError('Unexpected SKILL.md metadata: ' + skill)
        # Required linked references must not be silently absent.
        for ref in re.findall(r'\((references/[^)\s#]+)\)', text):
            refpath = skill_dir/ref
            if not refpath.is_file():
                raise ValueError('Missing referenced file: '+skill+'/'+ref)


def install(repo, timeout_s=120, archive_path=None):
    """Clone -> GitHub official archive -> local ZIP; verify before activating.

    --archive can be used with downloaded source archive when this machine is
    isolated. It must be a ZIP of the named full repository, not one SKILL.md.
    """
    if repo not in UPSTREAMS:
        raise ValueError('Choose a known upstream from --repo')
    dest = SKILLS_ROOT/repo
    if dest.exists():
        try:
            _validate_installed_tree(repo, dest)
            return {"status": "ALREADY_INSTALLED", "skills": status()[repo]}
        except ValueError:
            return {"status": "BLOCKED", "reason": "existing_invalid_destination", "directory": str(dest)}
    SKILLS_ROOT.mkdir(parents=True, exist_ok=True)

    if archive_path:
        archive = Path(archive_path)
        if not archive.is_file():
            return {"status": "BLOCKED", "reason": "archive_not_found", "path": str(archive)}
        if archive.stat().st_size > 64*1024*1024:
            return {"status": "BLOCKED", "reason": "archive_too_large"}
        data = archive.read_bytes()
        try:
            _safe_unpack_repo_zip(repo, data, dest)
        except (ValueError, OSError, zipfile.BadZipFile) as e:
            return {"status": "BLOCKED", "reason": "archive_validation_failed", "detail": str(e)[:300]}
        return {"status": "DOWNLOADED_READ_ONLY_NO_UPSTREAM_CODE_EXECUTED",
                "transport": "verified_user_supplied_zip", "archive_sha256": hashlib.sha256(data).hexdigest(),
                "skills": status()[repo]}

    problems=[]
    if shutil.which('git'):
        try:
            cmd=['git','clone','--depth','1','--',UPSTREAMS[repo]['url'],str(dest)]
            result=subprocess.run(cmd,capture_output=True,text=True,timeout=min(timeout_s,30),check=False)
            if result.returncode == 0:
                try:
                    _validate_installed_tree(repo, dest)
                    rev=subprocess.run(['git','-C',str(dest),'rev-parse','HEAD'],capture_output=True,text=True,check=False)
                    return {"status": "DOWNLOADED_READ_ONLY_NO_UPSTREAM_CODE_EXECUTED",
                            "transport": "git", "commit": rev.stdout.strip(), "skills": status()[repo]}
                except ValueError as e:
                    problems.append({'source':'git','error':'invalid_repo_tree','detail':str(e)})
            else:
                problems.append({'source':'git','error':'git_clone_failed','detail':result.stderr[-280:]})
        except subprocess.TimeoutExpired:
            problems.append({'source':'git','error':'git_clone_timeout'})
        if dest.exists(): shutil.rmtree(dest,ignore_errors=True)
    else:
        problems.append({'source':'git','error':'git_missing'})

    raw, source, errors=_fetch_official_zip(repo, timeout_s=min(timeout_s,40))
    problems.extend(errors)
    if raw is not None:
        try:
            _safe_unpack_repo_zip(repo, raw, dest)
        except (ValueError,OSError,zipfile.BadZipFile) as e:
            problems.append({'source': source, 'error': 'invalid_upstream_zip', 'detail': str(e)[:260]})
        else:
            return {"status": "DOWNLOADED_READ_ONLY_NO_UPSTREAM_CODE_EXECUTED",
                    "transport": "official_github_archive", "source": source,
                    "archive_sha256": hashlib.sha256(raw).hexdigest(), "skills": status()[repo]}
    # Last direct route: reconstruct the complete selected Skill folders from
    # GitHub's official Git object API, with per-file SHA1 verification.
    api_raw, api_source, api_errors=_fetch_official_files_via_api(repo, timeout_s=min(timeout_s,20))
    problems.extend(api_errors)
    if api_raw is not None:
        try:
            _safe_unpack_repo_zip(repo, api_raw, dest)
        except (ValueError,OSError,zipfile.BadZipFile) as e:
            problems.append({'source':api_source,'error':'invalid_api_snapshot','detail':str(e)[:260]})
        else:
            return {"status":"DOWNLOADED_READ_ONLY_NO_UPSTREAM_CODE_EXECUTED",
                    "transport":"github_git_blob_api_sha_verified","source":api_source,
                    "archive_sha256":hashlib.sha256(api_raw).hexdigest(),"skills":status()[repo]}
    return {"status": "BLOCKED", "reason": "all_official_download_routes_failed",
            "tried": problems,
            "offline_fallback": 'Download source ZIP on a networked PC and run install --repo '+repo+' --archive PATH_TO_ZIP'}

def validate_film_evidence():
    """Do not use a movie frame without real video provenance and a matching hash."""
    from gpt_director_study import verify_source
    source = verify_source()
    ref_data = read_json(ROOT / "output" / "gpt_director_study" / "study_and_rehearsal.json")
    cases = read_json(ROOT / "data" / "gpt_director_cases.json")["cases"]
    refs = ref_data["frame_references"]
    verified = {}
    for case in cases:
        frames = refs[case["id"]]
        if len(frames) != len(case["observations"]):
            raise ValueError("Reference count mismatch: " + case["id"])
        for k, (frame, observation) in enumerate(zip(frames, case["observations"])):
            p = (ROOT / frame["path"]).resolve()
            if not p.is_file() or not p.is_relative_to(ROOT.resolve()):
                raise ValueError("Missing or escaped film frame path")
            if file_hash(p) != frame["sha256"]:
                raise ValueError("Film frame tampering: " + frame["path"])
            if frame["time_s"] != observation["second"] or frame["observation"] != observation["visible"]:
                raise ValueError("Provenance/observation mismatch: " + case["id"])
        verified[case["id"]] = frames
    return source, cases, verified


def create_packets():
    source, cases, refs = validate_film_evidence()
    installed = status()
    packets = []
    roles = [
        ("open-film-skills", "director-agent", "导演/叙事：人物目标、表演、观众比人物知道的事实；不要凭空确立导演真意"),
        ("open-film-skills", "ai-storyboard-director", "导演/分镜：观众观看顺序、入画出画、轴线、观看终点、声音和机位") ,
        ("film-production-skills", "plan-camera-shots", "制作摄影方案：行动起止位置、机位/景别/焦点/运动、段落的前后状态和连续性"),
        ("film-production-skills", "review-and-assemble", "审片：先验证产生的媒体资产、原始镜头ID、来源时间码，再讨论取舍；不能用原片当待修复的失败作品"),
    ]
    for case in cases:
        for repo, name, question in roles:
            p = skill_file(repo, name)
            loaded = p.is_file()
            data = {
                "case_id": case["id"],
                "case_window_s": case["time_window"],
                "case_title": case["title"],
                "source_film_sha256": source["sha256"],
                "upstream_repository": UPSTREAMS[repo]["url"],
                "upstream_skill": name,
                "upstream_skill_sha256": file_hash(p) if loaded else None,
                "upstream_skill_loaded": loaded,
                "status": "READY_WITH_ORIGINAL_SKILL_TEXT" if loaded else "BLOCKED_SKILL_NOT_INSTALLED",
                "image_evidence": [{k: x[k] for k in ("time_s", "path", "sha256", "observation")}
                                   for x in refs[case["id"]]],
                "source_observations_not_verified_director_intent": True,
                "hypotheses_to_test": case["hypotheses"],
                "unverified": case["unverified"],
                "skill_task": question,
                "must_not_claim": ["原片剪辑有错误", "已经知道导演确切意图", "已经有生成的AI电影", "原片参考帧是原创AI画面"],
            }
            if loaded:
                # Verbatim external skill is loaded from the original git checkout,
                # not an assistant-generated simulation. The caller can pass the
                # SKILL.md text to a supported agent host, respecting its license.
                data["original_skill_location"] = str(p.relative_to(ROOT))
            packets.append(data)
    payload = {
        "film_excerpt_sha256": source["sha256"],
        "film_scope": "USER_776_SECOND_EXCERPT_NOT_COMPLETE_FEATURE",
        "method": "USE_UNMODIFIED_UPSTREAM_SKILL_MD_WHEN_INSTALLED",
        "upstream_status": installed,
        "source_cases": len(cases),
        "verified_frames": sum(map(len, refs.values())),
        "packets": packets,
        "actual_native_upstream_skill_executions": 0,
        "gpt_weight_updates": 0,
        "director_artistic_quality_verified": False,
    }
    write_json(OUT / "evidence_skill_packets.json", payload)
    return payload


def build_original_scene_handoff():
    """Feed an *existing*, not invented story into upstream production contracts.

    This does not execute a skill in absentia. The user has not approved any
    shot plan and final QC must remain blocked until real media is present.
    """
    evidence = create_packets()
    source = read_json(ROOT / "data" / "gpt_director_scene.json")
    scene = source["scene"]
    outline = [{"beat_id": "BEAT_" + s["id"],
                "story_source": "data/gpt_director_scene.json",
                "story_source_id": scene["id"],
                "start_s": s["start_s"], "end_s": s["end_s"],
                "existing_action": s["actor_action"],
                "audience_information": s.get("revealed_to_audience", []),
                "story_purpose": s["dramatic_purpose"]}
               for s in source["revised_shots"]]
    request = {
        "contract_version": "1.0.0",
        "request_id": "yaomao-transfer-original-observatory-001",
        "project": {"id": "yaomao-director-001", "title": "失联观测站",
                    "locale": "zh-CN", "format": "short-film",
                    "aspect_ratio": "2.39:1", "visual_medium": "live-action"},
        "payload": {
            "beats": outline,
            "existing_plan": source["revised_shots"],
            "spatial_baselines": scene["stage_map"],
            "initial_positions": scene["initial_positions"],
            "initial_character_knowledge": scene["initial_character_knowledge"],
            "source_film_learning_cases": ["CASE_A", "CASE_B"],
            "no_changes_to_locked_story_facts": scene["facts"],
            "ending_constraint": scene["ending_constraint"],
        },
        "options": {"phase": "SHOT_PLANNING_ONLY", "generation_enabled": False,
                    "allow_inference_of_missing_story_facts": False},
        "resume": {},
    }
    # Properly mark the upstream work not completed yet.
    result = {
        "request": request,
        "required_skill": "plan-camera-shots",
        "preparation_state": "READY_FOR_UPSTREAM_INVOCATION" if evidence["upstream_status"]["film-production-skills"]["ready_for_native_skill_invocation"] else "BLOCKED_UPSTREAM_SKILLS_NOT_INSTALLED",
        "native_skill_execution": False,
        "storyboard_quality_verified": False,
        "video_generated": False,
        "review_and_assemble_status": "BLOCKED_NO_GENERATED_TAKES",
        "note": "The pre-existing beat plan is research input only, not approved by the user or executed by the upstream skill."
    }
    write_json(OUT / "original_scene_upstream_request.json", result)
    return result


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor")
    install_p = sub.add_parser("install")
    install_p.add_argument("--repo", required=True, choices=list(UPSTREAMS))
    install_p.add_argument("--archive", default=None, help="Local full-repository GitHub ZIP for offline installation")
    sub.add_parser("prepare-film")
    sub.add_parser("prepare-original")
    a = p.parse_args()
    if a.command == "doctor": obj = status()
    elif a.command == "install": obj = install(a.repo, archive_path=a.archive)
    elif a.command == "prepare-film":
        q = create_packets()
        obj = {"cases": q["source_cases"], "frames": q["verified_frames"],
               "packets": len(q["packets"]),
               "ready_packets": sum(x["upstream_skill_loaded"] for x in q["packets"]),
               "native_upstream_executions": 0,
               "report": "output/professional_skills/evidence_skill_packets.json"}
    else:
        q = build_original_scene_handoff()
        obj = {"state": q["preparation_state"], "request_id": q["request"]["request_id"],
               "report": "output/professional_skills/original_scene_upstream_request.json"}
    print(json.dumps(obj, ensure_ascii=False, indent=2))

if __name__ == "__main__": main()
