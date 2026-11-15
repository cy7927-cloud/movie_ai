#!/usr/bin/env python3
"""Optional fully-local ComfyUI storyboard generator and bounded self-iteration.

Not installed, not bundled, no model weights. Uses ONLY http://127.0.0.1 or localhost.
Workflow must be exported in ComfyUI API format and have a text input node.
No paid video calls; local GPU resources are still consumed.
"""
import argparse,hashlib,json,time,urllib.parse,urllib.request,uuid
from pathlib import Path
import director as d

CONFIG=d.BASE/'local_model_config.json'

def configuration():
    if not CONFIG.is_file():return {'available':False,'reason':'Missing local_model_config.json. Copy local_model_config.example.json and configure your installed ComfyUI workflow.'}
    x=json.loads(CONFIG.read_text(encoding='utf-8'))
    u=urllib.parse.urlparse(x.get('url',''))
    if u.scheme!='http' or u.hostname not in ('127.0.0.1','localhost') or (u.path not in ('','/')):
        raise ValueError('Local model endpoint MUST use localhost HTTP, no paths or remote hosts.')
    wf=(d.BASE/x.get('workflow_json',''))
    if not wf.is_file() or not str(x.get('prompt_node','')).strip():raise ValueError('Missing workflow JSON or prompt_node.')
    return {**x,'available':True,'workflow_path':str(wf)}

def request(url,method='GET',body=None,ctype='application/json',timeout=30):
    req=urllib.request.Request(url,data=body,method=method)
    if body is not None:req.add_header('Content-Type',ctype)
    with urllib.request.urlopen(req,timeout=timeout) as r:return r.read()

def get_status():
    try:
        c=configuration()
        if not c['available']:return c
        response=request(c['url'].rstrip('/')+'/system_stats',timeout=3)
        return {'available':True,'connected':True,'workflow':c['workflow_json'],'host':'LOCALHOST_ONLY','server_info':json.loads(response) if response else {}}
    except Exception as e:return {'available':False,'connected':False,'error':str(e)[:250]}

def upload_image(url,path):
    name=Path(path).name
    boundary='----DirectorLocal'+uuid.uuid4().hex
    b=Path(path).read_bytes()
    payload=b'--'+boundary.encode()+b'\r\nContent-Disposition: form-data; name="image"; filename="'+name.encode()+b'"\r\nContent-Type: image/png\r\n\r\n'+b+b'\r\n--'+boundary.encode()+b'--\r\n'
    data=json.loads(request(url+'/upload/image','POST',payload,'multipart/form-data; boundary='+boundary,timeout=45))
    return data['name']

def generate_one(prompt,reference=None,previous=None,timeout_seconds=300):
    c=configuration()
    if not c.get('available'):raise RuntimeError(c['reason'])
    url=c['url'].rstrip('/')
    graph=json.loads(Path(c['workflow_path']).read_text(encoding='utf-8'))
    prompt_node=str(c['prompt_node'])
    if prompt_node not in graph or 'inputs' not in graph[prompt_node] or 'text' not in graph[prompt_node]['inputs']:
        raise ValueError('Configured prompt node is not a text-input node')
    graph[prompt_node]['inputs']['text']=prompt
    for param,path in [('reference_image_node',reference),('previous_image_node',previous)]:
        node=c.get(param)
        if node:
            if not path:continue
            if str(node) not in graph or 'image' not in graph[str(node)].get('inputs',{}):
                raise ValueError(param+' must refer to a LoadImage node')
            graph[str(node)]['inputs']['image']=upload_image(url,path)
    req={'prompt':graph,'client_id':'director-'+uuid.uuid4().hex}
    response=json.loads(request(url+'/prompt','POST',json.dumps(req).encode('utf-8'),timeout=35))
    pid=response.get('prompt_id')
    if not pid:raise RuntimeError('Local provider did not return a prompt_id')
    t=time.monotonic()
    while time.monotonic()-t<timeout_seconds:
        hist=json.loads(request(url+'/history/'+urllib.parse.quote(pid,safe=''),timeout=10))
        if pid in hist:
            values=hist[pid]
            status=values.get('status',{})
            if status.get('status_str')=='error':raise RuntimeError('Local model failed: '+str(status)[:400])
            for node in values.get('outputs',{}).values():
                for obj in node.get('images',[]):
                    if obj.get('type','output')!='output':continue
                    return request(url+'/view?'+urllib.parse.urlencode({'filename':obj['filename'],'subfolder':obj.get('subfolder',''),'type':'output'}),timeout=40)
            raise RuntimeError('Local workflow completed without an output image')
        time.sleep(1.8)
    raise TimeoutError('Local model output timed out; task was not counted as generated')

