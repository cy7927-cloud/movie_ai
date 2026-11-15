#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Film evidence -> activation parameters for *existing* professional Skills.

No SKILL.md is generated, changed or executed here. This is a reproducible
parameter selection + input packaging tool; it does not train model weights.
Every camera/style preference is explicitly distinguished from measured facts.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import html
import json
import statistics
import subprocess
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent
FILM = ROOT/'data/source_video.mp4'
CASES = ROOT/'data/gpt_director_cases.json'
FRAMES = ROOT/'output/gpt_director_study/source_frames'
SCENE = ROOT/'data/gpt_director_scene.json'
CAMERA = ROOT/'output/real_production_pilot/professional_camera_handoff.json'
REVIEW = ROOT/'output/real_production_pilot/independent_media_review.json'
OUT = ROOT/'output/film_style_activation'

# Existing upstream expert Skills; only link/reference their original sources.
EXPERT_SKILLS = {
 'structure-screenplay': {
  'repo':'zhangzhangco/film-production-skills',
  'path':'skills/structure-screenplay/SKILL.md',
  'role':'保留原著与新剧本事实，组织稳定场次/beat，不发明镜头',
 },
 'director-agent': {
  'repo':'62656456/ai-film-skills',
  'path':'skills/director-agent/SKILL.md',
  'role':'人物动机、叙事信息安排、表演与导演阐述',
 },
 'ai-storyboard-director': {
  'repo':'62656456/ai-film-skills',
  'path':'skills/ai-storyboard-director/SKILL.md',
  'role':'以观众观看任务组织分镜、表演与电影摄影',
 },
 'plan-camera-shots': {
  'repo':'zhangzhangco/film-production-skills',
  'path':'skills/plan-camera-shots/SKILL.md',
  'role':'摄影机、焦点、演员走位、空间基线、灯光与物件连续性',
 },
 'review-and-assemble': {
  'repo':'zhangzhangco/film-production-skills',
  'path':'skills/review-and-assemble/SKILL.md',
  'role':'逐镜可追溯的媒体审查、拒绝错误镜头、阻止虚假成片',
 },
}

DEFAULT_STYLE_SPEC = ROOT/'data/film_style_evidence_annotations.json'



