#!/usr/bin/env python3
"""Image-first film production gates: cross-anchor continuity, batch rework, audited export.

All operations are local and free. Reference previews are visibly watermarked.
This does not assert semantic character identity or directorial equivalence.
"""
import argparse,collections,hashlib,html,json,subprocess
from pathlib import Path
import cv2,numpy as np
import director as d


def best_valid_attempt(c,task):
    rows=c.execute('SELECT * FROM attempts WHERE task_id=? ORDER BY id',(task['id'],)).fetchall()
    live=[a for a in rows if a['reference_sha']==task['reference_sha'] and a['spec_sha']==d.task_spec_sha(task)
          and (d.BASE/a['candidate']).is_file() and d.sha(d.BASE/a['candidate'])==a['candidate_sha']]
    if not live:return None
    return max(live,key=lambda a:d.read_json(a['metrics'],{}).get('technical_score',0))


def color_vector(path):
    im=d.load_image(path,maxw=320)
    lab=cv2.cvtColor(im,cv2.COLOR_BGR2LAB)
    return np.mean(lab,axis=(0,1)).astype(float)


def shot_review(c,shot):
    tasks=c.execute('SELECT * FROM tasks WHERE shot_id=? ORDER BY CASE anchor WHEN "IN" THEN 0 WHEN "MID" THEN 1 ELSE 2 END',(shot,)).fetchall()
    if not tasks:return None
    entries=[];pairs=[];ready=0
    for t in tasks:
        a=best_valid_attempt(c,t)
        status=t['status']
        issue=[]
        if d.sha(d.BASE/t['reference'])!=t['reference_sha']:
            issue.append('REFERENCE_CHANGED; all prior evaluations are invalid');status='BLOCKED_REFERENCE_CHANGED'
        if a is None:
            issue.append('NO_CURRENT_GENERATED_CANDIDATE' if not c.execute('SELECT 1 FROM attempts WHERE task_id=?',(t['id'],)).fetchone() else 'STALE_OR_MODIFIED_CANDIDATE')
        if t['status']!='STORYBOARD_APPROVED':issue.append('DIRECTOR_SIGNOFF_NOT_COMPLETE')
        # Even when UI says APPROVED, require a matching immutable event for the current version.
        if t['status']=='STORYBOARD_APPROVED':
            ev=c.execute("SELECT payload FROM events WHERE task_id=? AND type='DIRECTOR_SIGNOFF' ORDER BY id DESC LIMIT 1",(t['id'],)).fetchone()
            signature=d.read_json(ev['payload'],{}) if ev else {}
            if a is None or signature.get('candidate_sha256')!=a['candidate_sha'] or signature.get('reference_sha256')!=t['reference_sha']:
                issue.append('SIGNOFF_EVIDENCE_STALE');status='BLOCKED_SIGNOFF_STALE'
            else:ready+=1
        entries.append({'task_id':t['id'],'anchor':t['anchor'],'status':status,
              'reference':t['reference'],'candidate':a['candidate'] if a else None,
              'provider':a['provider'] if a else None,
              'technical_score':d.read_json(a['metrics'],{}).get('technical_score') if a else None,
              'issues':issue,'version_count':c.execute('SELECT count(*) FROM attempts WHERE task_id=?',(t['id'],)).fetchone()[0]})
    for first,second in zip(entries,entries[1:]):
        if not first['candidate'] or not second['candidate']:
            pairs.append({'anchors':[first['anchor'],second['anchor']],'status':'INSUFFICIENT_GENERATED_FRAMES'})
            continue
        t1=d.BASE/first['reference'];t2=d.BASE/second['reference']
        c1=d.BASE/first['candidate'];c2=d.BASE/second['candidate']
        reference_shift=np.linalg.norm(color_vector(t2)-color_vector(t1))
        candidate_shift=np.linalg.norm(color_vector(c2)-color_vector(c1))
        deviation=abs(reference_shift-candidate_shift)
        pairs.append({'anchors':[first['anchor'],second['anchor']],'reference_lab_shift':round(float(reference_shift),2),
           'candidate_lab_shift':round(float(candidate_shift),2),'deviation_lab':round(float(deviation),2),
           'status':'COLOR_CHANGE_REVIEW' if deviation>16 else 'COLOR_HEURISTIC_OK',
           'warning':'Lab global color comparison cannot validate identity, action or spatial continuity'})
    return {'shot_id':shot,'anchors':entries,'cross_anchor_checks':pairs,
       'approved_anchors':ready,'is_fully_approved':ready==3,
       'status':'APPROVED_FOR_DOWNSTREAM' if ready==3 else 'STORYBOARD_INCOMPLETE'}


def project_audit():
    d.bootstrap()
    with d.connect() as c:
        shots=[r[0] for r in c.execute('SELECT DISTINCT shot_id FROM tasks ORDER BY shot_id').fetchall()]
        allreview=[shot_review(c,s) for s in shots]
        stats={'shots':len(shots),'frames':sum(len(s['anchors']) for s in allreview),
           'shots_fully_approved':sum(s['is_fully_approved'] for s in allreview),
           'anchors_with_candidates':sum(a['candidate'] is not None for s in allreview for a in s['anchors']),
           'anchors_pending_director_signoff':sum(a['status']!='STORYBOARD_APPROVED' for s in allreview for a in s['anchors']),
           'cross_anchor_pairs_measured':sum('deviation_lab' in p for s in allreview for p in s['cross_anchor_checks']),
           'actual_verified_model_generated_video':0,
           'scope':'Image-first storyboard quality; visual-semantic actor and performance equivalence not automatically proven'}
        out={'project':d.BASE.name,'stats':stats,'shots':allreview,
             'truth_in_reporting':'No automatic claim of film recreation; raw reference media and generated media are distinct.'}
        target=d.OUT/'production_audit.json';target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
        return out


