#!/usr/bin/env python3
# coding: utf-8
"""GPT-directed, original-film-grounded directing apprenticeship.

Two visually inspected excerpts of the user's uploaded movie are the learning material.
This module checks source frames and ORIGINAL rehearsal continuity; it never 'grades'
the original filmmakers, or claims to train GPT weights / confirm director intent.

Usage: python gpt_director_study.py run
       python gpt_director_study.py audit path/to/storyboard.json
"""
from __future__ import annotations
import argparse, hashlib, html, json, re
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import cv2

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'output'/'gpt_director_study'
SOURCE=ROOT/'data'/'source_video.mp4'
SCENE=ROOT/'data'/'gpt_director_scene.json'
CASES=ROOT/'data'/'gpt_director_cases.json'


def digest(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for chunk in iter(lambda:f.read(1048576),b''):h.update(chunk)
    return h.hexdigest()


def load(path):return json.loads(Path(path).read_text(encoding='utf-8'))


def save(path,data):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')


def _font(size):
    for name in ('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
                 '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',
                 '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'):
        if Path(name).is_file():return ImageFont.truetype(name,size)
    return ImageFont.load_default()


def verify_source():
    manifest=load(ROOT/'data'/'project_manifest.json')
    if not SOURCE.is_file():raise FileNotFoundError('Missing user source film segment')
    if digest(SOURCE)!=manifest['source_sha256']:
        raise ValueError('Original film checksum changed. Refuse to attribute screenshots to original.')
    return {'source_path':'data/source_video.mp4','sha256':manifest['source_sha256'],
       'source_scope':'UPLOADED_776_SECOND_EXCERPT_NOT_THE_FULL_FEATURE',
       'duration_s':manifest['duration_seconds'],'director_intent_verified':0}


def extract_frames(cases):
    cap=cv2.VideoCapture(str(SOURCE))
    if not cap.isOpened():raise RuntimeError('Video decoder failed')
    refs={}
    try:
        for case in cases:
            shots=[]
            for idx,p in enumerate(case['observations']):
                sec=p['second']
                cap.set(cv2.CAP_PROP_POS_MSEC,sec*1000)
                ok,frame=cap.read()
                if not ok:raise ValueError(f'Cannot decode film at {sec}s')
                path=OUT/'source_frames'/f'{case["id"]}_{idx+1:02d}_{sec:.1f}s.jpg'
                path.parent.mkdir(parents=True,exist_ok=True)
                if not cv2.imwrite(str(path),frame,[cv2.IMWRITE_JPEG_QUALITY,91]):
                    raise ValueError('Failed to save source frame')
                shots.append({'time_s':sec,'path':path.relative_to(ROOT).as_posix(),
                             'sha256':digest(path),'observation':p['visible'],
                             'status':'VISUAL_OBSERVATION_NOT_DIRECTOR_INTENT'})
            refs[case['id']]=shots
    finally:cap.release()
    return refs


def build_board(case,shots):
    cols=4;w,h=405,185;bar=49
    rows=(len(shots)+cols-1)//cols
    board=Image.new('RGB',(cols*w,rows*(h+bar)+65),'#111821')
    d=ImageDraw.Draw(board);font=_font(18)
    d.text((15,8),f'{case["id"]} · {case["title"]}',font=_font(23),fill='#f4e1bc')
    d.text((15,37),'真实原片帧（非AI生成）· 时间戳 · 局部视听观察',font=_font(15),fill='#dae0e8')
    for i,rec in enumerate(shots):
        p=ROOT/rec['path'];im=Image.open(p).convert('RGB');im.thumbnail((w-10,h))
        x=(i%cols)*w+4;y=(i//cols)*(h+bar)+65
        board.paste(im,(x,y));d.text((x+4,y+h+1),f'{rec["time_s"]:.1f}s',font=font,fill='#ffe1a7')
        desc=rec['observation'][:18]
        d.text((x+4,y+h+24),desc,font=_font(15),fill='#e1e9f4')
    path=OUT/f'{case["id"]}_真实导演观察板.jpg';board.save(path,quality=90)
    return path.relative_to(ROOT).as_posix()


def audit(scene,shots):
    """Independent, objective self-production gates, NOT an artistic-quality score."""
    issues=[];info=set(scene.get('initial_audience_knowledge',[]))
    know={k:set(v) for k,v in scene['initial_character_knowledge'].items()}
    last_end=0.0;last_positions=dict(scene['initial_positions'])
    seen_ids=set()
    for i,s in enumerate(shots):
        sid=s.get('id',f'#{i+1}');start=s.get('start_s');end=s.get('end_s')
        if sid in seen_ids:issues.append({'shot':sid,'type':'DUPLICATE_SHOT_ID'})
        seen_ids.add(sid)
        if not isinstance(start,(int,float)) or not isinstance(end,(int,float)) or end<=start:
            issues.append({'shot':sid,'type':'INVALID_DURATION'});continue
        if abs(start-last_end)>.001:issues.append({'shot':sid,'type':'GAP_OR_OVERLAP','from':last_end,'to':start})
        last_end=end
        if not s.get('single_setup',False):issues.append({'shot':sid,'type':'MULTI_SETUP_IN_SINGLE_SHOT'})
        if s.get('internal_cut',False):issues.append({'shot':sid,'type':'INTERNAL_CUT_NOT_SEPARATED'})
        if not s.get('cut_reason'):issues.append({'shot':sid,'type':'CUT_HAS_NO_DRAMATIC_REASON'})
        if not s.get('dramatic_purpose'):issues.append({'shot':sid,'type':'NO_DRAMATIC_PURPOSE'})
        if not s.get('actor_action'):issues.append({'shot':sid,'type':'MISSING_PERFORMANCE_DIRECTION'})
        if not s.get('sound'):issues.append({'shot':sid,'type':'MISSING_SOUND_PLAN'})
        if s.get('visible_to_character') and any(x not in scene['initial_character_knowledge'] for x in s['visible_to_character']):
            issues.append({'shot':sid,'type':'UNKNOWN_CHARACTER'})
        for actor,pos in s.get('positions_at_start',{}).items():
            if actor in last_positions and pos!=last_positions[actor]:
                issues.append({'shot':sid,'type':'TELEPORTATION_UNEXPLAINED','actor':actor,'expected':last_positions[actor],'actual':pos})
        for actor,pos in s.get('positions_at_end',{}).items():last_positions[actor]=pos
        previous_info=info.copy()
        for fact in s.get('revealed_to_audience',[]):info.add(fact)
        for actor,facts in s.get('learned_by_character',{}).items():
            if actor not in know:issues.append({'shot':sid,'type':'UNKNOWN_CHARACTER','actor':actor});continue
            for fact in facts:
                if fact not in scene['facts']:
                    issues.append({'shot':sid,'type':'UNREGISTERED_STORY_FACT','fact':fact})
                if fact not in s.get('evidence_audible_to_character',{}).get(actor,[]) and fact not in s.get('evidence_visible_to_character',{}).get(actor,[]):
                    issues.append({'shot':sid,'type':'UNSUPPORTED_CHARACTER_KNOWLEDGE','actor':actor,'fact':fact})
                know[actor].add(fact)
        if s.get('character_conclusion'):
            for actor,requirements in s['character_conclusion'].items():
                for fact in requirements:
                    if fact not in know.get(actor,set()):
                        issues.append({'shot':sid,'type':'CHARACTER_USES_UNKNOWN_FACT','actor':actor,'fact':fact})
    if abs(last_end-scene['target_duration_s'])>.001:
        issues.append({'shot':'END','type':'TOTAL_DURATION_MISMATCH',
                       'actual':last_end,'target':scene['target_duration_s']})
    for fact in info:
        if fact not in scene['facts']:issues.append({'shot':'END','type':'UNREGISTERED_STORY_FACT','fact':fact})
    return {'issues':issues,'issue_count':len(issues),'structural_constraints_met':not issues,
            'artistic_quality_verified':False,'spatial_3d_verified':False,
            'film_director_intent_verified':False,
            'audience_knowledge_final':sorted(info),
            'character_knowledge_final':{k:sorted(v) for k,v in know.items()}}


def negative_tests(scene,good):
    import copy
    vectors=[]
    def run_bad(label,fn,expected):
        a=copy.deepcopy(good);fn(a);errors=[x['type'] for x in audit(scene,a)['issues']]
        vectors.append({'test':label,'expected':expected,'detected':expected in errors,
                        'actual_issues':sorted(set(errors))})
    run_bad('夺取观众的私密信息', lambda x: x[2]['character_conclusion'].update({'A':['REMOTE_LOGIN']}), 'CHARACTER_USES_UNKNOWN_FACT')
    run_bad('人物瞬移',lambda x:x[3]['positions_at_start'].update({'B':'server_cage'}),'TELEPORTATION_UNEXPLAINED')
    run_bad('一个镜头暗含两套机位',lambda x:x[4].update({'single_setup':False}),'MULTI_SETUP_IN_SINGLE_SHOT')
    run_bad('剪辑时间重叠',lambda x:x[5].update({'start_s':x[4]['start_s']}),'GAP_OR_OVERLAP')
    run_bad('缺失切镜目的',lambda x:x[1].update({'cut_reason':''}),'CUT_HAS_NO_DRAMATIC_REASON')
    run_bad('声音没有设计',lambda x:x[1].update({'sound':''}),'MISSING_SOUND_PLAN')
    return {'cases':vectors,'detected_count':sum(x['detected'] for x in vectors),'total':len(vectors),
            'claim':'ONLY_DETECTION_OF_INTENTIONALLY_INJECTED_STRUCTURAL_ERRORS'}


def build_html(cases,refs,scene,initial,final,audit_before,audit_after,negative,source,boards):
    e=lambda x:html.escape(str(x),quote=True)
    blocks=[]
    for case in cases:
        frames=''.join(f'<figure><img src="{e(rec["path"])}" loading="lazy"><figcaption>{rec["time_s"]:.1f} s — {e(rec["observation"])}</figcaption></figure>' for rec in refs[case['id']])
        hypotheses=''.join(f'<li><b>{e(h["claim"])}</b> · {e(h["rationale"])}<p class="muted">其他解释：{e(h["alternative"])}；还需：{e(h["verification"])}</p></li>' for h in case['hypotheses'])
        blocks.append(f'<section class="card"><h2>{e(case["title"])}</h2><p class="muted">原片 {e(case["time_window"])} 秒 · {e(case["narrative_core"])}</p><img class="hero" src="{e(boards[case["id"]])}"><h3>逐帧事实</h3><div class="frames">{frames}</div><h3>GPT导演学习：仍待证伪的假设</h3><ul>{hypotheses}</ul><p class="call">可迁移导演方法：{e(case["transferable_craft"])}</p><p class="muted">尚未验证：{e("、".join(case["unverified"]))}</p></section>')
    table=''.join(f'<tr><td>{e(s["id"])}</td><td>{s["start_s"]:g}–{s["end_s"]:g}s</td><td>{e(s["camera"])}</td><td>{e(s["actor_action"])}</td><td>{e(s["dramatic_purpose"])}</td><td>{e(s["cut_reason"])}</td></tr>' for s in final)
    init_issues=''.join('<li>'+e(x['type'])+' · '+e(x.get('shot'))+'</li>' for x in audit_before['issues'])
    neg=''.join('<li>'+('检出' if x['detected'] else '漏检')+'：'+e(x['test'])+' / '+e(x['expected'])+'</li>' for x in negative['cases'])
    page=f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>GPT导演 · 《妖猫传》原片学习</title><style>body{{font:15px/1.7 system-ui,"Microsoft YaHei",sans-serif;background:#10141a;color:#e5e8ec;margin:0 auto;max-width:1380px;padding:22px}}h1{{font-size:28px;color:#edc891}}h2{{font-size:22px}}h3{{font-size:17px;color:#f1cf9b}}.card{{background:#192332;border:1px solid #334255;border-radius:14px;padding:20px;margin:20px 0}}.muted{{color:#a6b7c8}}.call{{border-left:3px solid #e0b874;padding:9px 16px;background:#212c39}}.hero{{width:100%;border-radius:9px}}.frames{{display:grid;grid-template-columns:repeat(4,1fr);gap:9px}}figure{{margin:0}}figure img{{width:100%;border-radius:5px}}figcaption{{font-size:12px;color:#aebfce}}table{{border-collapse:collapse;width:100%;font-size:13px}}td,th{{border-bottom:1px solid #3c4858;text-align:left;vertical-align:top;padding:8px}}.stats{{display:flex;gap:12px;flex-wrap:wrap}}.stats span{{border:1px solid #45586a;border-radius:8px;padding:12px}}.stats b{{font-size:22px;color:#f4c687}}@media(max-width:850px){{.frames{{grid-template-columns:repeat(2,1fr)}}}}</style></head><body>
<h1>GPT导演学习系统：从真实电影的导演问题开始</h1><p>本次只围绕《妖猫传》的<strong>已上传片段</strong>展开研究；不替导演判错，不推断未看到的剧情。GPT的分析是可反驳的创作假设，并非模型权重训练。</p>
<div class="stats"><span><b>{source['duration_s']:.1f}s</b>用户实际提供片段</span><span><b>{sum(len(v) for v in refs.values())}</b>复查的原片帧</span><span><b>{len(cases)}</b>手工视觉解读单元</span><span><b>{audit_before['issue_count']} → {audit_after['issue_count']}</b>原创方案结构问题</span><span><b>0</b>真正导演质量认证</span></div>
{''.join(blocks)}
<section class="card"><h2>迁移练习：《失联观测站》</h2><p>{e(scene['logline'])}</p><p>明确把「观众知道」与「角色知道」分开；用《妖猫传》“交织视线/插入信息”和“走位推进故事”的观察方法，进行原创创作，不照搬片中人物和剧情。</p><p><b>第一版审查问题：</b></p><ul>{init_issues}</ul><p class="call">GPT导演修订后，结构审查剩余：<b>{audit_after['issue_count']}</b> 项。这不是艺术质量通过。</p><table><tr><th>镜号</th><th>时段</th><th>单一机位</th><th>表演/走位</th><th>戏剧功能</th><th>切镜动机</th></tr>{table}</table><p><b>原创镜头与原片的关键区别：</b>观众通过终端插入和人物藏物动作获得先知信息；主人公没有自动获知信息。人物进出控制室必须用动作和门口/房间布局交代。</p><p class="muted">另一个可选导演策略：隐藏终端远程登录的信息，全部跟随主人公发现；可能更强化共同困惑，却减少观众先知造成的心理悬念。这两种策略没有绝对优劣，需拍摄对照后比较。</p></section>
<section class="card"><h2>独立审片的破坏性测试</h2><p>只评价自己生产的分镜结构。主动注入知识越权、人物瞬移、双机位、时间重叠、无切镜原因、缺声音6类问题：</p><ul>{neg}</ul><p><b>{negative['detected_count']}/{negative['total']}</b> 检出。此数字不是专业导演能力评分。</p></section>
<section class="card"><h2>这次还没达到的目标</h2><p>原片字幕台词和声音语义未解析；真正导演意图未证实；没有生成独立AI人物画面，没有真实表演、三维调度、视频作品和专业盲评。现有GPT导演分析仍由本次对话监督并记录，<strong>不会自动改变GPT底层模型权重。</strong></p></section></body></html>'''
    path=ROOT/'GPT_DIRECTOR_FILM_STUDY.html';path.write_text(page,encoding='utf-8')
    return path.relative_to(ROOT).as_posix()


def run():
    source=verify_source();cases=load(CASES)['cases'];scene_data=load(SCENE)
    source_frames=extract_frames(cases)
    boards={c['id']:build_board(c,source_frames[c['id']]) for c in cases}
    scene=scene_data['scene'];initial=scene_data['initial_draft'];final=scene_data['revised_shots']
    pre=audit(scene,initial);post=audit(scene,final)
    neg=negative_tests(scene,final)
    if post['issue_count']:raise AssertionError('Revised storyboard has unresolved structural issues: '+str(post['issues']))
    if neg['detected_count']!=neg['total']:raise AssertionError('Independent structural critic misses negative cases')
    if pre['issue_count']<3:raise AssertionError('Draft no longer demonstrates meaningful corrections')
    report={'source':source,'study_cases':cases,'frame_references':source_frames,
       'boards':boards,'scene':scene,'initial_draft':initial,'final_director_draft':final,
       'initial_critique':pre,'final_structural_audit':post,'negative_tests':neg,
       'model_used_for_directing':'GPT conversation visual analysis, manually saved as study cases',
       'director_intent_verified':False,'new_ai_image_generated':False,'new_film_generated':False,
       'director_quality_signoff':False}
    save(OUT/'study_and_rehearsal.json',report)
    page=build_html(cases,source_frames,scene,initial,final,pre,post,neg,source,boards)
    summary={'source_verified':True,'original_excerpt_s':source['duration_s'],
             'visual_frames_reinspected':sum(len(x) for x in source_frames.values()),
             'learned_provisional_case_studies':len(cases),'initial_storyboard_issues':pre['issue_count'],
             'revised_storyboard_issues':post['issue_count'],
             'independent_negative_detection':f"{neg['detected_count']}/{neg['total']}",
             'report':'output/gpt_director_study/study_and_rehearsal.json','interactive_page':page,
             'director_artistry_verified':False,'real_ai_movie_generated':False}
    save(OUT/'acceptance.json',summary)
    return summary


def main():
    ap=argparse.ArgumentParser();sp=ap.add_subparsers(dest='cmd',required=True)
    sp.add_parser('run');p=sp.add_parser('audit');p.add_argument('storyboard_json')
    a=ap.parse_args()
    if a.cmd=='run':print(json.dumps(run(),ensure_ascii=False,indent=2))
    elif a.cmd=='audit':
        data=load(SCENE);shots=load(a.storyboard_json)
        if isinstance(shots,dict):shots=shots['shots']
        print(json.dumps(audit(data['scene'],shots),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