def sha256(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for buf in iter(lambda:f.read(1024*1024),b''): h.update(buf)
 return h.hexdigest()


def load(path): return json.loads(Path(path).read_text(encoding='utf-8'))


def save(path,value):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
 return path


def git_blob_sha(content:bytes):
 return hashlib.sha1(b'blob '+str(len(content)).encode('ascii')+b'\x00'+content).hexdigest()


def original_skill_status():
 """Read-only check; cannot equate an instruction file with native host install."""
 rows={}
 for name,spec in EXPERT_SKILLS.items():
  p=ROOT/'external_skills'/spec['repo'].split('/')[-1]/spec['path']
  # The Open Film Skills repository is named ai-film-skills, not open-film-skills.
  if spec['repo']=='62656456/ai-film-skills':
   p=ROOT/'external_skills/open-film-skills'/spec['path']
  has=p.is_file()
  rows[name]={
   'official_source':'https://github.com/'+spec['repo']+'/blob/main/'+spec['path'],
   'local_original_instruction_available':has,
   'sha256':sha256(p) if has else None,
   'local_skill_path':p.relative_to(ROOT).as_posix() if has else None,
   'role':spec['role'],
   'native_host_executed':False,
  }
 return rows


def resolve_frame_paths(case,frame_root=FRAMES):
 cid=case['id']; rows=[]
 for idx,obs in enumerate(case['observations'],1):
  sec=float(obs['second']); stem=f'{cid}_{idx:02d}_{sec:.1f}s.jpg'
  p=Path(frame_root)/stem
  if not p.is_file():raise FileNotFoundError('Actual source reference frame missing: '+str(p))
  rows.append((obs,p))
 return rows


def frame_stats(path):
 # Deterministic image-based proxies, NOT conclusions about cinematography.
 bgr=cv2.imread(str(path),cv2.IMREAD_COLOR)
 if bgr is None:raise ValueError('Unreadable source frame: '+str(path))
 H,W=bgr.shape[:2]; bgr=bgr[int(H*.05):int(H*.95),int(W*.05):int(W*.95)]
 small=cv2.resize(bgr,(320,180),interpolation=cv2.INTER_AREA)
 hsv=cv2.cvtColor(small,cv2.COLOR_BGR2HSV)
 y=cv2.cvtColor(small,cv2.COLOR_BGR2YCrCb)[:,:,0]
 mean=np.mean(small,axis=(0,1))
 return {
  'luma_mean_0_255':round(float(y.mean()),2),
  'luma_p10_0_255':round(float(np.percentile(y,10)),2),
  'luma_p90_0_255':round(float(np.percentile(y,90)),2),
  'dark_area_fraction_luma_below_55':round(float(np.mean(y<55)),3),
  'saturation_mean_0_255':round(float(hsv[:,:,1].mean()),2),
  'warmth_rgb_red_minus_blue_proxy':round(float(mean[2]-mean[0]),2),
 }


def verify_reference_frames(reference_film, rows, max_mae=15.0):
 """Check the purported film reference JPEGs against the ACTUAL video.

 Video seek uncertainty permits a small difference; anything grossly
 different (e.g. unrelated screenshots) invalidates the style evidence.
 This is only authenticity evidence, not director-intent verification.
 """
 cap=cv2.VideoCapture(str(reference_film))
 if not cap.isOpened():raise ValueError('Movie not decodable for frame authenticity')
 result=[]
 try:
  for obs,path in rows:
   second=float(obs['second'])
   cap.set(cv2.CAP_PROP_POS_MSEC,second*1000)
   ok,frame=cap.read()
   if not ok:raise ValueError(f'Unable to seek reference video to {second} seconds')
   ref=cv2.imread(str(path),cv2.IMREAD_COLOR)
   if ref is None:raise ValueError('Reference still is not decodable: '+str(path))
   if frame.shape[:2]!=ref.shape[:2]:
    raise ValueError('Reference image/video geometry differs: '+str(path))
   frame=cv2.resize(frame,(320,134),interpolation=cv2.INTER_AREA).astype(np.float32)
   ref=cv2.resize(ref,(320,134),interpolation=cv2.INTER_AREA).astype(np.float32)
   mae=round(float(np.mean(np.abs(frame-ref))),3)
   if mae>max_mae:raise ValueError('Reference frame does NOT match the supplied video at '+str(second)+' s; MAE='+str(mae))
   result.append({'timestamp_s':second,'comparison_mae_0_255':mae,'authenticity_check':'PASS'})
 finally:cap.release()
 return result


def summarize_palette(rows):
 k=['luma_mean_0_255','dark_area_fraction_luma_below_55',
    'saturation_mean_0_255','warmth_rgb_red_minus_blue_proxy']
 samples=[frame_stats(p) for obs,p in rows]
 return {'samples':len(samples),
         'mean_of_sample_proxies':{x:round(statistics.mean(a[x] for a in samples),3) for x in k},
         'sample_luma_span':[min(a['luma_mean_0_255'] for a in samples),max(a['luma_mean_0_255'] for a in samples)],
         'warning':'18 selected source-film stills, not shot-exhaustive film color grading or calibrated camera LUT'}


def learn(reference_film=FILM, case_file=CASES, frame_root=FRAMES,
          style_spec=DEFAULT_STYLE_SPEC, name=None):
 film=Path(reference_film)
 if not film.is_file():raise FileNotFoundError('Reference film missing: '+str(film))
 cap=cv2.VideoCapture(str(film))
 if not cap.isOpened():raise ValueError('Cannot decode reference movie: '+str(film))
 fps=cap.get(cv2.CAP_PROP_FPS)
 count=cap.get(cv2.CAP_PROP_FRAME_COUNT)
 film_duration_s=round(float(count/fps),3) if fps and count else None
 cap.release()
 if not film_duration_s:raise ValueError('Reference film duration unavailable')
 case_data=load(style_spec)
 if case_data.get('schema')!='FILM_STYLE_EVIDENCE_ANNOTATIONS/1.0':raise ValueError('Unexpected style evidence annotation schema')
 mode_definitions=case_data['modes']
 cases=load(case_file)['cases'];case_by={c['id']:c for c in cases}
 if len(case_by)!=len(cases):raise ValueError('Duplicate study case ID')
 modes={}; allframe=[]
 for mode_name, spec in mode_definitions.items():
  c=case_by.get(spec['case'])
  if not c:raise ValueError('Required observed film case missing: '+spec['case'])
  actual_times=[float(v['second']) for v in c['observations']]
  if max(actual_times)>=film_duration_s or min(actual_times)<0:
   raise ValueError('Reference evidence timestamp outside movie duration')
  if actual_times!=spec['evidence_timestamps_s']:
   raise ValueError('Film study observations changed; re-analyse the film instead of silently using stale activation parameters')
  references=resolve_frame_paths(c,frame_root)
  matchchecks=verify_reference_frames(film,references)
  frameinfo=[{'second':o['second'],'path':str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p),'sha256':sha256(p),'visible_observation':o['visible']}
             for o,p in references]
  mode=copy.deepcopy(spec)
  mode['frame_evidence']=frameinfo
  mode['video_frame_authenticity_checks']=matchchecks
  mode['palette_proxy_from_actual_frames']=summarize_palette(references)
  mode['film_case_hypotheses_provisional']=c['hypotheses']
  mode['unverified']=c['unverified']
  modes[mode_name]=mode
  allframe.extend(frameinfo)
 profile={
  'schema':'FILM_REFERENCE_STYLE_ACTIVATION/1.0',
  'profile_id':case_data['profile_id'],
  'display_name':name or case_data['name'],
  'film_source':{'path':str(film.relative_to(ROOT)) if film.is_relative_to(ROOT) else str(film),
                 'sha256':sha256(film),'size_bytes':film.stat().st_size,
                 'duration_seconds_technical_proxy':film_duration_s,
                 'coverage':'USER_PROVIDED_REFERENCE_VIDEO_NOT_ASSUMED_FULL_FEATURE'},
  'evidence_source':str(Path(case_file).relative_to(ROOT)) if Path(case_file).is_relative_to(ROOT) else str(case_file),
  'style_annotation_sha256':sha256(style_spec),
  'reference_frame_count':len(allframe),
  'upstream_professional_skill_sources':original_skill_status(),
  'activation_policy':'SELECT_EXISTING_PROFESSIONAL_SKILL_NOT_WRITE_NEW_SKILL',
  'parameter_type':'EVIDENCE_BACKED_HUMAN_INTERPRETATION_NOT_MODEL_WEIGHT_FINETUNING',
  'modes':modes,
  'global_approval_guards':[
    'Never substitute source movie frames for original production images',
    'Unknown director intent must stay provisional',
    'Do not transfer copyrighted dialogue, film characters, or exact shot composition',
    'Do not assert stable performer acting style from sparse stills',
    'Asset identity, sound, dialogue, blocking and artistic quality require separate review',
    'Do not claim native execution of the upstream Skill until the host actually invokes it',
  ],
 }
 return profile


