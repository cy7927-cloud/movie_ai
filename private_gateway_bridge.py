#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bring-your-own OpenAI-compatible VLM gateway for film-director research.

No secret is stored in code or output. Real source stills are submitted only by
explicit 'vision' / 'batch' commands. Reproduction sign-off is NEVER automatic.
"""
from __future__ import annotations
import argparse
import datetime as dt
import html
import json
import os
from pathlib import Path
import re
import sys
import time
import urllib.parse
import urllib.request
import urllib.error

import cloud_director_inference as cloud
import director_model_hub as hub

ROOT=Path(__file__).resolve().parent
DEFAULT_BASE='https://behavioral-thanksgiving-cheapest-cooling.trycloudflare.com/v1'
DEFAULT_MODEL='qwen3vl-8b'
RESULTS=ROOT/'output'/'gateway_director_lab'
KEY_ENV='DIRECTOR_GATEWAY_API_KEY'

class GatewayFailure(RuntimeError):
    pass

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        raise GatewayFailure('Redirect refused, so the API credential was not forwarded')

OPENER=urllib.request.build_opener(NoRedirect())

def base_url():
    value=os.environ.get('DIRECTOR_GATEWAY_BASE_URL',DEFAULT_BASE).strip().rstrip('/')
    p=urllib.parse.urlsplit(value)
    if p.scheme != 'https' or not p.hostname or p.username or p.password or p.query or p.fragment or p.path != '/v1':
        raise GatewayFailure('Gateway Base URL must be https://<host>/v1 (no credentials, query, or fragment)')
    return value

def model_id():
    return os.environ.get('DIRECTOR_GATEWAY_MODEL',DEFAULT_MODEL).strip()

def secret():
    s=os.environ.get(KEY_ENV,'').strip()
    if not s: raise GatewayFailure(f'Missing {KEY_ENV}: no authenticated request was sent')
    return s

def api_json(method,url,body=None,auth=False,timeout=180,opener=None):
    # URLs are derived from the explicitly configured gateway base, never from
    # model output or user-controlled film metadata.
    if timeout < 1 or timeout > 600: raise GatewayFailure('Timeout out of supported range')
    body_bytes=json.dumps(body,ensure_ascii=False).encode('utf-8') if body is not None else None
    headers={'Accept':'application/json','User-Agent':'FilmDirector-PrivateGateway/1.0'}
    if body_bytes is not None: headers['Content-Type']='application/json'
    if auth:headers['Authorization']='Bearer '+secret()
    req=urllib.request.Request(url,data=body_bytes,headers=headers,method=method)
    try:
        with (opener or OPENER).open(req,timeout=timeout) as r:
            if not 200<=r.status<300: raise GatewayFailure('Gateway HTTP '+str(r.status))
            if 'json' not in r.headers.get('Content-Type','application/json'):
                raise GatewayFailure('Non-JSON gateway response')
            raw=r.read(2_000_000)
        return json.loads(raw.decode('utf-8'))
    except urllib.error.HTTPError as e:
        raise GatewayFailure('Gateway HTTP '+str(e.code)) from None
    except urllib.error.URLError as e:
        raise GatewayFailure('Network connection failed: '+type(e.reason).__name__) from None
    except (UnicodeDecodeError,json.JSONDecodeError):
        raise GatewayFailure('Gateway response was not valid JSON') from None

def health(opener=None):
    base=base_url()
    return api_json('GET',base.removesuffix('/v1')+'/health',auth=False,timeout=15,opener=opener)

def models(opener=None):
    return api_json('GET',base_url()+'/models',auth=True,timeout=30,opener=opener)

def text_body():
    return {'model':model_id(),'stream':False,'temperature':0.2,'max_tokens':800,'messages':[
      {'role':'system','content':'你是严谨的专业电影导演研究者，区分观察事实、解释假设和证据缺口。'},
      {'role':'user','content':('请用中文分析一组连续镜头：人物群像→黑猫特写→人物近景。'
       '在没有看到实际原片的情况下，不得描述不存在的画面细节。分别提出两种可能的剪辑目的、'
       '反证条件、需要原片哪个时间段或声音证据。明确说明正常切镜是电影语言，而不是原片错误。')}]}

def payload(task):
    # This existing adapter checks hashes and compresses each user's own movie
    # still to at most 640x360. The original movie and audio are NEVER sent.
    p, bytes_total=cloud.payload(task,model_id())
    return p,bytes_total

def chat(body,opener=None,timeout=180):
    t0=time.monotonic()
    packet=api_json('POST',base_url()+'/chat/completions',body,auth=True,timeout=timeout,opener=opener)
    choices=packet.get('choices',[])
    if not isinstance(choices,list) or not choices:
        raise GatewayFailure('Authenticated gateway responded but returned no choices')
    message=choices[0].get('message',{})
    content=message.get('content','')
    if isinstance(content,list):content='\n'.join(p.get('text','') for p in content if isinstance(p,dict))
    if not isinstance(content,str) or not content.strip():
        raise GatewayFailure('Gateway returned no substantive assistant content')
    return packet,content,(time.monotonic()-t0)*1000

def run_text(opener=None,timeout=180):
    packet,raw,elapsed=chat(text_body(),opener,timeout)
    record={'kind':'text','model':model_id(),'gateway_base_url':base_url(),
      'executed_at_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
      'raw_model_response':raw,'elapsed_ms':round(elapsed),
      'usage':packet.get('usage',{}),'model_response_obtained':True,
      'actual_film_images_supplied':False,'director_knowledge_proven':False}
    return save_record(record)

def run_vision(task_id,opener=None,timeout=180):
    task=cloud.source_task(task_id)
    body,frames_bytes=payload(task)
    packet,raw,elapsed=chat(body,opener,timeout)
    try:
        parsed=cloud.json_from_text(raw)
    except Exception:parsed=None
    if parsed is not None:
        audit=hub.evaluate_structure(parsed)
    else:
        audit={'schema_valid':False,'structure_warnings':['NON_JSON_OR_BAD_SCHEMA'],
          'cinematic_correctness_verified':False,'auto_signoff_permitted':False,
          'review_status':'UNVERIFIED_MODEL_HYPOTHESIS'}
    record={'kind':'vision','task_id':task_id,'task_kind':task['task_kind'],
      'shot_ids':task['shot_ids'],'times_s':task['times_s'],
      'model':model_id(),'gateway_base_url':base_url(),
      'executed_at_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
      'source_film_sha256':task['source_film_sha256'],
      'reference_image_paths':task['reference_images'][:cloud.MAX_FRAMES],
      'reference_sha256':task['reference_sha256'][:cloud.MAX_FRAMES],
      'sent_compressed_still_count':min(len(task['reference_images']),cloud.MAX_FRAMES),
      'sent_compressed_stills_bytes':frames_bytes,
      'raw_model_response':raw,'parsed_director_hypothesis':parsed,
      'audit':audit,'elapsed_ms':round(elapsed),'usage':packet.get('usage',{}),
      'model_response_obtained':True,'source_movie_or_audio_uploaded':False,
      'director_quality_verified':False,'film_reproduction_passed':False,
      'approved_for_video_generation':False,'paid_video_model_invocations':0}
    return save_record(record)

def save_record(record):
    RESULTS.mkdir(parents=True,exist_ok=True)
    filename=(record.get('task_id','TEXT')+'_'+dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.json')
    dest=RESULTS/filename
    dest.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
    render_report()
    return {'status':'MODEL_REPLY_RECEIVED','record':os.path.relpath(dest,ROOT),
      'mode':record['kind'],'model':record['model'],
      'response_chars':len(record['raw_model_response']),
      'director_approved':False,'report':os.path.relpath(RESULTS/'index.html',ROOT)}

def render_report():
    RESULTS.mkdir(parents=True,exist_ok=True)
    files=sorted(RESULTS.glob('*.json'),reverse=True)
    records=[]
    for path in files[:60]:
        try:
            obj=json.loads(path.read_text(encoding='utf-8'))
            if obj.get('kind') not in ('vision','text'):continue
            records.append((path,obj))
        except Exception:continue
    blocks=[]
    for path,record in records:
        image_paths=record.get('reference_image_paths',[])
        imgs=[]
        for p in image_paths:
            # All images are inside this project's source/reference tree.
            full=(ROOT/p).resolve()
            if not full.is_relative_to(ROOT.resolve()) or not full.is_file():continue
            rel=os.path.relpath(full,RESULTS)
            imgs.append(f'<img src="{html.escape(rel,quote=True)}" alt="原片参考分镜">')
        raw=html.escape(record['raw_model_response'])
        title=html.escape(record.get('task_id','文本健康检查'))
        kind='真实原片分镜视觉分析' if record.get('kind')=='vision' else '文本推理连通性检查'
        blocks.append(f'''<article><div class="head"><h2>{title}</h2><span>{kind}</span></div>
        <p class="muted">{html.escape(record.get('executed_at_utc',''))} · {html.escape(record.get('model',''))} · {record.get('elapsed_ms','?')} ms</p>
        <div class="photos">{''.join(imgs)}</div>
        <div class="warning">模型推断：尚未通过导演事实核验；未授权进入成片生产</div>
        <pre>{raw}</pre></article>''')
    if not blocks:
        blocks=['<article><h2>尚无真实推理回执</h2><p>执行 python private_gateway_bridge.py vision --task LESSON_LESSON_01 后，这里才会显示真实模型回答。</p></article>']
    doc='''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>AI导演 · 私有模型实测审查</title><style>
    body{background:#0e141c;color:#ecf1f5;font:16px/1.6 system-ui,'Microsoft YaHei',sans-serif;margin:0 auto;max-width:1120px;padding:28px}
    h1{font-size:29px}article{background:#182330;border:1px solid #374455;border-radius:14px;margin:22px 0;padding:20px}
    .head{display:flex;justify-content:space-between;gap:20px;align-items:center}h2{font-size:22px}.muted{color:#adbbca}
    .photos{display:flex;gap:10px;flex-wrap:wrap}.photos img{max-width:calc(33.33% - 8px);min-width:180px;border-radius:8px;object-fit:contain}
    .warning{padding:12px 0;color:#ffd395}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#111922;padding:18px;border-radius:9px;font:14px/1.7 ui-monospace,Consolas,monospace}
    </style></head><body><h1>AI电影导演 · 自有网关真实模型回执</h1>
    <p>分镜来源：用户上传的影片片段；与模型猜测分开展示。只有收到真实 API 回答才会生成记录。此页面不包含 API Key，不自动给导演验收通过。</p>'''+''.join(blocks)+'</body></html>'
    (RESULTS/'index.html').write_text(doc,encoding='utf-8')


def main():
    parser=argparse.ArgumentParser(description='私有Qwen3VL网关：导演分析真实文本与分镜回执')
    parser.add_argument('command',choices=('health','models','text','vision','batch','report'))
    parser.add_argument('--task',default='LESSON_LESSON_01')
    parser.add_argument('--limit',type=int,default=3)
    parser.add_argument('--timeout',type=int,default=180)
    args=parser.parse_args()
    try:
        if args.command=='health': result={'status':'HEALTH_ONLY_NOT_INFERENCE','gateway':base_url(),'server':health()}
        elif args.command=='models':
            m=models()
            result={'status':'MODELS_LISTED','model_expected':model_id(),
              'models':[x.get('id') for x in m.get('data',[]) if isinstance(x,dict)]}
        elif args.command=='text':result=run_text(timeout=args.timeout)
        elif args.command=='vision':result=run_vision(args.task,timeout=args.timeout)
        elif args.command=='batch':
            if not 1<=args.limit<=16:raise GatewayFailure('Batch limit must be 1..16')
            tasks=hub.build_tasks()[:args.limit];ans=[]
            for task in tasks:
                try:ans.append(run_vision(task['id'],timeout=args.timeout))
                except GatewayFailure as e:
                    ans.append({'task':task['id'],'status':'FAILED','reason':str(e)})
            result={'count':len(ans),'outcomes':ans}
        else:
            render_report();result={'status':'REPORT_GENERATED','path':str((RESULTS/'index.html').relative_to(ROOT))}
        print(json.dumps(result,ensure_ascii=False,indent=2))
    except Exception as e:
        # Deliberately do not echo request headers, API key or request body.
        print(json.dumps({'status':'NOT_COMPLETED','error_type':type(e).__name__,
           'reason':str(e)[:230]},ensure_ascii=False),file=sys.stderr)
        return 2
    return 0

if __name__=='__main__':raise SystemExit(main())
