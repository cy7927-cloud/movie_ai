#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Evidence-first static film director audit, on a REAL uploaded reference excerpt.

This pipeline does not hallucinate character identities, camera 3-D paths or scene intent.
It cannot label source-derived calibration pictures as independently generated.
It is entirely offline, and always separates reference baselines from recreated-content QA.
"""
from __future__ import annotations
import argparse, collections, csv, hashlib, html, json, math, statistics, datetime
from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

BASE=Path(__file__).resolve().parent
ANCHORS=('in','mid','out')

def readj(p, default=None):
    p=Path(p)
    return json.loads(p.read_text(encoding='utf-8')) if p.is_file() else default

def writej(path, obj):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')

def capture(path, width=480):
    image=cv2.imread(str(path),cv2.IMREAD_COLOR)
    if image is None: raise ValueError('Missing or unreadable frame '+str(path))
    if image.shape[1]>width:
        image=cv2.resize(image,(width,int(round(image.shape[0]*width/image.shape[1]))),interpolation=cv2.INTER_AREA)
    return image

def sparse_2d_motion(image1,image2):
    """Robust apparent 2D image displacement. Never infer actor versus camera motion."""
    a=capture(image1);b=capture(image2)
    if a.shape[:2]!=b.shape[:2]:b=cv2.resize(b,(a.shape[1],a.shape[0]))
    g1=cv2.cvtColor(a,cv2.COLOR_BGR2GRAY);g2=cv2.cvtColor(b,cv2.COLOR_BGR2GRAY)
    pts=cv2.goodFeaturesToTrack(g1,maxCorners=500,qualityLevel=.012,minDistance=8,blockSize=5)
    if pts is None or len(pts)<12:
        return {'status':'LOW_TEXTURE_UNDETERMINED','features_found':len(pts) if pts is not None else 0,
                'inlier_ratio':None,'motion':'UNDETERMINED','warning':'Not 3D camera or pose estimation'}
    nxt,st,_=cv2.calcOpticalFlowPyrLK(g1,g2,pts,None,winSize=(19,19),maxLevel=3,
                                        criteria=(cv2.TERM_CRITERIA_EPS|cv2.TERM_CRITERIA_COUNT,25,.02))
    good=st[:,0]==1; p=pts[good].reshape(-1,2);q=nxt[good].reshape(-1,2)
    if len(p)<12:return {'status':'INSUFFICIENT_TRACKS','features_found':len(pts),'tracks_valid':len(p),
                        'motion':'UNDETERMINED','warning':'Cannot measure global 2D displacement'}
    mat,inliers=cv2.estimateAffinePartial2D(p,q,method=cv2.RANSAC,ransacReprojThreshold=3.5,
                                             maxIters=2500,confidence=.97)
    if mat is None or inliers is None: return {'status':'RANSAC_UNSTABLE','tracks_valid':len(p),
                                               'motion':'UNDETERMINED','warning':'No robust planar transform'}
    inl=inliers.reshape(-1)>0; ratio=float(np.mean(inl))
    if np.count_nonzero(inl)<9 or ratio<.28:
        return {'status':'LOW_GLOBAL_COHERENCE','tracks_valid':len(p),'inlier_ratio':round(ratio,3),
                'motion':'MIXED_OR_UNDETERMINED','warning':'Object motion, parallax, edits or camera motion may coexist'}
    dx=float(mat[0,2]);dy=float(mat[1,2]);scale=float(math.hypot(mat[0,0],mat[1,0]));deg=float(math.degrees(math.atan2(mat[1,0],mat[0,0])))
    trans=float(math.hypot(dx,dy)); bits=[]
    if trans>4:bits.append('GLOBAL_IMAGE_TRANSLATION')
    if abs(scale-1)>.018:bits.append('APPARENT_SCALE_CHANGE')
    if abs(deg)>1.8:bits.append('APPARENT_ROTATION')
    if not bits:bits.append('LOW_GLOBAL_IMAGE_MOTION')
    return {'status':'2D_ESTIMATE_AVAILABLE','tracks_valid':int(len(p)),'inlier_ratio':round(ratio,3),
            'dx_px_at_480w':round(dx,2),'dy_px_at_480w':round(dy,2),
            'scale_factor_2d':round(scale,4),'rotation_deg_2d':round(deg,2),
            'motion':'+'.join(bits),'warning':'Not a 3D camera path, actor trajectory, or physical movement measurement'}

def challenge_selection(cards,minimum=60,maximum=120):
    """Choose a continuous, sufficiently diverse segment; not a cherry-picked single frame."""
    if not cards:return None
    options=[]
    for i in range(len(cards)):
        for j in range(i,len(cards)):
            shots=cards[i:j+1];dur=shots[-1]['end_sec']-shots[0]['start_sec']
            if dur>maximum+.01:break
            if dur<minimum or len(shots)<5:continue
            groups=len(set(s['visual_group_proposal'] for s in shots))
            moves=len(set(s['apparent_motion']['in_to_mid']['motion'] for s in shots))
            faces=sum(s['asset_observations']['possible_face_boxes'] for s in shots)
            audio=statistics.pstdev([s['reference_technical']['audio_rms'] for s in shots])
            difficult=sum(s['issues']!=[] for s in shots)
            # Prioritize variety, not inferred shot-quality success. Prefer ~95s for repeatable testing.
            score=2.1*min(groups,5)+.65*min(len(shots),15)+1.2*min(moves,4)+.5*min(faces,6)+\
                  min(audio*90,4)+.15*min(difficult,5)-.045*abs(dur-95)
            options.append((score,i,j,round(dur,2)))
    if not options:return {'status':'NO_CONTINUOUS_60_TO_120_SECOND_WINDOW_WITH_5_SHOTS'}
    score,i,j,duration=max(options,key=lambda x:(round(x[0],4),-x[1]))
    shots=cards[i:j+1]
    return {'status':'REFERENCE_EXCERPT_CHALLENGE_SELECTED_UNVERIFIED',
      'start_sec':shots[0]['start_sec'],'end_sec':shots[-1]['end_sec'],
      'duration_seconds':duration,'shot_ids':[s['shot_id'] for s in shots],
      'shot_count':len(shots),'visual_group_proposals':len(set(s['visual_group_proposal'] for s in shots)),
      'possible_face_box_count':sum(s['asset_observations']['possible_face_boxes'] for s in shots),
      'motion_types':sorted(set(s['apparent_motion']['in_to_mid']['motion'] for s in shots)),
      'definition':'A contiguous 60–120s mixed-shot acceptance challenge. Boundaries and group labels are provisional; not a confirmed complete scene.',
      'gates':['verify shot boundaries','generate independent IN/MID/OUT for every shot',
       'review identities and art design','review in-shot and neighboring-shot continuity',
       'iterate until signoff or explicit unresolved failure']}

def verify_generated_pair(a,b):
    """Compare temporal COLOR change against source (technical only)."""
    def lab(p):
        im=capture(p,320)
        return np.mean(cv2.cvtColor(im,cv2.COLOR_BGR2LAB),axis=(0,1))
    return round(float(np.linalg.norm(lab(a)-lab(b))),3)

def candidate_evidence(tasks, shots):
    """Build GENERATED evidence exclusively from current hash-validated candidate records."""
    import director as d
    import product_engine as eng
    with d.connect() as con:
        for card in shots:
            sid=card['shot_id'];audit=eng.shot_review(con,sid)
            if audit is None:continue
            card['production_state']={'current_candidate_anchors':sum(bool(t['candidate']) for t in audit['anchors']),
              'signed_off_anchors':audit['approved_anchors'],
              'full_shot_approved':bool(audit['is_fully_approved']),
              'anchor_verdicts':{t['anchor']:t['status'] for t in audit['anchors']},
              'reference_continuity_pairs_measured':2,
              'generated_continuity_pairs_measured':sum('deviation_lab' in a for a in audit['cross_anchor_checks']),
              'generated_continuity_checks':audit['cross_anchor_checks']}
            # Reuse existing SHA-valid candidate selection, never count original references.
            valid=dict((x['anchor'],x) for x in audit['anchors'] if x['candidate'])
            if len(valid)==3:
                scores=[x['technical_score'] for x in valid.values()]
                card['production_state']['min_technical_anchor_score']=round(min(scores),4)
            card['production_state']['gate']='SIGNED_OFF' if audit['is_fully_approved'] else 'BLOCKED_UNVERIFIED'
    return shots

def prepare_reference_evidence(root=BASE,compute_flow=True):
    root=Path(root)
    rows=list(csv.DictReader((root/'data/shots_source.csv').open(encoding='utf-8-sig')))
    feats=readj(root/'data/shot_features.json',{})
    byid={f['shot_id']:f for f in feats.get('features',[])}
    observations=readj(root/'data/asset_bible_observations.json',{})
    faces=collections.defaultdict(list)
    for o in observations.get('face_observations',[]):faces[o['shot_id']].append(o)
    cont=readj(root/'data/continuity_reference.json',{})
    cont_byid={x['shot']:x for x in cont.get('intra_shot_reference',[])}
    cut=readj(root/'data/cut_detector_crosscheck.json',{})
    ff_only=cut.get('ffmpeg_only_timestamps',[])
    cards=[]
    for idx,row in enumerate(rows):
        sid=row['shot_id']; f=byid.get(sid,{})
        ims={a:'data/references/'+row[a] for a in ANCHORS}
        for rel in ims.values():
            if not (root/rel).is_file(): raise FileNotFoundError(root/rel)
        if compute_flow:
            mi=sparse_2d_motion(root/ims['in'],root/ims['mid'])
            mo=sparse_2d_motion(root/ims['mid'],root/ims['out'])
        else:
            mi=mo={'status':'NOT_COMPUTED','motion':'UNDETERMINED'}
        start=float(row['start_sec']);end=start+float(row['duration_sec'])
        c=cont_byid.get(sid,{})
        current_face=faces[sid]
        issues=[]
        if idx and any(abs(start-x)<=.45 for x in ff_only):
            issues.append({'type':'SECOND_CUT_DETECTOR_DISAGREES_NEAR_START','severity':'REVIEW'})
        if float(row['duration_sec'])<.8:
            issues.append({'type':'VERY_SHORT_SHOT_CHECK_CUT_BOUNDARY','severity':'REVIEW'})
        if current_face:issues.append({'type':'POTENTIAL_FACE_OBSERVATIONS_REQUIRE_IDENTITY_REVIEW','severity':'REVIEW','count':len(current_face)})
        if mi.get('status')!='2D_ESTIMATE_AVAILABLE' or mo.get('status')!='2D_ESTIMATE_AVAILABLE':
            issues.append({'type':'CAMERA_MOTION_UNDETERMINED_IN_STATIC_TRIPLETS','severity':'CAUTION'})
        face_area=max((v['box_xywh_relative'][2]*v['box_xywh_relative'][3] for v in current_face),default=0.)
        shot_hypothesis='POSSIBLE_CLOSE_SUBJECT' if face_area>.07 else ('FACE_PRESENT_SIZE_UNCERTAIN' if current_face else 'UNDETERMINED')
        card={
          'shot_id':sid,'start_sec':round(start,3),'end_sec':round(end,3),'duration_sec':round(end-start,3),
          'target_frames':ims,'anchor_times_sec':[round(float(x),3) for x in f.get('anchor_sample_times',[])],
          'source_kind':'ACTUAL_UPLOADED_FILM_REFERENCE_NOT_AI_GENERATED',
          'cut_status':'UNVERIFIED_TWO_HEURISTIC_DETECTORS',
          'visual_group_proposal':f.get('visual_group_proposal','UNKNOWN'),
          'asset_observations':{'possible_face_boxes':len(current_face),
                'observations':[{'observation_id':v['observation_id'],'crop':v['crop'],
                  'location_relative':v['box_xywh_relative'],'identity':'UNKNOWN_UNVERIFIED'} for v in current_face],
                'character_master_locked':False,'costume_version_locked':False,'3d_set_layout_locked':False},
          'reference_technical':{'lighting':f.get('visual',{}).get('lighting_proxy'),
                'luminance':f.get('visual',{}).get('luminance'),
                'saturation':f.get('visual',{}).get('saturation'),
                'attention_xy_heuristic':f.get('visual',{}).get('visual_attention_proxy_xy'),
                'audio_rms':float(f.get('audio_rms',0)),
                'shot_size_hypothesis':shot_hypothesis,
                'reference_in_mid_color':c.get('in_to_mid',{}),
                'reference_mid_out_color':c.get('mid_to_out',{}),
                'audio_dialogue_transcription':'NOT_AVAILABLE',
                'confirmed_narrative_intent':'NOT_ANALYZED_OR_APPROVED'},
          'apparent_motion':{'in_to_mid':mi,'mid_to_out':mo},
          'issues':issues,
          'required_still_image_gates':['independent_source_separate_generation','character_identity','costume','period_props',
            'composition','setting','lighting','shot_semantic_function','camera_direction_2d','in_mid_out_continuity',
            'neighboring_shot_continuity','human_or_trustworthy_director_semantic_review'],
          'next_action':'INDEPENDENT_IMAGE_GENERATION_FOR_ALL_THREE_ANCHORS_AND_DIRECTOR_REVIEW',
          'verified_3d_camera_path':False,'verified_actor_choreography':False,
        }
        cards.append(card)
    return cards

def calibration(root=BASE,ids=None):
    """Instrument self-check on source-derived ARTIFICIAL degradation. NOT a replica generation.

    Simulates a color/brightness failure, and repairs histogram statistics only; does NOT
    feed these images into the director.sqlite3 candidates, hence cannot trigger signoff.
    """
    import director as d
    root=Path(root); dest=root/'output/evidence/calibration';dest.mkdir(parents=True,exist_ok=True)
    ids=ids or ['SH_00003','SH_00014','SH_00022']
    out=[]
    for shot in ids:
        ref=root/'data/references'/f'{shot}_mid.jpg'
        if not ref.is_file():continue
        a=capture(ref,640)
        # Color wash + contrast reduction: no geometry manipulation, no new content.
        corrupted=np.clip(a.astype(np.float32)*np.array([1.17,.66,.60],dtype=np.float32)[None,None,:]+18,0,255).astype(np.uint8)
        target_lab=cv2.cvtColor(a,cv2.COLOR_BGR2LAB).astype(np.float32)
        got_lab=cv2.cvtColor(corrupted,cv2.COLOR_BGR2LAB).astype(np.float32)
        m1=target_lab.mean((0,1));s1=target_lab.std((0,1))
        m2=got_lab.mean((0,1));s2=got_lab.std((0,1))
        restored=cv2.cvtColor(np.clip((got_lab-m2)*np.minimum(s1/np.maximum(s2,.1),3)+m1,0,255).astype(np.uint8),cv2.COLOR_LAB2BGR)
        corruption_file=dest/(shot+'_CORRUPTED_REFERENCE_DERIVED.jpg')
        restored_file=dest/(shot+'_STATISTICALLY_REPAIRED_REFERENCE_DERIVED.jpg')
        cv2.imwrite(str(corruption_file),corrupted,[cv2.IMWRITE_JPEG_QUALITY,90])
        cv2.imwrite(str(restored_file),restored,[cv2.IMWRITE_JPEG_QUALITY,90])
        before=d.score(ref,corruption_file);after=d.score(ref,restored_file)
        h,w=a.shape[:2]
        board=np.zeros((h+75,w*3,3),dtype=np.uint8)
        for i,img in enumerate([a,corrupted,restored]):board[48:48+h,i*w:(i+1)*w]=img
        for i,label in enumerate(['SOURCE / REFERENCE','ARTIFICIALLY DEGRADED','STATISTICAL COLOR REPAIR']):
            cv2.putText(board,label,(i*w+8,25),cv2.FONT_HERSHEY_SIMPLEX,.46,(240,240,240),1,cv2.LINE_AA)
        cv2.putText(board,'CALIBRATION ONLY - SOURCE-DERIVED PIXELS - NOT AI RECREATION',(10,h+66),cv2.FONT_HERSHEY_SIMPLEX,.56,(0,210,255),2,cv2.LINE_AA)
        boardpath=dest/(shot+'_QA_CALIBRATION.jpg');cv2.imwrite(str(boardpath),board,[cv2.IMWRITE_JPEG_QUALITY,91])
        out.append({'shot_id':shot,'source_reference':str(ref.relative_to(root)),
          'degraded':str(corruption_file.relative_to(root)),
          'repaired':str(restored_file.relative_to(root)),
          'comparison_board':str(boardpath.relative_to(root)),
          'before':{k:before[k] for k in ('ssim','edge_f1','palette_score','technical_score')},
          'after':{k:after[k] for k in ('ssim','edge_f1','palette_score','technical_score')},
          'technical_score_improved':bool(after['technical_score']>before['technical_score']),
          'grade':'CALIBRATION_ONLY_NOT_GENERATION_OR_SEMANTIC_QA',
          'warning':'Artificially damaged ORIGINAL film pixels; assesses image-QA machinery, not generative model or director ability.'})
    writej(root/'output/evidence/calibration_results.json',{'results':out,'origin':'REFERENCE_DERIVED_TEST_ONLY','AI_recreation':False})
    return out

def export_continuous_challenge(challenge, cards, root=BASE):
    """Actual-source contact sheet and 3-frame jobs for one contiguous 60-120 s challenge.
    Not an AI storyboard, shot boundary approval, or scene identification.
    """
    root=Path(root); out=root/'output/evidence';out.mkdir(parents=True,exist_ok=True)
    if not challenge or not challenge.get('shot_ids'):
        return {'status':'NO_VALID_CHALLENGE'}
    ids=set(challenge['shot_ids']);subset=[c for c in cards if c['shot_id'] in ids]
    width=1170; rowh=193;header=116
    sheet=Image.new('RGB',(width,header+rowh*len(subset)),(12,21,33))
    d=ImageDraw.Draw(sheet)
    try:
        font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',17)
        little=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',13)
    except OSError:
        font=ImageFont.load_default();little=font
    d.text((18,13),'CONTINUOUS CHALLENGE - REAL FILM REFERENCE / NOT AI GENERATED',fill='#eff3fb',font=font)
    d.text((18,47),f"{challenge['start_sec']:.1f}s - {challenge['end_sec']:.1f}s / {challenge['shot_count']} proposed shots / all IN-MID-OUT unapproved",fill='#f4c58e',font=font)
    d.text((18,76),'All boundaries, identities and director intent require review. Never use target images as generated output.',fill='#a4bbd3',font=little)
    jobs=[]
    available=root/'output/shot_work_orders.jsonl'
    if available.exists():
        for line in available.read_text(encoding='utf-8').splitlines():
            if not line.strip():continue
            item=json.loads(line)
            if item.get('shot_id') in ids:jobs.append(item)
    with (out/'challenge_work_orders.jsonl').open('w',encoding='utf-8') as f:
        for job in jobs:
            job['challenge_status']='REQUIRES_INDEPENDENT_AI_STILL_AND_SEMANTIC_REVIEW'
            f.write(json.dumps(job,ensure_ascii=False)+'\n')
    for i,card in enumerate(subset):
        y=header+i*rowh
        d.text((15,y+4),f"{card['shot_id']}    {card['start_sec']:.1f}s  + {card['duration_sec']:.1f}s",fill='#f1e0b2',font=little)
        for j,anch in enumerate(ANCHORS):
            a=Image.open(root/card['target_frames'][anch]).convert('RGB')
            a.thumbnail((376,158))
            xx=14+j*387;yy=y+30
            sheet.paste(a,(xx,yy))
            d.text((xx+6,yy+140),anch.upper()+' / REFERENCE ONLY',fill='#ffffff',font=little,stroke_width=1,stroke_fill='#050505')
        if i<len(subset)-1:d.line((14,y+rowh-3,width-14,y+rowh-3),fill='#314660',width=1)
    name=out/'challenge_reference_storyboard.jpg'
    sheet.save(name,quality=89,optimize=True)
    result={'status':'REFERENCE_ONLY_CHALLENGE_READY','contact_sheet':str(name.relative_to(root)),
      'work_orders':'output/evidence/challenge_work_orders.jsonl','work_order_count':len(jobs),
      'candidate_image_count':sum(c['production_state']['current_candidate_anchors'] for c in subset),
      'passed_shot_count':sum(c['production_state']['full_shot_approved'] for c in subset),
      'not_3d_or_ai_movie':True}
    writej(out/'challenge_acceptance.json',{**challenge,**result})
    return result

def render_dashboard(data,root=BASE):
    root=Path(root)
    slim={'summary':data['summary'],'challenge':data['challenge'],'cards':data['cards'],'calibration':data.get('calibration',[])}
    raw=json.dumps(slim,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    page=r'''<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>AI导演 | 原片证据与分镜验收工作台</title><style>
:root{color-scheme:dark;--bg:#0a1019;--panel:#101a29;--border:#263b50;--muted:#9cb0c7;--accent:#8cc7ff;--danger:#ffc17c}
*{box-sizing:border-box}body{margin:0;background:var(--bg);font:14px/1.6 system-ui,"Microsoft YaHei",sans-serif;color:#eef5ff}
header{padding:22px min(3vw,38px);border-bottom:1px solid var(--border);background:#111d2e}h1{margin:0 0 6px;font-size:24px}h2{font-size:18px;margin:0 0 8px}h3{font-size:15px;margin:0 0 10px}.muted{color:var(--muted)}.warning{color:var(--danger)}
a{color:var(--accent)}main{max-width:1550px;margin:auto;padding:20px}.stats{display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin-bottom:14px}.stat,.panel{border:1px solid var(--border);background:var(--panel);border-radius:12px;padding:15px}.stat strong{display:block;font-size:26px}.stat span{font-size:12px;color:var(--muted)}
.layout{display:grid;grid-template-columns:minmax(250px,330px) minmax(0,1fr);gap:16px;margin-top:16px}.list{height:min(75vh,740px);overflow-y:auto}.shot{width:100%;text-align:left;display:flex;justify-content:space-between;align-items:center;padding:10px;margin-bottom:5px;color:#dce8f6;background:#152539;border:1px solid transparent;border-radius:8px;cursor:pointer}.shot.sel{border-color:#8cc7ff;background:#1c3753}.shot:hover{background:#23344c}.shot small{display:block;color:#a5bbd0}
.frames{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin:12px 0}.frame{background:#090f17;border:1px solid #2c4158;border-radius:10px;overflow:hidden}.frame img{width:100%;aspect-ratio:1280/534;object-fit:contain;display:block}.frame div{padding:7px 10px;font-size:12px;color:#adc2d8}.cols{display:grid;grid-template-columns:1fr 1fr;gap:12px}pre{white-space:pre-wrap;word-break:break-word;color:#cbdbea;font:12px/1.6 ui-monospace,monospace;overflow:auto}ul{padding-left:18px}li{margin-bottom:3px}.pill{font-size:11px;background:#243b50;border-radius:20px;padding:4px 9px}input,select{border-radius:8px;border:1px solid #405672;background:#0c1725;color:#f3f7ff;padding:10px;width:100%}.tools{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:10px}.tools input{max-width:250px}.sample{border:1px solid #3a5b5c;background:#102429;padding:15px;border-radius:12px;margin:14px 0}.sample strong{color:#a5e4cc}.cal{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}.cal img{width:100%;border-radius:8px}.foot{margin-top:24px;padding:15px;border-top:1px solid var(--border);color:var(--muted)}
@media(max-width:950px){.stats{grid-template-columns:repeat(2,1fr)}.layout{grid-template-columns:1fr}.list{height:280px}.cols,.cal{grid-template-columns:1fr}}@media(max-width:560px){.frames{grid-template-columns:1fr}}
</style></head><body><header><h1>AI电影导演 · 真实分镜证据与自主迭代验收</h1><div class="muted">逐镜头证据、摄影二维线索、静态连续性、独立生成状态、返工门禁。所有数据来自实际上传视频与本地数据库。</div></header><main>
<div class="stats"><div class="stat"><strong id="shots">—</strong><span>候选镜头（待确认切点）</span></div><div class="stat"><strong id="anchors">—</strong><span>原片参考帧</span></div><div class="stat"><strong id="candidates">—</strong><span>有效独立生成分镜</span></div><div class="stat"><strong id="signed">—</strong><span>完整签核镜头</span></div><div class="stat"><strong>0</strong><span>经验证AI视频镜头</span></div></div>
<div class="sample"><h2>连续剧情验证挑战（自动选段，不是挑最好看的单帧）</h2><div id="challenge"></div><p><a href="output/evidence/challenge_reference_storyboard.jpg" id="challengeLink">查看连续挑战分镜长图（仅原片参考）</a></p><p class="warning">“参考帧完成”不等于“AI复刻完成”；不接付费视频模型也能验证静态生产工单，但真正独立重新绘制仍需图片模型。</p></div>
<div class="layout"><aside class="panel"><h2>镜头证据索引</h2><div class="tools"><input id="search" placeholder="镜头号、时间、视觉组" aria-label="搜索镜头"/><select id="filter"><option value="all">全部镜头</option><option value="challenge">挑战段落</option><option value="face">含人脸候选</option><option value="issue">需复核</option></select></div><div class="list" id="shotlist"></div></aside>
<section class="panel"><div id="detail"></div></section></div>
<section class="panel" style="margin-top:16px"><h2>校准测试（绝不算作AI复刻）</h2><p class="muted">从原片参考图人为制造光色偏差，再用统计分布进行安全修正。仅校验质检工具能发现、改善光色问题；不检验模型重画、人物表演或导演意图。</p><div class="cal" id="cal"></div></section>
<div class="foot">公开证据：<a href="output/evidence/director_evidence.json">完整镜头JSON数据</a> · <a href="output/FINAL_ACCEPTANCE.html">八阶段验收</a> · <a href="PROJECT_STORYBOARD_REPORT.html">全部参考分镜</a><br/>源片未确认版权与演员肖像许可；图片用于本地技术对照。3D机位、身份、对话含义、导演意图均未被虚假标成已确认。</div>
</main><script id="evidence" type="application/json">__DATA__</script><script>
const D=JSON.parse(document.getElementById('evidence').textContent);const E=id=>document.getElementById(id);
const esc=s=>String(s??'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
const media=p=>location.protocol==='file:'?p:'/file?path='+encodeURIComponent(p);
if(location.protocol!=='file:'){document.getElementById('challengeLink').href=media('output/evidence/challenge_reference_storyboard.jpg');document.querySelectorAll('.foot a').forEach(a=>{let href=a.getAttribute('href');if(href==='output/evidence/director_evidence.json')a.href='/evidence-data';else if(href==='output/FINAL_ACCEPTANCE.html')a.href='/acceptance';else if(href==='PROJECT_STORYBOARD_REPORT.html')a.href='/longform';});}
const sec=v=>{let m=Math.floor(v/60),s=(v%60).toFixed(1);return `${m}:${s.padStart(4,'0')}`};
E('shots').textContent=D.summary.shot_candidates;E('anchors').textContent=D.summary.reference_anchors;E('candidates').textContent=D.summary.current_generated_candidates;E('signed').textContent=D.summary.fully_approved_shots;
let active=D.challenge?.shot_ids?.[0]??D.cards[0]?.shot_id;
let CH=new Set(D.challenge?.shot_ids||[]);
const ch=D.challenge;E('challenge').innerHTML=ch?.shot_ids?`<strong>${sec(ch.start_sec)} – ${sec(ch.end_sec)}</strong> · ${ch.duration_seconds}秒 · ${ch.shot_count}个镜头 · ${ch.visual_group_proposals}个视觉分组候选 · ${ch.possible_face_box_count}处人脸观测。<br><span class="muted">需要独立重绘 ${ch.shot_count*3} 张IN/MID/OUT，再进行静态及跨镜头验收。</span>`:'没有符合60–120秒约束的连续候选段落';
function renderList(){let q=E('search').value.trim().toLowerCase(),f=E('filter').value;E('shotlist').innerHTML=D.cards.filter(s=>(f==='all'||f==='challenge'&&CH.has(s.shot_id)||f==='face'&&s.asset_observations.possible_face_boxes||f==='issue'&&s.issues.length)&&(`${s.shot_id} ${s.visual_group_proposal} ${sec(s.start_sec)}`.toLowerCase().includes(q))).map(s=>`<button class="shot ${s.shot_id===active?'sel':''}" onclick="selectShot('${esc(s.shot_id)}')"><span><b>${esc(s.shot_id)}</b><small>${sec(s.start_sec)} · ${s.duration_sec.toFixed(1)}秒 · ${esc(s.visual_group_proposal)}</small></span><span class="pill">${s.production_state.current_candidate_anchors}/3 AI图</span></button>`).join('')||'<p class="muted">无符合条件的镜头</p>'}
function selectShot(id){active=id;renderList();const s=D.cards.find(x=>x.shot_id===id);if(!s)return;
let miss=s.required_still_image_gates.map(x=>`<li>${esc(x)}</li>`).join('');
let cards=['in','mid','out'].map((a,i)=>`<div class="frame"><img loading="lazy" src="${media(s.target_frames[a])}" alt="${esc(id)} ${a}原片参考帧"/><div>${a.toUpperCase()} · ${sec(s.anchor_times_sec[i]??s.start_sec)} · 原片参考 / 非AI生成</div></div>`).join('');
let keys=(m)=>`${esc(m.motion||'—')} · ${esc(m.status)} · RANSAC ${m.inlier_ratio??'不可靠'}`;
E('detail').innerHTML=`<div class="tools"><h2 style="margin:0">${esc(s.shot_id)} · ${sec(s.start_sec)}–${sec(s.end_sec)}</h2><span class="pill">${CH.has(s.shot_id)?'连续挑战镜头':'其他参考镜头'}</span><span class="pill">镜头边界待复核</span></div>
<p class="warning">验收门禁：${esc(s.production_state.gate)}；${s.production_state.current_candidate_anchors}/3张有效AI候选，${s.production_state.signed_off_anchors}/3张签核。</p><div class="frames">${cards}</div>
<div class="cols"><div><h3>已测量的参考证据（非导演结论）</h3><ul><li>亮度：${s.reference_technical.luminance??'?'} · 饱和度：${s.reference_technical.saturation??'?'}</li><li>照明线索：${esc(s.reference_technical.lighting)}</li><li>视觉注意力代理位置：${esc(JSON.stringify(s.reference_technical.attention_xy_heuristic))}</li><li>音轨RMS：${s.reference_technical.audio_rms}（不等于台词转写）</li><li>人脸检测候选：${s.asset_observations.possible_face_boxes}（不等于已识别角色）</li><li>景别猜测：${esc(s.reference_technical.shot_size_hypothesis)}</li><li>视觉组提案：${esc(s.visual_group_proposal)}</li></ul></div>
<div><h3>运动与连续性证据</h3><ul><li>IN→MID：${keys(s.apparent_motion.in_to_mid)}</li><li>MID→OUT：${keys(s.apparent_motion.mid_to_out)}</li><li>原片两对图像颜色变化：${esc(s.reference_technical.reference_in_mid_color.histogram_bhattacharyya??'未测')} / ${esc(s.reference_technical.reference_mid_out_color.histogram_bhattacharyya??'未测')}</li><li>新生成图的连续性：${s.production_state.generated_continuity_pairs_measured}/2 对有效测量</li><li>3D机位：未重建 · 演员精确动作：未核验</li></ul></div></div>
<h3>自动复核工单</h3>${s.issues.length?`<ul>${s.issues.map(x=>`<li class="warning">${esc(x.type)} — ${esc(x.severity)}</li>`).join('')}</ul>`:'<p class="muted">参考技术检查无额外异常；不代表导演验收通过。</p>'}
<h3>进入视频生成前必须完成</h3><div class="cols"><ul>${miss}</ul><div><p class="warning">下一步：${esc(s.next_action)}</p><p class="muted">未确认人物身份、服化道和情节意图时，静态分镜不能被自动签核。</p><a href="${location.protocol==='file:'?'output/index.html':'/'}">进入交互工作台导入/重绘候选</a></div></div>`}
E('search').addEventListener('input',renderList);E('filter').addEventListener('change',renderList);window.selectShot=selectShot;
renderList();selectShot(active);
E('cal').innerHTML=D.calibration.map(x=>`<div><img loading="lazy" src="${media(x.comparison_board)}" alt="${esc(x.shot_id)}人工破坏与恢复对比"/><h3>${esc(x.shot_id)} 光色校准</h3><p class="muted">技术分 ${x.before.technical_score} → ${x.after.technical_score} · ${x.technical_score_improved?'算法检测到改善':'未检测到改善'} · 非AI生成</p></div>`).join('');
</script></body></html>'''
    page=page.replace('__DATA__',raw)
    target=root/'DIRECTOR_EVIDENCE.html';target.write_text(page,encoding='utf-8')
    return str(target)

def run(root=BASE,do_calibration=True,compute_flow=True):
    root=Path(root);cards=prepare_reference_evidence(root,compute_flow)
    # This module's dynamic DB bridge uses the product root from director.py;
    # it is intentionally called only for its own installed project directory.
    if root.resolve()==BASE.resolve():
        candidate_evidence(None,cards)
    else:
        for card in cards:
            card['production_state']={'current_candidate_anchors':0,'signed_off_anchors':0,'full_shot_approved':False,
                                      'generated_continuity_pairs_measured':0,'gate':'BLOCKED_UNVERIFIED'}
    accepted=sum(bool(s['production_state']['full_shot_approved']) for s in cards)
    candidate=sum(s['production_state']['current_candidate_anchors'] for s in cards)
    calib=calibration(root) if do_calibration and root.resolve()==BASE.resolve() else []
    challenge=challenge_selection(cards)
    report={'schema_version':'1.1-evidence','source_manifest':'data/project_manifest.json',
      'source_sha256':readj(root/'data/project_manifest.json',{}).get('source_sha256'),
      'generated_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'),
      'summary':{'shot_candidates':len(cards),'reference_anchors':len(cards)*3,
         'current_generated_candidates':candidate,'fully_approved_shots':accepted,
         'generated_continuity_pairs_measured':sum(c['production_state']['generated_continuity_pairs_measured'] for c in cards),
         'motion_pairs_2d_computed':sum(m['status']=='2D_ESTIMATE_AVAILABLE' for c in cards for m in c['apparent_motion'].values()),
         'possible_face_observations_not_identity':sum(c['asset_observations']['possible_face_boxes'] for c in cards),
         'verified_actor_identities':0,'verified_3d_scene_models':0,'verified_ai_video_shots':0,
         'film_recreation_accepted':False,'no_paid_video_model_calls':True},
      'challenge':challenge,'cards':cards,'calibration':calib,
      'acceptance_boundary':{'software_pipeline':'EXERCISED','reference_video':'ACTUAL_USER_UPLOAD',
         'independent_generated_content':'ONLY_DATABASE_VERIFIED_CANDIDATES',
         'director_semantics':'NOT_VALIDATED_FROM_2D_STATS',
         '3d_blocking':'NOT_MEASURED',
         'film_directing_goal_achieved':False}}
    challenge_assets=export_continuous_challenge(challenge,cards,root)
    report['challenge_assets']=challenge_assets
    writej(root/'output/evidence/director_evidence.json',report)
    with (root/'output/evidence/shot_director_cards.jsonl').open('w',encoding='utf-8') as out:
        for card in cards:out.write(json.dumps(card,ensure_ascii=False)+'\n')
    render_dashboard(report,root)
    return {'report':str(root/'output/evidence/director_evidence.json'),
      'dashboard':str(root/'DIRECTOR_EVIDENCE.html'),**report['summary'],
      'challenge':{k:v for k,v in (challenge or {}).items() if k not in ('shot_ids','gates')},
      'calibration_cases':len(calib),'challenge_assets':challenge_assets}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--skip-calibration',action='store_true')
    parser.add_argument('--skip-flow',action='store_true')
    args=parser.parse_args()
    print(json.dumps(run(do_calibration=not args.skip_calibration,compute_flow=not args.skip_flow),ensure_ascii=False,indent=2))