def effective_activations(profile,mode):
 active={a['skill']:copy.deepcopy(a) for a in profile['modes'][mode]['professional_activation']}
 # Script facts stage runs whenever a new script is supplied, regardless of style.
 active['structure-screenplay']={'skill':'structure-screenplay','priority':'required',
   'focus':['保留用户原剧本','稳定场次ID和来源','不改写剧情']}
 return [active[x] for x in EXPERT_SKILLS if x in active]


def apply(profile,mode,scene_file=SCENE,camera_file=CAMERA,review_file=REVIEW):
 if mode not in profile['modes']:raise ValueError('Style mode is not in selected reference-film profile')
 if mode not in ('audience_first_suspense','blocking_space_reveal'):
  raise ValueError('This production scene is a two-mode demo only; other reference-film modes require screenplay/shot planning through the original professional Skills')
 scene=load(scene_file)
 original_scene=scene['scene']
 shots=scene['revised_shots']
 base=load(camera_file)
 selected=copy.deepcopy(base)
 source_reviews=load(review_file)
 if len(shots)!=len(base['segments']):raise ValueError('Original scene/camera plan shot count mismatch')
 if {x['id'] for x in shots}!={x['id'] for x in base['segments']}:
  raise ValueError('Shots differ between canonical story and camera handoff')

 # The original movie influences the *choices* a professional Skill receives,
 # not the integrity of story beats or its native instructions.
 if mode=='audience_first_suspense':
  variant=copy.deepcopy(shots)
  # already-authored source plan contains a viewer-only insert.
  x=next(s for s in selected['segments'] if s['id']=='S03')
  x['activation_camera_explanation']='Viewer-only readable insert tests CASE_A information hierarchy, not a claimed film camera measurement'
  x['activate_priority']='viewer_information_insert'
  y=next(s for s in selected['segments'] if s['id']=='S05')
  y['activation_camera_explanation']='S05 tests whether viewers see a concealed badge without actor A noticing'
  y['activate_priority']='viewer_only_prop_reveal'
 else:
  from professional_skill_experiment import make_alternate
  variant=make_alternate(shots)
  x=next(s for s in selected['segments'] if s['id']=='S03')
  x['lens_focal_length_mm']=50
  x['focus_target']='A hand and upper log; lower remote-login status is unreadable from this camera'
  x['camera_position']={'unit':'m','x':3.0,'y':1.8,'z':1.45}
  x['camera_explicit_position']=[3.0,1.8,1.45]
  x['camera_target']={'unit':'m','xyz':[3.8,1.1,1.3]}
  x['actor_action']=variant[2]['actor_action']
  x['dramatic_purpose']=variant[2]['dramatic_purpose']
  x['cut_reason']=variant[2]['cut_reason']
  x['sound']=variant[2]['sound']
  x['activation_camera_explanation']='CASE_B: preserve room and character spatial relationship rather than isolate the viewer-only clue'
  x['activate_priority']='character_followed_spatial_discovery'
  for seg in selected['segments']:
   # A-scenario AI images are NOT a proof of the B-scenario camera plan.
   seg.pop('image_generation_ref',None)
   seg['new_visual_candidate_status']='NOT_GENERATED_FOR_THIS_STYLE' 
  y=next(s for s in selected['segments'] if s['id']=='S04')
  y['lens_focal_length_mm']=35
  y['focus_target']='B crosses doorway; keep fixed doorway and console geometry readable'
  y['activation_camera_explanation']='CASE_B: doorway blocking and screen direction prioritized; proposed lens, not measured from film'
  y['activate_priority']='blocking_and_threshold'

 # New screenplay facts/characters do not come from the film reference.
 for shot,segment in zip(variant,selected['segments']):
  if shot['id']!=segment['id']:raise ValueError('Shot ordering mismatch')
  if abs(float(shot['start_s'])-float(segment['start_s']))>.001 or abs(float(shot['end_s'])-float(segment['end_s']))>.001:
   raise ValueError('Duration mismatch')
  # Preserve all upstream state, geometry, assets, performer action except explicitly
  # identified camera/action change to conceal the clue in the B variant.

 from gpt_director_study import audit
 audit_result=audit(original_scene,variant)
 errors=[]
 if audit_result['issue_count']:errors.append('STORY_CONSTRAINTS_FAILED')
 if source_reviews.get('editorial_export',{}).get('status')!='BLOCKED':
  errors.append('REVIEW_STATUS_CHANGED_UNEXPECTEDLY')
 for v in selected['segments']:
  if not v.get('asset_bindings'):errors.append('NO_ASSETS_'+v['id'])
  if not v.get('focus_target'):errors.append('NO_FOCUS_'+v['id'])
  if 'camera_position' not in v:errors.append('NO_CAMERA_'+v['id'])
  for a in v['asset_bindings']:
   if a not in selected['assets']:errors.append('UNKNOWN_ASSET_'+v['id']+'_'+a)
 result={
  'schema':'PROFESSIONAL_SKILL_ACTIVATION_RUN/1.0',
  'mode':mode,
  'profile_id':profile['profile_id'],
  'film_sha256':profile['film_source']['sha256'],
  'reference_case':profile['modes'][mode]['case'],
  'activation_type':'PARAMETERIZED_EXISTING_SKILLS_NOT_A_NEW_SKILL',
  'selected_expert_skills':effective_activations(profile,mode),
  'skill_native_execution_claimed':False,
  'production_source_script_file':str(Path(scene_file).relative_to(ROOT)) if Path(scene_file).is_relative_to(ROOT) else str(scene_file),
  'story_identity':{'title':original_scene['title'],'duration_s':original_scene['target_duration_s'],
                    'story_facts':original_scene['facts'],
                    'characters':list(original_scene['initial_character_knowledge'])},
  'director_shots':variant,
  'shot_camera_handoff':selected,
  'story_audit':audit_result,
  'external_media_reviews':source_reviews['reviews'] if mode=='audience_first_suspense' else [],
  'legacy_A_media_not_validated_for_new_style': mode=='blocking_space_reveal',
  'media_final_approval':False,
  'film_export_blocked':True,
  'preflight':{'pass':not errors,'issues':errors,'not_a_quality_score':True},
  'generation_status':'B_HAS_NO_NEW_AI_IMAGES' if mode=='blocking_space_reveal' else 'A_HAS_7_PREVIOUS_STORYBOARD_CANDIDATES_WITH_NO_FINAL_APPROVAL',
  'caveats':['Film style learned from selected excerpt frames with human-authored annotations; not automatically trained model weights',
             'Camera positions in original new scene are proposed, not measured reference-film geometry',
             'No new video or approved original visual sequence has been produced by style activation alone'],
 }
 return result


