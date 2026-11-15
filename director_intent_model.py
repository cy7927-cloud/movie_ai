#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Optional LOCAL visual director analyst for reference IN/MID/OUT triplets.

Runs only with an already configured localhost Ollama vision model, never invokes
paid video generation. All results are DRAFT inferences, never verified actor ID,
3D camera reconstruction, or shot approval. External URLs are refused.
"""
import argparse,base64,csv,json,sys,time,urllib.parse,urllib.request
from pathlib import Path
BASE=Path(__file__).resolve().parent
ALLOWED=('127.0.0.1','localhost')
SCHEMA_KEYS=('visible_subjects','visible_actions','blocking_foreground_background','shot_size_hypothesis',
             'camera_direction_hypothesis','art_and_costume_observations','lighting_and_palette',
             'narrative_intent_hypothesis','uncertainties','confidence')
SYSTEM='''You are a cinematography/director analysis assistant. You are given three REAL reference movie images at IN, MID and OUT times of one candidate shot. Only describe VISIBLE facts, not identities, film lore, names, events outside these frames, or unseen camera paths. Be cautious with narrative purpose. Return only one JSON object with fields: visible_subjects (list of objective descriptions), visible_actions (list), blocking_foreground_background (string), shot_size_hypothesis (string), camera_direction_hypothesis (string; say unknown when not inferrable), art_and_costume_observations (list), lighting_and_palette (string), narrative_intent_hypothesis (string explicitly labeled hypothesis), uncertainties (list), confidence (number 0..1). Do NOT claim confirmed actor identities. Do NOT equate these photos with new AI-generated footage.'''

def local_url(url):
    parsed=urllib.parse.urlparse(url)
    if parsed.scheme!='http' or parsed.hostname not in ALLOWED or parsed.username or parsed.password or parsed.path not in ('','/','/api/chat'):
        raise ValueError('Vision server must be a local HTTP Ollama endpoint, e.g. http://127.0.0.1:11434')
    return f'http://{parsed.hostname}:{parsed.port or 11434}/api/chat'

def request_model(images,model='llava',url='http://127.0.0.1:11434',timeout=180):
    endpoint=local_url(url)
    payload={'model':model,'stream':False,'format':'json','messages':[{'role':'system','content':SYSTEM},
      {'role':'user','content':'Analyze this film shot using all three consecutive reference anchor images (IN, MID, OUT). They are NOT output generated frames.','images':[base64.b64encode(Path(p).read_bytes()).decode('ascii') for p in images]}]}
    request=urllib.request.Request(endpoint,data=json.dumps(payload).encode('utf-8'),headers={'Content-Type':'application/json'},method='POST')
    with urllib.request.urlopen(request,timeout=timeout) as response:
        raw=json.loads(response.read().decode('utf-8'))
    txt=raw.get('message',{}).get('content','')
    if not isinstance(txt,str):raise ValueError('Ollama returned no text response')
    try:
        obj=json.loads(txt)
    except Exception as e:raise ValueError('Ollama response was not valid JSON') from e
    if not isinstance(obj,dict):raise ValueError('Expected JSON object')
    for key in SCHEMA_KEYS:
        if key not in obj:raise ValueError('Missing review field '+key)
    obj['confidence']=max(0.,min(1.,float(obj['confidence'])))
    for k in ('visible_subjects','visible_actions','art_and_costume_observations','uncertainties'):
        if not isinstance(obj[k],list):raise ValueError(f'{k} must be list')
        obj[k]=[str(item)[:300] for item in obj[k][:20]]
    for k in ('blocking_foreground_background','shot_size_hypothesis','camera_direction_hypothesis','lighting_and_palette','narrative_intent_hypothesis'):
        obj[k]=str(obj[k])[:800]
    obj.update({'status':'UNVERIFIED_VISION_MODEL_DRAFT','identity_verified':False,'camera_3d_verified':False,
      'source':'ACTUAL_REFERENCE_IMAGES_NOT_GENERATED'})
    return obj

def run(shot=None,limit=0,model='llava',url='http://127.0.0.1:11434',apply=False):
    rows=list(csv.DictReader((BASE/'data/shots_source.csv').open(encoding='utf-8')))
    selected=[r for r in rows if not shot or r['shot_id']==shot]
    if limit:selected=selected[:limit]
    if not selected:raise ValueError('Shot ID not found')
    # no network call without explicit command execution
    results=[]
    out=BASE/'data/director_intent_drafts.jsonl'
    import director as d
    for row in selected:
        imgs=[BASE/'data/references'/row[k] for k in ('in','mid','out')]
        review=request_model(imgs,model=model,url=url)
        rec={'shot_id':row['shot_id'],'model':model,'review':review,
             'reference_sha256':[d.sha(p) for p in imgs],'timestamp':d.utc()}
        with out.open('a',encoding='utf-8') as f:f.write(json.dumps(rec,ensure_ascii=False)+'\n')
        if apply:
            # Every edit invalidates old evaluations via content-addressed spec hashes.
            with d.connect() as c:
                for anchor in d.ANCHORS:
                    tid=row['shot_id']+':'+anchor
                    task=c.execute('SELECT * FROM tasks WHERE id=?',(tid,)).fetchone()
                    if task is None:continue
                    cons=d.read_json(task['constraints'],{})
                    cons['draft_director_analysis']={**review,'explicit_status':'NOT_APPROVED'}
                    intent='AI视觉模型推断（未核验）：'+review['narrative_intent_hypothesis']
                    d.rebase_spec(c,tid,intent,cons)
        results.append({'shot_id':row['shot_id'],'confidence_unverified':review['confidence'],'applied':apply,'approved':False})
    return {'processed':len(results),'draft_file':str(out),'results':results,'director_signoff_created':False}

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--shot');ap.add_argument('--limit',type=int,default=1)
    ap.add_argument('--model',default='llava');ap.add_argument('--url',default='http://127.0.0.1:11434');ap.add_argument('--apply',action='store_true')
    args=ap.parse_args()
    print(json.dumps(run(args.shot,args.limit,args.model,args.url,args.apply),ensure_ascii=False,indent=2))
