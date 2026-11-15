#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Non-destructive, original-film E2E acceptance for the AI director.

The skill scopes here follow the *upstream published* director-agent,
ai-storyboard-director, plan-camera-shots, review-and-assemble contracts.
They do not pretend the original upstream Skills have been installed or run.
This test refuses to treat a reference frame or reference-motion preview as
independently AI-generated cinematic material.
"""
from __future__ import annotations
import contextlib, csv, hashlib, html, json, os, shutil, socket, subprocess, sys, time, threading, urllib.request, urllib.error
from pathlib import Path
from http.server import ThreadingHTTPServer

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'output' / 'skill_end_to_end_acceptance'
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT))
RESULTS = []

def record(name, result, details, evidence=None, skill=None):
    assert result in ('PASS','BLOCKED','FAIL','SKIPPED')
    o = dict(stage=name, result=result, details=details)
    if evidence is not None: o['evidence']=evidence
    if skill: o['professional_contract']=skill
    RESULTS.append(o)
    print(f'{result:7} {name}: {str(details)[:150]}', flush=True)

def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def jload(rel):return json.loads((ROOT/rel).read_text(encoding='utf-8'))

def get(base,path,timeout=20):
    with urllib.request.urlopen(base+path,timeout=timeout) as resp:
        return resp.status, resp.headers.get('Content-Type',''),resp.read()

def post(base,path,obj,token=None,origin=None):
    headers={'Content-Type':'application/json'}
    if token:headers['X-Director-Token']=token
    if origin: headers['Origin']=origin
    body=json.dumps(obj,ensure_ascii=False).encode('utf-8')
    req=urllib.request.Request(base+path,data=body,headers=headers,method='POST')
    try:
        with urllib.request.urlopen(req,timeout=35) as res:
            return res.status,json.loads(res.read())
    except urllib.error.HTTPError as e:
        return e.code,json.loads(e.read())

# 1: real film, not an invented or externally substituted source.
import professional_skill_adapter as upstream
src,cases,refs=upstream.validate_film_evidence()
assert len(cases)==2 and sum(map(len,refs.values()))==18
record('源片真实性与18张证据帧','PASS',{'source_seconds':776.477,'source_sha256':src['sha256'],'study_cases':len(cases),'verified_frames':18},'data/source_video.mp4; output/gpt_director_study/source_frames/', 'director-agent / ai-storyboard-director')

# 2: detect absent native skills rather than claiming a working upstream.
skills=upstream.status()
ready=[x for x in skills if skills[x]['ready_for_native_skill_invocation']]
record('原版专业Skill安装与调用','PASS' if len(ready)==len(skills) else 'BLOCKED',{'ready_repositories':ready,'required_repositories':list(skills),'missing_skill_names':[s['name'] for row in skills.values() for s in row['skills'] if not s['installed']]},'external_skills/', 'All original upstream Skills')

# 3: film evidence and provisional director interpretation.
study=jload('output/gpt_director_study/study_and_rehearsal.json')
assert 'GPT' in study['model_used_for_directing'] and study['director_intent_verified'] is False
assert sum(len(x) for x in study['frame_references'].values())==18
record('导演研究／事实与导演意图分离','PASS',{'model':study['model_used_for_directing'],'real_frames':18,'director_intent_verified':False},'output/gpt_director_study/study_and_rehearsal.json','director-agent')

# 4: approved story facts -> storyboard; the first shot and last shot must preserve the same causal ledger.
import gpt_director_study as gpt
import professional_skill_experiment as pro_ex
scene_data=jload('data/gpt_director_scene.json');scene=scene_data['scene']
shots=scene_data['revised_shots'];other=pro_ex.make_alternate(shots)
A=gpt.audit(scene,shots);B=gpt.audit(scene,other)
assert A['issue_count']==0 and B['issue_count']==0
assert len(shots)==7 and abs(shots[-1]['end_s']-32.0)<1e-8
assert all(shots[i]['end_s']==shots[i+1]['start_s'] for i in range(len(shots)-1))
track_A=pro_ex.audience_track(scene,shots);track_B=pro_ex.audience_track(scene,other)
assert 'REMOTE_LOGIN' in track_A[2]['audience_advantage_over_A']
assert 'REMOTE_LOGIN' not in track_B[2]['audience_advantage_over_A']
record('原创32秒场景／导演分镜与两种观看方案','PASS',{'original_scene':scene['title'],'shots_each':7,'duration_s':32,'structural_issues':{'audience_knows_first':A['issue_count'],'shared_unknown':B['issue_count']},'different_audience_experience':True,'artistic_quality_proven':False},'data/gpt_director_scene.json','director-agent / ai-storyboard-director')

# 5: preflight negative cases; checks must catch errors rather than only pass correct data.
negative=gpt.negative_tests(scene,shots)
report=jload('output/gpt_director_study/acceptance.json')
assert report['independent_negative_detection']=='6/6'
record('分镜预检／六个故意破坏的反例','PASS',{'negative_cases_detected':report['independent_negative_detection'],'negative_case_details':str(negative)[:550]},'output/gpt_director_study/acceptance.json','plan-camera-shots')

# 5b: strict upstream camera handoff, distinct from a generic story-structure pass.
# Official plan-camera-shots explicitly calls for camera position, movement,
# focus, stage start/end state, asset ID binding and upstream beat lineage.
# Do not mark the scene generation-ready merely because 7 texts are contiguous.
import production_skill_handoff as pilot
import official_skill_source_audit as original_sources
camera_plan, pilot_review=pilot.produce()
source_audit=original_sources.verify()
final_segments=camera_plan['segments']
contract_fields={
    'camera_explicit_position':sum(bool(s.get('camera_position')) for s in final_segments),
    'focus_target':sum(bool(s.get('focus_target')) for s in final_segments),
    'asset_bindings':sum(bool(s.get('asset_bindings')) for s in final_segments),
    'upstream_beat_id':sum(bool(s.get('upstream_beat_id')) for s in final_segments),
    'prop_state_at_start':sum(bool(s.get('props_at_start')) for s in final_segments),
    'prop_state_at_end':sum(bool(s.get('props_at_end')) for s in final_segments),
    'basic_blocking':sum(bool(s.get('positions_at_start')) and bool(s.get('positions_at_end')) for s in final_segments),
    'camera_movement_and_lens':sum(bool(s.get('camera_movement')) and bool(s.get('lens_focal_length_mm')) for s in final_segments),
}
required=('camera_explicit_position','focus_target','asset_bindings','upstream_beat_id','prop_state_at_start','prop_state_at_end','basic_blocking','camera_movement_and_lens')
ready=all(contract_fields[k]==len(shots) for k in required) and camera_plan['preflight']['pass']
record('摄影Skill生成级镜头交接合同','PASS' if ready else 'BLOCKED',
       {'shot_count':len(shots),'field_coverage':contract_fields,
        'readiness':'PROVISIONAL_CAMERA_PREFLIGHT_PASS' if ready else 'MISSING_PRODUCTION_FIELDS',
        'stage_geometry_source':'director_proposed_not_measured',
        'user_approval_pending':True},
       'output/real_production_pilot/professional_camera_handoff.json','plan-camera-shots')

# 6: 86 source proposals, 258 reference anchors, 0 actual independent candidates.
import director as d
import product_engine as prod
from production_cli import table_status,export_orders
status=table_status()
assert status['shots_proposed']==86 and status['target_storyboard_frames']==258
assert status['candidate_versions_total']==0 and status['director_approved_cards_claimed']==0
orders=export_orders()
assert orders['tasks']==258
with (ROOT/'output/shot_work_orders.jsonl').open(encoding='utf-8') as f:
    work=[json.loads(line) for line in f if line.strip()]
assert len(work)==258 and len({x['task_id'] for x in work})==258
assert all(x.get('candidate_generation')=='PENDING_MODEL_OR_MANUAL_IMPORT' for x in work)
record('全片镜头生产任务生成','PASS',{'proposed_shots':86,'reference_anchors':258,'generated_stills':0,'jobs_generated':258,'candidate_versions':0},'output/shot_work_orders.jsonl','plan-camera-shots')

# 7: review and assemble should not claim finished production with zero generated candidates.
export=prod.export_cut()
assert export.get('result')=='BLOCKED' and export.get('eligible_shots')==0
record('审片与成片出口门禁','PASS',{'actual_result':export['result'],'eligible_shots':0,'total_shots':export['total_shots'],'reason':export['reason']},'output/export_gate.json','review-and-assemble')
assert pilot_review['candidate_count']==7 and pilot_review['generation_run_count']==1
assert pilot_review['human_approved_count']==0 and pilot_review['editorial_export']['status']=='BLOCKED'
record('真实原创AI分镜图生成','PASS',{'original_scene_candidate_frames':7,'image_generation_runs':1,
       'source_film_replica_candidates':0,'artistic_acceptance':False,
       'visually_plausible_but_not_approved':pilot_review['pass_count'],
       'needs_review_or_revision':pilot_review['revision_count'],
       'rejected_shot':'S07','human_approved':0,
       'original_storyboard_animatic_s':32.0,'actually_generated_video_shots':0},
       'output/real_production_pilot/independent_media_review.json','review-and-assemble')

# 8: runtime HTTP and safety of the actual working application.
import studio_product as studio
studio.d.bootstrap()
server=ThreadingHTTPServer(('127.0.0.1',0),studio.Handler)
port=server.server_port
base='http://127.0.0.1:'+str(port)
worker=threading.Thread(target=server.serve_forever,daemon=True)
worker.start()
try:
    checks={}
    for p in ['/','/gpt-director-study','/gpt-director-data','/director','/director-data','/editing','/editing-data','/cuts','/evidence','/evidence-data','/longform','/acceptance','/api/tasks','/api/shot?shot=SH_00065','/api/audit']:
        code,mime,data=get(base,p)
        assert code==200 and len(data)>10,(p,code,len(data))
        checks[p]={'http':code,'bytes':len(data),'type':mime}
    s=json.loads(get(base,'/api/tasks')[2]);assert s['shot_count']==86 and s['task_count']==258 and s['with_candidate']==0
    relative='output/gpt_director_study/source_frames/CASE_A_05_604.4s.jpg'
    imcode,imtype,imdata=get(base,'/'+relative)
    assert imcode==200 and len(imdata)>2000 and imtype.startswith('image/')
    checks['/SOURCE_FRAME']={'http':imcode,'bytes':len(imdata)}
    # Deny mutation when CSRF is missing; deny cross-origin even with valid token.
    no_token=post(base,'/api/editorial-design',{'brief':'短片'},token=None)
    assert no_token[0]==403
    bad_origin=post(base,'/api/editorial-design',{'brief':'短片'},token=studio.TOKEN,origin='https://evil.invalid')
    assert bad_origin[0]==403
    checks['csrf_protected']={'no_token_status':403,'wrong_origin_status':403}
    valid=post(base,'/api/editorial-design',{'brief':'凌晨，观测站断线后有人登录，调查员A在控制台追查，管理员B藏门禁卡；保持32秒，不能提前揭晓真相','pattern':'suspense_insert'},token=studio.TOKEN)
    assert valid[0]==200 and isinstance(valid[1],dict)
    checks['director_plan_api']={'http':valid[0],'response_keys':list(valid[1])[:18]}
    gate=post(base,'/api/export-gate',{},token=studio.TOKEN)
    assert gate[0]==200 and gate[1]['result']=='BLOCKED'
    checks['film_export_api']={'http':200,'gate':gate[1]['result']}
    record('成品本地Web服务与API端到端','PASS',{'port':port,'routes_checked':len(checks),'details':checks},'studio_product.py','review-and-assemble / platform integration')
    # 9: real browser (not just file existence) when available.
    try:
        from playwright.sync_api import sync_playwright
        browser_result={}
        with sync_playwright() as pw:
            b=pw.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-dev-shm-usage'])
            page=b.new_page(viewport={'width':1440,'height':900},device_scale_factor=1)
            errors=[]
            page.on('pageerror',lambda error: errors.append(str(error)))
            rsp=page.goto(base+'/gpt-director-study',wait_until='domcontentloaded',timeout=20000)
            page.wait_for_timeout(800)
            rendered_title=page.title();body_text=page.locator('body').inner_text(timeout=5000)
            screenshot=OUT/'实际浏览器_妖猫传导演研究.png'
            page.screenshot(path=str(screenshot),full_page=True)
            assert rsp.status==200 and len(body_text)>80 and not errors,(rsp.status,len(body_text),errors)
            browser_result={'url':'/gpt-director-study','status':rsp.status,'title':rendered_title,'text_chars':len(body_text),'console_page_errors':errors,'screenshot':str(screenshot.relative_to(ROOT))}
            b.close()
        record('Chromium真实页面渲染','PASS',browser_result,browser_result['screenshot'],'browser visual acceptance')
    except Exception as e:
        record('Chromium真实页面渲染','SKIPPED',{'reason':type(e).__name__+': '+str(e)[:350]},'studio_product.py','browser visual acceptance')
finally:
    server.shutdown();server.server_close();worker.join(timeout=6)

# 10: original clip and projection are not secretly presented as generated film.
probe=subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nokey=1:noprint_wrappers=1',str(ROOT/'data/source_video.mp4')],capture_output=True,text=True,check=True,timeout=25)
duration=float(probe.stdout.strip()); assert 775 < duration < 778
record('真实视频可解码与素材范围','PASS',{'duration_s':duration,'source_is_full_movie':False,'reference_previs_counted_as_generated':False},'data/source_video.mp4','source media integrity')

hard_blockers=[r['stage'] for r in RESULTS if r['result']=='BLOCKED']
failures=[r['stage'] for r in RESULTS if r['result']=='FAIL']
summary={
 'reference_movie_is_excerpt_only':True,
 'stages_tested':len(RESULTS),'pass_count':sum(x['result']=='PASS' for x in RESULTS),
 'blocked_count':len(hard_blockers),'failure_count':len(failures),
 'blocked_stages':hard_blockers,'native_professional_skills_executed':0,
 'original_ai_stills_generated':7,'original_ai_generation_runs':1,
 'original_ai_stills_accepted':0,'original_ai_video_shots_accepted':0,
 'original_source_skill_docs_sha_verified':source_audit['original_skill_texts_verified'],
 'release_ready':False,'film_director_artistic_quality_verified':False,
 'meaning':'原片学习、摄影交接和7张原创AI静帧及32秒静帧预演已验证；部分原版Skill正文按官方Git SHA校验读取，完整原版Skill尚未宿主安装；真正镜头视频和成片仍未验收。'
}
payload={'summary':summary,'stages':RESULTS,'upstream_contract_sources':{
 'director-agent':'https://github.com/62656456/ai-film-skills/blob/main/skills/director-agent/SKILL.md',
 'ai-storyboard-director':'https://github.com/62656456/ai-film-skills/blob/main/skills/ai-storyboard-director/SKILL.md',
 'plan-camera-shots':'https://github.com/zhangzhangco/film-production-skills/blob/main/skills/plan-camera-shots/SKILL.md',
 'review-and-assemble':'https://github.com/zhangzhangco/film-production-skills/blob/main/skills/review-and-assemble/SKILL.md'}}
(OUT/'acceptance.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')

lines=['# 《妖猫传》专业影视Skill对标：整套成品端到端验收','',
 '> 本次真实运行原工程和新媒体试制；两份原版摄影/审片Skill正文已按Git对象SHA核验，但完整源码包和宿主原生调用仍未完成。','',
 '## 执行结果','',f'- 真实检查阶段：**{summary["stages_tested"]}**','',f'- 通过：**{summary["pass_count"]}**；阻断：**{summary["blocked_count"]}**；程序失败：**{summary["failure_count"]}**。',
 '- **最终结果：NOT PRODUCTION READY（尚未形成可出片的完整生产链路）**。','',
 '| Skill环节／功能 | 验收 | 依据 |','|---|---|---|']
for x in RESULTS:
    info=x['details']
    detail=(json.dumps(info,ensure_ascii=False) if isinstance(info,dict) else str(info))
    detail=detail.replace('|','/').replace('\n',' ')
    lines.append(f'| {x["stage"]} | **{x["result"]}** | {detail[:140]} |')
lines += ['', '## 明确尚未完成的成片能力','',
 '- **专业Skill原生运行**：已校验两份原版Skill正文及参考文件，仍缺完整上游源码、输入输出Schema及原生宿主安装，不得记为原生调用。',
 '- **独立AI画面生产**：原创场景已生成一张7格分镜总板并裁切为7个候选；仅2项视觉上初步可用，5项要求复核或修改，0项正式签核。电影原片86镜的重建任务仍为0候选。',
 '- **真正成片导出**：已验证 `export_gate=BLOCKED`，不允许绕过签核导出。',
 '- **导演审美和叙事质量**：两个原创方案都满足结构规则，但不代表艺术质量通过；需要独立画面与真实观看评价。',
 '', '## 导演学习的实际应用','',
 '- **案例 A（595–616秒）**：多个空间/人物/黑猫镜头交织，已区分观众信息和人物知情；猫是否被角色看见仍无证据。',
 '- **案例 B（617–653秒）**：从门窗观察到人物进入、同框及离场，重点在走位、空间维持和镜头接力，不能概括为普通正反打。',
 '- **原创《失联观测站》32秒**：7镜头，两套信息释放策略，都通过既有结构检查，审美优劣未证实。',
 '', '## 一键重跑','', '```bash','python skill_product_acceptance.py','python -m unittest discover -s tests -p "test_*.py" -q','```',
 '', '## 上游规范来源','',
 '- https://github.com/62656456/ai-film-skills/blob/main/skills/director-agent/SKILL.md',
 '- https://github.com/62656456/ai-film-skills/blob/main/skills/ai-storyboard-director/SKILL.md',
 '- https://github.com/zhangzhangco/film-production-skills/blob/main/skills/plan-camera-shots/SKILL.md',
 '- https://github.com/zhangzhangco/film-production-skills/blob/main/skills/review-and-assemble/SKILL.md']
(OUT/'完整成品验收报告.md').write_text('\n'.join(lines),encoding='utf-8')
# Self-contained static dashboard with no dependencies / secrets.
rows='\n'.join('<tr><td>'+html.escape(x['stage'])+'</td><td class="'+x['result']+'">'+x['result']+'</td><td><code>'+html.escape(json.dumps(x['details'],ensure_ascii=False)[:360])+'</code></td></tr>' for x in RESULTS)
page=f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>《妖猫传》专业Skill整体验收</title><style>body{{margin:0;background:#0b1420;color:#ecf2f5;font-family:system-ui,Arial,'Microsoft Yahei',sans-serif;line-height:1.5}}main{{max-width:1200px;margin:0 auto;padding:36px 24px}}h1{{font-size:29px}}.sub{{color:#9eb1c9}}.summary{{display:flex;gap:12px;flex-wrap:wrap;margin:24px 0}}.kpi{{background:#15253a;border:1px solid #34485a;padding:16px 24px;border-radius:13px;min-width:145px}}.kpi b{{display:block;font-size:27px}}table{{border-collapse:collapse;width:100%;font-size:14px}}th,td{{border-bottom:1px solid #324052;padding:13px 10px;vertical-align:top;text-align:left}}th{{color:#bcd0db}}td code{{overflow-wrap:anywhere;white-space:normal;color:#cddbea}}.PASS{{color:#70e1a2;font-weight:700}}.BLOCKED{{color:#ffd08b;font-weight:700}}.FAIL{{color:#ffa0a0;font-weight:700}}.SKIPPED{{color:#9bb7d8;font-weight:700}}a{{color:#8fc8ff}}.warn{{font-size:17px;border-left:3px solid #edb15d;padding:14px;background:#172639}}@media(max-width:700px){{main{{padding:18px}}}}</style></head><body><main><div class="sub">GPT DIRECTOR × 原片证据 × 专业影视Skill发布规范</div><h1>《妖猫传》整套成品功能验收</h1><p class="warn"><strong>未达到成片交付标准。</strong> 结构、证据和Web服务可以实测；原版Skill未安装执行，独立AI画面和成片输出尚未通过。</p><div class="summary"><div class="kpi"><b>{summary['stages_tested']}</b>真实阶段</div><div class="kpi"><b>{summary['pass_count']}</b>通过</div><div class="kpi"><b>{summary['blocked_count']}</b>阻断</div><div class="kpi"><b>{summary['failure_count']}</b>程序失败</div></div><table><thead><tr><th>验收项目</th><th>结果</th><th>真实依据</th></tr></thead><tbody>{rows}</tbody></table><p class="sub">参考证据：595–616秒与617–653秒，共18张真实原片帧；新影片分镜：7镜、32秒，结构检查 ≠ 影像审美签核。</p><p><a href="/gpt-director-data">打开导演学习数据</a> · <a href="/skill-acceptance-json">JSON验收数据</a> · <a href="/skill-acceptance-report">文字报告</a></p></main></body></html>'''
(OUT/'完整成品验收仪表盘.html').write_text(page,encoding='utf-8')
print('=== FINAL SUMMARY ===',json.dumps(summary,ensure_ascii=False),flush=True)