def compare(profile,a,b):
 def byshot(run):return {s['id']:s for s in run['director_shots']}
 sa,sb=byshot(a),byshot(b)
 ca={s['id']:s for s in a['shot_camera_handoff']['segments']}
 cb={s['id']:s for s in b['shot_camera_handoff']['segments']}
 assert sa.keys()==sb.keys()==ca.keys()==cb.keys()
 changes=[]
 keys=['camera','actor_action','dramatic_purpose','revealed_to_audience','cut_reason','sound']
 for sid in sa:
  d=[]
  for k in keys:
   if sa[sid].get(k)!=sb[sid].get(k):d.append(k)
  for k in ['lens_focal_length_mm','focus_target','camera_position','activate_priority']:
   if ca[sid].get(k)!=cb[sid].get(k):d.append('camera.'+k)
  if d:changes.append({'shot_id':sid,'changed_fields':d})
 return {'same_original_story':a['story_identity']==b['story_identity'],
         'same_shot_time_ranges':all(sa[s]['start_s']==sb[s]['start_s'] and sa[s]['end_s']==sb[s]['end_s'] for s in sa),
         'same_actor_spatial_paths':all(sa[s]['positions_at_start']==sb[s]['positions_at_start'] and sa[s]['positions_at_end']==sb[s]['positions_at_end'] for s in sa),
         'modes':[a['mode'],b['mode']],
         'changed_shots':changes,
         'style_changes_operational_not_label_only':len(changes)>0,
         'style_fidelity_verified':False,
         'artistic_comparison_verified':False,
         'reason':'Changes to camera/storyboard selection are measurable; reference-style artistic similarity needs real new images/video and independent critique.'}


