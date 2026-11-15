#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Cloud open-weight VLM adapter for a film director's evidence-locked benchmark.

Zero API calls by default. With an explicitly configured provider API key,
--run submits ONLY up to four downsized reference stills from one chosen
benchmark item (never the original video file). Returns evidence, alternative
interpretations and limitations, not a claim to know the original director's mind.

Provider endpoints and model IDs are separate: do not mistake a provider's
hosted API for a self-hosted or necessarily free inference service.
"""
from __future__ import annotations
import argparse, base64, datetime as dt, hashlib, io, json, os, sys, urllib.error, urllib.request
from pathlib import Path
from PIL import Image
import director_model_hub as hub

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'output'/'cloud_director_lab'
# Strict host list means no arbitrary URL or accidental exfiltration to local-network targets.
PROVIDERS={
  'groq': {'url':'https://api.groq.com/openai/v1/chat/completions','key_env':'GROQ_API_KEY','model':'qwen/qwen3.8-27b',
           'notes':'Open-weight model, provider free tier may require an account and has limits; verify vision availability.'},
  'openrouter': {'url':'https://openrouter.ai/api/v1/chat/completions','key_env':'OPENROUTER_API_KEY','model':'qwen/qwen2.5-vl-3b-instruct:free',
                 'notes':'Free model IDs and rate limits change; inspect the catalog before use.'},
  'huggingface': {'url':'https://router.huggingface.co/v1/chat/completions','key_env':'HF_TOKEN','model':'Qwen/Qwen3-VL-8B-Instruct',
                   'notes':'Availability depends on configured inference providers; Hugging Face account/token required.'},
  'private_gateway': {'url':os.environ.get('DIRECTOR_GATEWAY_BASE_URL','https://behavioral-thanksgiving-cheapest-cooling.trycloudflare.com/v1').rstrip('/')+'/chat/completions',
                    'key_env':'DIRECTOR_GATEWAY_API_KEY','model':'qwen3vl-8b',
                    'notes':'User-operated Cloudflare HTTPS to authenticated Ollama OpenAI-compatible gateway. Only sends selected compressed storyboard stills.'},
}
MAX_FRAMES=4

def source_task(task_id):
    tasks=hub.build_tasks()  # verifies source frame hashes before selecting
    t=next((x for x in tasks if x['id']==task_id),None)
    if t is None: raise ValueError('Unknown benchmark task id')
    return t

def miniature_image(path):
    im=Image.open(path).convert('RGB')
    im.thumbnail((640,360))
    b=io.BytesIO();im.save(b,format='JPEG',quality=72,optimize=True)
    data=b.getvalue()
    return 'data:image/jpeg;base64,'+base64.b64encode(data).decode('ascii'),len(data)

def prompt(t):
    # Avoid leaking earlier human interpretation into independent inference.
    return ('这是一部成熟已上映电影的镜头参考，它是导演语言的学习对象。\n'
      '请分别写出：画面可观察事实，镜头/摄影、人物调度和表演假设，剪辑如何传达信息，'
      '两种替代解释，以及为了确认解释仍需要什么声音或剧情证据。'
      '不得把正常切镜或场景变化认定为影片质量问题。'
      '请只根据附上的分镜，不要声称知道真实导演的意图。'
      '输出JSON，包含observable_facts,shot_language,blocking_and_eyelines,'
      'performance_hypothesis,editing_functions,alternative_interpretations,'
      'evidence_needed,transferable_director_lesson,confidence。\n'
      '参考镜头ID: '+', '.join(t['shot_ids'])+'；参考时间(秒): '+str(t['times_s'])+'。\n任务：'+t['question'])

def payload(t,model):
    images=t['reference_images'][:MAX_FRAMES]
    content=[{'type':'text','text':prompt(t)}]
    btotal=0
    for p in images:
        uri,n=miniature_image(ROOT/p); btotal+=n
        content.append({'type':'image_url','image_url':{'url':uri}})
    return {'model':model,'temperature':0.2,'max_tokens':1200,'messages':[
      {'role':'system','content':'你是审慎的电影剪辑与导演语言分析师。仅分析给出的图像。分清事实、可能解释和待验证假说。'},
      {'role':'user','content':content}]},btotal

def describe(task_id,provider='groq',model=None):
    if provider not in PROVIDERS: raise ValueError('Unknown provider')
    t=source_task(task_id)
    c=PROVIDERS[provider];p,upload_bytes=payload(t,model or c['model'])
    return {'task_id':task_id,'provider':provider,'endpoint':c['url'],'model':p['model'],
      'frame_count':len(p['messages'][1]['content'])-1,'approx_image_bytes':upload_bytes,
      'source_reference_sha256':t['reference_sha256'][:MAX_FRAMES],
      'key_configured':bool(os.environ.get(c['key_env'])),
      'actual_inference_performed':False,'money_spent_by_this_script':0,
      'status':'PREPARED_NOT_SENT',
      'warning':'You must explicitly invoke run and supply the API key. Movie stills leave the computer when run is used; check your rights and provider data policies.'}

def json_from_text(text):
    s=text.strip()
    if s.startswith('```'):
        s='\n'.join(s.splitlines()[1:]);s=s[:s.rfind('```')].strip() if '```' in s else s
    try:return hub.parse_analysis(s)
    except ValueError:
        # Non-conforming text is saved raw but never upgraded to a director-approved result.
        return None

def infer(task_id,provider='groq',model=None,timeout=90,opener=None):
    if provider not in PROVIDERS:raise ValueError('Unsupported provider')
    cfg=PROVIDERS[provider]
    token=os.environ.get(cfg['key_env'],'')
    if not token:raise RuntimeError('Missing '+cfg['key_env']+'; no external call made')
    if not 1<=timeout<=240:raise ValueError('Timeout out of bounds')
    t=source_task(task_id)
    body,bytes_sent=payload(t,model or cfg['model'])
    req=urllib.request.Request(cfg['url'],data=json.dumps(body,ensure_ascii=False).encode('utf-8'),
      headers={'Content-Type':'application/json','Authorization':'Bearer '+token,'User-Agent':'AI-Film-Director-Lab/1.0'},method='POST')
    with (opener or urllib.request.urlopen)(req,timeout=timeout) as response:
        packet=json.loads(response.read(2_000_000))
    choices=packet.get('choices',[])
    if not choices:raise ValueError('Provider returned no choices')
    raw=choices[0].get('message',{}).get('content','')
    if isinstance(raw,list):raw='\n'.join(x.get('text','') for x in raw if isinstance(x,dict))
    if not isinstance(raw,str) or not raw.strip():raise ValueError('Empty model reply')
    parsed=json_from_text(raw)
    audit=hub.evaluate_structure(parsed) if parsed else {'schema_valid':False,'structure_warnings':['NON_JSON_OR_BAD_SCHEMA'],
       'cinematic_correctness_verified':False,'auto_signoff_permitted':False,'review_status':'UNVERIFIED_MODEL_HYPOTHESIS'}
    timestamp=dt.datetime.now(dt.timezone.utc).isoformat()
    record={'task_id':task_id,'provider':provider,'model':body['model'],'endpoint':cfg['url'],
      'executed_at_utc':timestamp,'request_frame_sha256':t['reference_sha256'][:MAX_FRAMES],
      'source_film_sha256':t['source_film_sha256'],'sent_downsized_frame_bytes':bytes_sent,
      'response_text':raw,'parsed_director_hypothesis':parsed,'audit':audit,
      'provider_usage':packet.get('usage',{}),'reproduction_quality_passed':False,
      'model_claims_independently_validated':False,'video_model_invocations':0}
    path=OUT/'runs'/provider/(task_id+'_'+timestamp.replace(':','-').replace('+','_')+'.json')
    hub.write(path,record)
    return {'record_path':str(path),'provider':provider,'model':body['model'],
      'schema_valid':audit['schema_valid'],'director_approved':False,'raw_response_present':True}

def main():
    ap=argparse.ArgumentParser(description='电影导演学习：按任务试用公开云端视觉模型（仅明确run才上传少量分镜）')
    ap.add_argument('command',choices=('providers','prepare','run'))
    ap.add_argument('--task',default='LESSON_LESSON_01')
    ap.add_argument('--provider',choices=PROVIDERS,default='groq')
    ap.add_argument('--model',default=None)
    ap.add_argument('--timeout',type=int,default=90)
    a=ap.parse_args()
    try:
        if a.command=='providers':result=PROVIDERS
        elif a.command=='prepare':result=describe(a.task,a.provider,a.model)
        else:result=infer(a.task,a.provider,a.model,a.timeout)
        print(json.dumps(result,ensure_ascii=False,indent=2))
    except Exception as e:
        # Never include token or request body in errors or logs.
        print(json.dumps({'status':'NOT_RUN_OR_FAILED','error':type(e).__name__,
          'detail':str(e)[:250]},ensure_ascii=False),file=sys.stderr)
        raise SystemExit(2)
if __name__=='__main__': main()