def batch_local_refine(limit=0,rounds=2):
    """Perform real, limited local image rework only where a current candidate exists."""
    d.bootstrap();out=[]
    with d.connect() as c:
        eligible=[]
        for task in c.execute("SELECT * FROM tasks ORDER BY start_sec,CASE anchor WHEN 'IN' THEN 0 WHEN 'MID' THEN 1 ELSE 2 END").fetchall():
            if task['status']=='STORYBOARD_APPROVED':continue
            if best_valid_attempt(c,task) is None:continue
            eligible.append(task['id'])
        for tid in eligible[:limit or len(eligible)]:
            try:
                attempts=d.safe_local_refinement(c,tid,min(3,max(1,rounds)))
                out.append({'task_id':tid,'new_attempts':len(attempts),'result': 'MODIFIED_NOT_SEMANTIC_APPROVED' if attempts else 'NO_SAFE_IMPROVEMENT'})
            except Exception as e:out.append({'task_id':tid,'result':'ERROR','error':str(e)[:300]})
    return out


def export_cut(manifest=None,output=None,reference_previs=False,max_seconds=0):
    """Only fully signed-off images can be exported as generated-still animatic.
    Reference-only opt-in mode includes explicit permanent watermark, NEVER film output.
    """
    audit=manifest or project_audit()
    full=audit['shots'];valid=[s for s in full if s['is_fully_approved']]
    if not reference_previs and len(valid)!=len(full):
        info={'result':'BLOCKED','reason':'All three image anchors for all shots require current director signoff.',
          'eligible_shots':len(valid),'total_shots':len(full),'missing_shots':[s['shot_id'] for s in full if not s['is_fully_approved']]}
        (d.OUT/'export_gate.json').write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding='utf-8')
        return info
    allshots=full if reference_previs else valid
    output=Path(output) if output else d.OUT/('REFERENCE_previs_NOT_AI_MOVIE.mp4' if reference_previs else 'APPROVED_STORYBOARD_ANIMATIC.mp4')
    output.parent.mkdir(parents=True,exist_ok=True)
    writer=cv2.VideoWriter(str(output),cv2.VideoWriter_fourcc(*'mp4v'),6,(640,360))
    if not writer.isOpened():raise RuntimeError('MP4 writer unavailable')
    count=0
    try:
        for s in allshots:
            duration=0
            with d.connect() as c:
                row=c.execute('SELECT duration FROM tasks WHERE id=?',(s['shot_id']+':MID',)).fetchone()
                duration=float(row['duration'] if row else 2)
            samples=max(3,int(round(duration*6)))
            for j in range(samples):
                if max_seconds and count/6>=max_seconds:break
                anch=s['anchors'][min(2,int(j/samples*3))]
                file=d.BASE/(anch['reference'] if reference_previs else anch['candidate'])
                source=d.load_image(file,640)
                sh,sw=source.shape[:2]
                scale=min(640/max(1,sw),360/max(1,sh))
                fw,fh=max(1,round(sw*scale)),max(1,round(sh*scale))
                img=np.zeros((360,640,3),dtype=np.uint8)
                imagefit=cv2.resize(source,(fw,fh),interpolation=cv2.INTER_AREA)
                xx=(640-fw)//2;yy=(360-fh)//2
                img[yy:yy+fh,xx:xx+fw]=imagefit
                if reference_previs:
                    cv2.rectangle(img,(0,0),(640,34),(0,0,0),-1)
                    cv2.putText(img,'REFERENCE ONLY - NOT AI GENERATED',(10,24),cv2.FONT_HERSHEY_SIMPLEX,.60,(30,240,250),2)
                else:
                    cv2.rectangle(img,(0,0),(640,26),(0,0,0),-1)
                    cv2.putText(img,'APPROVED STILL ANIMATIC - NOT VIDEO MODEL',(8,19),cv2.FONT_HERSHEY_SIMPLEX,.46,(240,240,240),1)
                writer.write(img);count+=1
            if max_seconds and count/6>=max_seconds:break
    finally:writer.release()
    return {'result':'PREVIS_EXPORTED','path':str(output),'seconds':round(count/6,2),'mode':'REFERENCE_ONLY' if reference_previs else 'APPROVED_STILL_ANIMATIC','is_ai_video':False}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    subs=p.add_subparsers(dest='command',required=True)
    subs.add_parser('audit')
    b=subs.add_parser('batch-local');b.add_argument('--limit',type=int,default=5);b.add_argument('--steps',type=int,default=2)
    s=subs.add_parser('animatic');s.add_argument('--reference-previs',action='store_true');s.add_argument('--max-seconds',type=int,default=0)
    args=p.parse_args()
    if args.command=='audit':out=project_audit();print(json.dumps(out['stats'],ensure_ascii=False,indent=2))
    elif args.command=='batch-local':print(json.dumps(batch_local_refine(args.limit,args.steps),ensure_ascii=False,indent=2));project_audit()
    elif args.command=='animatic':print(json.dumps(export_cut(reference_previs=args.reference_previs,max_seconds=args.max_seconds),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