def build_web(profile,comparison,runs):
 esc=lambda s:html.escape(str(s),quote=True)
 modecards=[]
 for key,mode in profile['modes'].items():
  details=''.join('<li><b>'+esc(x['skill'])+'</b> ['+esc(x['priority'])+']: '+esc('、'.join(x['focus']))+'</li>' for x in effective_activations(profile,key))
  refs=''.join('<figure><img loading="lazy" src="../gpt_director_study/source_frames/'+esc(Path(r['path']).name)+'"><figcaption>'+esc(r['second'])+'s · '+esc(r['visible_observation'])+'</figcaption></figure>' for r in mode['frame_evidence'])
  modecards.append('<section><h2>'+esc(mode['name'])+'</h2><p><b>可见事实：</b>'+esc(mode['observed_structure'])+'</p><p><b>待验证假说：</b>'+esc(mode['inference_not_certainty'])+'</p><h3>激活已有专业 Skill</h3><ul>'+details+'</ul><div class="gallery">'+refs+'</div></section>')
 shotrows=[]
 for x in comparison['changed_shots']:
  shotrows.append('<tr><td>'+esc(x['shot_id'])+'</td><td>'+esc('、'.join(x['changed_fields']))+'</td></tr>')
 page='''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>《妖猫传》电影风格→现成专业Skill激活</title><style>body{background:#101822;color:#e7e8e9;font:15px/1.7 system-ui,'Microsoft Yahei',sans-serif;max-width:1300px;margin:auto;padding:26px}h1{font-size:27px}h2{color:#dbb98a;font-size:20px}section{background:#19222f;border:1px solid #334153;border-radius:13px;padding:20px;margin:16px 0}.gallery{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}figure{margin:0}figure img{width:100%;border-radius:6px}figcaption{font-size:11px;color:#b9c3ca}table{border-collapse:collapse;width:100%}td,th{border-bottom:1px solid #384656;padding:10px;text-align:left}.warn{border-left:4px solid #d59b61;padding:10px 14px;background:#27252a}@media(max-width:850px){.gallery{grid-template-columns:repeat(2,1fr)}}</style></head><body><h1>从《妖猫传》学习 → 激活现有专业导演 Skill</h1><p class="warn">本系统不创建新的 SKILL.md，也不改动专业 Skill 的原文；采用来自用户上传影片片段的真实帧证据，选择现成导演、分镜、摄影和审片流程的任务重点。未运行原生 Skill 宿主，没有底层模型微调，也没有宣称艺术水准已达标。</p><p><b>原片范围：</b>仅限上传的776.477秒片段 · <b>复查证据：</b>18张原片帧 · <b>配置：</b>两个不同的导演观看模式</p>'''+''.join(modecards)+'''<section><h2>同一新剧本两种风格配置：可观测差异</h2><p>人物、剧情事实、32秒总时长和演员走位保持不变，差异必须发生在镜头信息、摄影焦点、景别建议及切镜理由，而不是给同一分镜换名。</p><table><thead><tr><th>镜头</th><th>实际改变字段</th></tr></thead><tbody>'''+''.join(shotrows)+'''</tbody></table><p><b>两个方案结构预检：</b>'''+('通过' if all(r['preflight']['pass'] for r in runs) else '不通过')+'''；<b>原创媒体审批：</b>均为未通过，原有S07仍拒收；<b>视觉风格迁移质量：</b>尚无独立审片结论。</p></section><section><h2>本轮可验证边界</h2><p>专业Skill：plan-camera-shots 和 review-and-assemble 已有官方Git SHA核验的原始规则；director-agent 和 ai-storyboard-director 仍需完整上游安装与原生调用。A方案沿用上一轮已经生成的7张AI候选；B方案仅有摄影和分镜计划，没有新生成的镜头画面，禁止以A的图片证明B方案。</p><p>色彩统计是抽样帧像素指标，不是导演电影色彩意图或可直接使用的LUT。专业摄影参数是创作建议，而不是从原片逆算出的真实镜头焦距。</p></section></body></html>'''
 p=OUT/'电影风格_专业Skill激活对照实验.html';p.write_text(page,encoding='utf-8')
 return p


