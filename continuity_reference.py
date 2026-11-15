#!/usr/bin/env python3
"""Reference chronology/continuity technical baselines only; not identity or 3D certification."""
import csv,json
from pathlib import Path
import cv2,numpy as np
ROOT=Path(__file__).resolve().parent

def extract():
    rows=list(csv.DictReader((ROOT/'data/shots_source.csv').open(encoding='utf-8')))
    hist=[];features=[]
    for row in rows:
        aa=[]
        for a in ('in','mid','out'):
            im=cv2.imread(str(ROOT/'data/references'/row[a]));im=cv2.resize(im,(256,106),interpolation=cv2.INTER_AREA)
            hsv=cv2.cvtColor(im,cv2.COLOR_BGR2HSV)
            h=cv2.calcHist([hsv],[0,1],None,[16,12],[0,180,0,256]);cv2.normalize(h,h)
            aa.append({'lab':np.mean(cv2.cvtColor(im,cv2.COLOR_BGR2LAB).astype(np.float32),axis=(0,1)), 'hist':h})
        hist.append(aa)
    continuity=[];across=[]
    def pair(x,y):
        lab=float(np.linalg.norm(x['lab']-y['lab']))
        hs=float(cv2.compareHist(x['hist'],y['hist'],cv2.HISTCMP_BHATTACHARYYA))
        return {'lab_mean_distance':round(lab,3),'histogram_bhattacharyya':round(hs,3),
          'review':'HIGH_VISUAL_SHIFT' if hs>.48 else 'NO_LARGE_COLOR_HISTOGRAM_SHIFT',
          'caution':'Cannot confirm facial identity, action continuity, camera or scene topology'}
    for row,aa in zip(rows,hist):
        continuity.append({'shot':row['shot_id'],'in_to_mid':pair(aa[0],aa[1]),'mid_to_out':pair(aa[1],aa[2])})
    for i in range(len(rows)-1):
        across.append({'from':rows[i]['shot_id'],'to':rows[i+1]['shot_id'],**pair(hist[i][2],hist[i+1][0])})
    doc={'image_only_reference_baseline':True,'intra_shot_pairs':len(continuity)*2,'adjacent_shot_pairs':len(across),
      'reconstructed_content_continuity_status':'NOT_MEASURABLE_WITHOUT_GENERATED_CANDIDATES',
      'intra_shot_reference':continuity,'adjacent_shot_reference':across}
    (ROOT/'data/continuity_reference.json').write_text(json.dumps(doc,ensure_ascii=False,indent=2),encoding='utf-8')
    return {'intra_shot_reference_pairs':len(continuity)*2,'adjacent_shot_reference_pairs':len(across),
      'recreated_continuity_passed_pairs':0}
if __name__=='__main__':print(json.dumps(extract(),ensure_ascii=False,indent=2))
