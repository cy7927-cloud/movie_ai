#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Evidence-locked director-learning benchmark for interchangeable pretrained tools.

Only local Ollama is executable here; ShotTransformer, FilmAgent and Skills are
catalog entries until separately installed. Film is a teaching reference; cut
variation must never be marked a defect. Analyses are *hypotheses*, never sign-off.
"""
from __future__ import annotations
import argparse, base64, datetime as dt, hashlib, html, io, json, os, urllib.parse, urllib.request
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'output'/'model_research_lab'
CATALOG=[
 {'id':'qwen3_vl','name':'Qwen3-VL (Ollama)','kind':'pretrained_vision_model','url':'https://ollama.com/library/qwen3-vl',
  'role':'人物可见事实、空间层次、镜头语法多图初判','installation':'ollama pull qwen3-vl:4b','execution':'localhost Ollama JSON API','available_in_this_environment':False},
 {'id':'shottransformer','name':'ShotTransformer','kind':'pretrained_shot_classifier','url':'https://github.com/litchiar/ShotTransformer',
  'role':'景别、机位角度和镜头运动的独立分类基线','installation':'需先取得发行版预训练checkpoint并按原仓库运行','execution':'external CLI adapter pending','available_in_this_environment':False},
 {'id':'filmagent','name':'FilmAgent','kind':'director_multi_agent_framework','url':'https://github.com/kekewolf/FilmAgent',
  'role':'编剧/导演/演员/摄影Agent协作与虚拟场景规划','installation':'按仓库要求安装3D环境和对应依赖','execution':'separate sandbox workflow','available_in_this_environment':False},
 {'id':'open_film_skills','name':'Open Film Skills','kind':'agent_skills','url':'https://github.com/62656456/ai-film-skills',
  'role':'director-agent、ai-storyboard-director、whitebox-previs-executor','installation':'git clone后审阅SKILL.md，再明确选用','execution':'skill instruction packages; requires agent host','available_in_this_environment':False},
 {'id':'film_production_skills','name':'Film Production Skills','kind':'agent_skills','url':'https://github.com/zhangzhangco/film-production-skills',
  'role':'剧本、资产、镜头规划、生成、审片之间的数据契约','installation':'阅读README与SKILL.md后按需安装','execution':'schema/skill workflow','available_in_this_environment':False},
 {'id':'movienet','name':'MovieNet','kind':'research_dataset_and_benchmarks','url':'https://movienet.github.io/',
  'role':'镜头景别、运动、场景、人物等标注作为模型评估真值参照','installation':'获取适用授权的数据集标注与工具','execution':'offline benchmark after download','available_in_this_environment':False},
 {'id':'ava_encoder','name':'AVA-Encoder','kind':'research_framework','url':'https://github.com/HBDYW/AVA-Encoder',
  'role':'电影知识图谱与重建残差反馈的研究方向','installation':'需要分别确认公开实现、模型、许可证和复现条件','execution':'research reference only','available_in_this_environment':False},
]
SYSTEM='''你是电影导演、电影语言研究者。输入为一部已上映电影的参考关键帧，电影是需要学习的作品，绝不是被你找瑕疵的对象。你需要区分三层：A可被图像直接观察的事实，B可能的电影语言/编剧/剪辑解释，C需要更多证据才能确认的部分。禁止声称认识演员名字或导演创作意图，禁止把正常切镜、跨场景、光色差当成电影错误。请用中文输出有效JSON对象，字段严格包含：observable_facts(字符串数组), shot_language(字符串), blocking_and_eyelines(字符串), performance_hypothesis(字符串), editing_functions(字符串数组), alternative_interpretations(字符串数组), evidence_needed(字符串数组), transferable_director_lesson(字符串), confidence(0到1的小数)。不使用缺乏画面证据的断言。'''

def jload(p):return json.loads(Path(p).read_text('utf-8'))
def write(p,obj):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 p.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def build_tasks():
 cards=jload(ROOT/'output/director_lab/director_cards.json')
 lessons=jload(ROOT/'output/editorial_language/director_lessons.json')
 byid={c['shot_id']:c for c in cards}
 source=jload(ROOT/'data/project_manifest.json')
 tasks=[]
 # Three lesson tasks, each with 3-4 actual movie shot frames, audio verification notes.
 for lesson in lessons:
  files=[ROOT/p for p in lesson['reference_mid_frames']]
  for p,sha in zip(files,lesson['reference_sha256']):
   if not p.is_file() or digest(p)!=sha:raise RuntimeError('Source integrity mismatch: '+str(p))
  tasks.append({'id':'LESSON_'+lesson['id'],'task_kind':'EDITING_CASE',
     'shot_ids':lesson['shots'],
     'times_s':[byid[x]['time']['start'] for x in lesson['shots']],
     'reference_images':[str(p.relative_to(ROOT)) for p in files],
     'reference_sha256':[digest(p) for p in files],
     'source_film_sha256':source['source_sha256'],
     'prior_interpretation_hypothesis':lesson['hypothesis'],
     'alternatives_from_previous_study':lesson['alternatives'],
     'film_cut_is_not_an_error':True,
     'question':'这组镜头怎样组织观众信息、人物反应和剪辑节奏？分别给出可见事实、导演假说、反证与可迁移规则。'})
 # Nine single-shot triplets across the three real, reviewable examples.
 unique=list(dict.fromkeys(x for ls in lessons for x in ls['shots']))
 for sid in unique:
  c=byid[sid]
  paths=[ROOT/c['reference_images'][k] for k in ('in','mid','out')]
  for key,p in zip(('in','mid','out'),paths):
   if not p.is_file() or digest(p)!=c['anchor_source_shas'][key]:raise RuntimeError('Source frame integrity mismatch: '+str(p))
  tasks.append({'id':'SHOT_'+sid,'task_kind':'SHOT_LANGUAGE', 'shot_ids':[sid],
     'times_s':[c['time']['start'],c['time']['end']],
     'reference_images':[str(p.relative_to(ROOT)) for p in paths],
     'reference_sha256':[digest(p) for p in paths],
     'source_film_sha256':source['source_sha256'],
     'film_cut_is_not_an_error':True,
     'question':'审阅IN/MID/OUT：客观观察人物调度、景别、视线、行动时序，提出机位与表演功能假设并标注不能凭三帧确定的事项。'})
 return tasks

def create_evidence_board(tasks):
 fontfile=Path('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')
 ft=ImageFont.truetype(str(fontfile),19) if fontfile.is_file() else ImageFont.load_default()
 selected=[t for t in tasks if t['task_kind']=='EDITING_CASE']
 w=1080;rowh=225
 bg=Image.new('RGB',(w,90+len(selected)*rowh),'#101923');d=ImageDraw.Draw(bg)
 d.text((20,20),'电影语言研究：真实镜头组合（待模型独立解读）',font=ft,fill='#f7dfb5')
 for i,t in enumerate(selected):
  y=85+i*rowh
  d.text((22,y),t['id']+' / '+' → '.join(t['shot_ids']),font=ft,fill='#d8e0ed')
  imgs=t['reference_images'][:4];x=22;slot=(w-45)//len(imgs)
  for n,p in enumerate(imgs):
   im=Image.open(ROOT/p).convert('RGB');im.thumbnail((slot-6,174))
   bg.paste(im,(x+(slot-im.width)//2,y+32))
   d.text((x+8,y+207),t['shot_ids'][n],font=ft,fill='#9cb4cd')
   x+=slot
 OUT.mkdir(parents=True,exist_ok=True)
 bg.save(OUT/'真实镜头语言对照板.jpg',quality=90)

def export():
 tasks=build_tasks();OUT.mkdir(parents=True,exist_ok=True)
 write(OUT/'catalog.json',CATALOG)
 write(OUT/'benchmark_tasks.json',tasks)
 with (OUT/'benchmark_tasks.jsonl').open('w',encoding='utf-8') as f:
  for t in tasks:f.write(json.dumps(t,ensure_ascii=False)+'\n')
 create_evidence_board(tasks)
 make_html(tasks)
 return {'reference_film':'USER_PROVIDED_12_MIN_56_SEC_EXCERPT','cases':sum(t['task_kind']=='EDITING_CASE' for t in tasks),
         'shot_triplets':sum(t['task_kind']=='SHOT_LANGUAGE' for t in tasks),
         'total_tasks':len(tasks),'inference_calls':0,'film_quality_passed':0,'model_inference_verified':False,
         'catalog_count':len(CATALOG),'output':str(OUT)}

def image_b64(p):
 im=Image.open(p).convert('RGB');im.thumbnail((640,360));o=io.BytesIO();im.save(o,'JPEG',quality=76)
 return base64.b64encode(o.getvalue()).decode('ascii')

def ollama_url(base):
 parsed=urllib.parse.urlsplit(base)
 if parsed.scheme!='http' or parsed.hostname not in ('localhost','127.0.0.1') or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ('','/'):
  raise ValueError('Only an explicitly configured localhost Ollama server is permitted')
 return f'http://{parsed.hostname}:{parsed.port or 11434}/api/chat'

def doctor(base='http://127.0.0.1:11434'):
 url=ollama_url(base).replace('/api/chat','/api/tags')
 try:
  with urllib.request.urlopen(url,timeout=2) as r:obj=json.loads(r.read())
  return {'local_ollama_connected':True,'models':[x.get('name') for x in obj.get('models',[])],
          'verified_director_semantics':False,'paid_video_model_used':False}
 except Exception as e:
  return {'local_ollama_connected':False,'reason':type(e).__name__,
          'verified_director_semantics':False,'paid_video_model_used':False}

def parse_analysis(answer):
 try:res=json.loads(answer)
 except Exception as e:raise ValueError('Model did not return valid JSON') from e
 if not isinstance(res,dict):raise ValueError('Model result is not an object')
 keys=('observable_facts','shot_language','blocking_and_eyelines','performance_hypothesis',
       'editing_functions','alternative_interpretations','evidence_needed','transferable_director_lesson','confidence')
 if any(k not in res for k in keys):raise ValueError('Missing required director fields')
 for k in ('observable_facts','editing_functions','alternative_interpretations','evidence_needed'):
  if not isinstance(res[k],list):raise ValueError(k+' must be a list')
  res[k]=[str(a)[:800] for a in res[k][:30]]
 for k in ('shot_language','blocking_and_eyelines','performance_hypothesis','transferable_director_lesson'):
  res[k]=str(res[k])[:3000]
 res['confidence']=max(0.0,min(1.0,float(res['confidence'])))
 return res

def evaluate_structure(res):
 # These checks test honesty and parseability, NEVER true cinematic correctness.
 warnings=[]
 if not res['alternative_interpretations']:warnings.append('MISSING_ALTERNATIVE_HYPOTHESIS')
 if not res['evidence_needed']:warnings.append('MISSING_FALSIFICATION_PLAN')
 if not res['observable_facts']:warnings.append('NO_OBSERVABLE_FACTS')
 suspicious=('原片有问题','电影拍错','剪辑错误','导演一定','电影质量缺陷')
 if any(x in json.dumps(res,ensure_ascii=False) for x in suspicious):warnings.append('UNSUPPORTED_FILM_DEFECT_OR_INTENT_CLAIM')
 return {'schema_valid':True,'structure_warnings':warnings,'cinematic_correctness_verified':False,
         'original_director_intent_verified':False,'review_status':'UNVERIFIED_MODEL_HYPOTHESIS',
         'auto_signoff_permitted':False}

def run_local(task_id,model='qwen3-vl:4b',base='http://127.0.0.1:11434'):
 tasks=build_tasks();task=next((t for t in tasks if t['id']==task_id),None)
 if task is None:raise ValueError('Unknown source task id')
 body={'model':model,'stream':False,'format':'json','options':{'temperature':0.2},'messages':[
  {'role':'system','content':SYSTEM},
  {'role':'user','content':json.dumps({'question':task['question'],'times_s':task['times_s'],
       'shot_ids':task['shot_ids'],'note':'图片来自真实影片，只分析可见证据','prior_hypothesis_is_unverified':task.get('prior_interpretation_hypothesis')},ensure_ascii=False),
   'images':[image_b64(ROOT/x) for x in task['reference_images']]}]}
 url=ollama_url(base)
 request=urllib.request.Request(url,data=json.dumps(body).encode('utf-8'),headers={'Content-Type':'application/json'},method='POST')
 with urllib.request.urlopen(request,timeout=240) as r:response=json.loads(r.read())
 raw=response.get('message',{}).get('content','');res=parse_analysis(raw)
 checks=evaluate_structure(res)
 rec={'task_id':task_id,'model':model,'source_film_sha256':task['source_film_sha256'],
      'source_reference_sha256':task['reference_sha256'],'result':res,'audit':checks,
      'timestamp_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
      'model_prompt_sha256':hashlib.sha256(SYSTEM.encode()).hexdigest(),
      'source':'REAL_LOCAL_MODEL_OUTPUT_UNVERIFIED'}
 out=OUT/'runs'/model.replace(':','_')/(task_id+'.json');write(out,rec)
 return {'file':str(out),'audit':checks,'signed_off':False}

def make_html(tasks):
 # offline review, images need source folder relative to this HTML
 rel='../../'
 cards=[]
 for t in tasks:
  ims=''.join(f'<figure><img src="{rel+html.escape(p,quote=True)}" loading="lazy"><figcaption>{html.escape(t["shot_ids"][min(i,len(t["shot_ids"])-1)])}</figcaption></figure>' for i,p in enumerate(t['reference_images']))
  cards.append(f'<article><h2>{html.escape(t["id"])}</h2><p>{html.escape(t["question"])}</p><div class="frames">{ims}</div><p>状态：参考影片观察任务 · 未执行视觉模型推理 · 未核验导演意图</p></article>')
 page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>导演预训练模型实验室</title><style>
 body{font-family:system-ui,"Noto Sans CJK SC",sans-serif;background:#0b1422;color:#e8efff;max-width:1220px;margin:30px auto;padding:0 22px}
 h1{color:#f0dba7}article{background:#162237;border:1px solid #2c415b;border-radius:12px;padding:18px;margin:18px 0}
 .frames{display:flex;gap:10px;align-items:start}figure{flex:1;margin:0;min-width:0}img{width:100%;height:auto;object-fit:contain;border-radius:6px}
 figcaption{color:#9eb8d0;margin-top:6px}p{line-height:1.65;color:#d2dbea}</style><h1>导演预训练模型实验室</h1>
 <p>学习对象是上映电影；不对正常切镜扣缺陷分。下面是用户影片原始参考帧，不是AI重新生成。所有任务都带原图SHA，供Qwen3-VL、镜头分类模型和影视Agent做对照分析。</p>
 <p>当前仅建立真实基准任务；未调用预训练视觉模型，导演理解通过率不可计算。</p>'''+''.join(cards)+r"<script>if(location.pathname==='/director-model-lab'){document.querySelectorAll('img').forEach(function(i){let p=i.getAttribute('src').replace(/^\.\.\/\.\.\//,'');i.src='/file?path='+encodeURIComponent(p);});}</script></html>"
 (OUT/'导演模型实验室.html').write_text(page,encoding='utf-8')

def main():
 p=argparse.ArgumentParser(description=__doc__)
 sub=p.add_subparsers(dest='cmd',required=True)
 sub.add_parser('export');sub.add_parser('catalog')
 doc=sub.add_parser('doctor');doc.add_argument('--url',default='http://127.0.0.1:11434')
 run=sub.add_parser('run-local');run.add_argument('--task',required=True);run.add_argument('--model',default='qwen3-vl:4b');run.add_argument('--url',default='http://127.0.0.1:11434')
 args=p.parse_args()
 try:
  if args.cmd=='export':out=export()
  elif args.cmd=='catalog':out=CATALOG
  elif args.cmd=='doctor':out=doctor(args.url)
  else:out=run_local(args.task,args.model,args.url)
  print(json.dumps(out,ensure_ascii=False,indent=2))
 except Exception as e:
  print(json.dumps({'error':type(e).__name__,'message':str(e)},ensure_ascii=False))
  raise SystemExit(2)
if __name__=='__main__':main()