def run():
 profile=learn()
 a=apply(profile,'audience_first_suspense')
 b=apply(profile,'blocking_space_reveal')
 comp=compare(profile,a,b)
 if not(a['preflight']['pass'] and b['preflight']['pass'] and comp['style_changes_operational_not_label_only'] and comp['same_original_story'] and comp['same_shot_time_ranges'] and comp['same_actor_spatial_paths']):
  raise AssertionError('Actual style activation did not pass independent story/shot gates')
 save(OUT/'妖猫传_风格激活配置.json',profile)
 save(OUT/'方案A_观众先知.json',a)
 save(OUT/'方案B_空间调度.json',b)
 save(OUT/'对照验收.json',comp)
 html_file=build_web(profile,comp,[a,b])
 return {'reference_film_sha256':profile['film_source']['sha256'],
         'verified_reference_frames':profile['reference_frame_count'],
         'professional_skill_original_docs_local':sum(v['local_original_instruction_available'] for v in profile['upstream_professional_skill_sources'].values()),
         'native_skill_runs':0,'custom_new_skill_files_generated':0,
         'camera_plans_compared':2,'changed_shot_count':len(comp['changed_shots']),
         'original_story_same':comp['same_original_story'],
         'story_integrity_pass':a['preflight']['pass'] and b['preflight']['pass'],
         'original_media_approved':0,'reference_style_artistry_verified':False,
         'web_report':str(html_file.relative_to(ROOT))}


