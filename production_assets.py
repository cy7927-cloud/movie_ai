#!/usr/bin/env python3
"""Offline asset *observations*: face boxes and location-look proposals, not identity recognition."""
import csv,json,math
from pathlib import Path
from PIL import Image,ImageDraw
import cv2,numpy as np
ROOT=Path(__file__).resolve().parent

def run():
    rows=list(csv.DictReader((ROOT/'data/shots_source.csv').open(encoding='utf-8')))
    features=json.loads((ROOT/'data/shot_features.json').read_text(encoding='utf-8'))
    face=cv2.CascadeClassifier(cv2.data.haarcascades+'haarcascade_frontalface_default.xml')
    observations=[];out=ROOT/'data/observed_assets';out.mkdir(parents=True,exist_ok=True)
    facesdir=out/'face_observations';facesdir.mkdir(exist_ok=True)
    for row in rows:
        image=cv2.imread(str(ROOT/'data/references'/row['mid']))
        if image is None:continue
        h,w=image.shape[:2];thumb=cv2.resize(image,(min(640,w),round(h*min(640,w)/w)))
        gh,gw=thumb.shape[:2]
        g=cv2.cvtColor(thumb,cv2.COLOR_BGR2GRAY)
        coords=face.detectMultiScale(g,scaleFactor=1.08,minNeighbors=5,minSize=(28,28))
        # Haar frontal faces are observations only, no cross-shot identity inference.
        for x,y,ww,hh in sorted(coords,key=lambda q:-q[2]*q[3])[:4]:
            rr=[int(x*w/gw),int(y*h/gh),int(ww*w/gw),int(hh*h/gh)]
            xx,yy,bw,bh=rr
            pad=int(max(bw,bh)*.22)
            roi=image[max(0,yy-pad):min(h,yy+bh+pad),max(0,xx-pad):min(w,xx+bw+pad)]
            if roi.size==0:continue
            oid=f'OBS_{len(observations)+1:04}'
            filename=f'{oid}.jpg';cv2.imwrite(str(facesdir/filename),roi)
            observations.append({'observation_id':oid,'shot_id':row['shot_id'],'frame_anchor':'MID',
             'box_xywh_relative':[round(xx/w,3),round(yy/h,3),round(bw/w,3),round(bh/h,3)],
             'crop':f'data/observed_assets/face_observations/{filename}',
             'identity':'UNKNOWN_UNVERIFIED','classifier':'OPENCV_HAAR_FRONTAL_FACE_POSSIBLE_FALSE_POSITIVE'})
    groups=features['visual_group_proposals']
    doc={'asset_bible_status':'PARTIAL_OBSERVATION_INDEX_REQUIRES_IDENTITY_AND_SCENE_REVIEW',
      'source_shots':len(rows),'possible_face_observations':len(observations),
      'face_observations':observations,'visual_location_proposals':groups,
      'character_master_assets':[],'verified_costume_states':[],
      'verified_prop_models':[],'3d_scene_geometry':[],
      'warning':'Face detections are not cast identities; visual groups are not confirmed locations, and no 3D assets were reconstructed.'}
    (ROOT/'data/asset_bible_observations.json').write_text(json.dumps(doc,ensure_ascii=False,indent=2),encoding='utf-8')
    # Contact card, preserve unsupported identity information unknown.
    if observations:
        cw=840;tilew=105;tileh=136;count=min(120,len(observations));rowsn=math.ceil(count/8)
        sheet=Image.new('RGB',(cw,rowsn*tileh),(20,27,37));dr=ImageDraw.Draw(sheet)
        for i,ob in enumerate(observations[:count]):
            pic=Image.open(ROOT/ob['crop']).convert('RGB');pic.thumbnail((tilew-4,tileh-28))
            x=(i%8)*tilew;y=(i//8)*tileh
            sheet.paste(pic,(x+(tilew-pic.width)//2,y))
            dr.text((x+2,y+tileh-23),ob['observation_id'],fill='#e9ecef');dr.text((x+2,y+tileh-11),ob['shot_id'],fill='#bbc9d9')
        sheet.save(ROOT/'output/人脸观测_非身份识别.jpg',quality=89)
    return {'shots':len(rows),'face_observations_unverified':len(observations),
      'visual_group_proposals_unverified':len(groups),'verified_character_assets':0,'3d_models':0}

if __name__=='__main__':print(json.dumps(run(),ensure_ascii=False,indent=2))
