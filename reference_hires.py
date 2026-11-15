#!/usr/bin/env python3
"""Replace sample-size reference stills with original-resolution source decodes.

Intended only BEFORE candidate generation. If any candidate already exists, do not
rewrite reference images; modifications invalidate downstream approvals and need rebase.
"""
import argparse,csv,json,hashlib,sqlite3
from pathlib import Path
import cv2

ROOT=Path(__file__).resolve().parent

def run(force=False):
    rows=list(csv.DictReader((ROOT/'data/shots_source.csv').open(encoding='utf-8')))
    db=ROOT/'data/director.sqlite3'
    if db.exists():
        c=sqlite3.connect(db)
        existing=c.execute('SELECT COUNT(*) FROM attempts').fetchone()[0]
        c.close()
        if existing>0:raise RuntimeError(f'Refusing to change reference frames: {existing} existing attempts would become stale')
    meta=json.loads((ROOT/'data/shot_features.json').read_text(encoding='utf-8'))
    cap=cv2.VideoCapture(str(ROOT/'data/source_video.mp4'))
    if not cap.isOpened():raise RuntimeError('Source video cannot be opened')
    n=0
    for row,feat in zip(rows,meta['features']):
        for anchor,t in zip(('in','mid','out'),feat['anchor_sample_times']):
            cap.set(cv2.CAP_PROP_POS_MSEC,float(t)*1000)
            ok,fr=cap.read()
            if not ok:raise RuntimeError(f'Cannot decode {row["shot_id"]}:{anchor} at {t}s')
            target=ROOT/'data/references'/row[anchor]
            if not cv2.imwrite(str(target),fr,[cv2.IMWRITE_JPEG_QUALITY,90]):raise RuntimeError(str(target))
            n+=1
    cap.release()
    manifest=ROOT/'data/project_manifest.json';ob=json.loads(manifest.read_text(encoding='utf-8'))
    ob['reference_resolution']=f'{fr.shape[1]}x{fr.shape[0]}'
    ob['reference_upscaled']=False
    ob['reference_mode']='DECODED_ORIGINAL_FULL_RESOLUTION_NEAREST_SAMPLED_TIMESTAMP'
    manifest.write_text(json.dumps(ob,ensure_ascii=False,indent=2),encoding='utf-8')
    if db.exists():
        c=sqlite3.connect(db)
        for row in rows:
            for anchor in ('in','mid','out'):
                path=ROOT/'data/references'/row[anchor]
                digest=hashlib.sha256(path.read_bytes()).hexdigest()
                c.execute('UPDATE tasks SET reference_sha=? WHERE id=?',(digest,f'{row["shot_id"]}:{anchor.upper()}'))
        c.commit();c.close()
    return {'replaced_reference_frames':n,'resolution':ob['reference_resolution'],
            'candidate_images':0,'verification':'ALL_REFERENCE_NOT_AI_GENERATED'}

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--force',action='store_true');args=ap.parse_args()
    print(json.dumps(run(args.force),ensure_ascii=False,indent=2))