def local_self_iterate(task_id,max_rounds=3,mode='reference',timeout_seconds=300):
    """Real iterative generation with local provider. Strictly never auto-signs off a shot."""
    d.bootstrap()
    if max_rounds<1 or max_rounds>8:raise ValueError('max_rounds must be 1..8')
    results=[];best_score=-1.0;stalls=0
    with d.connect() as c:
        task=c.execute('SELECT * FROM tasks WHERE id=?',(task_id,)).fetchone()
        if not task:raise KeyError(task_id)
        if task['status']=='STORYBOARD_APPROVED':raise RuntimeError('Approved storyboard is locked')
        rows=[a for a in c.execute('SELECT * FROM attempts WHERE task_id=? ORDER BY id',(task_id,)).fetchall()
              if a['reference_sha']==task['reference_sha'] and a['spec_sha']==d.task_spec_sha(task)]
        for prev in rows:best_score=max(best_score,d.read_json(prev['metrics'],{}).get('technical_score',0))
        settings=configuration()
        vision_model=('ollama:'+settings['local_vision_model']) if settings.get('local_vision_model') else None
        for index in range(max_rounds):
            latest=rows[-1] if rows else None
            best=max(rows,key=lambda a:d.read_json(a['metrics'],{}).get('technical_score',0)) if rows else None
            # Require previous candidate to be associated with current director spec.
            if best and best['spec_sha']!=d.task_spec_sha(task):best=None
            prompt=d.build_prompt(task,d.read_json(latest['issues'],[]) if latest else [],best,d.history_for(c,task['shot_id']),mode)
            ref=(d.BASE/task['reference']) if mode=='reference' else None
            prior=(d.BASE/best['candidate']) if best else None
            raw=generate_one(prompt,ref,prior,timeout_seconds)
            path=d.OUT/'local_provider_output'/(task_id.replace(':','_')+'_'+str(index)+'.png')
            path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
            result=d.store_attempt(c,task_id,path,'comfyui_local','user_configured_workflow',mode,prompt,vision_model,0)
            results.append(result)
            if result.get('vision_error'):
                d.event(c,task_id,'LOCAL_VISION_UNAVAILABLE',{'reason':result['vision_error']})
                break
            rows=[a for a in c.execute('SELECT * FROM attempts WHERE task_id=? ORDER BY id',(task_id,)).fetchall()
                  if a['spec_sha']==d.task_spec_sha(task)]
            s=result['metrics']['technical_score']
            if s>best_score+.012:best_score=s;stalls=0
            else:stalls+=1
            if result['verdict'] in ('REJECTED_REFERENCE_COPY','BLOCKED_LOW_INFORMATION') or stalls>=2:break
        d.event(c,task_id,'LOCAL_AI_LOOP_FINISHED',{'actual_generations':len(results),'not_semantically_verified':True})
    return {'task_id':task_id,'generated':len(results),'results':results,'semantic_status':'NOT_VERIFIED','approved':False}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='cmd',required=True)
    s.add_parser('doctor');r=s.add_parser('run');r.add_argument('--shot',required=True);r.add_argument('--anchor',default='MID',choices=d.ANCHORS);r.add_argument('--max-rounds',type=int,default=3);r.add_argument('--mode',choices=('independent','reference'),default='reference')
    a=p.parse_args()
    print(json.dumps(get_status() if a.cmd=='doctor' else local_self_iterate(a.shot+':'+a.anchor,a.max_rounds,a.mode),ensure_ascii=False,indent=2))
