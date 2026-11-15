#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Offline full-length shot/asset pre-production, image-first. No generative/video API.

Heuristic boundaries, visual clusters, faces and camera motion MUST be reviewed. The
source frames are targets, not AI reconstructions. Idempotent manifest rebuild.
"""
from __future__ import annotations
import argparse, collections, csv, hashlib, io, json, math, os, shutil, subprocess, sys, time
from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

BASE=Path(__file__).resolve().parent
DATA=BASE/'data'; REF=DATA/'references'; OUT=BASE/'output'; ROOT=DATA/'source_video.mp4'
FPS_SAMPLE=5; RAW_W=384; RAW_H=160

def dump(o,p):
    Path(p).parent.mkdir(parents=True,exist_ok=True)
    Path(p).write_text(json.dumps(o,ensure_ascii=False,indent=2),encoding='utf-8')

def hashfile(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def ffprobe(p):
    b=subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration,size:stream=codec_type,codec_name,width,height,r_frame_rate','-of','json',str(p)])
    d=json.loads(b);d['seconds']=float(d['format']['duration']);return d

def decode_samples(video, sample_fps=5,width=384):
    info=ffprobe(video); original_width=next(x['width'] for x in info['streams'] if x.get('codec_type')=='video')
    original_height=next(x['height'] for x in info['streams'] if x.get('codec_type')=='video')
    height=round(round(original_height*width/original_width)/2)*2
    size=width*height*3
    cmd=['ffmpeg','-nostdin','-loglevel','error','-threads','2','-i',str(video),'-vf',f'fps={sample_fps},scale={width}:{height}:flags=area','-pix_fmt','bgr24','-f','rawvideo','pipe:1']
    process=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,bufsize=size*2)
    desc=[]; jpg=[]; prev=None; i=0;last_update=-1
    while True:
        raw=process.stdout.read(size)
        if not raw or len(raw)<size:break
        f=np.frombuffer(raw,np.uint8).reshape(height,width,3)
        thumb=cv2.resize(f,(192,80),interpolation=cv2.INTER_AREA)
        hsv=cv2.cvtColor(thumb,cv2.COLOR_BGR2HSV)
        h=cv2.calcHist([hsv],[0,1],None,[24,8],[0,180,0,256]);cv2.normalize(h,h)
        gray=cv2.cvtColor(thumb,cv2.COLOR_BGR2GRAY)
        # Low-light & subtitle overlays create false positives; boundary confidence remains a suggestion.
        pix=float(np.mean(cv2.absdiff(thumb,prev[0])))/255 if prev is not None else 0
        hs=float(cv2.compareHist(h,prev[1],cv2.HISTCMP_BHATTACHARYYA)) if prev is not None else 0
        desc.append((i/sample_fps,hs,pix,float(np.mean(gray))/255,float(np.std(gray)),h.flatten().astype(np.float32)))
        jpg.append(cv2.imencode('.jpg',f,[cv2.IMWRITE_JPEG_QUALITY,82])[1].tobytes())
        prev=(thumb.copy(),h);i+=1
        current=int(i/sample_fps//60)
        if current!=last_update and current%2==0:
            print(f'ANALYZING {i/sample_fps:.0f}s / {info["seconds"]:.0f}s | sampled frames {i}',flush=True);last_update=current
    process.stdout.close(); err=process.stderr.read().decode('utf-8','replace')[-1500:]; rc=process.wait()
    if rc!=0 or len(jpg)==0:raise RuntimeError('FFmpeg failed: '+err)
    return desc,jpg,info,(width,height)

def propose_cuts(desc, duration,min_shot=.48,cap=2500):
    arr=np.array([(x[1],x[2]) for x in desc],dtype=np.float32)
    # Pair of temporal changes -- a single-frame flash/rapid camera shake can produce false cuts.
    scores=arr[:,0]*.72 + arr[:,1]*.28
    cuts=[];last=0.
    for i in range(2,len(desc)-2):
        hist,pix=arr[i]
        s=float(scores[i]);surround=scores[i-2:i+3]
        if s<max(surround)-1e-5:continue
        if not ((hist>=.42 and pix>=.10) or (hist>=.30 and pix>=.22) or hist>=.63):continue
        t=desc[i][0]
        if t-last<min_shot or t>duration-.15:continue
        cuts.append({'time_sec':round(t,3),'histogram_jump':round(float(hist),3),'pixel_jump':round(float(pix),3),'confidence_heuristic':round(s,3),'verified':False})
        last=t
        if len(cuts)>=cap:break
    boundaries=[0.]+[c['time_sec'] for c in cuts]+[duration]
    pairs=[(a,b) for a,b in zip(boundaries,boundaries[1:]) if b-a>=.1]
    return cuts,pairs,{'median_hist_change':round(float(np.median(arr[:,0])),4),'p95_hist_change':round(float(np.percentile(arr[:,0],95)),4)}

def nearest(sample_t, n):return min(n-1,max(0,round(sample_t*FPS_SAMPLE)))

def image_stats(fr):
    h,w=fr.shape[:2];small=cv2.resize(fr,(256,round(h*256/w)))
    gray=cv2.cvtColor(small,cv2.COLOR_BGR2GRAY)
    lab=cv2.cvtColor(small,cv2.COLOR_BGR2LAB)
    hsv=cv2.cvtColor(small,cv2.COLOR_BGR2HSV)
    edges=cv2.Canny(gray,70,130)
    # Energy centroid approximate composition attention, not a real semantic subject detector.
    e=cv2.GaussianBlur(edges.astype(np.float32),(0,0),5)
    total=float(e.sum());
    if total>1:
        ys,xs=np.indices(e.shape)
        centroid=[round(float((xs*e).sum()/total/e.shape[1]),3),round(float((ys*e).sum()/total/e.shape[0]),3)]
    else:centroid=[.5,.5]
    return {'luminance':round(float(np.mean(gray)/255),3),
      'contrast':round(float(np.std(gray)/128),3),
      'saturation':round(float(np.mean(hsv[:,:,1])/255),3),
      'edge_density':round(float(np.mean(edges>0)),3),
      'visual_attention_proxy_xy':centroid,
      'lab_mean':[round(float(v),1) for v in np.mean(lab,axis=(0,1))],
      'lighting_proxy':'dark' if np.mean(gray)<75 else ('bright' if np.mean(gray)>160 else 'mid-key')}

def motion_proxy(frames):
    # sparse optical flow does NOT establish camera motion separately from actor motion.
    motions=[]
    for x,y in zip(frames,frames[1:]):
        a=cv2.cvtColor(x,cv2.COLOR_BGR2GRAY);b=cv2.cvtColor(y,cv2.COLOR_BGR2GRAY)
        pts=cv2.goodFeaturesToTrack(a,maxCorners=130,qualityLevel=.018,minDistance=6)
        if pts is None or len(pts)<9:continue
        nxt,st,_=cv2.calcOpticalFlowPyrLK(a,b,pts,None)
        if nxt is None:continue
        d=(nxt[st.flatten()>0]-pts[st.flatten()>0]).reshape(-1,2)
        if len(d)<9:continue
        v=np.median(d,axis=0); motions.append(v)
    if not motions:return {'label':'UNDETERMINED','flow_median_xy':[0,0], 'warning':'2D motion is NOT calibrated 3D camera movement'}
    v=np.mean(motions,axis=0);speed=float(np.linalg.norm(v))
    label='LOW_FRAME_DISPLACEMENT' if speed<2 else ('RIGHTWARD_VISUAL_FLOW' if abs(v[0])>abs(v[1]) and v[0]>0 else 'LEFTWARD_VISUAL_FLOW' if abs(v[0])>abs(v[1]) else 'DOWNWARD_VISUAL_FLOW' if v[1]>0 else 'UPWARD_VISUAL_FLOW')
    return {'label':label,'flow_median_xy':[round(float(q),2) for q in v], 'warning':'Flow mixes foreground actor motion, camera movement, parallax and possible transition'}

def extract_audio_envelope(video,duration):
    cmd=['ffmpeg','-nostdin','-v','error','-i',str(video),'-vn','-ac','1','-ar','8000','-f','s16le','pipe:1']
    p=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    audio=np.frombuffer(p.communicate()[0],dtype=np.int16).astype(np.float32)/32768.
    if p.returncode!=0 or len(audio)==0:return {'available':False,'note':'No readable audio decoded'},np.zeros(max(1,math.ceil(duration*2)),np.float32)
    step=4000
    rms=np.array([float(np.sqrt(np.mean(audio[i:i+step]**2))) for i in range(0,len(audio),step)],dtype=np.float32)
    return {'available':True,'sample_rate':8000,'window_seconds':.5,'windows':len(rms),'global_rms':round(float(np.mean(rms)),5),'warning':'Audio energy is not speech recognition or dialogue/music separation'},rms

def contact_sheets(rows, max_per_page=24):
    # 4 columns / 6 rows; reference middle frame; no source frames are AI candidates.
    OUTPUT=OUT/'contact_sheets'; OUTPUT.mkdir(parents=True,exist_ok=True)
    for batch in range(math.ceil(len(rows)/max_per_page)):
        seq=rows[batch*max_per_page:(batch+1)*max_per_page]
        tile_w=312;tile_h=176;hgap=8;vgap=8
        img=Image.new('RGB',(4*(tile_w+hgap)+hgap,6*(tile_h+vgap)+vgap),(15,20,29));d=ImageDraw.Draw(img)
        for i,s in enumerate(seq):
            x=hgap+(i%4)*(tile_w+hgap);y=vgap+(i//4)*(tile_h+vgap)
            f=REF/s['mid'];pic=Image.open(f).convert('RGB')
            pic.thumbnail((tile_w,tile_h-24)); img.paste(pic,(x,y+(tile_h-24-pic.height)//2))
            d.text((x+3,y+tile_h-21),f"{s['shot_id']}   {float(s['start_sec']):.1f}s  +{float(s['duration_sec']):.1f}s",fill=(234,237,243))
        img.save(OUTPUT/f'page_{batch+1:03}.jpg',quality=85)
    return math.ceil(len(rows)/max_per_page)

def ingest(video=None, force=False, sample_fps=5, min_shot=.48):
    global FPS_SAMPLE
    FPS_SAMPLE=sample_fps
    video=Path(video or ROOT).resolve(); assert video.is_file(),str(video)
    DATA.mkdir(exist_ok=True);REF.mkdir(exist_ok=True);OUT.mkdir(exist_ok=True)
    if (DATA/'shots_source.csv').exists():
        if not force:
            raise RuntimeError('Already imported. Use --force only to rebuild an unchanged project; do not overwrite a reviewed project.')
        db=DATA/'director.sqlite3'
        if db.exists():
            import sqlite3
            with sqlite3.connect(db) as c:
                if c.execute('SELECT COUNT(*) FROM attempts').fetchone()[0]>0:
                    raise RuntimeError('Cannot overwrite a project with candidate history; start a NEW project folder instead.')
        # Existing task identities are never silently rewritten by rerun.
        if db.exists():db.unlink()
    print('PHASE 1: Decode actual footage and compute shot candidate boundaries',flush=True)
    desc,jpg,info,(w,h)=decode_samples(video,sample_fps=sample_fps)
    duration=info['seconds'];cuts,pairs,dist=propose_cuts(desc,duration,min_shot=min_shot)
    print(f'Detected {len(pairs)} tentative shots in {duration:.1f}s, sample rate {sample_fps}fps',flush=True)
    # save 3 reference anchor frames from decoded samples (exact sample-nearest, not original native res)
    rows=[]; features=[]
    for k,(start,end) in enumerate(pairs,1):
        shot=f'SH_{k:05}'
        sels=[('in',start+.08*(end-start)),('mid',(start+end)/2),('out',start+.92*(end-start))]
        indices=[nearest(t,len(jpg)) for _,t in sels]
        refs={}
        for (anc,t),idx in zip(sels,indices):
            f=REF/f'{shot}_{anc}.jpg'
            f.write_bytes(jpg[idx]);refs[anc]=f.name
        frames=[cv2.imdecode(np.frombuffer(jpg[idx],np.uint8),1) for idx in indices]
        mid_stats=image_stats(frames[1]);motion=motion_proxy(frames)
        rows.append({'shot_id':shot,'start_sec':round(start,3),'duration_sec':round(end-start,3),
          'cut_status':'AUTO_SUGGESTED_UNVERIFIED','in':refs['in'],'mid':refs['mid'],'out':refs['out']})
        features.append({'shot_id':shot,'start_sec':round(start,3),'end_sec':round(end,3),'duration_sec':round(end-start,3),
          'reference_images':refs,'anchor_sample_times':[round(desc[i][0],3) for i in indices],
          'visual':mid_stats,'optical_flow':motion,
          'director_intent':'REQUIRES_HUMAN_OR_VISION_MODEL_INTERPRETATION',
          'character_identity':'UNKNOWN_UNVERIFIED',
          'camera_path_3d':'NOT_INFERRED', 'boundary_status':'UNVERIFIED_HEURISTIC',
          'storyboard_generation':'PENDING_INDEPENDENT_AI_GENERATION'})
    with (DATA/'shots_source.csv').open('w',encoding='utf-8',newline='') as f:
        cw=csv.DictWriter(f,list(rows[0].keys()));cw.writeheader();cw.writerows(rows)
    print('PHASE 2: Analyze existing source audio and visual groupings',flush=True)
    ain,rms=extract_audio_envelope(video,duration)
    # sequential visual cluster candidates, not equivalent to edited dramatic scenes.
    clusters=[];grp=[];lastlab=None
    for feat in features:
        start=feat['start_sec'];lab=np.array(feat['visual']['lab_mean'])
        shock=float(np.linalg.norm(lab-lastlab)) if lastlab is not None else 0
        if grp and (shock>45 or len(grp)>=9):
            clusters.append(grp);grp=[]
        grp.append(feat['shot_id']);feat['visual_group_proposal']=f'VG_{len(clusters)+1:03}'
        a=math.floor(start*2);b=min(len(rms),max(a+1,math.ceil(feat['end_sec']*2)))
        feat['audio_rms']=round(float(np.mean(rms[a:b])) if a<len(rms) else 0,5)
        lastlab=lab
    if grp:clusters.append(grp)
    proposed=[{'id':f'VG_{j+1:03}','shot_ids':ids,'status':'VISUAL_GROUP_HEURISTIC_NOT_SCENE_VERIFIED'} for j,ids in enumerate(clusters)]
    dump({'features':features,'visual_group_proposals':proposed,'audio':ain},DATA/'shot_features.json')
    dump({'source':str(video.relative_to(BASE)) if BASE in video.parents else str(video),'source_sha256':hashfile(video),
      'source_scope':'UPLOADED_EXCERPT_NOT_FULL_THEATRICAL_FEATURE','duration_seconds':round(duration,3),
      'fps_original':next((x['r_frame_rate'] for x in info['streams'] if x.get('codec_type')=='video'),'unknown'),
      'resolution_original':next((f"{x['width']}x{x['height']}" for x in info['streams'] if x.get('codec_type')=='video'),'unknown'),
      'shot_count':len(rows),'reference_anchor_count':len(rows)*3,'sample_fps':sample_fps,
      'reference_resolution':f'{w}x{h}','boundaries':cuts,'distance_distribution':dist,
      'visual_group_proposals':len(proposed),'audio_summary':ain,
      'claims':{'independently_generated_AI_storyboards':0,'AI_generated_video_shots':0,'director_verified_shots':0},
      'notes':['Boundaries and visual groups are hypotheses, NOT verified cuts/scenes.',
        'Reference JPEGs are low-resolution samples of the uploaded source, NOT AI generation.',
        'Video model is not required to inspect storyboard composition, identity, costume, setting and still-frame continuity.',
        'Accurate camera movement, facial acting and audio/dialogue synchronization require additional models/verification.']},DATA/'project_manifest.json')
    page_count=contact_sheets(rows)
    # initialize existing production database and export task cards without faking production.
    import director
    boot=director.bootstrap()  # fast per-film task cards come from production_cli export-jobs
    print('PHASE 3: Build human-readable director dashboard',flush=True)
    from longform_dashboard import build_dashboard
    report=build_dashboard(BASE)
    return {'duration':round(duration,2),'shots':len(rows),'reference_cards':len(rows)*3,
      'contact_sheet_pages':page_count,'visual_cluster_proposals':len(clusters),
      'audio_windows':ain.get('windows',0),'database_rows':boot['database_rows'],
      'production_tasks':len(rows)*3,'ai_storyboards_produced':0,
      'result':'REFERENCE_PREPRODUCTION_CREATED_NOT_AI_RECONSTRUCTION',
      'dashboard':str(report)}

if __name__=='__main__':
    pa=argparse.ArgumentParser();pa.add_argument('--video',default=str(ROOT));pa.add_argument('--force',action='store_true');pa.add_argument('--fps',type=int,default=5)
    args=pa.parse_args(); print(json.dumps(ingest(args.video,args.force,args.fps),ensure_ascii=False,indent=2))
