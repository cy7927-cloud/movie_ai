#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Evidence-bound film-language study -> original directing rehearsal -> critique/repair.

IMPORTANT: The original movie is the teacher, never a defect target. Offline computations
measure visible patterns, not screenwriter intent, actor identity, or artistic quality.
The original-scene picture panels are PROGRAMMATIC 2D blocking sketches. No AI render,
no paid model, no 3D animation, no reconstructed movie is represented by this module.
"""
from __future__ import annotations
import argparse, copy, hashlib, html, json, math, os, re, shutil, statistics, subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parent
OUT=Path('output/apprentice')
LESSON_BEATS={
 'suspense_insert':['SETUP','INSERT','REACTION','COUNTERPOINT','DECISION'],
 'dialogue_reactions':['ESTABLISH','SPEAKER_A','LISTENER_B','SPEAKER_B','REACTION_A','RE_ESTABLISH'],
 'spatial_reveal':['ESTABLISH','POV_HINT','INSERT','REACTION','BLOCKING'],
}
GRAMMAR_CASES={
 'suspense_insert':'LESSON_01',
 'dialogue_reactions':'LESSON_03',
 'spatial_reveal':'LESSON_02',
}
BAD_STATES=('MISSING_BEAT','WRONG_ORDER','MISSING_CUT_REASON','MISSING_ACTING',
 'MISSING_SOUND_PLAN','AXIS_CROSS_UNMOTIVATED','PROP_NOT_LOCKED','CHARACTER_NOT_LOCKED',
 'GAZE_CONTRADICTION','ILLEGAL_DURATION','NARRATIVE_CAUSAL_GAP','DUPLICATE_SHOT',
 'BAD_STAGE_GEOMETRY','MISSING_SCENE_GOAL')


def load_json(p,default=None):
 p=Path(p)
 return json.loads(p.read_text('utf-8')) if p.is_file() else default

def save_json(p,obj):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 temp=p.with_suffix(p.suffix+'.tmp')
 temp.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
 temp.replace(p)

def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for part in iter(lambda:f.read(1024*1024),b''):h.update(part)
 return h.hexdigest()

def font(sz=23):
 for p in ['/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
           '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',
           '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf']:
  if Path(p).is_file():return ImageFont.truetype(p,sz)
 return ImageFont.load_default()


def visual_vector(file):
 """Tiny non-semantic low-cost viewpoint proxy; no recognizer or embedding claims."""
 im=cv2.imread(str(file))
 if im is None:raise FileNotFoundError(file)
 im=cv2.resize(im,(160,72),interpolation=cv2.INTER_AREA)
 lab=cv2.cvtColor(im,cv2.COLOR_BGR2LAB)
 hist=cv2.calcHist([lab],[0,1],None,[12,10],[0,256,0,256]).flatten()
 hist=hist/(np.linalg.norm(hist)+1e-8)
 g=cv2.cvtColor(im,cv2.COLOR_BGR2GRAY)
 # Gaussian blurred coarse spatial layout avoids overrating same palette, but NOT identity.
 coarse=cv2.resize(cv2.GaussianBlur(g,(9,9),0),(16,8)).astype(np.float32)/255
 contrast=float(g.std()/255)
 return {'hist':hist,'spatial':coarse.ravel(),'luma':float(g.mean()/255),'contrast':contrast}

def viewpoint_similarity(a,b):
 color=float(np.dot(a['hist'],b['hist']))
 layout=1.0-float(np.mean(np.abs(a['spatial']-b['spatial'])))
 return max(0.,min(1.,.55*color+.45*layout))


def scan_film_grammar(root=ROOT):
 """Unsupervised *candidates* for A-B-A visual return, pacing & audio continuation.

 A/B/A only means a visual echo by coarse image signals. It does NOT prove a reverse
 angle, same actor, same scene, matching eyeline, intent, or that the movie has an error.
 """
 root=Path(root)
 cards=load_json(root/'output/director_lab/director_cards.json',[])
 trans=load_json(root/'output/editorial_language/transitions.json',[])
 if not cards:raise RuntimeError('No director cards. Run director_craft.py run first')
 vectors=[]
 for c in cards:
  path=root/c['reference_images']['mid']
  actual=sha(path)
  if actual!=c['anchor_source_shas']['mid']:
   raise RuntimeError('Reference MID changed: '+c['shot_id'])
  vectors.append(visual_vector(path))
 echoes=[];rhythm=[]
 for i in range(len(cards)-2):
  a,b,c=vectors[i:i+3];ca,cb,cc=cards[i:i+3]
  adjacent=(viewpoint_similarity(a,b)+viewpoint_similarity(b,c))/2
  return_sim=viewpoint_similarity(a,c)
  contrast=round(return_sim-adjacent,4)
  if contrast>=0.025:
   echoes.append({'shots':[ca['shot_id'],cb['shot_id'],cc['shot_id']],
       'times_s':[ca['time']['start'],cb['time']['start'],cc['time']['start']],
       'visual_return_similarity':round(return_sim,4),
       'adjacent_similarity':round(adjacent,4),
       'visual_echo_margin':contrast,
       'label':'VISUAL_REPRISE_CANDIDATE_NOT_CONFIRMED_REVERSE_SHOT',
       'claims_actor_identity':False,'claims_editing_intent':False,
       'mid_frames':[x['reference_images']['mid'] for x in (ca,cb,cc)],
       'source_mid_sha256':[x['anchor_source_shas']['mid'] for x in (ca,cb,cc)],
       'interpretations_to_test':['是否真实回到同一空间或人物视角','是否是正反打／反应／插入镜头','对齐实际切点和声音后再确定叙事功能']})
  lengths=[x['time']['duration'] for x in (ca,cb,cc)]
  if lengths[1] < .65*min(lengths[0],lengths[2]):
   rhythm.append({'shots':[ca['shot_id'],cb['shot_id'],cc['shot_id']],
      'durations_s':lengths,'pattern':'LONG_SHORT_LONG_PROPOSED',
      'center_ratio':round(lengths[1]/min(lengths[0],lengths[2]),3),
      'narrative_interpretation_verified':False})
 echoes.sort(key=lambda r:r['visual_echo_margin'],reverse=True)
 rhythm.sort(key=lambda r:r['center_ratio'])
 sound=[]
 for t in trans:
  s=t.get('sound_at_cut',{})
  if s.get('status')!='MEASURED_REFERENCE_ONLY':continue
  sound.append({'from':t['from'],'to':t['to'],'time_s':t['cut_time_sec'],
       'audio_energy_similarity':s['energy_similarity_ratio'],
       'spectral_proxy':s['spectral_shape_cosine_proxy'],
       'status':'AUDIO_SIGNAL_ONLY_NOT_VERIFIED_SOUND_BRIDGE'})
 sound.sort(key=lambda x:(x['audio_energy_similarity']+x['spectral_proxy']),reverse=True)
 lessons=load_json(root/'output/editorial_language/director_lessons.json',[])
 byshot={c['shot_id']:c for c in cards}
 learned=[]
 for lesson in lessons:
  names=lesson.get('shots',[])
  if not all(x in byshot for x in names):continue
  # No model is fed invented cinema scores. Only durations are measured from source.
  learned.append({'lesson_id':lesson['id'],'name':lesson['title'],
    'source_shots':names,'measured_durations_s':[round(byshot[x]['time']['duration'],2) for x in names],
    'working_interpretation':lesson.get('hypothesis',''),
    'alternative_explanations':lesson.get('alternatives',[]),
    'verification_todo':lesson.get('verify',[]),
    'approved_director_intent':bool(lesson.get('narrative_approved',False)),
    'source_mid_images':lesson.get('reference_mid_frames',[]),
    'training_status':'CASE_STUDY_HYPOTHESIS_NEEDS_REVIEW'})
 source=load_json(root/'data/project_manifest.json',{})
 return {'source_sha256':source.get('source_sha256'),'shots_proposed':len(cards),
   'potential_visual_reprises_count':len(echoes),'visual_reprises':echoes,
   'rhythmic_triplets_count':len(rhythm),'rhythmic_triplets':rhythm,
   'reference_audio_cut_samples':len(sound),'sound_continuation_proxies':sound,
   'grounded_case_studies':learned,'grounded_case_count':len(learned),
   'film_defect_claims':0,'director_intent_verified':0,
   'what_is_not_learned':['screenplay causality','dialogue content','face identity','true shot axis','actual director intention','3D motion'],
   'provenance':'LOCAL_SOURCE_IMAGES_AUDIO_AND_USER_PROJECT_CASE_STUDIES_ONLY'}


def scene_example():
 return {'id':'ORIGINAL_SCENE_RESEARCH_STATION','title':'失联信号','brief':'深夜的科研站里，一台失联的探测器突然传来未知信号。研究员与同伴发现信号指向禁区，最终决定封锁通道。',
  'location':'深夜科研站控制室','time_of_day':'night','tone':'克制、悬疑、逐步警觉',
  'characters':[{'id':'ACT_A','name':'研究员','x':.30,'depth':.52,'costume':'灰蓝研究服'},
                {'id':'ACT_B','name':'同伴','x':.76,'depth':.58,'costume':'深灰研究服'}],
  'props':[{'id':'PROP_SIGNAL','name':'失联探测器终端','x':.58,'depth':.68}],
  'central_question':'失联信号来自谁，为什么指向禁区？',
  'reveal':'终端出现未知信号，地图显示禁区坐标',
  'decision':'两人决定封锁通道','emotion_arc':['疑惑','怀疑','惊觉','决断'],
  'audience_information_rule':'先让观众看见异常信号，再展示研究员的反应，不提前揭晓来源',
  'camera_axis_side':'SOUTH','lighting':'冷色低照度，终端屏幕是局部光源',
  'origin':'DEMONSTRATION_ORIGINAL_SCENE_NOT_PART_OF_REFERENCE_FILM'}


def check_scene(scene):
 if not isinstance(scene,dict) or not (4<=len(str(scene.get('brief','')))<=3000):raise ValueError('Need a scene brief')
 for k in ('location','reveal','decision','camera_axis_side'):
  if not str(scene.get(k,'')).strip():raise ValueError('Missing required scene field: '+k)
 chars=scene.get('characters',[])
 if len(chars)<1 or len(chars)>8:raise ValueError('1-8 explicit characters required')
 ids=[x['id'] for x in chars]
 if len(ids)!=len(set(ids)):raise ValueError('Character ids must be unique')
 for a in chars:
  if not isinstance(a.get('x'),(int,float)) or not .05<=a['x']<=.95:raise ValueError('Invalid blocking x')
  if not isinstance(a.get('depth'),(int,float)) or not .05<=a['depth']<=.95:raise ValueError('Invalid blocking depth')
 props=scene.get('props',[])
 if len({x['id'] for x in props})!=len(props):raise ValueError('Duplicate prop ids')
 return True


def _shot(beat,scene,style,detail=True):
 a=scene['characters'][0];b=(scene['characters'][1] if len(scene['characters'])>1 else a)
 prop=scene.get('props',[{'id':'UNKNOWN','name':'未锁定道具','x':.55,'depth':.66}])[0]
 conf={
 'SETUP':(3.3,a['id'],'WIDE','人物面对异常前的处境与悬念铺垫','观察环境，尚未发现信号','AUDIO_ROOM'),
 'ESTABLISH':(3.8,a['id'],'WIDE','建立人物和场景的地理关系','停顿并观察空间','AUDIO_ROOM'),
 'INSERT':(1.8,prop['id'],'INSERT','向观众交代新出现的可见线索',scene['reveal'],'AUDIO_SIGNAL'),
 'POV_HINT':(2.3,prop['id'],'MEDIUM','让观众沿人物视线接近局部线索',scene['reveal'],'AUDIO_ROOM'),
 'REACTION':(2.4,a['id'],'CLOSE','观众已经看见异常，观察人物是否理解','先眼神变化，后身体转向','AUDIO_DUCK'),
 'REACTION_A':(2.2,a['id'],'CLOSE','让人物沉默构成情绪反馈','眼神先于台词改变','AUDIO_PAUSE'),
 'LISTENER_B':(2.3,b['id'],'CLOSE','观察倾听者，避免机械轮流给说话者特写','先听后反应','AUDIO_VOICE_OVER'),
 'SPEAKER_A':(2.5,a['id'],'CLOSE','由A引出问题、关系或信息','A提出疑问，并稍作停顿','AUDIO_DIALOGUE_A'),
 'SPEAKER_B':(2.7,b['id'],'CLOSE','B回应并改变人物的判断','B作出克制回答','AUDIO_DIALOGUE_B'),
 'COUNTERPOINT':(2.9,b['id'],'MEDIUM','给观众第二层证据或不同视角','B开始分析信号，准备行动','AUDIO_CONTINUE'),
 'DECISION':(3.4,a['id'],'WIDE','让人物行动完成这一场戏的因果选择',scene['decision'],'AUDIO_ACTION'),
 'RE_ESTABLISH':(3.6,a['id'],'WIDE','重新建立两人的相对位置与关系','两人形成新的行动关系','AUDIO_ROOM'),
 'BLOCKING':(3.6,a['id'],'WIDE','验证角色从观察到行动的动线',scene['decision'],'AUDIO_STEPS'),
 }
 dur,focus,size,purpose,action,sound=conf[beat]
 xs={x['id']:{'x':x['x'],'depth':x['depth']} for x in scene['characters']}
 return {'beat':beat,'duration_s':dur,'lens_size':size,'focus_asset_id':focus,
   'narrative_purpose':purpose,'blocking':xs,'acting':action if detail else '',
   'gaze_target_id':prop['id'] if beat in ('REACTION','REACTION_A','SETUP','POV_HINT') else (b['id'] if beat=='SPEAKER_A' else a['id'] if beat in ('SPEAKER_B','LISTENER_B') else ''),
   'axis_side':scene['camera_axis_side'],'cut_reason':('这一次切镜改变观众已知的信息或情绪焦点' if detail else ''),
   'audio_plan':sound if detail else '',
   'sound_bridge_policy':'EXPLICIT_NOT_YET_CHECKED' if detail else '',
   'scene_id':scene['id'],
   'declared_characters':[x['id'] for x in scene['characters']],
   'declared_props':[x['id'] for x in scene.get('props',[])],
   'location':scene['location'],'lighting':scene.get('lighting','未指定'),
   'key_reveal_text':scene['reveal'] if beat in ('INSERT','POV_HINT') else '',
   'decision_text':scene['decision'] if beat in ('DECISION','BLOCKING') else '',
   'informed_by_source_lesson':GRAMMAR_CASES[style],
   'film_intent_claimed_verified':False}


def make_baseline(scene,mode):
 if mode not in LESSON_BEATS:raise ValueError('Unknown mode')
 beats=LESSON_BEATS[mode]
 # A simple first-draft outline; details/causal links have not yet been directed.
 sampled=[beats[0],beats[1],beats[-1]]
 draft=[]
 for b in sampled:
  shot=_shot(b,scene,mode,detail=False)
  shot['audio_plan']='';shot['sound_bridge_policy']='';shot['gaze_target_id']=''
  shot['cut_reason']=''
  draft.append(shot)
 return draft


def _issues(shots,scene,mode):
 expected=LESSON_BEATS[mode]
 beats=[x['beat'] for x in shots]
 errs=[]
 def add(code,explanation,which=None):errs.append({'code':code,'shot_index':which,'reason':explanation})
 for b in expected:
  if b not in beats:add('MISSING_BEAT',f'缺少{b}的叙事功能')
 ordering=[expected.index(b) for b in beats if b in expected]
 if any(b<a for a,b in zip(ordering,ordering[1:])):add('WRONG_ORDER','因果或叙事功能顺序不成立')
 actorids={a['id'] for a in scene['characters']};propids={p['id'] for p in scene.get('props',[])}
 for i,x in enumerate(shots):
  if not x.get('cut_reason','').strip():add('MISSING_CUT_REASON','缺少具体的切镜理由',i)
  if not x.get('acting','').strip():add('MISSING_ACTING','没有可执行的表演动作',i)
  if not x.get('audio_plan') or not x.get('sound_bridge_policy'):add('MISSING_SOUND_PLAN','音画节拍或声桥处理未制定',i)
  if x.get('axis_side')!=scene['camera_axis_side'] and not x.get('axis_reset_justified'):
   add('AXIS_CROSS_UNMOTIVATED','人物方向被无说明地越轴',i)
  fid=x.get('focus_asset_id','')
  if fid not in actorids|propids:add('PROP_NOT_LOCKED','焦点未引用已声明的角色或道具ID',i)
  if set(x.get('declared_characters',[]))!=actorids:add('CHARACTER_NOT_LOCKED','角色资产依赖丢失或被替换',i)
  if x['beat'] in ('REACTION','REACTION_A','POV_HINT'):
   if x.get('gaze_target_id')!=(next(iter(propids)) if propids else ''):
    add('GAZE_CONTRADICTION','视线目标与已展示的信息不匹配或未填写',i)
  if not 0.5<=float(x.get('duration_s',0))<=12:add('ILLEGAL_DURATION','镜头时长不可用于当前静态预演',i)
  geom=x.get('blocking',{})
  if any(not 0.<=a.get('x',-1)<=1 or not 0.<=a.get('depth',-1)<=1 for a in geom.values()):
   add('BAD_STAGE_GEOMETRY','舞台坐标超出归一化范围',i)
  if x.get('location')!=scene['location']:add('BAD_STAGE_GEOMETRY','场景连续性被无意修改',i)
  if i and x['beat']==shots[i-1]['beat'] and x.get('focus_asset_id')==shots[i-1].get('focus_asset_id'):
   add('DUPLICATE_SHOT','镜头没有提供新的叙事信息或视觉焦点',i)
 if 'INSERT' in expected:
  if 'INSERT' in beats and 'REACTION' in beats and beats.index('REACTION')<beats.index('INSERT'):
   add('NARRATIVE_CAUSAL_GAP','人物反应先于应当触发它的信息出现')
  if not any(x.get('key_reveal_text')==scene['reveal'] for x in shots):
   add('MISSING_SCENE_GOAL','关键信息没有被镜头展示')
 if not any(x.get('decision_text')==scene['decision'] for x in shots if x['beat'] in ('DECISION','BLOCKING')):
  # Dialogue grammar might close on emotional change rather than explicit physical decision.
  if mode!='dialogue_reactions':add('MISSING_SCENE_GOAL','场景行动目标没有在结尾明确')
 return errs


def critique(shots,scene,mode):
 issues=_issues(shots,scene,mode)
 codes=sorted(set(x['code'] for x in issues))
 # Transparent technical coverage ONLY. It is not a 0..1 cinema-quality metric.
 structural_coverage=round((len(BAD_STATES)-len(codes))/len(BAD_STATES),3)
 return {'issues':issues,'issue_types':codes,'issue_count':len(issues),
   'structural_coverage_fraction':structural_coverage,
   'structural_checks_passing':len(BAD_STATES)-len(codes),
   'structural_checks_total':len(BAD_STATES),
   'director_artistic_score':None,'director_identity_verified':False,
   'moving_actor_performance_verified':False,'real_visual_fidelity_checked':False,
   'acceptable_for_visual_production':False,
   'interpretation':'仅检查导演生产指令的可执行性；不判断电影艺术质量。'}


def revise(shots,scene,mode,report):
 """Versioned, targeted structural repairs; no learned-network/model claims."""
 result=copy.deepcopy(shots)
 codes=set(report['issue_types']);edits=[]
 # First repair causal shot order / missing beats without rewriting already stable shots.
 if 'MISSING_BEAT' in codes or 'WRONG_ORDER' in codes:
  old={x['beat']:x for x in result}
  result=[copy.deepcopy(old.get(beat) or _shot(beat,scene,mode,detail=False)) for beat in LESSON_BEATS[mode]]
  edits.append({'type':'NARRATIVE_STRUCTURE','reason':'补齐叙事信息→反应→行动的必要节拍','affected_beats':LESION_SAFE_LIST(LESION=LESSON_BEATS[mode])})
  return result,edits
 # All next-cycle fixes are local to only failed fields, not a re-creation of the movie.
 actors={a['id'] for a in scene['characters']}
 props={p['id'] for p in scene.get('props',[])}
 for i,x in enumerate(result):
  blueprint=_shot(x['beat'],scene,mode,detail=True)
  if 'MISSING_CUT_REASON' in codes and not x.get('cut_reason'):
   x['cut_reason']=blueprint['cut_reason'];edits.append({'type':'CUT_MOTIVATION','index':i})
  if 'MISSING_ACTING' in codes and not x.get('acting'):
   x['acting']=blueprint['acting'];edits.append({'type':'ACTING_INSTRUCTIONS','index':i})
  if 'MISSING_SOUND_PLAN' in codes and (not x.get('audio_plan') or not x.get('sound_bridge_policy')):
   x['audio_plan']=blueprint['audio_plan'];x['sound_bridge_policy']='VERIFY_AGAINST_TIMED_PREVIS';edits.append({'type':'SOUND_PLAN','index':i})
  if 'AXIS_CROSS_UNMOTIVATED' in codes and x.get('axis_side')!=scene['camera_axis_side']:
   x['axis_side']=scene['camera_axis_side'];edits.append({'type':'CAMERA_AXIS','index':i})
  if 'CHARACTER_NOT_LOCKED' in codes and set(x.get('declared_characters',[]))!=actors:
   x['declared_characters']=sorted(actors);edits.append({'type':'ASSET_LOCK','index':i})
  if 'PROP_NOT_LOCKED' in codes and x.get('focus_asset_id') not in actors|props:
   x['focus_asset_id']=blueprint['focus_asset_id'];edits.append({'type':'FOCUS_ASSET','index':i})
  if 'GAZE_CONTRADICTION' in codes and x['beat'] in ('REACTION','REACTION_A','POV_HINT'):
   x['gaze_target_id']=blueprint['gaze_target_id'];edits.append({'type':'EYELINE','index':i})
  if 'ILLEGAL_DURATION' in codes and not .5<=x.get('duration_s',0)<=12:
   x['duration_s']=blueprint['duration_s'];edits.append({'type':'PACING','index':i})
  if 'BAD_STAGE_GEOMETRY' in codes:
   x['blocking']=blueprint['blocking'];x['location']=scene['location'];edits.append({'type':'STAGING_GEOMETRY','index':i})
  if 'MISSING_SCENE_GOAL' in codes:
   x['key_reveal_text']=blueprint['key_reveal_text'];x['decision_text']=blueprint['decision_text'];edits.append({'type':'DRAMATIC_GOAL','index':i})
  if 'DUPLICATE_SHOT' in codes and i and x['beat']==result[i-1]['beat']:
   # Removing a redundant adjacent shot is more honest than swapping a random angle.
   x['_redundant_remove']=True;edits.append({'type':'REMOVE_REDUNDANCY','index':i})
 result=[x for x in result if not x.pop('_redundant_remove',False)]
 if 'WRONG_ORDER' in codes or 'NARRATIVE_CAUSAL_GAP' in codes:
  result.sort(key=lambda x:LESSON_BEATS[mode].index(x['beat']) if x['beat'] in LESSON_BEATS[mode] else 999)
  edits.append({'type':'REORDER_FOR_CAUSALITY'})
 return result,edits

def LESION_SAFE_LIST(LESION):
 return list(LESION)


def iterate_scene(scene,mode='suspense_insert',max_rounds=7):
 check_scene(scene)
 if mode not in LESSON_BEATS:raise ValueError('Unknown grammar')
 if not 1<=max_rounds<=30:raise ValueError('max_rounds must be 1..30')
 shots=make_baseline(scene,mode)
 history=[];prev_hash=None
 for round_n in range(max_rounds+1):
  report=critique(shots,scene,mode)
  j=json.dumps(shots,ensure_ascii=False,sort_keys=True).encode('utf-8')
  h=hashlib.sha256(j).hexdigest()
  row={'round':round_n,'candidate_sha256':h,'shot_count':len(shots),'shots':copy.deepcopy(shots),'self_review':report,
       'edits_before_next_round':[],'operator':'EXPLICIT_RULE_BASED_DIRECTOR_WORKFLOW'}
  history.append(row)
  if not report['issues']:break
  if round_n>=max_rounds:break
  revised,changes=revise(shots,scene,mode,report)
  if not changes:break
  next_h=hashlib.sha256(json.dumps(revised,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
  if next_h in {v['candidate_sha256'] for v in history}:break
  row['edits_before_next_round']=changes
  shots=revised
 final=history[-1]
 return {'scene':scene,'grammar':mode,'lesson_case':GRAMMAR_CASES[mode],
   'history':history,'final':{'round':final['round'],'shot_count':len(final['shots']),
                              'technical_review':final['self_review'],'shots':final['shots']},
   'structural_planning_complete':final['self_review']['issue_count']==0,
   'director_review_required':True,'director_quality_verified':False,
   'generated_original_ai_stills':0,'generated_ai_video':0,'paid_video_calls':0,
   'learning_status':'CASES_ARE_HYPOTHESES; REVISION_IS_DETERMINISTIC_RULES',
   'truthful_claim':'原片只提供导演语法学习线索；本输出为原创场景程序化导演方案，未验证艺术质量。'}


def controlled_negative_tests(plan):
 """Adversarial stress tests. These mutations NEVER touch reference movie frames."""
 source=plan['final']['shots'];scene=plan['scene'];mode=plan['grammar']
 tests=[]
 def trial(name,fn,expected):
  v=copy.deepcopy(source);fn(v)
  grade=critique(v,scene,mode)
  tests.append({'case':name,'expected_detected_issue':expected,
   'actual_issues':grade['issue_types'],'pass':expected in grade['issue_types'],
   'target':'GENERATED_DIRECTOR_PLAN_NOT_REFERENCE_FILM'})
 required= 'REACTION' if mode!='dialogue_reactions' else 'LISTENER_B'
 trial('删除反应／倾听镜头',lambda v:v.__setitem__(slice(None),[x for x in v if x['beat']!=required]),'MISSING_BEAT')
 trial('无理由越过人物调度轴线',lambda v:v[1].update(axis_side='NORTH' if scene['camera_axis_side']!='NORTH' else 'SOUTH'),'AXIS_CROSS_UNMOTIVATED')
 trial('擦除切镜理由',lambda v:v[1].update(cut_reason=''),'MISSING_CUT_REASON')
 trial('替换未锁定的角色或道具',lambda v:v[1].update(focus_asset_id='ASSET_FICTITIOUS'),'PROP_NOT_LOCKED')
 trial('出现不合理镜头时长',lambda v:v[1].update(duration_s=.01),'ILLEGAL_DURATION')
 trial('声桥信息丢失',lambda v:v[1].update(audio_plan=''),'MISSING_SOUND_PLAN')
 trial('失去人物资产版本绑定',lambda v:v[1].update(declared_characters=['UNKNOWN_ACTOR']),'CHARACTER_NOT_LOCKED')
 if mode!='dialogue_reactions':
  trial('人物目光指向未定义目标',lambda v:next(x for x in v if x['beat']=='REACTION').update(gaze_target_id='UNSEEN_PROP'),'GAZE_CONTRADICTION')
 return {'tests':tests,'passed':sum(x['pass'] for x in tests),'total':len(tests),
   'not_a_movie_quality_score':True}


def paint_frame(scene,shot,index,total,path):
 """Draw a cartoon 2D blocking thumbnail, NOT a generative cinematic still."""
 W,H=960,540;im=Image.new('RGB',(W,H),(16,28,43));d=ImageDraw.Draw(im)
 # Full scene background: gradients and simple horizon/perspective, deliberately schematic.
 for y in range(0,455):
  z=y/455.;d.line((0,y,W,y),fill=(int(18+18*z),int(29+28*z),int(44+35*z)))
 d.rectangle((0,365,W,455),fill='#22374d')
 for i in range(11):
  xx=int(i*W/10);d.line((W//2,255,xx,455),fill='#385269',width=1)
 d.line((0,365,W,365),fill='#536779',width=2)
 d.rectangle((17,35,942,410),outline='#5b7892',width=2)
 # Lab / station visual shorthand; props may be drawn big as inserts.
 fid=shot['focus_asset_id'];is_insert=shot['lens_size']=='INSERT';is_close=shot['lens_size']=='CLOSE'
 if 'PROP' in fid or is_insert:
  cx=475 if is_insert else 556;cy=220 if is_insert else 240;sc=1.9 if is_insert else .95
  box=(int(cx-125*sc),int(cy-75*sc),int(cx+125*sc),int(cy+65*sc))
  d.rounded_rectangle(box,radius=15,fill='#162839',outline='#62d0db',width=5)
  d.line((box[0]+20,cy,box[2]-20,cy),fill='#62d0db',width=2)
  points=[(box[0]+20+j*(box[2]-box[0]-40)//20, cy-int(math.sin(j*.73)*15)-int((j%4==0)*14)) for j in range(21)]
  d.line(points,fill='#e4b968',width=4)
  d.ellipse((cx-8,cy-8,cx+8,cy+8),fill='#e9c678')
 else:
  # Station screens / architectural cues
  d.rectangle((355,122,700,275),fill='#132735',outline='#51858a',width=4)
  d.rectangle((376,143,678,255),outline='#4a7a87',width=2)
  d.line((400,208,663,205),fill='#4eb1a9',width=2)
  d.ellipse((520,181,542,203),outline='#d3ac66',width=2)
  for i,a in enumerate(scene['characters'][:4]):
   px=int(a['x']*W);px=int(W*.47+(px-W*.47)*(.45 if is_close else 1.)) if is_close else px
   if is_close and shot['focus_asset_id']==a['id']:px=480
   scale=1.65 if is_close and shot['focus_asset_id']==a['id'] else 1.0
   cy=int(286+(a['depth']-.5)*65)
   width=int(54*scale);head=int(26*scale);body=int(100*scale)
   d.ellipse((px-head,cy-head-48*scale,px+head,cy+head-48*scale),fill=('#86b6d0' if i==0 else '#bdac91'),outline='#ccdae0',width=2)
   d.polygon([(px-width,cy),(px+width,cy),(px+int(width*.73),cy+body),(px-int(width*.73),cy+body)],
             fill=('#355f7e' if i==0 else '#74665f'),outline='#acc2ca')
   if not is_close or shot['focus_asset_id']==a['id']:
    d.text((px-38,cy+body+5),a['id'],font=font(20),fill='#d7e8f6')
  if is_close:
   # Out-of-focus actors intentionally simplified: the focus on reaction, not identity proof.
   d.text((26,303),'FOCUS  '+fid,font=font(27),fill='#e0c786')
 # Explicitly label the programme, avoiding confusion with film-generated artwork.
 d.rectangle((0,455,W,H),fill='#0b1726')
 d.text((20,462),f'PREVIS  {index+1}/{total}  ·  {shot["beat"]}  ·  {shot["duration_s"]:.1f}s',font=font(25),fill='#f3d59c')
 d.text((20,496),(shot['narrative_purpose'][:42]),font=font(22),fill='#e2eefa')
 d.text((700,15),'SCHEMATIC · 2D',font=font(19),fill='#f0b4a3')
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);im.save(path,quality=91)
 return path


def draw_storyboard(scene,shots,paths,destination):
 cols=3;rows=math.ceil(len(paths)/cols);margin=18;cw,ch=640,360
 board=Image.new('RGB',(cols*cw+(cols+1)*margin,rows*ch+(rows+1)*margin+95),'#09121f')
 d=ImageDraw.Draw(board)
 d.text((24,15),'原创场景导演分镜 · 程序化二维站位预演',font=font(29),fill='#efd9b2')
 d.text((24,52),'不是电影画面，不是AI图像模型产物；用于检查剪辑、演员站位和镜头时长。',font=font(19),fill='#afc8d6')
 for i,p in enumerate(paths):
  im=Image.open(p);im.thumbnail((cw,ch))
  x=margin+(i%cols)*(cw+margin);y=95+margin+(i//cols)*(ch+margin)
  board.paste(im,(x,y))
 destination=Path(destination);destination.parent.mkdir(parents=True,exist_ok=True)
 board.save(destination,quality=89)
 return destination


def make_animatic(shots,paths,destination):
 """Cut a timed STILLS slideshow via local ffmpeg: NOT an AI-generated moving image."""
 if not shutil.which('ffmpeg'):return {'status':'SKIPPED_FFMPEG_UNAVAILABLE','is_ai_generated_video':False}
 path=Path(destination);path.parent.mkdir(parents=True,exist_ok=True)
 playlist=path.with_suffix('.ffconcat')
 # ffconcat keeps fractional still durations; last duplicated frame avoids truncation.
 def quote(p):return str(Path(p).resolve()).replace("'", "'\\''")
 lines=['ffconcat version 1.0']
 for p,s in zip(paths,shots):
  lines.extend(["file '"+quote(p)+"'",f'duration {float(s["duration_s"]):.3f}'])
 lines.append("file '"+quote(paths[-1])+"'")
 playlist.write_text('\n'.join(lines)+'\n',encoding='utf-8')
 try:
  p=subprocess.run(['ffmpeg','-nostdin','-y','-hide_banner','-loglevel','error','-f','concat',
   '-safe','0','-i',str(playlist),'-r','10','-pix_fmt','yuv420p','-c:v','libx264',
   '-preset','ultrafast','-crf','32','-movflags','+faststart',str(path)],
   stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=80)
  if p.returncode:return {'status':'FAILED','stderr':p.stderr.decode('utf-8','replace')[:500],'is_ai_generated_video':False}
  return {'status':'CREATED_TIMED_STORYBOARD_SLIDESHOW','path':str(path),
   'is_ai_generated_video':False,'film_reconstruction':False,'paid_video_calls':0}
 except (subprocess.TimeoutExpired,OSError) as e:return {'status':'FAILED','reason':str(e)[:250],'is_ai_generated_video':False}


def _escape(x):return html.escape(str(x),quote=True)

def build_html(root,study,plan,negative,board,animatic):
 root=Path(root);out=root/OUT;out.mkdir(parents=True,exist_ok=True)
 examples=[]
 for item in study['visual_reprises'][:8]:
  imgs=''.join('<figure><img src="'+_escape('../'+p)+'"><figcaption>'+_escape(s)+'</figcaption></figure>' for p,s in zip(item['mid_frames'],item['shots']))
  examples.append(f'<article class="motif"><div class="triple">{imgs}</div><p>视觉回归差值 {_escape(item["visual_echo_margin"])} — 仅为自动检索线索，<strong>不能自动认定正反打或同一演员。</strong></p></article>')
 histories=[]
 for h in plan['history']:
  issues='、'.join(h['self_review']['issue_types']) or '结构约束已齐备（不代表画面质量通过）'
  histories.append('<li><b>第'+str(h['round'])+'轮</b> · '+str(h['shot_count'])+'镜头 · 未满足项 '+str(h['self_review']['issue_count'])+' · '+_escape(issues)+'</li>')
 cases=[]
 for case in study['grounded_case_studies']:
  pics=''.join('<img src="'+_escape('../'+p)+'" title="原片参考">' for p in case['source_mid_images'][:5])
  cases.append('<article class="motif"><b>'+_escape(case['name'])+'</b><div class="triple">'+pics+'</div><p>原片候选镜头：'+_escape(' → '.join(case['source_shots']))+'</p><p>解释假设：'+_escape(case['working_interpretation'])+'</p><p>替代解释：'+_escape('；'.join(case['alternative_explanations']))+'</p></article>')
 orig_shots=''.join('<tr><td>'+str(i+1)+'</td><td>'+_escape(s['beat'])+'</td><td>'+_escape(s['duration_s'])+'s</td><td>'+_escape(s['narrative_purpose'])+'</td><td>'+_escape(s['acting'])+'</td><td>'+_escape(s['cut_reason'])+'</td></tr>' for i,s in enumerate(plan['final']['shots']))
 tests=''.join('<li>' + ('✓ ' if x['pass'] else '✕ ') + _escape(x['case'])+' → '+_escape(x['expected_detected_issue'])+'</li>' for x in negative['tests'])
 output=f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>AI电影导演 · 自学习审片与原创预演</title><style>
 :root{{color-scheme:dark;font:15px/1.65 system-ui,Arial,sans-serif;background:#0b1320;color:#e6eff7}}*{{box-sizing:border-box}}body{{margin:0 auto;max-width:1460px;padding:18px}}header{{border-bottom:1px solid #3b536d;padding:10px 0 16px}}h1{{font-size:27px;color:#f1d1a0}}h2{{font-size:21px;margin-top:32px}}h3{{color:#edc488}}p{{margin:9px 0}}small,.muted{{color:#a9b9c9}}a{{color:#99d9ff}}article,.panel{{border-radius:12px;background:#17273a;border:1px solid #324b67;padding:14px;margin-bottom:13px}}.triple{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin-top:12px}}.triple img{{width:100%;border-radius:6px}}figure{{margin:0}}figcaption{{font-size:12px;color:#b2c6d6}}.lead{{color:#e9c68f}}.grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}}.metrics{{display:flex;flex-wrap:wrap;gap:9px}}.metrics b{{display:block;font-size:26px}}.metrics span{{border:1px solid #3c5977;padding:10px 18px;border-radius:9px}}table{{border-collapse:collapse;width:100%}}td,th{{border-bottom:1px solid #394c62;padding:8px;text-align:left;vertical-align:top}}th{{color:#eec99b}}img.full{{max-width:100%;border-radius:9px;border:1px solid #36506e}}video{{max-width:100%;border-radius:10px}}code{{color:#e3b98f}}@media(max-width:760px){{.grid{{grid-template-columns:1fr}}.triple{{grid-template-columns:1fr}}}}</style></head><body>
 <header><h1>AI电影导演 · 电影语言学习、反例自审与定向重写</h1><p class="lead">原片是导演学习对象，不是质量故障对象。生成物是原创二维站位预演，不是AI电影复刻。</p><p><a href="/editing">电影语言案例</a> · <a href="/director">镜头导演卡</a> · <a href="/">生成分镜与审片</a></p></header>
 <h2>本次真实状态</h2><div class="metrics"><span><b>{study['shots_proposed']}</b>候选镜头</span><span><b>{study['potential_visual_reprises_count']}</b>视觉回归候选</span><span><b>{study['rhythmic_triplets_count']}</b>节奏三连候选</span><span><b>{len(plan['history'])}</b>原创方案的自审版本</span><span><b>{negative['passed']}/{negative['total']}</b>规则反例检出</span><span><b>0</b>导演真实成片验收</span></div>
 <h2>一、研究原片如何组织信息</h2><p>以下仅为低成本视觉检索与人工假设的证据，不是人物识别、正反打分类或真正剧本理解。</p>
 <div class="grid">{''.join(cases)}</div>
 <h3>自动发现：A—B—A 视觉回归候选</h3><div class="grid">{''.join(examples) or '<p>未达到当前视觉回归阈值；这不是电影语言质量评价。</p>'}</div>
 <h2>二、原创场景：导演试拍与自我返工</h2><div class="panel"><b>{_escape(plan['scene']['title'])}</b><p>{_escape(plan['scene']['brief'])}</p><p>语法研究来源：{_escape(plan['lesson_case'])}；原案例仍为假设，原创编排仍需要导演终审。</p><ol>{''.join(histories)}</ol></div>
 <img class="full" src="../{_escape(str(board.relative_to(root)))}" alt="原创场景程序化二维导演分镜"/>
 <p class="muted">二维程序化站位图仅供讨论镜头功能、切镜节奏、演员视线与资产约束；人物形象、真实摄影、表演、三维机位、音画质量尚未验证。</p>
 <h3>定时粗剪预演（本地FFmpeg静帧拼接，不是AI生成视频）</h3>
 {('<video controls preload="metadata" src="../'+_escape(str(Path(animatic['path']).relative_to(root)))+'"></video>') if animatic.get('status')=='CREATED_TIMED_STORYBOARD_SLIDESHOW' else '<p>本机未生成粗剪视频，仍可直接查看上面的静态分镜。</p>'}
 <h3>最终镜头生产指令</h3><table><thead><tr><th>#</th><th>叙事节拍</th><th>时长</th><th>戏剧目的</th><th>演员动作</th><th>切镜动机</th></tr></thead><tbody>{orig_shots}</tbody></table>
 <h2>三、反例检验：系统真的能识别哪类错误？</h2><p>针对<strong>自己生产的镜头方案</strong>主动制造越轴、漏反应、无镜头理由等错误，检查审查程序是否能检出。成功不等于高艺术质量。</p><div class="panel"><ol>{tests}</ol></div>
 <h2>四、真实验收边界</h2><div class="panel"><p>电影真实导演意图确认：<b>0</b>；本项目独立AI画面复刻通过：<b>0</b>；二维预演：已生成；真实AI视频：<b>0</b>；付费视频模型调用：<b>0</b>。</p><p>系统已经从原片提取候选剪辑语法，能够进行原创分镜的规则型自我修改与反例测试；它还没有学会完整的专业导演判断。需要台词、剧情、演员、三维空间和真实作品复核。</p></div></body></html>'''
 path=root/'DIRECTOR_APPRENTICE.html';path.write_text(output,'utf-8');return path


def run(root=ROOT,scene=None,mode='suspense_insert',max_rounds=7,make_video=True):
 root=Path(root);folder=root/OUT;folder.mkdir(parents=True,exist_ok=True)
 study=scan_film_grammar(root)
 scene=scene or scene_example()
 plan=iterate_scene(scene,mode,max_rounds)
 negative=controlled_negative_tests(plan)
 save_json(folder/'film_grammar_index.json',study)
 save_json(folder/'original_director_loop.json',plan)
 save_json(folder/'counterfactual_tests.json',negative)
 frames=[]
 for i,s in enumerate(plan['final']['shots']):frames.append(paint_frame(scene,s,i,len(plan['final']['shots']),folder/'previs_frames'/f'frame_{i+1:02d}.jpg'))
 board=draw_storyboard(scene,plan['final']['shots'],frames,folder/'original_2D_storyboard.jpg')
 animatic=make_animatic(plan['final']['shots'],frames,folder/'original_timed_previs.mp4') if make_video else {'status':'DISABLED','is_ai_generated_video':False}
 page=build_html(root,study,plan,negative,board,animatic)
 meta={'source_sha256':study['source_sha256'],'reference_shots_proposed':study['shots_proposed'],
   'visual_reprise_candidates':study['potential_visual_reprises_count'],
   'pacing_triplets_candidates':study['rhythmic_triplets_count'],
   'reference_case_studies':study['grounded_case_count'],
   'self_review_rounds':len(plan['history']),'original_shot_count':len(plan['final']['shots']),
   'initial_issue_count':plan['history'][0]['self_review']['issue_count'],
   'final_issue_count':plan['final']['technical_review']['issue_count'],
   'counterfactuals_detected':negative['passed'],'counterfactuals_total':negative['total'],
   'procedural_2D_previs':str(board.relative_to(root)),'timed_slideshow':animatic,
   'html':str(page.relative_to(root)),
   'model_generated_images':0,'ai_generated_video':0,'paid_video_requests':0,
   'director_intent_verified':0,'reconstruction_passed':0,
   'programmatic_rule_critic_not_vision_model':True,
   'note':'参考影片的剪辑信息是学习素材；新分镜为程序化草图；结构自审通过不等于具有专业导演艺术判断。'}
 save_json(folder/'acceptance.json',meta)
 return meta


def main():
 ap=argparse.ArgumentParser(description=__doc__)
 ap.add_argument('--scene',help='Original scene JSON with actor IDs, locked prop, blocking and story beats')
 ap.add_argument('--mode',choices=list(LESSON_BEATS),default='suspense_insert')
 ap.add_argument('--rounds',type=int,default=7)
 ap.add_argument('--no-animatic',action='store_true')
 a=ap.parse_args()
 scene=load_json(a.scene) if a.scene else None
 print(json.dumps(run(ROOT,scene,a.mode,a.rounds,not a.no_animatic),ensure_ascii=False,indent=2))

if __name__=='__main__':main()