def compile_for_script(profile, mode, script_path):
 """Prepare authoritative upstream Skill inputs for ANY new script.

 No code in these expert Skills is executed: the packet is for a GPT/Agent
 Skills host to invoke the ORIGINAL instructions. This prevents a crude
 keyword parser from pretending to have learned professional screenwriting.
 """
 if mode not in profile['modes']:raise ValueError('Style mode not in selected profile')
 p=Path(script_path)
 if not p.is_file():raise FileNotFoundError(p)
 raw=p.read_text(encoding='utf-8-sig')
 if not raw.strip():raise ValueError('Empty source screenplay')
 if len(raw)>2_000_000:raise ValueError('Source screenplay exceeds 2 million characters')
 upstream=profile['upstream_professional_skill_sources']
 stages=[]
 for a in effective_activations(profile,mode):
  name=a['skill']
  stages.append({'stage':name,'original_skill_source':upstream[name]['official_source'],
                 'native_skill_available_in_this_environment':False,
                 'priority':a['priority'],'activated_topics':a['focus'],
                 'instruction':'Use the upstream SKILL.md without rewriting its directions; preserve script facts and evidence; do not claim performance without media review'})
 return {'schema':'NEW_SCRIPT_PROFESSIONAL_SKILL_INVOCATION/1.0',
         'original_script':{'path':str(p),'sha256':sha256(p),'text':raw},
         'selected_reference_profile_id':profile['profile_id'],
         'selected_style_mode':mode,'source_movie_sha256':profile['film_source']['sha256'],
         'film_style_cues_not_story_facts':profile['modes'][mode]['creative_bias_not_film_measurement'],
         'film_evidence_refs':[{'timestamp_s':x['second'],'sha256':x['sha256']} for x in profile['modes'][mode]['frame_evidence']],
         'ordered_original_skill_stages':stages,
         'stage_status':'PENDING_NATIVE_SKILL_HOST_EXECUTION',
         'next_required_action':'Pass the new script to original structure-screenplay Skill; approve structured beats before director and camera stages',
         'do_not_copy_source_movie_characters_or_dialogue':True,
         'generated_shots':0,'approved_movie':False}


if __name__=='__main__':
 parser=argparse.ArgumentParser(description='电影风格证据→原版专业导演Skill参数激活（不生成新Skill）')
 parser.add_argument('command',choices=['run','learn','compare','prepare-script'],nargs='?',default='run')
 parser.add_argument('--reference',type=Path,default=FILM)
 parser.add_argument('--case-file',type=Path,default=CASES)
 parser.add_argument('--frame-dir',type=Path,default=FRAMES)
 parser.add_argument('--style-spec',type=Path,default=DEFAULT_STYLE_SPEC)
 parser.add_argument('--script',type=Path)
 parser.add_argument('--mode',default='audience_first_suspense')
 parser.add_argument('--output',type=Path)
 args=parser.parse_args()
 if args.command=='run':
  res=run()
 else:
  profile=learn(args.reference,args.case_file,args.frame_dir,args.style_spec)
  if args.command=='learn':
   path=args.output or (OUT/(profile['profile_id']+'_style_profile.json'))
   save(path,profile);res={'profile':str(path),'reference_frame_count':profile['reference_frame_count']}
  elif args.command=='compare':res=compare(profile,apply(profile,'audience_first_suspense'),apply(profile,'blocking_space_reveal'))
  else:
   if not args.script:parser.error('--script is required for prepare-script')
   res=compile_for_script(profile,args.mode,args.script)
   save(args.output or (OUT/'待执行的原版专业Skill_新剧本任务.json'),res)
 print(json.dumps(res if args.command!='prepare-script' else {k:v for k,v in res.items() if k!='original_script'},ensure_ascii=False,indent=2))
