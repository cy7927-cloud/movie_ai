#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Evidence-led director's craft workbench. No AI video or paid image model.

Core principles:
- Measured features from reference are NOT new generated frames or a director's interpretation.
- Narrative and acting notes are PROVISIONAL visual readings, never asserted as model verified.
- A reference boundary which may hide a cut BLOCKS shot-level production approval.
- Operator notes are versioned by reference hashes and invalidate dependent storyboard approval.
"""
from __future__ import annotations
import argparse, csv, hashlib, html, json, math, os, re, statistics, subprocess, sys, tempfile, time
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import quote
import cv2
import numpy as np
from skimage.metrics import structural_similarity

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'output/director_lab'
DATA=ROOT/'data'
SRC=DATA/'source_video.mp4'
AN=('in','mid','out')

# Human-style observations made by inspecting the actual extracted IN/MID/OUT contact sheet.
# These are reference-only, tentative visual descriptions, not automated AI classification.
OBSERVED={
55:('器物/户外环境的快速转换','目标卡包含明显不同视觉空间；首先核对是否漏切，不能当成一条连续摄影调度。','疑似多个地点或景别混并','强制校正镜头边界之后再判断叙事作用'),
56:('室外到暗室入口的转换','门与人物的空间转换明显，需要验证是否属于连续镜头。','入口/遮挡/可能的调度转折','辨认实际切点与人物出入口'),
57:('两名红衣男子的反应关系','前景人物更突出、另一人位于后方；注视方向和表情推动紧张感。','前后两人/红衣/面部视线','锁定两人对应身份、前后层级及视线方向'),
58:('深色服饰男子与装饰性画面的转换','前景人物之后出现装饰性视觉内容；不宜未经检查就推断是同机位运动。','暗室人物/纹样或顶饰','核对是否插入镜头或画面转场'),
59:('暗室中人的动作/操作','人物位于光源附近，桌面道具和手部关系值得作为表演关键帧。','暗光/桌面/操作动作','明确手部动作的起止及道具状态'),
60:('装饰结构与台阶的转换','纹样与台阶出现明显视角差异，优先复核是否需要拆镜。','器物/建筑台阶','切镜后分别定义镜头目标'),
61:('台阶区域的人物活动','以地面与台阶作为稳定空间参照，重点检查人物接地位置。','近地面/台阶/衣物边缘','标注人物足部与台阶几何关系'),
62:('栏杆作为空间引导线','装饰性栏杆把视线引向远处光亮区域，空间纵深是关键。','长斜线/远处暖光','锁定栏杆走向与透视消失位置'),
63:('暗石洞与亮门洞的纵深','近处强暗部、远处暖光形成明确的目标导向。','暗石洞/小范围亮口','禁止把亮口放大造成环境关系失真'),
64:('年轻男子的面部反应','面部与门洞同框，表情及视线变化是重点；不能仅靠SSIM判定表演。','面部/门洞/侧向视线','锁定视线对象及表情变化的关键时刻'),
65:('红衣人物面对建筑构件','人物背向镜头接近石质构件，末帧切向面部；待确认是否隐藏切镜。','双人红衣/石质建筑','核对人物位置与身体朝向连续性'),
66:('黑猫行走于横向台面','猫的姿态和轮廓构成视觉焦点；应以动物重心、足部接触和运动方向作为动态验收。','动物侧面剪影/暖黄背景','锁定黑猫姿态与行走方向，静帧先审足部站位'),
67:('男性近景的表情/视线','主体面部贯穿三帧，偏向右侧的关注与反应需要表演节拍。','近景面部/室内暗光','指定眼神变化和嘴部状态，不推断对白'),
68:('暗石洞开口与远处人物','洞口的狭小亮区突出远处人影，保留遮挡关系非常重要。','洞壁遮挡/远景人物','锁定内外空间纵深，防止背景生成过亮'),
69:('男子在门边的动作','人物与门框同框，末帧手部姿态出现变化，需定义动作结束姿势。','男子/门框/手势','选定动作关键点、手部与门框相对位置'),
70:('进入明亮室内的空间建立','从狭窄遮挡过渡到明亮室内的可见面积，可能承担场景介绍功能。','门窗框架/明亮室内','确认镜头起点遮挡和空间方向'),
71:('浅色衣服僧人的近景反应','人物面部角度和神态有变化，窗边软光是稳定资产约束。','浅色僧衣/室内窗光','锁定朝向、视线落点、服装领口'),
72:('深衣男子的相对机位','近景人物处于明亮窗外背景之前，可能构成对话反打。','深色衣服/斜屋檐/背景植被','与71、73镜头核验反打轴线，勿擅自声称同一人'),
73:('僧人反向近景','可见僧人侧面与室内框架，需验证与上一镜视线匹配。','浅色僧衣/室内轮廓','对比71、72、73的视线与180度轴线'),
74:('室内双人空间关系','广一些的室内布局、窗口和人物位置可用于验证对话场面空间。','室内窗格/两名人物','建立可编辑平面走位图，确认站位及切入切出位置')}

def J(path,default=None):
    p=Path(path);return json.loads(p.read_text(encoding='utf-8')) if p.is_file() else default

def savej(path,obj):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    tmp=p.with_suffix(p.suffix+'.tmp')
    tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8');tmp.replace(p)

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def image_info(path):
    im=cv2.imread(str(path))
    if im is None:raise FileNotFoundError(path)
    im=cv2.resize(im,(384,160),interpolation=cv2.INTER_AREA)
    gray=cv2.cvtColor(im,cv2.COLOR_BGR2GRAY)
    hsv=cv2.cvtColor(im,cv2.COLOR_BGR2HSV)
    edges=cv2.Sobel(gray,cv2.CV_32F,1,0,ksize=3)**2+cv2.Sobel(gray,cv2.CV_32F,0,1,ksize=3)**2
    edges=np.sqrt(edges);weights=np.maximum(edges-np.quantile(edges,.62),0)
    rows,cols=np.indices(weights.shape)
    total=float(weights.sum())
    focus=[float((cols*weights).sum()/total/(im.shape[1]-1)),float((rows*weights).sum()/total/(im.shape[0]-1))] if total>1e-3 else [None,None]
    L=float(np.mean(gray)/255)
    return {'brightness':round(L,3),'contrast':round(float(gray.std()/255),3),
            'saturation':round(float(np.mean(hsv[:,:,1])/255),3),
            'visual_detail_focus_proxy_xy':[round(v,3) if v is not None else None for v in focus],
            'left_right_luma_difference':round(float((np.mean(gray[:,:192])-np.mean(gray[:,192:]))/255),3),
            'bright_area_fraction':round(float(np.mean(gray>180)),3)}

def analysis_evidence():
    raw=J(OUT/'reference_visual_timeline.json')
    if raw:return raw
    return {'challenge_window':{},'intervals':[],'candidate_events':[],'internal_cut_warnings':[]}

def scan_reference_window(start=559.4,end=652.4,fps=4,run_extract=True):
    """Extract low-res diagnostic frames, independently estimate sharp transition candidates.

    NEVER split source shots automatically: missed-cut candidates remain proposals.
    """
    cache=OUT/'probe_frames';cache.mkdir(parents=True,exist_ok=True)
    n_expected=math.floor((end-start)*fps)-1
    frames=sorted(cache.glob('f_*.jpg'))
    meta=J(cache/'meta.json',{})
    if run_extract and (len(frames)<n_expected or meta.get('source_sha256')!=J(DATA/'project_manifest.json',{}).get('source_sha256') or meta.get('window')!=[start,end,fps]):
        for p in frames:p.unlink()
        cmd=['ffmpeg','-hide_banner','-loglevel','error','-ss',str(start),'-i',str(SRC),'-t',str(end-start),
             '-vf',f'fps={fps},scale=448:-2','-q:v','5','-vsync','vfr',str(cache/'f_%04d.jpg')]
        subprocess.run(cmd,check=True,timeout=120)
        frames=sorted(cache.glob('f_*.jpg'))
        savej(cache/'meta.json',{'source_sha256':J(DATA/'project_manifest.json',{}).get('source_sha256'), 'window':[start,end,fps], 'frames':len(frames)})
    if len(frames)<10:raise RuntimeError('No sample frames to scan')
    vals=[];old=None
    for idx,file in enumerate(frames):
        im=cv2.imread(str(file));im=cv2.resize(im,(224,94))
        g=cv2.cvtColor(im,cv2.COLOR_BGR2GRAY)
        hsv=cv2.cvtColor(im,cv2.COLOR_BGR2HSV)
        hist=cv2.calcHist([hsv],[0,1],None,[18,8],[0,180,0,256]);cv2.normalize(hist,hist)
        if old:
            structure=float(structural_similarity(old[0],g,data_range=255))
            hist_dist=float(cv2.compareHist(old[1],hist,cv2.HISTCMP_BHATTACHARYYA))
            luminance_change=float(np.abs(old[0].astype(np.float32)-g).mean()/255)
            score=.55*hist_dist+.25*(1-structure)+.20*luminance_change
            vals.append({'t':round(start+idx/fps,3),'frame_i':idx,'transition_score':round(score,4),
                'histogram_distance':round(hist_dist,4),'structural_difference':round(1-structure,4),
                'luma_change':round(luminance_change,4)})
        old=(g,hist)
    data=np.array([v['transition_score'] for v in vals]); q95=float(np.quantile(data,.95))
    threshold=max(.42,min(.52,q95))
    shotcsv=list(csv.DictReader((DATA/'shots_source.csv').open(encoding='utf-8-sig')))
    bounds=sorted(float(z['start_sec']) for z in shotcsv[1:])
    cross=J(DATA/'cut_detector_ffmpeg_times.json',{}).get('timestamps_sec',[])
    selected=[]
    for i,v in enumerate(vals):
        if v['transition_score']<threshold and not (v['transition_score']>=.32 and min((abs(float(b)-v['t']) for b in cross),default=999)<=.35):continue
        nearby=vals[max(0,i-2):min(len(vals),i+3)]
        if any(x['transition_score']>v['transition_score'] for x in nearby):continue
        if selected and v['t']-selected[-1]['t']<.70:
            if v['transition_score']>selected[-1]['transition_score']:selected[-1]=v
            continue
        selected.append(v)
    events=[];inside=[]
    for x in selected:
        t=x['t'];proximity=min((abs(b-t) for b in bounds),default=999)
        ff=min((abs(float(b)-t) for b in cross),default=999)
        sid=next((r['shot_id'] for r in shotcsv if float(r['start_sec'])<=t<float(r['start_sec'])+float(r['duration_sec'])),'OUTSIDE')
        record={**x,'shot_id_current':sid,'near_original_boundary':proximity<=.45,
          'distance_to_original_boundary_s':round(proximity,3),
          'ffmpeg_corrob':ff<=.40,'distance_to_second_detector_s':round(ff,3),
          'interpretation':'POSSIBLE_UNDETECTED_CUT_NEEDS_REVIEW' if proximity>.45 else 'NEAR_EXISTING_PROPOSED_CUT',
          'reference_only':True}
        events.append(record)
        if proximity>.45:inside.append(record)
    allj={'source_sha256':J(DATA/'project_manifest.json',{}).get('source_sha256'),
          'challenge_window':{'start':start,'end':end,'fps':fps,'frame_samples':len(frames)},
          'status':'REFERENCE_CUT_HEURISTICS_NOT_EDITORIAL_TRUTH','transition_threshold':round(threshold,4),
          'intervals':vals,'candidate_events':events,'internal_cut_warnings':inside,
          'warning':'Camera moves, effects, dissolves and actor motion can create false positives; 4fps may miss very short cuts.'}
    savej(OUT/'reference_visual_timeline.json',allj)
    return allj

def preface_score(s,previous,next_):
    duration=float(s['duration_sec']);mean_d=float(previous['duration_sec']) if previous else duration
    next_d=float(next_['duration_sec']) if next_ else duration
    return {'current_duration_s':duration,'previous_s':round(mean_d,2),'next_s':round(next_d,2),
      'relative_pacing':'QUICKER_THAN_NEIGHBORS' if duration<.55*(mean_d+next_d)/2 else 'LONGER_THAN_NEIGHBORS' if duration>1.6*(mean_d+next_d)/2 else 'SIMILAR_DURATION',
      'editorial_rhythm_verified':False}

def camera_direction(motion):
    status=motion.get('status','')
    if status!='2D_ESTIMATE_AVAILABLE':return '无法从低置信度二维特征轨迹判断；待视频或三维复核'
    parts=[]
    dx=float(motion.get('dx_px_at_480w',0));dy=float(motion.get('dy_px_at_480w',0));s=float(motion.get('scale_factor_2d',1))
    if abs(dx)>4:parts.append('图像整体'+('向右' if dx>0 else '向左')+'漂移')
    if abs(dy)>4:parts.append('图像整体'+('向下' if dy>0 else '向上')+'漂移')
    if abs(s-1)>.018:parts.append('表观比例'+('增大' if s>1 else '缩小'))
    return '、'.join(parts) if parts else '全局二维位移较小；不能据此认定摄影机静止'

def p95_text(a):
    try:return f'{float(a):.2f}'
    except Exception:return '未知'

def build_cards(timeline=None):
    reference=J(ROOT/'output/evidence/director_evidence.json',{})
    cards=reference.get('cards',[])
    features=J(DATA/'shot_features.json',{}).get('features',[])
    feats={f['shot_id']:f for f in features}
    if not cards:raise RuntimeError('Run director_evidence.py first')
    if timeline is None:timeline=analysis_evidence()
    internal=timeline.get('internal_cut_warnings',[])
    scores=timeline.get('intervals',[])
    snippets=J(DATA/'director_decisions.json',{})
    if not isinstance(snippets,dict):snippets={}
    out=[]
    for i,c in enumerate(cards):
        sid=c['shot_id'];f=feats.get(sid,{})
        frames=c['target_frames']
        im={a:image_info(ROOT/frames[a]) for a in AN}
        concerns=[x for x in internal if x['shot_id_current']==sid]
        peaks=sorted((x for x in scores if c['start_sec']<=x['t']<c['end_sec']),key=lambda q:q['transition_score'],reverse=True)[:3]
        idx=int(sid.split('_')[-1]);ob=OBSERVED.get(idx)
        faces=c.get('asset_observations',{}).get('possible_face_boxes',0)
        dur=c['duration_sec']; bright=statistics.mean(im[a]['brightness'] for a in AN)
        approxsize='FACE_DETECTED_UNVERIFIED_SCALE' if faces else 'FRAME_SIZE_UNDETERMINED'
        base_intent=('可见人物关系与注意力转移（待导演确认）' if faces else
                     '可能承担环境/空间/节奏功能，需结合剧情和前后镜确认')
        visual_role=('人物反应/对话关系候选' if faces else
                     '环境/动作/过渡候选')
        if ob: visual_role=ob[0]
        cut={'is_contaminated':bool(concerns), 'internal_cut_candidates':concerns,
          'action':'VERIFY_SPLIT_BEFORE_GENERATION' if concerns else 'REVIEW_SOURCE_BOUNDARIES',
          'cut_verified':False}
        m=c.get('apparent_motion',{})
        fvisual=f.get('visual',{})
        opt=f.get('optical_flow',{})
        cues={
            'visual_role_hypothesis':visual_role,
            'dramatic_intent_hypothesis':ob[1] if ob else base_intent,
            'visible_geometry':ob[2] if ob else '未提供可靠的人工逐镜场景/人物解读',
            'director_action':ob[3] if ob else '确认镜头戏剧作用、人物关系、动作和切点后再锁定',
            'provenance':'assistant visual inspection of source IN/MID/OUT; unverified hypothesis' if ob else 'rule-based low-confidence placeholder',
            'source_confirmed':False,
            'requires_story_context':True}
        q={
          'shot_id':sid,'time':{'start':c['start_sec'],'end':c['end_sec'],'duration':dur},
          'reference_images':frames,'anchor_source_shas':{a:sha(ROOT/frames[a]) for a in AN},
          'camera_2d':{'in_mid':camera_direction(m.get('in_to_mid',{})),'mid_out':camera_direction(m.get('mid_to_out',{})),
            'motion_metrics':m,'camera_3d_path_confirmed':False,'camera_motion_inferred_only':True},
          'framing':{'shot_size_hypothesis':approxsize,'attention_anchor_xy':fvisual.get('visual_attention_proxy_xy'),
             'measured_per_anchor':im,'human_framing_confirmed':False},
          'light_art':{'mean_brightness':round(bright,3),'lighting_proxy':fvisual.get('lighting_proxy'),
             'mean_saturation':round(statistics.mean(im[a]['saturation'] for a in AN),3),
             'art_and_costume_identity_verified':False},
          'actor_blocking':{'possible_face_observations':faces,'character_id_locked':False,
             'pose_estimated':False,'gaze_verified':False,'beat_timecodes_verified':False},
          'audio':{'reference_rms':float(f.get('audio_rms',0)),'dialogue_transcript_available':False,
             'sync_verified':False},
          'rhythm':preface_score(c,cards[i-1] if i else None,cards[i+1] if i+1<len(cards) else None),
          'cut_analysis':cut,'visible_change_peak_proxies':peaks,'director_reading':cues,
          'sequence_group_proposal':f.get('visual_group_proposal','UNDETERMINED'),
          'production_gates':{'shot_boundary_verified':False,'narrative_intent_verified':False,'performance_verified':False,
               'asset_identities_locked':False,'independent_generated_candidate':bool(c.get('production_state',{}).get('current_candidate_anchors',0)),
               'director_approved':bool(c.get('production_state',{}).get('full_shot_approved',False)),
               'official_status':'BLOCKED_NEEDS_REAL_DIRECTOR_VALIDATION'},
          'decision_notes':snippets.get(sid,{}),
          'production_instruction':{
             'step_0':'先确认原片中是否包含多个真实镜头；不可拿跨切点三帧当作同一镜头',
             'shot_objective_draft':cues['dramatic_intent_hypothesis'],
             'spatial_constraints':f"参照真实原片三张关键帧；逐帧锁定人物、空间层次与视线，不自动猜角色ID。{cues['visible_geometry']}",
             'camera_constraints':'按二维技术证据约束画面变化：'+camera_direction(m.get('in_to_mid',{}))+'。不得当作准确三维机位。',
             'acting_constraints':f"待确认人物身份与表演节拍；{cues['director_action']}",
             'art_constraints':f"使用参考片段的{fvisual.get('lighting_proxy','未知')}光照、{p95_text(bright)}平均灰度比例及对应美术参考，服装和物品版本未锁定。",
             'next_storyboard_production':'独立生成IN/MID/OUT，逐帧对照，确认身份、空间、表演与叙事才能签核',
             'block_if':'切镜存在争议，或人物/意图/资产/候选/签核任一缺失'} }
        out.append(q)
    return out

def static_comparison_cards(cards):
    # If generated images are absent, create *zero* comparison success records.
    return {'total_shots':len(cards),'reference_anchors':len(cards)*3,
         'generated_current_cards':sum(bool(x['production_gates']['independent_generated_candidate']) for x in cards),
         'director_signoff_shots':sum(bool(x['production_gates']['director_approved']) for x in cards),
         'reference_only':True}

def cut_contact_sheet(timeline,output=None,limit=24):
    """Side by side before/after real video frames, for transition proposals."""
    from PIL import Image,ImageDraw,ImageFont
    events=timeline.get('internal_cut_warnings',[])[:limit]
    if not events:return None
    fw=376;fh=235;col=3;row=math.ceil(len(events)/col)
    sheet=Image.new('RGB',(fw*col,fh*row),'#101b2b');draw=ImageDraw.Draw(sheet)
    font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',14) if Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf').is_file() else ImageFont.load_default()
    cache=OUT/'probe_frames'
    for i,e in enumerate(events):
        x=(i%col)*fw;y=(i//col)*fh
        k=e['frame_i']
        left=cache/f'f_{k:04}.jpg';right=cache/f'f_{k+1:04}.jpg'
        # For score between frame k-1 and k (0-index), names are f_{k} / f_{k+1}; indexes 0->f_0001.
        for j,p in enumerate([left,right]):
            try:
                image=Image.open(p).convert('RGB');image.thumbnail((180,145))
                sheet.paste(image,(x+8+j*186,y+42))
            except Exception:pass
        draw.text((x+8,y+8),f"{e['shot_id_current']}  {e['t']:.2f}s  score {e['transition_score']:.2f}",font=font,fill='#f1d6a7')
        draw.text((x+8,y+199),'POSSIBLE missed cut / manual review',font=font,fill='#d6c7aa')
        draw.text((x+8,y+217),'independent detector: '+str(e['ffmpeg_corrob']),font=font,fill='#a5bad2')
    path=Path(output or OUT/'potential_missed_cuts.jpg');path.parent.mkdir(exist_ok=True,parents=True);sheet.save(path,quality=88)
    return str(path.relative_to(ROOT))

def build_sequence(challenge,cards,ts):
    ids=challenge.get('shot_ids',[]);subset=[c for c in cards if c['shot_id'] in ids]
    findings=[]
    for i,c in enumerate(subset):
        if c['cut_analysis']['is_contaminated']:
            findings.append({'kind':'SHOTS_MAY_HIDE_INTERNAL_CUTS','shot_id':c['shot_id'],
               'times':[x['t'] for x in c['cut_analysis']['internal_cut_candidates']],
               'advice':'暂停对此镜头的表演、运镜、三帧生成任务；先复核切点并重新建立镜头ID'})
        if i:
            a=subset[i-1];b=c
            delta=abs(b['light_art']['mean_brightness']-a['light_art']['mean_brightness'])
            if delta>.25:
                findings.append({'kind':'STRONG_LIGHTING_CONTRAST_AT_CUT',
                    'shot_id':b['shot_id'],'previous':a['shot_id'],
                    'brightness_jump':round(delta,3),
                    'advice':'可能是有意的场景切换，先确认是否转场；不可自动做色彩连续性修复'})
    return {'status':'DIRECTOR_DIAGNOSTIC_NOT_FINAL_SCENE_INTERPRETATION',
      'start_sec':challenge.get('start_sec'),'end_sec':challenge.get('end_sec'),
      'shot_count':len(subset),'shot_ids':ids,
      'shot_rhythm_seconds':[{'shot_id':c['shot_id'],'length':c['time']['duration']} for c in subset],
      'provisional_boundaries':True,
      'detected_visual_peaks':len([x for x in ts.get('candidate_events',[]) if x['shot_id_current'] in ids]),
      'suspected_hidden_cut_events':len([x for x in ts.get('internal_cut_warnings',[]) if x['shot_id_current'] in ids]),
      'specific_director_findings':findings,
      'editorial_rule':'Do not treat strong color contrast at a real cut as a defect before narrative intent has been reviewed',
      'narrative_continuity_verified':False,'actor_consistency_verified':False}

def derive_delivery(root=ROOT,scan=True):
    global ROOT,OUT,DATA,SRC
    root=Path(root).resolve();ROOT=root;OUT=root/'output/director_lab';DATA=root/'data';SRC=DATA/'source_video.mp4'
    OUT.mkdir(parents=True,exist_ok=True)
    man=J(DATA/'project_manifest.json',{})
    challenge=J(ROOT/'output/evidence/challenge_acceptance.json',{})
    if not challenge:challenge={'status':'NO_60_TO_120_SECOND_CHALLENGE_IN_SHORT_IMPORT','shot_ids':[], 'start_sec':None,'end_sec':None}
    timeline=scan_reference_window(challenge['start_sec'],challenge['end_sec'],fps=4) if scan and challenge.get('start_sec') is not None and challenge.get('end_sec') is not None else {'challenge_window':{},'intervals':[],'candidate_events':[],'internal_cut_warnings':[]}
    cards=build_cards(timeline)
    seq=build_sequence(challenge,cards,timeline)
    paths={
       'cut_contact_sheet':cut_contact_sheet(timeline),
       'per_shot_director_cards':'output/director_lab/director_cards.json',
       'sequence_diagnosis':'output/director_lab/sequence_director_review.json',
       'film_work_orders':'output/director_lab/director_shot_work_orders.jsonl'}
    savej(OUT/'director_cards.json',cards)
    savej(OUT/'sequence_director_review.json',seq)
    with (OUT/'director_shot_work_orders.jsonl').open('w',encoding='utf-8') as h:
        for c in cards:
            order={'shot_id':c['shot_id'],'status':'DRAFT_NOT_AUTHORIZED_FOR_GENERATION' if c['cut_analysis']['is_contaminated'] else 'REQUIRES_DIRECTOR_REVIEW_BEFORE_GENERATION',
                  'source_times':c['time'],'storyboard_anchors':c['reference_images'],'source_kind':'ORIGINAL_REFERENCE_ONLY',
                  'director_instruction':c['production_instruction'],'blocking_issues':c['cut_analysis'],
                  'required_proof':['confirmed_shot_boundary','identity_lock','3d_blocking_if_complex',
                    'independent_generated_image','semantic_review','in_mid_out_consistency','director_approval']}
            h.write(json.dumps(order,ensure_ascii=False)+'\n')
    summary={'source_sha256':man.get('source_sha256'),
        'video_duration_s':man.get('duration_seconds'),
        'reference_shots':len(cards),'real_reference_frames':len(cards)*3,
        'manually_inspected_director_hypotheses':sum(c['director_reading']['provenance'].startswith('assistant') for c in cards),
        'visual_transition_cues_in_challenge':len(timeline.get('candidate_events',[])),
        'potential_internal_cuts_in_challenge':len(timeline.get('internal_cut_warnings',[])),
        'affected_current_shot_cards':len(set(x['shot_id_current'] for x in timeline.get('internal_cut_warnings',[]))),
        'visual_frame_samples':timeline.get('challenge_window',{}).get('frame_samples',0),
        'confirmed_director_narrative_intents':0,
        'verified_actor_identities':0,
        'ai_recreated_stills_approved':static_comparison_cards(cards)['director_signoff_shots'],
        'ai_generated_video':0,
        'real_model_api_used':False,
        'cost_paid_video_generation':0,
        'rigor':'No film reference is considered an independently generated storyboard; no auto-splitting prior to editorial review.',
        'sequence':seq,'assets':paths}
    savej(OUT/'DIRECTOR_LAB_ACCEPTANCE.json',summary)
    build_html(cards,summary)
    return summary

def safe_notes(shot_id,notes,project_root=ROOT):
    """Persist a director's hypotheses, with reference-based integrity and spec invalidation."""
    root=Path(project_root)
    if not re.fullmatch(r'SH_\d{5}',str(shot_id)):raise ValueError('Invalid shot id')
    cards=J(root/'output/director_lab/director_cards.json',[])
    card=next((x for x in cards if x['shot_id']==shot_id),None)
    if card is None:raise ValueError('Unknown shot id')
    if any(sha(root/card['reference_images'][a])!=card['anchor_source_shas'][a] for a in AN):
        raise ValueError('Reference frame changed; rerun director_craft.py before editing')
    if not isinstance(notes,dict):raise ValueError('Expected notes object')
    allowed=('narrative_purpose','blocking','acting','camera','cut_rationale','scene_topology','identity_refs','art_costume','sound_rhythm','review_status')
    if set(notes)-set(allowed):raise ValueError('Unknown note key')
    if 'review_status' in notes and notes['review_status'] not in ('DRAFT','NEEDS_INSPECTION','REVIEWED_REFERENCE_ONLY'):
        raise ValueError('This interface never signs off AI reconstructions')
    normalized={k:str(v).strip()[:2500] for k,v in notes.items()}
    decisions_path=root/'data/director_decisions.json';decisions=J(decisions_path,{})
    now=datetime.now(timezone.utc).isoformat()
    before=decisions.get(shot_id,{}).get('notes',{})
    entry={'shot_id':shot_id,'notes':normalized,'timestamp':now,
      'source_frame_sha256':card['anchor_source_shas'],'source_sha256':J(root/'data/project_manifest.json',{}).get('source_sha256'),
      'approval':'REFERENCE_DIRECTOR_NOTES_ONLY','reconstruction_approved':False,
      'revision':int(decisions.get(shot_id,{}).get('revision',0))+(1 if before!=normalized else 0)}
    if before==normalized:return entry
    import director as d
    with d.connect() as con:
        # Updating validated spec resets any downstream approval rather than claiming success.
        for anchor in ('IN','MID','OUT'):
            tid=shot_id+':'+anchor
            row=con.execute('SELECT * FROM tasks WHERE id=?',(tid,)).fetchone()
            if row:
                cons=d.read_json(row['constraints'],{})
                cons['director_craft_notes']={'notes':normalized,'revision':entry['revision'],
                                              'source_frame_sha256':card['anchor_source_shas']}
                d.rebase_spec(con,tid,normalized.get('narrative_purpose','导演备注草案，非已证实叙事'),cons)
    decisions[shot_id]=entry
    savej(decisions_path,decisions)
    return entry

