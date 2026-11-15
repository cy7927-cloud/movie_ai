"""Evidence-first reference-film style calibration: do NOT create or mutate SKILL.md.

Uses user-supplied video and time-coded 4fps/2fps extractions. Optical/color/audio
numbers are observational proxies, NEVER artistic quality scores or true edit labels.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, math, os, shutil, subprocess
from datetime import datetime, timezone
from pathlib import Path
from collections import Counter
import cv2
import numpy as np

ROOT=Path(__file__).resolve().parent
DEFAULT_DENSE=Path('/mnt/data/妖猫传_全片段密集采样')
STYLE_NAME='妖猫传_用户提供12分56秒参考片_密集风格校准'
VIDEO_SHA='a6f7c66c269d8b89d1588c0b7418102efdc14f7dd3a52562b21373de9c4d18a8'

# Every row's visible facts came from inspecting the source-specific minute boards;
# no invented character names, quotations, motives, or exact cinematographic optics.
MINUTES=[
('00:00–01:00','水边开阔空间、人物与黑猫、室内纵深','浅金色水边远景里有人物站在近水处；随后出现人物侧身回望与黑猫近景；约00:36后转换为门廊和圆形亮窗的室内画面。','室外开阔画面到室内门窗空间的交替提供了两种不同的观看距离；猫成为显眼的视觉信息点。','不要断言猫是人物的主观视线所见；不可由画面判定人物真实动机。',['scene_space','object_insert','architecture'],[10,21,39,52]),
('01:00–02:00','猫的移动、庭院步行、地面细节','黑猫在门窗内外活动；浅色服饰人物从室内转至岩石和庭院空间；约01:42–01:52画面集中于地面的红褐色痕迹及小型物件。','移动主体和突然强调的物件细节改变观众要注意的对象。','红褐色痕迹的成因和物件性质不能只凭缩略图确认。',['object_insert','blocking','architecture'],[65,73,100,109]),
('02:00–03:00','红衣人物穿越门廊、室内动作、建筑大景','身穿红色服装的人物通过石门和连续木柱走廊；随后在室内与其他人物同框；02:37后切到金色天际的开阔大景，02:54后出现对称的巨大建筑空间。','人物前进方向与重复柱廊让运动过程可追踪；宏大景观在局部行动之后出现，提供尺度反差。','人物的姓名、具体政治关系与建筑地点尚未由此确认。',['blocking','scene_space','architecture'],[121,140,160,178]),
('03:00–04:00','建筑正轴、人物与书卷、烛光陈设','广场与轴线建筑、行进中的人物出现；03:21左右转向灯火映照的书卷与桌案；暖烛光室内人物近景、对称金色室内大景和卧床人物交替出现。','从建筑规模缩至具体书卷，再返回室内关系的景别调整，建立多层观看尺度。','无法仅据无声截图确认书卷内容、对白及病人状态。',['architecture','object_insert','lighting_context'],[192,201,220,238]),
('04:00–05:00','床榻、双人调度、黑猫意象与人物反应','床榻上的人物、红衣人物与浅色衣人物多次同框；04:17–04:19出现云雾中的黑猫；随后浅色衣人物的头部转动与目光方向变化；之后回到床榻、灯光和房间人物。','短暂的动物意象与人物视线变化、床榻画面之间形成可研究的镜头组织关系。','不能断定人物真的看见云雾里的猫，也不能将其解释为确定的超自然因果。',['object_insert','performance_timing','lighting_context'],[243,258,271,287]),
('05:00–06:00','近距离人物关系与夜间栏廊','开头存在床榻附近的近身动作；05:03后有暖烛光双人画面和低机位的衣物局部；随后出现竖向建筑结构、浅色衣人物夜间沿栏廊移动，继而出现另一人物面对的构图。','用身体距离、门栏遮挡和夜间不同景别来组织人物关系，而不是通篇采用统一近景。','演员对白、心理变化以及精确机位移动路线未确认。',['performance_timing','blocking','occlusion'],[300,310,328,345]),
('06:00–07:00','夜间双人移动、阴影、停留与对视','浅色衣人物与深色衣人物沿建筑前方移动；06:24后出现两人长影落在地面的俯看画面；06:35后有连续双人对话构图与近景；后段人物转身和低身动作。','人物的同框、影子、相互面对和镜头拉开共同维护空间位置。','镜头内是否真正移动摄影机要用视频运动分析，不能凭等间隔静帧判定。',['blocking','performance_timing','occlusion'],[366,389,404,414]),
('07:00–08:00','夜外对话切向隔帘室内与通道','07:00起夜间对话延续；07:12后切换至绿色薄帘、床榻和两人的近距离动作，持续较长片段；07:44后转换到深色门面及室内纵向结构。','两人的身体接触、停顿和姿态变化比景别频繁变化更显著；薄帘既是道具也是画面前景。','不能据静帧确定场面表达的情感性质，须复核语音和动作完整过程。',['performance_timing','occlusion','lighting_context'],[429,445,461,478]),
('08:00–09:00','俯视器物、低光移动、青色空间与金色装置','08:00后是暗色室内俯视画面、手持器物细节；08:22后转为岩石或园林中的人物移动；08:44以后进入蓝绿色石质空间与台阶，08:57后出现醒目的暖金色建筑装置。','同一参考段落内冷暖色与材质反差强烈，画面色彩需要随场景目的切换。','无法仅据静帧确定装置用途和场景是否为同一实际空间。',['object_insert','scene_space','lighting_context'],[484,496,524,537]),
('09:00–10:00','金色器物、装饰纹样与蓝绿石室','深色衣人物面向金色台座及纹样墙体；09:18有单独的细长物件画面；之后人物在室外与其他人群相遇，09:42后交替呈现青色装饰空间、器物和人物。','道具近景与建筑表面纹样反复出现，构成可追踪的视觉母题与观看对象。','不能推断器物象征意义、谁知道什么或物件的历史用途。',['object_insert','architecture','lighting_context'],[545,560,579,591]),
('10:00–11:00','红衣群像与黑猫，转入日光室内走位','10:00–10:04先见红衣人物，10:04–10:07为黑猫沿金色栏杆行走；随后深色衣人物出镜并经过门廊；10:21后有阳光照亮的室内、两个人物交替出现及入室走位。','先改变注意对象、再由门窗和行进中的人物把观众带进较开阔的室内。','不能只凭前后切镜认定人物目击了黑猫。',['object_insert','blocking','scene_space'],[604,610,625,638]),
('11:00–12:00','室内静对、廊下同行、街市人群与格窗遮挡','前段先以两个不同人物的室内近景构图延续；11:12后经过木构廊道；11:25后街市中有行人、伞棚、笼架和多人穿行；11:37后镜头透过深色格窗观察人物经过。','镜头从安静室内扩展到多人街市，再把人物部分遮在格窗后，空间层次和运动方向清楚。','未见整场戏对白，不能宣称人物彼此关系或情绪已被确定。',['blocking','occlusion','architecture'],[665,679,696,708]),
('12:00–12:56.48','室内多人对坐转向长廊与桥道同行','开头在日光室内有两人坐立互动；12:18后转到繁忙户外廊桥、多人经过；12:30后较长时间沿木桥、柱廊拍摄人物向前，最后两人保持并行构图。','静态对坐与有纵深的群体移动形成节奏对照；建筑框架反复组织人物的可见与遮挡。','本片段到12:56结束，无法据此推断原电影后续镜头。',['blocking','scene_space','architecture'],[724,735,748,765]),
]

# Deep lookups from 4fps sequence inspection; labels refer to OBSERVABLE visual action only.
DEEP=[
(15,30,'人物回望与猫的显露','开阔水边与近身画面的注意对象切换','确认是否为视线匹配需要较完整方向镜头','director-agent','camera/eyeline uncertainty'),
(75,90,'室内移动的黑猫与人物','黑猫在日光投影明显的室内经过，之后画面回到人物','剪辑主观性未确认','ai-storyboard-director','audience information vs POV'),
(135,150,'红衣人物经过廊柱','重复立柱构成横向深度，走位延续到推门区域','无法判断机位是否真正移动','plan-camera-shots','spatial baseline / actor path'),
(195,210,'灯烛与书卷','文书和灯火的近景被人物画面包围','书卷意义需对白/上下文','director-agent','object motivated attention'),
(255,270,'猫的云雾段与人物转头','4:17开始黑猫意象，4:19切回浅色衣人物的头部转向','不得推断人物看到猫','ai-storyboard-director','non-POV insert / knowledge gap'),
(315,330,'廊柱前的移动','人物通过楼阁栏边，竖向立柱多次遮挡','判断跟拍/静机位需连贯视频','plan-camera-shots','foreground occlusion'),
(390,405,'夜间双人同框与背向关系','人物在广场上出现面向及背向关系，镜头切入双人脸部','无台词、人物动机待核验','director-agent','performance and orientation'),
(435,450,'绿色薄帘内的双人动作','两人从俯身位置逐渐移动到正面近距离，浅绿帘持续作为前景','不能确认台词与情感指向','ai-storyboard-director','blocking beats / screen direction'),
(525,540,'青绿色台阶与金色装置','青蓝色阶梯转向明显发光的金色器物，冷暖对照强烈','不把色差自动解释为场景好坏','ai-storyboard-director','color and image formation'),
(555,570,'金色纹样墙与器物','深色人物与饰纹物件的过肩关系和独立器物细节','物件用途与象征未知','director-agent','object motif + audience attention'),
(600,615,'红衣人物、黑猫、深衣人物','红衣近景后黑猫在金色栏杆行走，深衣人物单独出镜，间隔空间镜头','人物是否看到猫未确认','ai-storyboard-director','non-POV insert'),
(615,630,'门窗与室内空间揭示','窗格、暗墙、开敞的日光室内依次出现，并有不同人物出镜','镜头的时间顺序不等于建筑的实测平面图','plan-camera-shots','room entry / geography'),
(630,645,'对坐的准备和接近','深衣人物移动至亮窗房间并与浅衣人物靠近，桌案与窗格充当参照','真实走位尺寸未知','plan-camera-shots','blocking / over-shoulder'),
(690,705,'街市行进与格窗','不同角色穿过人群，转为从格窗内观察','无法推断谁在监视谁','ai-storyboard-director','occlusion / visual reveal'),
(740,755,'廊桥同行','两人沿木质走廊继续移动，背景深处可见其他人','运镜方向需审视频连续帧而非单帧','plan-camera-shots','walk-and-talk spatial path'),
]

CAPABILITIES={
 'scene_space':{'source':'ai-storyboard-director','activate':['spatial-reveal','shot-design-engine','framing-and-axis'],'film_reason':'同一片段内水边、门廊、巨大建筑、室内及街市多层空间互相转换','not_a_rule':'不能机械规定所有镜头都要对称或大景'},
 'object_insert':{'source':'director-agent + ai-storyboard-director','activate':['visual-storytelling','object-motif','audience-information-order'],'film_reason':'黑猫、书卷、地面痕迹、器物被给予单独观看时间','not_a_rule':'不能将任何插入镜头自动认定为角色主观所见'},
 'architecture':{'source':'ai-storyboard-director + plan-camera-shots','activate':['framing-and-axis','architectural-depth','spatial-baselines'],'film_reason':'桥、廊柱、格窗、建筑中轴反复成为人物行动框架','not_a_rule':'不能凭缩略图反推出真实焦距'},
 'blocking':{'source':'plan-camera-shots','activate':['character-start-end-state','blocking-continuity','camera-position-and-focus'],'film_reason':'长廊、夜间广场、街市及桥道均有较明显的演员移动','not_a_rule':'不能只用固定静帧证明摄影机轨迹'},
 'performance_timing':{'source':'director-agent + ai-storyboard-director','activate':['performance-beats','micro-actions','performance-time-budget'],'film_reason':'近身互动、静对、转头、靠近、离开有不同速度的动作段落','not_a_rule':'表情与情绪需连贯视频和对白复核'},
 'occlusion':{'source':'ai-storyboard-director + plan-camera-shots','activate':['foreground-masking','visual-discovery','screen-direction-check'],'film_reason':'薄帘、柱廊、门窗、格栅反复挡住或局部显露人物','not_a_rule':'不能一概定义遮挡为悬念或偷看'},
 'lighting_context':{'source':'ai-storyboard-director','activate':['color-and-image-formation','scene-motivated-light','warm-cool-scene-contrast'],'film_reason':'日光金色、暗暖烛光、青蓝色地下空间在片段内并存','not_a_rule':'严禁整片套用同一个暗金色滤镜'},
}


def sha(path:Path)->str:
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
 return h.hexdigest()

def tm(s):
 return f'{int(s//60):02d}:{s%60:05.2f}'

def load_csv(p):
 with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))

def extract_audio_rms(video, windows):
 # No ASR; only objective waveform magnitude. Time ranges cover all 776.477s.
 cmd=['ffmpeg','-v','error','-i',str(video),'-vn','-f','f32le','-ac','1','-ar','8000','-']
 p=subprocess.run(cmd,capture_output=True,check=True,timeout=120)
 wav=np.frombuffer(p.stdout,dtype='<f4')
 for w in windows:
  i,j=int(w['start']*8000),int(w['end']*8000)
  a=wav[i:j]
  w['audio_rms']=round(float(np.sqrt(np.mean(a*a))) if a.size else 0,5)
  w['audio_note']='电平代理；不识别对白、音乐、音效或L/J-cut'

def generate(dense:Path, out:Path, video:Path, include_evidence:bool=True):
 assert video.exists() and sha(video)==VIDEO_SHA,'video hash mismatch: refuse mixing films'
 rows=load_csv(dense/'sample_timeline_4fps.csv')
 assert len(rows)==3106,len(rows)
 change=load_csv(dense/'cut_candidates_sensitive.csv')
 strong=load_csv(dense/'cut_boundary_pairs.csv')
 assert len(change)==595 and len(strong)==116,'cut candidate lists changed; review before using'
 out.mkdir(parents=True,exist_ok=True)
 evidence=out/'evidence'
 if include_evidence:
  evidence.mkdir(exist_ok=True)
  for sub in ['minute','15sec','frames']:(evidence/sub).mkdir(exist_ok=True)
  for i in range(13):
   source=sorted((dense/'01_每分钟总览').glob(f'minute_{i:02d}_*.jpg'))[0]
   shutil.copyfile(source,evidence/'minute'/f'minute_{i:02d}.jpg')
  for i in range(52):
   source=dense/'07_每15秒四帧每秒细看'/f'dense_4fps_{i:03d}.jpg'
   assert source.exists()
   shutil.copyfile(source,evidence/'15sec'/f'window_{i:02d}.jpg')
  for second in sorted(set(int(x) for m in MINUTES for x in m[6])):
   f=dense/'frames_2fps_original_resolution'/f'{int(second*2):05d}.jpg'
   if f.exists():shutil.copyfile(f,evidence/'frames'/f'{second:04d}s.jpg')

 # Self-contained SHA evidence manifest survives ZIP extraction and Windows moves.
 origin_map={}
 for i in range(13):
  a=f'evidence/minute/minute_{i:02d}.jpg'
  b=sorted((dense/'01_每分钟总览').glob(f'minute_{i:02d}_*.jpg'))[0]
  origin_map[a]=b
 for i in range(52):
  origin_map[f'evidence/15sec/window_{i:02d}.jpg']=dense/'07_每15秒四帧每秒细看'/f'dense_4fps_{i:03d}.jpg'
 for frame in (evidence/'frames').glob('*.jpg'):
  second=int(frame.stem[:-1]); origin_map['evidence/frames/'+frame.name]=dense/'frames_2fps_original_resolution'/f'{second*2:05d}.jpg'
 manifest={}
 for rel, src in sorted(origin_map.items()):
  copied=out/rel
  assert src.is_file() and copied.is_file()
  digest=sha(src)
  assert sha(copied)==digest,'evidence mismatch '+rel
  manifest[rel]={'sha256':digest,'origin_relative':str(src.relative_to(dense))}
 (out/'evidence_manifest.json').write_text(json.dumps({'source_film_sha256':VIDEO_SHA,'file_count':len(manifest),'files':manifest},ensure_ascii=False,indent=2),encoding='utf-8')

 windows=[]
 frames_per_window=60
 ts=[float(x['timestamp_sec']) for x in change]
 tc=[float(x['cut_timestamp_sec']) for x in strong]
 for i in range(52):
  lo=i*15.0; hi=min((i+1)*15.,776.477)
  file_idxs=range(i*60,min((i+1)*60,len(rows)))
  lum=[];sat=[]; diffs=[];prev=None; dark=[]
  for k in file_idxs:
   path=dense/rows[k]['image_path']
   im=cv2.imread(str(path))
   assert im is not None,str(path)
   small=cv2.resize(im,(96,54))
   hsv=cv2.cvtColor(small,cv2.COLOR_BGR2HSV)
   gray=cv2.cvtColor(small,cv2.COLOR_BGR2GRAY)
   lum.append(float(gray.mean()))
   sat.append(float(hsv[:,:,1].mean()))
   dark.append(float(np.mean(gray<55)))
   if prev is not None:
    diffs.append(float(np.mean(np.abs(gray.astype(np.float32)-prev.astype(np.float32)))))
   prev=gray
  w={'id':f'WIN_{i:03d}','start':lo,'end':hi,'time_range':f'{tm(lo)}–{tm(hi)}',
     'frame_count':len(lum),'luma_mean_0_255':round(float(np.mean(lum)),1),
     'saturation_mean_0_255':round(float(np.mean(sat)),1),
     'dark_pixel_fraction_below55':round(float(np.mean(dark)),3),
     'inter_sample_absdiff_mean':round(float(np.mean(diffs)),2),
     'inter_sample_absdiff_max':round(max(diffs),2) if diffs else 0,
     'sensitive_change_candidates':sum(lo<=t<hi for t in ts),
     'strong_change_candidates':sum(lo<=t<hi for t in tc),
     'manual_visual_analysis_status':'分钟总览已核看；15秒全序列尚未逐帧人工审定',
     'evidence':f'evidence/15sec/window_{i:02d}.jpg',
     'caution':'亮度/饱和度/跨帧差分不是艺术质量、演员情绪、真实切镜数量或摄影机运动类别'}
  windows.append(w)
 extract_audio_rms(video,windows)

 minute_cards=[]
 for i,(times,title,fact,hyp,limits,caps,anchors) in enumerate(MINUTES):
  minute_cards.append({'id':f'MIN_{i:02d}','times':times,'title':title,
   'visible_facts':fact,'filmmaking_hypothesis_unverified':hyp,'unknowns':limits,
   'activation_ids':caps,'reference_seconds':anchors,
   'reference_frames':[{'timestamp_sec':t,'timecode':tm(t),'path':f'evidence/frames/{t:04d}s.jpg'} for t in anchors if (evidence/'frames'/f'{t:04d}s.jpg').exists()],
   'evidence_image':f'evidence/minute/minute_{i:02d}.jpg',
   'scope':'整分钟采样概览，非完整电影剧情确认'})

 deep=[]
 for a,b,short,fact,unknown,skill,focus in DEEP:
  deep.append({'range_sec':[a,b],'range':f'{tm(a)}–{tm(b)}',
  'topic':short,'visible_facts':fact,'unknowns':unknown,'upstream_skill':skill,
  'focus_to_activate':focus,'evidence_15sec':f'evidence/15sec/window_{int(a//15):02d}.jpg'})

 profile={'id':'yaomao_uploaded_776s_dense_v2','reference_film_label':'《妖猫传》用户上传片段（不是完整电影）',
  'source_sha256':VIDEO_SHA,'duration_seconds':776.477,'frame_evidence_4fps':3106,
  'frame_evidence_2fps_original':1553,'cut_candidates_not_confirmed':{'sensitive':595,'strong':116},
  'research_boundary':{
   'filmed':True,'script_source_present':False,'dialogue_transcribed':False,
   'actor_identity_verified':False,'camera_intrinsics_known':False,'director_intent_verified':False,
   'skill_native_execution_verified':False,'style_transfer_quality_proven':False},
  'provenance':'本风格参数为GPT依据用户上传原片的时间码及图像证据所做研究记录，不等于模型权重训练。',
  'upstream_skills_unchanged':True,
  'upstream':[
   {'skill':'director-agent','repo':'62656456/ai-film-skills','use':'audience information, performance, visual-storytelling; record unknown dialogue'},
   {'skill':'ai-storyboard-director','repo':'62656456/ai-film-skills','use':'framing, optical shot selection, blocking and spatial perspective'},
   {'skill':'plan-camera-shots','repo':'zhangzhangco/film-production-skills','use':'spatial baseline, actor start/end state, durations, camera and focus'},
   {'skill':'review-and-assemble','repo':'zhangzhangco/film-production-skills','use':'take-specific review, immutable evidence, no false acceptance'},
   {'skill':'structure-screenplay','repo':'zhangzhangco/film-production-skills','use':'WAIT for user-provided screenplay; do NOT infer screenplay from mute stills'}],
  'activations':CAPABILITIES,
  'priority_interactions':[
   {'primary':'scene_space','secondary':'architecture','evidence':['MIN_00','MIN_02','MIN_11','MIN_12']},
   {'primary':'object_insert','secondary':'performance_timing','evidence':['MIN_01','MIN_03','MIN_04','MIN_09','MIN_10']},
   {'primary':'blocking','secondary':'occlusion','evidence':['MIN_05','MIN_06','MIN_07','MIN_11','MIN_12']},
   {'primary':'lighting_context','secondary':'scene_space','evidence':['MIN_00','MIN_03','MIN_08','MIN_09','MIN_10']}],
  'activation_status':'证据校准配置已生成；原版专业Skill的宿主原生执行与质量迁移尚待验证',
  'scene_specific_not_global_lut':True}

 data={'schema_version':'2026-11-14-evidence-v2','generated_utc':datetime.now(timezone.utc).isoformat(),
 'source':{'video_name':video.name,'sha256':VIDEO_SHA,'duration_seconds':776.477,
  'scope':'12分56秒视频片段，不是完整电影','frame_interval':0.25,'frame_count':3106,
  'original_resolution_frame_interval':0.5,'original_resolution_frame_count':1553,
  'film_still_copyright':'user supplied reference media; for private research'},
 'definitions':{
  'visible_facts':'目视观察分镜板，可由原帧复核；不是对白/剧情事实证明',
  'filmmaking_hypothesis_unverified':'GPT导演推断，未获得导演本人证实，随上下文可能修正',
  'sensitive_change_candidates':'图像变化检测器触发，可能由光线、运镜、人物运动引起，不等于切点',
  'audio_rms':'声音波形均方根，不表示演说/音乐/镜头关系',
  'image_brightness':'低分辨率JPEG观察帧像素统计，不代表原始调色LUT或影片质量'},
 'minutes':minute_cards,'deep_studies':deep,'windows_15sec':windows,'professional_skill_activation':profile,
 'counts':{'minutes':len(minute_cards),'deep_visual_studies':len(deep),'windows_15sec':len(windows),
  'source_frames_checked_hash':1,'source_audio_observed_semantically':0,
  'skill_natively_executed':0,'transfer_films_completed':0}}
 (out/'film_study_data.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
 (out/'professional_skill_activation.json').write_text(json.dumps(profile,ensure_ascii=False,indent=2),encoding='utf-8')
 write_report(out,data)
 write_html(out,data)
 print(json.dumps({'result':'OK','source_sha256':VIDEO_SHA,'minute_cards':13,'15sec_windows':52,
  'deep_studies':len(deep),'evidence_files':len(list(evidence.rglob('*.jpg'))),'output':str(out)},ensure_ascii=False))
 return data

def write_report(out,data):
 lines=['# 《妖猫传》密集导演研究｜专业Skill证据校准 V2','',
  '> 范围：用户上传的00:00–12:56.48片段；不是原电影全部内容。没有台词转录，也未取得导演对创作意图的确认。','',
  '**这一轮从“抽帧”推进到“研究”：13个分钟单元全部检查，52组15秒板均有画面/声音数值代理，另有15个较深入的导演研究片段。**',
  '','## 使用的现成专业Skill（不新建Skill，不修改其原文）','',
  '| 专业Skill | 按证据激活什么 | 验证边界 |','|---|---|---|']
 for row in data['professional_skill_activation']['upstream']:
  lines.append(f"| `{row['skill']}` | {row['use']} | 尚无原生执行回执 |")
 lines+=['','## 全时间轴：真实观察与待证解释','']
 for m in data['minutes']:
  lines+= [f"### {m['times']}　{m['title']}",
   f"**可复查画面事实：** {m['visible_facts']}",
   f"**待证导演解释：** {m['filmmaking_hypothesis_unverified']}",
   f"**不得擅自确定：** {m['unknowns']}",
   f"**激活能力：** {', '.join(m['activation_ids'])}；参考时间码：{', '.join(str(x)+'s' for x in m['reference_seconds'])}",'']
 lines+=['## 15组重点动作/构图研究','']
 for c in data['deep_studies']:
  lines += [f"- **{c['range']}｜{c['topic']}**：{c['visible_facts']}。调用 `{c['upstream_skill']}` 的 {c['focus_to_activate']}；未证：{c['unknowns']}"]
 lines+=['','## 量化检查只作为研究工具','',
  '- 每15秒记录60张四帧每秒抽样的平均亮度、饱和度、暗像素比例、跨帧绝对差分和声音RMS。',
  '- 595处高敏感变化和116处强变化**只是检测候选**，不能由数量宣称影片的剪辑点或导演好坏。',
  '- 不能由静帧推断真实机位焦距、准确的摄像机移动、人物对白、演员的完整表演动机与色彩管理技术。',
  '- 不使用单一暗金色LUT替代《妖猫传》的多场景风格；日光、烛光、青绿空间有明显差异。',
  '','## 交付与真实阻断','',
  '1. 已完成：真实视频SHA绑定、13个分钟单元观察、52个15秒量化窗口、15处演员/摄影/镜头组织研究、现成专业Skill激活配置。',
  '2. 未完成：整部《妖猫传》的研究（用户只提供了12分56秒片段）；有声音但尚无对白转录；原版上游专业Agent在宿主原生执行尚无记录。',
  '3. 未完成：参考片风格在用户未来新剧本上的导演级视觉迁移测试；没有新剧本就不虚构一个进行验证。',
  '4. 严格禁止：将原片的截帧算作原创画面，将算法变化点称为原片错误，或把“风格分析”冒充新模型训练。',
  '','## 数据文件','',
  '- `film_study_data.json`：52窗口逐项技术数据、13个分钟笔记、15组重点研究和证据文件。',
  '- `professional_skill_activation.json`：不改写上游Skill的能力选择配置，明确未知/待验证内容。',
  '- `evidence_manifest.json`：117份证据图的原始路径与SHA256，支持独立解压后校验。',
  '- `index.html`：离线可打开的整片段交互学习工作台；视频帧及所有密集图保留原始时间码。',
  '']
 (out/'导演密集研究与专业Skill激活_真实报告.md').write_text('\n'.join(lines),encoding='utf-8')

def write_html(out,data):
 # Static HTML with embedded JSON: no network dependencies and no arbitrary model output injection.
 import html
 htmlp=html.escape
 minute=[]
 for m in data['minutes']:
  cards=''.join(f'<a href="{htmlp(x["path"])}" target="_blank">{htmlp(x["timecode"])} 1280×534帧</a> ' for x in m['reference_frames'])
  minute.append(f'''<article class="minute" id="{m['id']}"><div class="visual"><a href="{htmlp(m['evidence_image'])}" target="_blank"><img loading="lazy" src="{htmlp(m['evidence_image'])}" alt="{htmlp(m['times'])}原片一分钟观察板"></a></div><div class="content"><h3>{htmlp(m['times'])} · {htmlp(m['title'])}</h3><h4>可复查画面事实</h4><p>{htmlp(m['visible_facts'])}</p><h4>有待核验的导演解释</h4><p>{htmlp(m['filmmaking_hypothesis_unverified'])}</p><h4>证据不足/不能断言</h4><p>{htmlp(m['unknowns'])}</p><p class="mini"><b>激活专业能力：</b>{htmlp(', '.join(m['activation_ids']))}</p><p class="mini links">{cards}</p></div></article>''')
 deep=[]
 for c in data['deep_studies']:
  deep.append(f'''<article class="deep"><a href="{htmlp(c['evidence_15sec'])}" target="_blank"><img loading="lazy" src="{htmlp(c['evidence_15sec'])}" alt="{htmlp(c['range'])}"></a><div><h3>{htmlp(c['range'])} · {htmlp(c['topic'])}</h3><p>{htmlp(c['visible_facts'])}</p><p><b>专业入口：</b><code>{htmlp(c['upstream_skill'])}</code> · {htmlp(c['focus_to_activate'])}</p><p class="uncertain">未证：{htmlp(c['unknowns'])}</p></div></article>''')
 cards=[]
 for w in data['windows_15sec']:
  cards.append(f'''<a class="window" href="{htmlp(w['evidence'])}" target="_blank"><img loading="lazy" src="{htmlp(w['evidence'])}"><div><b>{htmlp(w['time_range'])}</b><span>亮度 {w['luma_mean_0_255']} · 暗比例 {w['dark_pixel_fraction_below55']:.0%} · 变化候选 {w['sensitive_change_candidates']}（未经确认）</span></div></a>''')
 styles=[]
 for k,v in CAPABILITIES.items():
  styles.append(f'''<div class="style"><b>{htmlp(k)}</b><p>调用现成Skill：{htmlp(v['source'])}</p><p>激活：{htmlp(' / '.join(v['activate']))}</p><p>{htmlp(v['film_reason'])}</p><p class="uncertain">边界：{htmlp(v['not_a_rule'])}</p></div>''')
 page='''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>《妖猫传》密集导演研究｜专业Skill激活</title><style>body{margin:0;background:#0e1115;color:#e9ebec;font:15px/1.65 -apple-system,BlinkMacSystemFont,'Microsoft YaHei',sans-serif}header{padding:46px clamp(16px,5vw,90px);background:radial-gradient(circle at 90% 5%,#272726,#131719 63%)}h1{font-size:30px;margin:0 0 10px}h2{font-size:22px;margin:42px 0 18px;border-left:4px solid #d6b27b;padding-left:14px}h3{font-size:17px;margin:0 0 10px;color:#f1d6a9}h4{font-size:13px;color:#d0bda2;margin:14px 0 3px}p{margin:4px 0 7px}.sub{color:#bac2c7;max-width:900px}.metrics{display:flex;gap:12px;flex-wrap:wrap;margin:20px 0}.metric{background:#202429;border:1px solid #383c3f;padding:12px 18px;border-radius:10px}.metric b{font-size:23px;display:block}.metric small{font-size:12px;color:#afb7bb}nav{display:flex;flex-wrap:wrap;gap:8px;padding:12px 0}a{color:#d6b27b}nav a{border:1px solid #4d5559;background:#1b2025;padding:5px 10px;border-radius:7px;text-decoration:none}.container{max-width:1560px;margin:auto;padding:0 20px 60px}.minute{display:grid;grid-template-columns:minmax(300px,1fr) minmax(360px,1fr);gap:16px;padding:16px 0;border-bottom:1px solid #35393e}.minute .visual img{width:100%;border:1px solid #333;border-radius:8px}.content{padding:6px 0}.uncertain{color:#d5a3a3}.mini{font-size:12px}.links a{white-space:nowrap;margin-right:8px}.deep{display:grid;grid-template-columns:48% 1fr;gap:14px;border:1px solid #363c3f;border-radius:10px;padding:10px;margin:14px 0;background:#171b20}.deep img{width:100%;border-radius:6px}.deep div{padding:4px}.windows{display:grid;grid-template-columns:repeat(auto-fit,minmax(290px,1fr));gap:10px}.window{color:#eee;text-decoration:none;background:#202429;border:1px solid #3d4246;border-radius:10px;overflow:hidden}.window img{width:100%;height:110px;object-fit:cover}.window div{padding:9px}.window span{font-size:11px;color:#b7c1c6;display:block}.styles{display:grid;grid-template-columns:repeat(auto-fit,minmax(285px,1fr));gap:10px}.style{padding:14px;background:#202429;border-radius:8px;border:1px solid #393f44}.style b{color:#f0cb96}code{background:#282b2e;padding:2px 4px;border-radius:4px}footer{margin:60px 0 0;color:#879298;font-size:12px}@media(max-width:760px){.minute,.deep{grid-template-columns:1fr}.container{padding:0 14px}.window img{height:130px}}</style></head><body><header><h1>《妖猫传》密集导演研究</h1><p class="sub">基于你上传的真实片段 00:00–12:56.48。重点研究摄影、演员走位、物件信息、灯光美术、剪辑观看关系，然后调用 <strong>已有的专业 Skill</strong>；本页不创建新 Skill，也不把自己的假设当成导演本人意图。</p><div class="metrics"><div class="metric"><b>3,106</b><small>4fps取样帧</small></div><div class="metric"><b>52</b><small>15秒密集分镜</small></div><div class="metric"><b>13</b><small>逐分钟人工观察</small></div><div class="metric"><b>15</b><small>重点导演研究</small></div><div class="metric"><b>0</b><small>原版Skill原生运行回执</small></div></div><nav><a href="#minute">逐分钟</a><a href="#focus">重点研究</a><a href="#activate">专业Skill激活</a><a href="#windows">全部52个窗口</a><a href="film_study_data.json">原始结构化数据</a><a href="evidence_manifest.json">证据图SHA清单</a><a href="professional_skill_activation.json">激活配置</a><a href="导演密集研究与专业Skill激活_真实报告.md">完整报告</a></nav></header><main class="container"><h2 id="minute">全时间轴 · 画面事实与导演解释分开</h2>'''+''.join(minute)+'''<h2 id="focus">15段重点摄影、表演和剪辑研究</h2>'''+''.join(deep)+'''<h2 id="activate">激活现成专业Skill的哪些能力</h2><p class="sub">这是原版Skill的外部任务配置，不是改写它们的源码；还没有取得上游Agent的独立执行回执。</p><div class="styles">'''+''.join(styles)+'''</div><h2 id="windows">52个15秒密集时间窗口</h2><p class="sub">技术代理（亮度、动态差分、声音电平）仅用于帮助寻找研究段落，不是镜头质量打分；变化候选不是经确认的剪辑点。</p><div class="windows">'''+''.join(cards)+'''</div><footer>原始参考影片 SHA256：'''+VIDEO_SHA+'''；无对白转录／无完整影片／无独立导演意图确认。静帧不是原创画面。</footer></main></body></html>'''
 (out/'index.html').write_text(page,encoding='utf-8')

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--dense',type=Path,default=DEFAULT_DENSE);p.add_argument('--video',type=Path,default=ROOT/'data/source_video.mp4');p.add_argument('--out',type=Path,default=ROOT/'output/dense_film_style_study');p.add_argument('--no-evidence-copy',action='store_true');args=p.parse_args()
 generate(args.dense,args.out,args.video,include_evidence=not args.no_evidence_copy)
