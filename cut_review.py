#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Two-detector cut-disagreement evidence and human-review log, local/offline.

Two algorithms agreeing is NOT ground truth. A saved review only annotates
boundaries and NEVER silently rewrites historical shot IDs or signoffs.
"""
import argparse,csv,datetime,hashlib,html,json,re,subprocess,math
from pathlib import Path
import cv2,numpy as np
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parent

def readj(p,default=None):
    p=Path(p)
    return json.loads(p.read_text(encoding='utf-8')) if p.is_file() else default

def writej(path,x):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')

def ff_scene_times(path):
    # Read full timestamps already independently measured by FFmpeg, or detect on new film.
    cached=ROOT/'data/cut_detector_ffmpeg_times.json'
    meta=readj(ROOT/'data/project_manifest.json',{})
    old=readj(cached)
    if old and old.get('source_sha256')==meta.get('source_sha256') and old.get('threshold')==.24:
        return old['timestamps_sec']
    args=['ffmpeg','-nostdin','-hide_banner','-threads','2','-i',str(path),'-vf','select=gt(scene\\,0.24),showinfo','-an','-f','null','-']
    # Actual ffmpeg may format filter escaping differently; use fixed -vf argument.
    args[args.index('-vf')+1]="select='gt(scene,0.24)',showinfo"
    p=subprocess.run(args,capture_output=True,text=True,timeout=300)
    if p.returncode!=0:raise RuntimeError('FFmpeg cut detection failed: '+p.stderr[-1000:])
    times=sorted({round(float(t),3) for t in re.findall(r'pts_time:([0-9.]+)',p.stderr)})
    writej(cached,{'source_sha256':meta.get('source_sha256'),'threshold':.24,
      'detector':'FFmpeg scene-select full native frame rate', 'timestamps_sec':times,
      'status':'HEURISTIC_UNVERIFIED'})
    return times

def compare_cuts(main,alternative,tolerance=.45):
    # Deterministic one-to-one matching. A clustered flash cannot match several boundaries.
    used=set();matches=[];only_a=[]
    for a in main:
        eligible=[(abs(b-a),j) for j,b in enumerate(alternative) if j not in used and abs(b-a)<=tolerance]
        if eligible:
            diff,j=min(eligible);used.add(j);matches.append({'main_sec':a,'ffmpeg_sec':alternative[j],'delta_sec':round(diff,3)})
        else:only_a.append(a)
    return matches,only_a,[b for j,b in enumerate(alternative) if j not in used]

def frame_at(cap,sec,final_sec):
    cap.set(cv2.CAP_PROP_POS_MSEC,max(0.,min(final_sec-.05,sec))*1000)
    ok,frame=cap.read()
    if not ok:return None
    h,w=frame.shape[:2]
    neww=340
    return cv2.resize(frame,(neww,int(round(h*neww/w))),interpolation=cv2.INTER_AREA)

def local_difference(a,b):
    if a is None or b is None:return {'status':'FRAME_READ_FAILED'}
    hb=cv2.cvtColor(b,cv2.COLOR_BGR2HSV);ha=cv2.cvtColor(a,cv2.COLOR_BGR2HSV)
    h1=cv2.calcHist([ha],[0,1],None,[24,12],[0,180,0,256]);h2=cv2.calcHist([hb],[0,1],None,[24,12],[0,180,0,256])
    cv2.normalize(h1,h1);cv2.normalize(h2,h2)
    jump=float(cv2.compareHist(h1,h2,cv2.HISTCMP_BHATTACHARYYA))
    g1=cv2.cvtColor(a,cv2.COLOR_BGR2GRAY);g2=cv2.cvtColor(b,cv2.COLOR_BGR2GRAY)
    from skimage.metrics import structural_similarity
    sim=float(structural_similarity(g1,g2,data_range=255))
    return {'status':'FRAME_PAIR_OBSERVATION_ONLY','hsv_histogram_jump':round(jump,4),
      'ssim_across_boundary':round(sim,4),'warning':'Fades, flashes and camera movement can mimic hard cuts; not editorial ground truth'}

def make_sheet(items,output):
    # 2 frames per suspect, 3 suspects x 4 rows, hard captions in English to avoid font dependencies.
    tilew=680;tileh=190
    font=ImageFont.load_default()
    for start in range(0,len(items),12):
        group=items[start:start+12]
        page=Image.new('RGB',(tilew*3,tileh*4),(9,18,30))
        dr=ImageDraw.Draw(page)
        for j,it in enumerate(group):
            x=(j%3)*tilew;y=(j//3)*tileh
            if it.get('_before') is not None:
                for k,img in enumerate((it['_before'],it['_after'])):
                    z=Image.fromarray(cv2.cvtColor(img,cv2.COLOR_BGR2RGB));z.thumbnail((335,145))
                    page.paste(z,(x+k*340,y+20))
            txt=f"{it['type']}  t={it['time_sec']:.2f}s  hist={it['observation'].get('hsv_histogram_jump','NA')}"
            dr.text((x+5,y+3),txt,fill='#fbd6a2',font=font)
            dr.text((x+6,y+168),'BEFORE (-0.16s)                       AFTER (+0.16s)   /   REVIEW CUT',fill='#afc2d9',font=font)
        dest=output/f'cut_disagreements_page_{start//12+1:02}.jpg'
        page.save(dest,quality=85)
        for it in group:it['sheet']=str(dest.relative_to(ROOT))

def run():
    meta=readj(ROOT/'data/project_manifest.json',{})
    rows=list(csv.DictReader((ROOT/'data/shots_source.csv').open(encoding='utf-8-sig')))
    main=[round(float(r['start_sec']),3) for r in rows[1:]]
    ff=ff_scene_times(ROOT/'data/source_video.mp4')
    matches,main_only,ff_only=compare_cuts(main,ff)
    out=ROOT/'output/cut_review';out.mkdir(parents=True,exist_ok=True)
    video=ROOT/'data/source_video.mp4'
    cap=cv2.VideoCapture(str(video))
    if not cap.isOpened():raise RuntimeError('Could not open source video for cut review')
    probes=[]
    try:
        for typ,seq in [('MAIN_ONLY',main_only),('FFMPEG_ONLY',ff_only)]:
            for ts in seq:
                before=frame_at(cap,ts-.16,meta.get('duration_seconds',1))
                after=frame_at(cap,ts+.16,meta.get('duration_seconds',1))
                obs=local_difference(before,after)
                probes.append({'id':f'{typ}_{ts:.3f}','time_sec':ts,'type':typ,'observation':obs,
                  'review_state':'NOT_REVIEWED','is_true_cut':None,'_before':before,'_after':after})
    finally:cap.release()
    probes=sorted(probes,key=lambda x:x['time_sec'])
    make_sheet(probes,out)
    for p in probes:p.pop('_before',None);p.pop('_after',None)
    decisions=readj(ROOT/'data/cut_review_decisions.json',{})
    if decisions.get('source_sha256')!=meta.get('source_sha256'):decisions={'source_sha256':meta.get('source_sha256'),'reviews':{}}
    for item in probes:
        if item['id'] in decisions['reviews']:
            item['review_state']=decisions['reviews'][item['id']]['decision']
    report={'source_sha256':meta.get('source_sha256'),
      'source_duration_sec':meta.get('duration_seconds'),
      'detectors':'Main 5fps HSV vs native-frame FFmpeg scene select(0.24)',
      'tolerance_sec':.45,'main_cut_count':len(main),'ffmpeg_cut_count':len(ff),
      'two_detector_matches':len(matches),'main_only':len(main_only),'ffmpeg_only':len(ff_only),
      'disagreement_count':len(probes),'reviewed_count':sum(x['review_state'] in ('CONFIRMED_CUT','REJECTED_FALSE_POSITIVE') for x in probes),
      'confirmed_editorial_cuts':0,
      'matched':matches,'disputed':probes,
      'warnings':['Two heuristics agreeing is NOT human-editorial ground truth.',
        'Before/after thumbnails may include camera motion or dissolve rather than true cut.',
        'A cut decision does not rewrite the existing timeline until a deliberate re-ingest and invalidation.']}
    writej(out/'cut_disagreements.json',report)
    render_html(report)
    return {k:report[k] for k in ('main_cut_count','ffmpeg_cut_count','two_detector_matches','main_only','ffmpeg_only','disagreement_count','reviewed_count')}

def mark(suspect_id,decision,reviewer,reason):
    if decision not in ('CONFIRMED_CUT','REJECTED_FALSE_POSITIVE','UNDECIDED'):
        raise ValueError('Invalid review decision')
    if not reviewer.strip() or not reason.strip():raise ValueError('Reviewer and reason must be nonempty')
    report=readj(ROOT/'output/cut_review/cut_disagreements.json',{})
    if suspect_id not in {p['id'] for p in report.get('disputed',[])}:raise KeyError('Unknown disagreement ID')
    meta=readj(ROOT/'data/project_manifest.json',{})
    path=ROOT/'data/cut_review_decisions.json'
    decisions=readj(path,{})
    if decisions.get('source_sha256')!=meta.get('source_sha256'):
        decisions={'source_sha256':meta.get('source_sha256'),'reviews':{}}
    decisions['reviews'][suspect_id]={'decision':decision,'reviewer':reviewer[:120],
       'reason':reason[:2000],'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')}
    writej(path,decisions)
    for item in report.get('disputed',[]):
        if item['id']==suspect_id:item['review_state']=decision
    report['reviewed_count']=sum(z['review_state'] in ('CONFIRMED_CUT','REJECTED_FALSE_POSITIVE') for z in report.get('disputed',[]))
    writej(ROOT/'output/cut_review/cut_disagreements.json',report)
    render_html(report)
    return {'id':suspect_id,'decision':decision,'saved':True,
            'note':'Reviewed status is an annotation; shot boundaries and already-generated cards are unchanged.'}

def render_html(report):
    rows=[]
    for r in report['disputed']:
        rows.append('<tr><td>'+html.escape(r['id'])+'</td><td>'+str(r['time_sec'])+'s</td><td>'+html.escape(r['type'])+'</td>'+
                    '<td>'+str(r['observation'].get('hsv_histogram_jump','?'))+'</td><td>'+html.escape(r['review_state'])+'</td><td><a href="'+html.escape(Path(r['sheet']).name)+'">比对图</a></td></tr>')
    body='''<!DOCTYPE html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>切镜分歧复核</title><style>body{background:#0d1622;color:#e5effb;font:14px/1.65 system-ui;margin:auto;max-width:1200px;padding:20px}a{color:#92c9f2}.panel{background:#17263b;border:1px solid #37516b;border-radius:10px;padding:17px;margin:10px 0}table{border-collapse:collapse;width:100%}td,th{border-bottom:1px solid #34495d;padding:7px;text-align:left}b{font-size:20px}img{width:100%;margin:10px 0;border-radius:8px}</style><h1>电影切镜分歧 · 真实双算法审查</h1><p>主算法__MAIN__、第二算法__FF__个候选切点；在0.45秒内匹配 <b>__MATCH__</b>处，分歧 <b>__DIFF__</b>处。无人工签核时不是最终镜头表。</p><div class="panel"><p>每个候选切点取前后各0.16秒画面进行对比。镜头运动、闪白、渐隐和快速演员运动均可能导致误判；算法不自动调整影片时间轴。</p><p>复核操作可使用命令：<code>python cut_review.py mark --id MAIN_ONLY_... --decision CONFIRMED_CUT --reviewer 导演 --reason 说明</code>。</p></div><h2>分歧汇总</h2><table><tr><th>编号</th><th>时间码</th><th>来自</th><th>色彩突变量</th><th>复核状态</th><th>对照</th></tr>__ROWS__</table><h2>分镜前后帧对照</h2>__IMGS__<p>参考素材用于复核，不是AI生成，也不代表已经完成复刻。</p></html>'''
    sheets=sorted(set(Path(r['sheet']).name for r in report['disputed']))
    imgs=''.join(f'<img loading="lazy" src="{html.escape(s)}" alt="分歧切镜前后对比"/>' for s in sheets)
    for a,b in {'__MAIN__':str(report['main_cut_count']),'__FF__':str(report['ffmpeg_cut_count']),'__MATCH__':str(report['two_detector_matches']),
                '__DIFF__':str(report['disagreement_count']),'__ROWS__':'\n'.join(rows),'__IMGS__':imgs}.items():body=body.replace(a,b)
    options=''.join(f'<option value="{html.escape(r["id"])}">{html.escape(r["id"])} — {r["time_sec"]}s</option>' for r in report['disputed'])
    controls='''<div class="panel"><h2>保存人工切镜复核（仅在本地服务中可用）</h2><p>此操作仅保存判断依据；不会默默改变镜头ID或复刻候选。</p>
      <label>分歧切点：<select id="cid">__OPTIONS__</select></label>
      <label>结论：<select id="dec"><option value="UNDECIDED">尚待确认</option><option value="CONFIRMED_CUT">确认切镜</option><option value="REJECTED_FALSE_POSITIVE">驳回误判</option></select></label>
      <p><input id="reviewer" placeholder="复核人（必填）"/><input id="reason" placeholder="依据说明（必填）"/></p>
      <button onclick="submitReview()">保存当前切镜复核</button> <span id="reviewstatus"></span></div>'''.replace('__OPTIONS__',options)
    body=body.replace('<h2>分歧汇总</h2>',controls+'<h2>分歧汇总</h2>')
    script="""<script>
      const reviewToken='__CSRF__';
      if(location.protocol==='file:'){document.querySelectorAll('button').forEach(b=>b.disabled=true);}
      else {
        document.querySelectorAll('a[href^="cut_disagreements_page_"]').forEach(a=>a.href='/cut-image?name='+encodeURIComponent(a.getAttribute('href')));
        document.querySelectorAll('img[src^="cut_disagreements_page_"]').forEach(im=>im.src='/cut-image?name='+encodeURIComponent(im.getAttribute('src')));
      }
      async function submitReview(){
        let res=await fetch('/api/cut-decision',{method:'POST',headers:{'X-Director-Token':reviewToken,'Content-Type':'application/json'},body:JSON.stringify({id:document.getElementById('cid').value,decision:document.getElementById('dec').value,reviewer:document.getElementById('reviewer').value,reason:document.getElementById('reason').value})});
        let j=await res.json();document.getElementById('reviewstatus').textContent=res.ok?'已存复核意见：'+j.decision:'失败：'+(j.error||res.status);
      }</script>"""
    body=body.replace('</html>',script+'</html>')
    (ROOT/'output/cut_review/index.html').write_text(body,encoding='utf-8')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='cmd',required=True)
    sub.add_parser('run')
    z=sub.add_parser('mark');z.add_argument('--id',required=True);z.add_argument('--decision',required=True);z.add_argument('--reviewer',required=True);z.add_argument('--reason',required=True)
    args=p.parse_args()
    print(json.dumps(run() if args.cmd=='run' else mark(args.id,args.decision,args.reviewer,args.reason),ensure_ascii=False,indent=2))