def build_html(cards,summary):
    tpl='''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>AI导演 · 镜头语言与表演工作台</title><style>
:root{font-family:ui-sans-serif,system-ui,"Microsoft YaHei",sans-serif;color:#e8eef7;background:#0e1624}*{box-sizing:border-box}body{margin:0}header{padding:18px 24px;border-bottom:1px solid #314359;background:#142239}header h1{font-size:22px;margin:0 0 5px}p{margin:5px 0 10px;line-height:1.6}a{color:#9fd7ff}.warn{color:#edca84}.muted{color:#9daec3;font-size:12px}.main{display:grid;grid-template-columns:280px minmax(0,1fr);gap:14px;max-width:1620px;margin:auto;padding:14px}.pane{border:1px solid #34455f;background:#18263a;border-radius:12px;padding:16px}.shots{max-height:85vh;overflow:auto}.shots button{background:#223650;color:#eef3fa;padding:8px;border:1px solid #304760;border-radius:8px;margin:3px 3px 3px 0;cursor:pointer;width:112px;text-align:left}.shots button.active{border-color:#e6bb70;background:#4a3e2f}.shots button.flag{box-shadow:inset 4px 0 #e2aa6d}.images{display:grid;grid-template-columns:repeat(3,1fr);gap:7px}.images img{width:100%;aspect-ratio:1280/534;object-fit:cover;border:1px solid #34475e;border-radius:7px}.stat{display:inline-block;background:#263f58;border-radius:7px;padding:6px 9px;margin:4px 4px 4px 0}.cols{display:grid;grid-template-columns:repeat(2,1fr);gap:12px}.section{background:#132134;border:1px solid #2d405b;border-radius:9px;padding:13px;margin:10px 0}h2{font-size:18px;margin:10px 0}h3{font-size:15px;color:#e2c18b;margin:4px 0 9px}label{display:block;color:#b0c4d9;font-size:13px;margin-bottom:5px}textarea{width:100%;background:#101b2c;color:#fff;border:1px solid #47617b;border-radius:7px;padding:8px;min-height:68px;resize:vertical;font-family:inherit}button.primary{background:#d8b67b;border:0;color:#171e27;font-weight:bold;padding:11px 20px;border-radius:9px;cursor:pointer}input[type=search]{width:100%;padding:11px;background:#091626;border:1px solid #43607c;color:white;border-radius:8px}#cutview img{max-width:100%}.tag{border:1px solid #876243;background:#412e29;color:#ffd3a4;border-radius:5px;padding:2px 6px}.confidence{font-size:12px;color:#b5c6d8}.kbd{font-family:monospace}pre{white-space:pre-wrap;font-size:12px}footer{padding:24px;text-align:center;color:#a9b4c4}@media(max-width:850px){.main{grid-template-columns:1fr}.shots{max-height:190px}.cols{grid-template-columns:1fr}}
</style></head><body><header><h1>AI电影导演 · 导演工作与分镜验收台</h1><p class="warn">真实影片参考 ≠ AI复刻；动作节拍峰值 ≠ 确认的演员动作；二维运动 ≠ 三维摄影机轨迹。全部导演推断均待确认。</p><p><a href="/">主工作台</a> · <a href="/evidence">原片证据卡</a> · <a href="/cuts">切镜争议审核</a></p></header>
<main class="main"><aside class="pane"><h3>镜头导航 · 86张导演卡</h3><p class="muted">黄色边框表示本镜头内出现疑似遗漏切点，须先复核。</p><input type="search" id="search" placeholder="输入镜头号，例如 00055"><div id="shotlist" class="shots"></div></aside><section><div id="summary"></div><div class="pane" id="detail"></div><section class="pane" id="cutview"><h2>连续段落 · 疑似遗漏切点复核</h2><p class="muted">该图只来自原片低分辨率采样，分数较高不等于真实切点。优先处理后才能相信摄影连续性。</p><img id="cutSheet" alt="待复核切镜前后帧"></section></section></main><footer>电影导演生产工程 · 禁止将任何原片像素评分当作AI生成质量结论</footer>
<script id="seed" type="application/json">__SEED__</script><script>
const seed=JSON.parse(document.getElementById('seed').textContent);const cards=seed.cards;const s=seed.summary;let current=cards[0]?.shot_id;let token='__CSRF__';
function safe(v){return String(v??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;')}
function media(p){return location.protocol.startsWith('http')?'/file?path='+encodeURIComponent(p):p}
function nav(){let q=document.getElementById('search').value.trim().toLowerCase();let filtered=cards.filter(c=>c.shot_id.toLowerCase().includes(q));document.getElementById('shotlist').innerHTML=filtered.map(c=>`<button onclick="show('${c.shot_id}')" class="${current===c.shot_id?'active':''} ${c.cut_analysis.is_contaminated?'flag':''}">${safe(c.shot_id)}${c.cut_analysis.is_contaminated?' ⚠':''}<br><span class="muted">${c.time.duration}s</span></button>`).join('')}
document.getElementById('search').addEventListener('input',nav);
function show(id){current=id;nav();let c=cards.find(z=>z.shot_id===id);if(!c)return;let read=c.director_reading;let notes=c.decision_notes?.notes||{};
let cuts=c.cut_analysis.internal_cut_candidates.map(x=>`${x.t.toFixed(2)}s（突变 ${x.transition_score}，第二算法${x.ffmpeg_corrob?'支持':'未支持'}）`).join('、');
let ims=['in','mid','out'].map(a=>`<div><label>${a.toUpperCase()} · 原片参考帧，不是生成图</label><img src="${media(c.reference_images[a])}"></div>`).join('');
let pe=c.visible_change_peak_proxies.map(v=>`${v.t.toFixed(2)}s: ${v.transition_score.toFixed(3)}`).join(' / ') || '该段未精采样';
let form=[['narrative_purpose','戏剧目的（叙事信息）'],['blocking','人物走位／前后层次'],['acting','动作与眼神／表演节拍'],['camera','机位／景别／摄影运动'],['cut_rationale','切镜理由／转场意图'],['scene_topology','空间轴线与场景方位'],['identity_refs','角色、服装、道具资产ID'],['art_costume','服化道和光照约束'],['sound_rhythm','对白／音乐／音画节奏']].map(([key,label])=>`<div><label>${label}</label><textarea data-key="${key}">${safe(notes[key]||'')}</textarea></div>`).join('');
document.getElementById('detail').innerHTML=`<h2>${id} · ${c.time.start.toFixed(2)}–${c.time.end.toFixed(2)}s</h2><div class="images">${ims}</div>
<div class="section"><h3>导演阅读 · 非已认证的语义推断</h3><p><b>画面可读信息：</b>${safe(read.visible_geometry)}</p><p><b>可能承担的戏剧作用：</b>${safe(read.dramatic_intent_hypothesis)}</p><p><b>需要明确的导演决定：</b>${safe(read.director_action)}</p><p class="confidence">依据：${safe(read.provenance)}；导演叙事尚未确认。</p></div>
${c.cut_analysis.is_contaminated?`<div class="section"><h3>⚠ 发现疑似漏切 · 先复核</h3><p>${safe(cuts)}</p><p>该镜头的IN/MID/OUT可能来自多个独立镜头，暂不能作为同一条摄影或演员调度使用。</p></div>`:''}
<div class="cols"><div class="section"><h3>摄影语言与画面重心</h3><p>IN→MID：${safe(c.camera_2d.in_mid)}</p><p>MID→OUT：${safe(c.camera_2d.mid_out)}</p><p>画面重心技术代理：${safe(c.framing.attention_anchor_xy?.join(', '))}</p><p>景别：${safe(c.framing.shot_size_hypothesis)}，待确定</p><p class="muted">二维光流不能区分人物移动、摄影机移动、遮挡或转场。</p></div>
<div class="section"><h3>演员、剪辑、音轨</h3><p>可能的人脸检测框：${c.actor_blocking.possible_face_observations}，身份未锁定</p><p>相邻镜头节奏：${safe(c.rhythm.relative_pacing)}</p><p>源音频均方根：${c.audio.reference_rms.toFixed(3)}，非对白识别</p><p>画面突变峰：${safe(pe)}</p><p class="muted">仅为画面变化事件候选，不能直接说某演员做了某个动作。</p></div></div>
<div class="section"><h3>逐帧画面目标（技术证据）</h3><div class="cols">${['in','mid','out'].map(a=>`<p>${a.toUpperCase()}：亮度 ${c.framing.measured_per_anchor[a].brightness}，饱和度 ${c.framing.measured_per_anchor[a].saturation}，重点区域 ${c.framing.measured_per_anchor[a].visual_detail_focus_proxy_xy.join(',')}</p>`).join('')}</div></div>
<div class="section"><h3>导演修订栏 · 不能自动变成签核</h3><p class="muted">保存到工程的数据记录；修改会使依赖旧规范的审核失效。未连接图片模型也可完成导演工作。</p><div class="cols">${form}</div><button class="primary" onclick="save()">保存本镜头导演决策</button><p id="saveState" class="muted">未保存修改</p></div>`;}
async function save(){let fields={};document.querySelectorAll('#detail textarea[data-key]').forEach(el=>fields[el.dataset.key]=el.value);fields.review_status='REVIEWED_REFERENCE_ONLY';if(!location.protocol.startsWith('http')){let b=new Blob([JSON.stringify({shot_id:current,notes:fields},null,2)],{type:'application/json'});let a=document.createElement('a');a.href=URL.createObjectURL(b);a.download=current+'_director_notes.json';a.click();document.getElementById('saveState').textContent='离线文件已导出；在本机服务启动后才能保存到项目数据库。';return}
try{let res=await fetch('/api/director-notes',{method:'POST',headers:{'Content-Type':'application/json','X-Director-Token':token},body:JSON.stringify({shot_id:current,notes:fields})});let out=await res.json();if(!res.ok)throw Error(out.error||'failed');document.getElementById('saveState').textContent='保存成功，审查仍未通过，修订号 '+out.revision;cards.find(x=>x.shot_id===current).decision_notes=out}catch(e){document.getElementById('saveState').textContent='保存失败：'+e.message}}
document.getElementById('cutSheet').src=media('output/director_lab/potential_missed_cuts.jpg');document.getElementById('summary').innerHTML=`<div class="pane"><h2>导演工作实际验收</h2><span class="stat">真实参考镜头 ${s.reference_shots}</span><span class="stat">三帧 ${s.real_reference_frames}</span><span class="stat">人工目视分析草稿 ${s.manually_inspected_director_hypotheses}</span><span class="stat">93秒疑似内部漏切 ${s.potential_internal_cuts_in_challenge}</span><span class="stat">正式导演签核 ${s.ai_recreated_stills_approved}</span><p class="warn">完成的是源影片导演证据与制作指令，不是AI重建成功。所有镜头仍需身份、表演、空间与真正生成内容验收。</p></div>`;nav();show(current);
</script></body></html>'''
    blob=json.dumps({'cards':cards,'summary':summary},ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
    # Deliberately serialize as untrusted JSON text, not executable JS source.
    blob=blob.replace('&','\\u0026').replace('<','\\u003c').replace('>','\\u003e')
    target=ROOT/'DIRECTOR_DESK.html';target.write_text(tpl.replace('__SEED__',blob),encoding='utf-8')
    return str(target)

def main():
    ap=argparse.ArgumentParser(description='Cinematography, performance, staging and cut review based on real source reference')
    sub=ap.add_subparsers(dest='cmd',required=True)
    sub.add_parser('run');sub.add_parser('status');e=sub.add_parser('export');e.add_argument('--shot',default=None)
    a=ap.parse_args()
    if a.cmd=='run':print(json.dumps(derive_delivery(),ensure_ascii=False,indent=2))
    elif a.cmd=='status':print(json.dumps(J(OUT/'DIRECTOR_LAB_ACCEPTANCE.json',{}),ensure_ascii=False,indent=2))
    elif a.cmd=='export':
        cards=J(OUT/'director_cards.json',[])
        result=[c['production_instruction'] for c in cards if not a.shot or c['shot_id']==a.shot]
        print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
