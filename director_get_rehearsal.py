#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Directors' rehearsal over a user's explicitly enabled GET-only Ollama gateway.

Security: never prints or stores the token, refuses redirects, does not upload
images, and declines to sign off any generated storyboard. GET with a token in
query is inherently loggable; use a short-lived token and prefer authenticated
POST for proper multi-image evaluation.
"""
from __future__ import annotations
import argparse
import datetime as dt
import html
import json
import os
from pathlib import Path
import re
import time
import urllib.parse
import urllib.request
import urllib.error

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'output'/'gateway_director_lab'
ENV_TOKEN='DIRECTOR_GATEWAY_API_KEY'
ENV_BASE='DIRECTOR_GATEWAY_BASE_URL'
DEFAULT_BASE='https://behavioral-thanksgiving-cheapest-cooling.trycloudflare.com/v1'
PROMPTS={
 'editorial':('你是电影导演研究者，只有以下相邻镜头简述：多人场景→黑猫→人物近景，未看过原片。'
   '请列出可直接确定的事实、两种不相容的剪辑功能假说、逐一需要的视线/声音/前后文证据。'
   '绝不能断言黑猫被角色看见，绝不能把正常切镜视为影片错误。'),
 'creative':('原创电竞虚拟战场倒数18秒，选手仅12点生命值，必须接近信标开始拆除；'
   '高桥狙击手位置只有观众提前知道，角色看不到也听不到任何人提醒。'
   '设计5镜且总时间覆盖0-18秒，每镜单一机位单一时刻、景别、走位、叙事功能、切镜原因与游戏内音效。'
   '只拍虚拟游戏，生命值不能擅自变0。'),
 'critique':('请严格审查以下待修镜头方案，而不是夸赞：'
   '0-3秒女选手位于信标旁且血量12%；3-5秒瞥高桥；5-7秒敌人已经开枪；'
   '7-12秒人物因观众尖叫而后退；12-15秒生命值归零。'
   '事实设定：女选手血量12点、18秒内接近信标并开始操作、观众应先看到高桥狙击手、角色未知其位置。'
   '逐条找出错位、信息泄露、主角知识及无依据死亡的问题，给出5镜修订方案，'
   '不得把剪辑手法视为原片错误。'),
 'strict':('请重新设计倒数18秒原创电竞虚拟战场的五镜方案，每镜唯一视角、唯一时刻，镜头时间连续。'
   '第1镜交代女选手血量12点且距离信标还有一段路；第2镜明确接近；'
   '第3镜独立高桥狙击手镜头，让观众知道威胁但女选手不知道；'
   '第4镜抵达并开始拆除；第5镜持续拆除、狙击威胁未解除。'
   '禁止角色死亡或血量变化，禁止观众席、分屏、同一镜出现两个机位、凭空得知狙击手。'
   '每镜写时间、景别、动作、切镜原因、声效，最后指出尚待人工验收问题。'),
}

class GatewayError(Exception): pass
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self, req, fp, code, msg, headers, newurl):
  raise GatewayError('Gateway refused redirect (credential would be exposed)')

def base():
 value=os.getenv(ENV_BASE,DEFAULT_BASE).strip().rstrip('/')
 p=urllib.parse.urlsplit(value)
 if p.scheme!='https' or not p.hostname or p.username or p.password or p.query or p.fragment or p.path!='/v1':
  raise GatewayError('Expected HTTPS base URL with exact /v1 path, no secrets or query')
 return value

def response_text(packet):
 if not isinstance(packet,dict) or not isinstance(packet.get('choices'),list) or not packet['choices']:
  raise GatewayError('Malformed response: no choices')
 msg=packet['choices'][0].get('message',{})
 raw=msg.get('content','')
 if not isinstance(raw,str) or not raw.strip():raise GatewayError('Empty model reply')
 if packet.get('answer') and packet['answer'].strip()!=raw.strip():raise GatewayError('answer and choices content disagree')
 return raw

def fetch(prompt, opener=None, timeout=120):
 token=os.getenv(ENV_TOKEN,'').strip()
 if not token:raise GatewayError(f'Missing {ENV_TOKEN}; no request sent')
 if not isinstance(prompt,str) or not 5<=len(prompt)<=2500:raise GatewayError('Invalid prompt size')
 # DO NOT log this query URL. Proxies may still log credentials embedded in GET.
 uri=base()+'/chat?'+urllib.parse.urlencode({'token':token,'q':prompt})
 req=urllib.request.Request(uri,method='GET',headers={'Accept':'application/json','User-Agent':'Director-GET-Rehearsal/1'})
 started=time.monotonic()
 try:
  with (opener or urllib.request.build_opener(NoRedirect())).open(req,timeout=timeout) as r:
   status=r.status
   raw=r.read(2_000_000)
 except urllib.error.HTTPError as e:
  raise GatewayError('HTTP '+str(e.code)) from None
 except (urllib.error.URLError,TimeoutError):
  raise GatewayError('Network request failed; secret URL omitted') from None
 except GatewayError:raise
 if status!=200:raise GatewayError('HTTP '+str(status))
 try:packet=json.loads(raw)
 except (UnicodeError,ValueError):raise GatewayError('Invalid JSON response') from None
 answer=response_text(packet)
 return {'model':packet.get('model'),'created':packet.get('created'),
  'answer':answer,'usage':packet.get('usage',{}),'latency_ms':round(1000*(time.monotonic()-started)),
  'http_status':status,'images_sent':0,'source_video_sent':False,'model_response_obtained':True,
  'director_semantic_correctness_verified':False,'film_recreation_approved':False}

def audit(case,answer):
 """Only objective/heuristic flags; not a score of filmmaking quality."""
 flags=[]
 if case in {'creative','critique','strict'}:
  if re.search(r'12\s*%|12\s*％',answer): flags.append('HP_12_MISREAD_AS_PERCENT')
  if re.search(r'(?:12|十二)\s*(?:→|->|至|变成|变为|降低到)\s*0|血(?:量|条|值)[^。\n]{0,15}归零|生命值[^。\n]{0,12}归零',answer):flags.append('UNAUTHORIZED_HP_ZERO')
  if re.search(r'观众席|大屏幕',answer):flags.append('REAL_WORLD_SPECTATOR_INSERT')
  if re.search(r'同时插入|同镜头切至',answer):flags.append('MULTI_CAMERA_IN_ONE_SHOT')
  if re.search(r'因.*(?:观众尖叫|观众提醒|观众呼喊)',answer):flags.append('OUT_OF_WORLD_KNOWLEDGE_LEAK')
  # Do not turn missing regex hits into a subjective PASS.
 return {'mechanical_warnings':flags,'mechanical_warning_count':len(flags),
  'manual_review_required':['shot_space_geometry','eyelines','screen_direction','knowledge_asymmetry',
                            'blocking_continuity','sound_motivation','cinematic_quality'],
  'semantic_quality_verified':False,'director_approved':False}

def save(record):
 OUT.mkdir(parents=True,exist_ok=True)
 name='GET_'+record['case']+'_'+dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'.json'
 (OUT/name).write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
 return str((OUT/name).relative_to(ROOT))

def run(case,opener=None):
 response=fetch(PROMPTS[case],opener=opener)
 record={'source':'ACTUAL_GATEWAY_GET','case':case,'question':PROMPTS[case],**response,
  'audit':audit(case,response['answer']),
  'credential_written_to_file':False,'director_verdict':'UNVERIFIED_MODEL_HYPOTHESIS'}
 path=save(record)
 return {'status':'ACTUAL_MODEL_REPLY_OBTAINED','record':path,'model':response['model'],
  'answer':response['answer'],'audit':record['audit'],'images_sent':0}

def main():
 p=argparse.ArgumentParser(description='Real text-only film-director benchmark over GET-only private gateway')
 p.add_argument('--case',choices=[*PROMPTS,'all'],default='editorial')
 args=p.parse_args()
 try:
  keys=list(PROMPTS) if args.case=='all' else [args.case]
  for key in keys:print(json.dumps(run(key),ensure_ascii=False,indent=2))
 except GatewayError as exc:
  print(json.dumps({'status':'FAILED','error':str(exc),'credential_logged':False},ensure_ascii=False))
  raise SystemExit(2)
if __name__=='__main__':main()
