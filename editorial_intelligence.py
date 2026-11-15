#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Director's editing language laboratory, grounded in source frames.

The *film* is the teacher, NOT an object to flag for visual discontinuity.
A visual cut is a unit of cinematic language. Its *intent* is a hypothesis
until supported by scene context / sound / an editorial review.

No model calls, claims of AI-generated art, or external connections.
"""
from __future__ import annotations
import argparse, hashlib, html, json, math, re, statistics, subprocess
from datetime import datetime, timezone
from pathlib import Path
import cv2
import numpy as np

BASE=Path(__file__).resolve().parent
FRAME_OUT='output/editorial_language'
ALLOWED_RELATIONS={
 'SPATIAL_ESTABLISH_TO_DETAIL':'建立空间→细节',
 'INSERT_SHOT':'插入镜头／新信息',
 'REACTION_SHOT':'反应镜头',
 'SHOT_REVERSE_SHOT':'正反打（可能）',
 'RE_ESTABLISH':'空间重新定位',
 'ACTION_MATCH':'动作匹配剪辑（待核实）',
 'EYELINE_MATCH':'视线匹配（待核实）',
 'PARALLEL_MONTAGE':'平行蒙太奇（待核实）',
 'TEMPORAL_ELLIPSIS':'时间省略／跳切（待核实）',
 'RHYTHMIC_CONTRAST':'节奏对比／视觉对位',
 'SCENE_TRANSITION':'场景转换',
 'OTHER':'其他／需要进一步理解',
 'UNKNOWN':'尚未判断',
}

# Selected visual hypotheses from the CURRENT uploaded 12:56 material and its
# actual MID keyframes. No assertions of plot, character identity, dialogue.
LESSONS=[
 {'id':'LESSON_01','title':'人物→黑猫→人物：插入与反应的注意力组织',
  'shots':['SH_00065','SH_00066','SH_00067'],
  'observable':'前镜画面为几名红衣人物与建筑；中镜是栏杆上的黑猫；后镜为一名男子近景。',
  'hypothesis':'把视觉焦点从人的行动转到黑猫，再切回人的面部，可构成“发现／提示／反应”的电影语法；是否为真实因果必须结合视线和音轨。',
  'alternatives':['三个镜头也可能在交替建立不同地点／时间的信息','黑猫可能是独立悬念意象，而不是被镜中人物看见'],
  'verify':['逐帧确认黑猫出现前后人物是否朝向其位置','检查猫声、音乐和画外音是否跨切点衔接','核对是否同一场次与可见空间'],
  'teachable_rule':'当观众需要注意一个关键对象，可以用“人物处境→信息插入→人物反应”建立观看路径；不要把跨镜颜色变化当错误。',
  'transfer':'原创科幻片：研究员看到异常→仪表上的未知信号→研究员克制反应',
  'narrative_approved':False},
 {'id':'LESSON_02','title':'环境→人物→环境：让空间成为悬念',
  'shots':['SH_00062','SH_00063','SH_00064','SH_00068','SH_00069'],
  'observable':'可见栏杆与光源导向、暗处通道和远方亮口、人物近景，以及随后回到洞口／门边的画面。',
  'hypothesis':'环境远景与人物表情交替，可以让空间本身提供悬念对象，再让面部承担感受与判断。',
  'alternatives':['存在段落间的场景切换，不能直接推断同一连续空间','近景人物可能是在回应画外声音，而非空间本身'],
  'verify':['用连续原片确认空间方向与出入口关系','检查人物视线是否指向亮口及动作起止','区分摄影机运动与人物移动'],
  'teachable_rule':'用遮挡、亮口和远近关系控制信息释放；反应镜头应服务观众知道什么，而不是机械追求相邻画面相似。',
  'transfer':'原创悬疑片：暗走廊的远处门缝亮起→人物听见声响→回到门缝并出现新细节',
  'narrative_approved':False},
 {'id':'LESSON_03','title':'僧人→对方→僧人→室内：对话与空间重定位',
  'shots':['SH_00070','SH_00071','SH_00072','SH_00073','SH_00074'],
  'observable':'先出现明亮室内；随后浅衣僧人近景、深衣人物镜头、再到僧人侧面及室内双人／场景调度画面。',
  'hypothesis':'可能呈现“建立空间→角色A→角色B→角色A→重新交代二人位置”的反打语法，用镜头切换组织对话注意力。',
  'alternatives':['未核对对白前，不能确认是谁在讲话或倾听','SH_00074本身较长，必须核对内部是否存在正常剪辑'],
  'verify':['核对70—74实际对白音轨与说话人的对应','验证180度轴线、左右画面方向和角色视线','标记停顿、说话／听话、情绪变化的切点'],
  'teachable_rule':'对话戏不是平均轮流给脸：先建立两人空间，再依据话语和反应切换视角，必要时回到双人镜头重新说明空间关系。',
  'transfer':'原创职场戏：控制室双人站位→负责人发问→技术员回应→负责人沉默→双人中景解除张力',
  'narrative_approved':False},
]

# A small number of pairs given provisional editorial-reading prompts.
# No auto relabeling of remaining source edits based on pixel distance.
PAIR_HINTS={
 (62,63):('SPATIAL_ESTABLISH_TO_DETAIL','栏杆的纵深和暗通道亮口相继出现，可能逐步引导观众进入空间。','也可能是两个地点的交替展示'),
 (63,64):('REACTION_SHOT','亮口远景之后切人物面部，可研究环境信息和人物心理的关系。','人物可能回应场外声音而不是远景'),
 (65,66):('INSERT_SHOT','红衣人物场景后切到黑猫的独立画面，物体插入可能重新分配叙事关注。','尚不能确认人物确实看见猫'),
 (66,67):('REACTION_SHOT','猫的全身画面之后出现男性近景，可能是物体—人物的反应结构。','也可能平行交替呈现不同地点'),
 (67,68):('RHYTHMIC_CONTRAST','人物特写切回深暗洞口和远处亮区，可能把关注重新交给空间。','不一定与前一人处在同一空间'),
 (70,71):('SPATIAL_ESTABLISH_TO_DETAIL','明亮室内空间后出现僧人近景，可研究从空间到人物的注意力缩放。','可能已出现独立场次的切换'),
 (71,72):('SHOT_REVERSE_SHOT','僧人与深衣人物的镜头可作为对话反打假设来核验。','需要音轨、机位轴线、视线方向确认'),
 (72,73):('SHOT_REVERSE_SHOT','深衣人物后重新切僧人的侧面，值得核对反打与倾听反应。','也可能是非对话视线关系'),
 (73,74):('RE_ESTABLISH','僧人近景后转室内较广镜头，可能重新交代两人的空间关系。','较长的镜头卡可能包含独立剪辑，先确认边界'),
}

def read_json(path, default):
    p=Path(path)
    return json.loads(p.read_text(encoding='utf-8')) if p.is_file() else default

def write_json(path, data):
    p=Path(path);p.parent.mkdir(exist_ok=True,parents=True)
    t=p.with_suffix(p.suffix+'.tmp')
    t.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    t.replace(p)

def hash_file(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def image_signature(path):
    im=cv2.imread(str(path))
    if im is None:raise FileNotFoundError(path)
    small=cv2.resize(im,(144,64),interpolation=cv2.INTER_AREA)
    lab=cv2.cvtColor(small,cv2.COLOR_BGR2LAB).astype(np.float32)
    gray=cv2.cvtColor(small,cv2.COLOR_BGR2GRAY)
    return {'mean_luma':float(np.mean(gray)/255.0),
      'mean_lab':list(np.mean(lab,axis=(0,1)).round(2).astype(float)),
      'detail':float(cv2.Laplacian(gray,cv2.CV_32F).var())}

def reference_audio_samples(root,rate=8000):
    """Decode the user's actual source audio locally; no ASR or sound attribution."""
    f=Path(root)/'data/source_video.mp4'
    if not f.is_file():return None
    try:
        p=subprocess.run(['ffmpeg','-nostdin','-hide_banner','-loglevel','error',
                          '-i',str(f),'-vn','-ac','1','-ar',str(rate),
                          '-f','f32le','pipe:1'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=75)
        if p.returncode!=0 or len(p.stdout)<rate*4:return None
        return np.frombuffer(p.stdout,dtype='<f4')
    except (OSError,subprocess.TimeoutExpired):return None

def audio_cut_measurement(samples,second,rate=8000):
    if samples is None:return {'status':'NO_DECODABLE_AUDIO','dialogue_or_music_classified':False}
    pos=round(second*rate);w=round(.48*rate);gap=round(.04*rate)
    if pos-w-gap<0 or pos+w+gap>len(samples):return {'status':'OUT_OF_AUDIO_RANGE','dialogue_or_music_classified':False}
    before=samples[pos-gap-w:pos-gap];after=samples[pos+gap:pos+gap+w]
    a=float(np.sqrt(np.mean(before*before)));b=float(np.sqrt(np.mean(after*after)))
    # Relative spectral difference can reveal an abrupt change in the sound bed;
    # it cannot tell whether the cut is a J-cut, L-cut, dialogue, music or foley.
    speca=np.abs(np.fft.rfft(before*np.hanning(len(before))))
    specb=np.abs(np.fft.rfft(after*np.hanning(len(after))))
    dot=float(np.dot(speca,specb))
    cos=dot/(float(np.linalg.norm(speca)*np.linalg.norm(specb))+1e-10)
    ratio=min(a,b)/max(a,b,1e-9)
    label='SOUND_ENERGY_BOTH_SIDES' if min(a,b)>.005 else 'ONE_OR_BOTH_SIDES_QUIET'
    return {'status':'MEASURED_REFERENCE_ONLY','rms_before':round(a,5),'rms_after':round(b,5),
            'energy_similarity_ratio':round(ratio,3),'spectral_shape_cosine_proxy':round(cos,3),
            'possible_audible_layer_across_cut':label,
            'sound_bridge_verified':False,'dialogue_or_music_classified':False,
            'warning':'音频信号连续仅是技术线索；不能证明电影有声桥或对白对位。'}

def transition_dataset(root=BASE, cards=None):
    root=Path(root)
    cards=cards if cards is not None else read_json(root/'output/director_lab/director_cards.json',[])
    pairs=[]
    samples=reference_audio_samples(root)
    for a,b in zip(cards,cards[1:]):
        aid=a['shot_id'];bid=b['shot_id'];x=int(aid.split('_')[-1]);y=int(bid.split('_')[-1])
        pa=root/a['reference_images']['out'];pb=root/b['reference_images']['in']
        ia,ib=image_signature(pa),image_signature(pb)
        gap=round(abs(ia['mean_luma']-ib['mean_luma']),3)
        lab=round(math.sqrt(sum((u-v)**2 for u,v in zip(ia['mean_lab'],ib['mean_lab'])))/255,3)
        hint=PAIR_HINTS.get((x,y))
        notes=({'type':hint[0],'primary_hypothesis':hint[1],'alternative_explanation':hint[2],
                'evidence_status':'HYPOTHESIS_FROM_VISIBLE_SOURCE_FRAMES','verified':False}
               if hint else {'type':'UNKNOWN','primary_hypothesis':'需要结合该处前后画面、剧情、对白及声音判断切镜功能。',
                             'alternative_explanation':'视觉差异不是剪辑错误。','evidence_status':'NOT_YET_STUDIED','verified':False})
        pairs.append({'id':aid+'__'+bid,'from':aid,'to':bid,
          'cut_time_sec':b['time']['start'],'out_frame':a['reference_images']['out'],
          'in_frame':b['reference_images']['in'],'out_sha256':a['anchor_source_shas']['out'],
          'in_sha256':b['anchor_source_shas']['in'],
          'out_shot_duration_sec':a['time']['duration'],'in_shot_duration_sec':b['time']['duration'],
          'sound_at_cut':audio_cut_measurement(samples,b['time']['start']),
          'proxies':{'brightness_abs_difference':gap,'lab_color_difference_proxy':lab,
                     'out_duration_sec':a['time']['duration'],'in_duration_sec':b['time']['duration']},
          'film_quality_fault':False, 'visual_change_is_defect':False,
          'cut_boundary_status':'AUTO_PROPOSED_NOT_EDITORIALLY_CONFIRMED',
          'director_interpretation':notes,'human_review':None})
    return pairs

def case_studies(root=BASE):
    root=Path(root)
    cards=read_json(root/'output/director_lab/director_cards.json',[])
    by_id={x['shot_id']:x for x in cards}
    out=[]
    for l in LESSONS:
        if not all(i in by_id for i in l['shots']):continue
        out.append({**l,
          'reference_mid_frames':[by_id[i]['reference_images']['mid'] for i in l['shots']],
          'reference_sha256':[by_id[i]['anchor_source_shas']['mid'] for i in l['shots']],
          'grounding':'ASSISTANT_VISUAL_INTERPRETATION_NOT_MODEL_OR_DIRECTOR_VERIFIED',
          'film_learning_not_film_fault_detection':True})
    return out

# Structured, inexpensive editorial production previsualisation.  This is
# algorithmic storyboard *planning*, not images or autonomous artistic success.
PATTERNS=('suspense_insert','dialogue_reactions','spatial_reveal')
PATTERN_NAMES={'suspense_insert':'信息插入与反应',
               'dialogue_reactions':'对话反打与空间重定位',
               'spatial_reveal':'空间悬念与信息控制'}

def _make_shot(index,code,seconds,purpose,camera,blocking,acting,cut_reason,sound,question=None):
    return {'id':f'GEN_{index:02d}','beat':code,'duration_s':seconds,
      'narrative_purpose':purpose,'camera':camera,'blocking':blocking,
      'acting':acting,'cut_reason':cut_reason,'sound_cue':sound,
      'audience_question':question or ''}

def _generate_full(brief,pattern):
    if pattern=='dialogue_reactions':
        config=[
        ('ESTABLISH',3.2,'建立人物相对位置、动作空间和对话轴线','双人中景／机位在轴线一侧','人物A在左、人物B在右；记录双方视线方向','对话之前一个可见的迟疑','观众知道谁与谁同场','室内环境底噪','两个人为何沉默？'),
        ('SPEAKER_A',2.4,'人物A提出新信息或问题','人物A近景，同一轴线侧','A偏左看向画外B','开口或目光停顿必须明确','将注意力交给听话者','对白A或临时静音节拍','B会如何回应？'),
        ('LISTENER_B',1.8,'让人物B倾听而非机械轮流说话','人物B反向近景，保持视线方向成立','B面向画外A','先听后微表情反应','情绪比台词更重要时切到B','对白尾音跨切点','B相信这句话吗？'),
        ('SPEAKER_B',2.5,'B提供改变情境的回应','B中近景','保持位置及服装版本不变','明确回应与呼吸时刻','交给A进行评估','对白B','A如何作出判断？'),
        ('REACTION_A',1.9,'A在关键句之后沉默，构成反应','人物A静近景','A朝B视线方向稳定','眼神和呼吸层面的表演节拍','由说话切到被影响的人','声音留白0.5秒','他们之间的关系是否改变？'),
        ('RE_ESTABLISH',3.3,'回到双人空间，验证关系和情绪距离','双人中／远景，轴线侧稳定','空间与初镜一致，人物距离可做有目的变化','一人转身或停留','关系被重新定义后用空间收束','环境声盖过对白','下一个行动是什么？')]
    elif pattern=='spatial_reveal':
        config=[
        ('ESTABLISH',3.5,'只交代可见入口和行动目标，不一次展示所有空间','远景，有方向性的遮挡和明暗','主体在前景，目标只露局部','先停住再靠近','形成空间期待','远处声音先于物体出现','光亮后是什么？'),
        ('POV_HINT',2.2,'沿人物视线给出目标的局部信息','中景／近景，遮挡保留','视线与目标方向需要可追溯','视线微调','从人物需要切向视觉证据','声源方向保持','目标安全吗？'),
        ('INSERT',1.4,'关键细节提供新的可见线索','特写，避免用全景解释一切','道具与场景对应，ID仍需锁定','信息出现但不解释','让观众比人物先知道一点','短音效与细节同步','这个痕迹意味着什么？'),
        ('REACTION',2.3,'人物因新信息而改变行动','近景，保留背景空间指引','人物与门框/光源方向一致','由试探转为确定','以反应确认上一镜的意义','短暂静音','他会继续前进吗？'),
        ('BLOCKING',3.4,'给出空间内的行动路径及障碍物','有纵深的中远景','相对距离、入口、障碍要可验证','行动开始与中止时刻清楚','完成空间与动作衔接','脚步与环境声','会遭遇谁？')]
    else:
        config=[
        ('SETUP',3.0,'建立人物当下处境与尚未解决的问题','人物和环境的中景','保留关键视线方向与空间关系','动作或注意力开始集中','引出悬念而非展示全部答案','环境声音底','会发生什么？'),
        ('INSERT',1.7,'切到关键物件／异常讯息','突出细节的特写','插入对象有明确环境位置，但不可凭空新增','异常讯息出现','改变观众当前的信息量','一个可辨认的音效','人物看见了吗？'),
        ('REACTION',2.0,'切回人物，表现得知线索后的微妙反应','人物近景','人物视线要与插入对象匹配或标记不确定','眼神先于身体动作改变','反应镜头承接新信息','音乐弱化让反应清晰','他是否理解了线索？'),
        ('COUNTERPOINT',2.6,'以另一视觉信息给出第二层解释','带环境线索的中景','保持真实地理方向或明确标记蒙太奇','不要与前镜完全重复','剪辑提供新的信息，而非机械连镜','声桥连接两镜','这个异常来自哪里？'),
        ('DECISION',3.1,'角色做出行动选择，并给下场戏入口','中远景／有移动余地','人物动作终点与后续切点可对齐','从观察到行动的起止节拍清楚','建立因果推进','脚步声启动','下一场戏如何发展？')]
    return [_make_shot(i+1,*x) for i,x in enumerate(config)]

def grade_structure(shots,pattern):
    beats=[x['beat'] for x in shots]
    rules={
       '镜头各有明确戏剧功能':all(bool(x['narrative_purpose'].strip()) for x in shots),
       '镜头切换有叙事理由':all(bool(x['cut_reason'].strip()) for x in shots),
       '人物调度约束已填写':all(bool(x['blocking'].strip()) for x in shots),
       '表演节拍有约束':all(bool(x['acting'].strip()) for x in shots),
       '音画关系有规划':all(bool(x['sound_cue'].strip()) for x in shots),
       '观众问题被设置':any(bool(x['audience_question'].strip()) for x in shots),
       '镜头长度明确':all(0.3<=float(x['duration_s'])<=30 for x in shots),
       '存在建立空间或处境的镜头':any(x in beats for x in ['ESTABLISH','SETUP']),
       '悬念信息后有反应承接':pattern=='dialogue_reactions' or ('INSERT' in beats and 'REACTION' in beats and beats.index('INSERT')<beats.index('REACTION')),
       '对话场面交代双方空间关系':pattern!='dialogue_reactions' or ('SPEAKER_A' in beats and 'LISTENER_B' in beats and 'RE_ESTABLISH' in beats),
       '结尾具备下一步动作或空间归位':beats[-1] in ['RE_ESTABLISH','DECISION','BLOCKING'],
    }
    return {'rule_checks':rules,'structural_check_passed':sum(rules.values()),
            'structural_check_total':len(rules),
            'director_quality_verified':False,
            'acting_and_identity_verified':False,
            'content_produced_as_ai_images':False,
            'meaning':'规则检查只证明文字分镜的结构约束完整，不代表导演质量得分。'}

def extract_brief_cues(brief):
    """Conservative rule-based cues, never claims to have understood the screenplay."""
    vocab={'possible_character_terms':['工程师','船长','声呐员','警察','研究员','侍卫','僧人','乘客','船员','医生','老师','同伴'],
           'possible_key_objects':['信号','来信','门缝','屏幕','黑猫','猫','密信','脚印','声音','光','探测器','无人机','警报','电话'],
           'possible_places':['科研站','潜艇','控制室','实验室','海面','小镇','宫廷','走廊','房间','船舱','码头']}
    cues={k:[w for w in vals if w in brief] for k,vals in vocab.items()}
    cues['extraction_kind']='KEYWORD_MATCH_ONLY_NOT_NARRATIVE_MODEL'
    return cues

def design_scene(brief,pattern='suspense_insert'):
    if not isinstance(brief,str) or not (3<=len(brief.strip())<=1500):raise ValueError('输入3到1500字的原创场景简介')
    if pattern not in PATTERNS:raise ValueError('未知导演语法类型')
    full=_generate_full(brief,pattern)
    cues=extract_brief_cues(brief)
    place='／'.join(cues['possible_places']) or '待确认场景'
    actor='、'.join(cues['possible_character_terms']) or '未提及的角色'
    object_='、'.join(cues['possible_key_objects']) or '待确定叙事关键物'
    for shot in full:
        shot['source_story_brief']=brief.strip()
        shot['source_specific_scenario_cues']={'place':place,'people':actor,'key_object':object_}
        shot['shootable_director_prompt_draft']=(
          f'原剧情：{brief.strip()}；场景参考：{place}；人物观察对象：{actor}；'
          f'关键叙事物：{object_}。本镜头要做：{shot["narrative_purpose"]}；'
          f'摄影：{shot["camera"]}；表演：{shot["acting"]}；'
          f'切镜因由：{shot["cut_reason"]}。所有未知身份与地理关系必须先核验。')
    # Deliberate baseline: no time/space re-establishment or expressive listening.
    weak=[dict(x) for x in full]
    weak=[x for x in weak if x['beat'] not in ('REACTION','LISTENER_B','RE_ESTABLISH','DECISION','BLOCKING')]
    for w in weak[1:]:w['cut_reason']=''
    before=grade_structure(weak,pattern);after=grade_structure(full,pattern)
    missing=[k for k,v in before['rule_checks'].items() if not v]
    return {'brief':brief.strip(),'detected_brief_cues':cues,'chosen_grammar':pattern,'grammar_label':PATTERN_NAMES[pattern],
      'method':'RULE_BASED_EDITORIAL_PLANNING_NOT_AUTONOMOUS_CINEMATIC_AI',
      'original_filmmaking_context':'同样的剪辑语法可迁移到原创剧本，但所有角色、空间、表演与效果仍需真实审查。',
      'iteration_trace':[
       {'round':0,'version':'INITIAL_UNDER_SPECIFIED','shots':weak,'technical_review':before,'issues':missing},
       {'round':1,'version':'REVISED_WITH_EDITORIAL_BEATS','shots':full,'technical_review':after,'changes':['明确每镜戏剧目的与切镜理由','补充信息与反应关系','增加人物动作／视线和音画节拍','增加空间交代／结束动作']},
      ],'required_final_checks':['原创剧情及情绪强度的真实导演判断','场景空间轴线与演员站位','角色身份及服装一致性',
        '是否存在不必要镜头／是否应该省略','演员动作与声音时间码','完整静态分镜独立生成与人工验收'],
      'real_image_model_called':False,'paid_video_model_called':False,'fully_directed_movie':False}

def save_director_edit(root, transition_id, relation, hypothesis, evidence, reviewer):
    root=Path(root)
    all_transitions=read_json(root/FRAME_OUT/'transitions.json',[])
    t=next((x for x in all_transitions if x['id']==transition_id),None)
    if t is None:raise ValueError('Unknown transition')
    if relation not in ALLOWED_RELATIONS:raise ValueError('Unsupported relation type')
    if not isinstance(hypothesis,str) or len(hypothesis.strip())<5 or len(hypothesis)>2200:raise ValueError('Hypothesis length invalid')
    if not isinstance(evidence,str) or len(evidence)>3000:raise ValueError('Evidence too long')
    if not isinstance(reviewer,str) or len(reviewer)>150:raise ValueError('Invalid reviewer')
    if hash_file(root/t['out_frame'])!=t['out_sha256'] or hash_file(root/t['in_frame'])!=t['in_sha256']:
        raise ValueError('Source frame changed. Rebuild analysis before editing.')
    p=root/'data/editorial_director_reviews.json';prev=read_json(p,{})
    old=prev.get(transition_id)
    entry={'transition_id':transition_id,'relation':relation,'hypothesis':hypothesis.strip(),
           'evidence':evidence.strip(),'reviewer':reviewer.strip(),
           'status':'REVIEWED_REFERENCE_RELATION_NOT_AI_RECONSTRUCTION_APPROVAL',
           'source_hashes':[t['out_sha256'],t['in_sha256']],
           'reference_only':True,'director_approval':False,
           'revision':(old or {}).get('revision',0)+1,
           'saved_utc':datetime.now(timezone.utc).isoformat()}
    if old and all(old.get(k)==entry[k] for k in ('relation','hypothesis','evidence','reviewer')):return old
    prev[transition_id]=entry;write_json(p,prev)
    # Keep the standalone offline HTML consistent after an actual browser edit.
    if (root/'EDITORIAL_DIRECTOR_LAB.html').exists():
        studies=read_json(root/FRAME_OUT/'director_lessons.json',[])
        exercise=read_json(root/FRAME_OUT/'original_scene_rehearsal.json',{})
        meta=read_json(root/FRAME_OUT/'acceptance.json',{})
        if exercise:
            meta['saved_reviews']={k:v for k,v in prev.items()
                                   if k in {z['id'] for z in all_transitions}}
            build_html(root,{'transitions':all_transitions,'lessons':studies,
                             'transfer_example':exercise,'summary':meta})
    return entry

def build_study_board(root,cases):
    from PIL import Image,ImageDraw,ImageFont
    width=1200;pad=18;columns=5;tilew=225;tileh=155
    height=150+len(cases)*230
    im=Image.new('RGB',(width,height),'#0b1422');d=ImageDraw.Draw(im)
    try:font=ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',17)
    except OSError:font=ImageFont.load_default()
    try:big=ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',24)
    except OSError:big=font
    d.text((25,19),'电影导演语法：真实素材镜头组合观察',font=big,fill='#f4e4c4')
    d.text((25,62),'只研究镜头组合为什么可能有效；剪辑中的画面变化不是影片错误。',font=font,fill='#b5c9df')
    d.text((25,94),'素材：上传的12分56秒片段 | 所有下方截图均为原片参考，不是独立AI生成。',font=font,fill='#c2c8d4')
    for row,c in enumerate(cases):
        y=140+230*row
        d.text((pad,y),f"{c['id']}   {c['title']}",font=font,fill='#e9c58d')
        for i,(sid,p) in enumerate(zip(c['shots'],c['reference_mid_frames'])):
            x=pad+235*i
            frame=Image.open(root/p).convert('RGB');frame.thumbnail((tilew,115))
            d.rectangle((x,y+34,x+tilew,y+169),outline='#354b65',width=1)
            im.paste(frame,(x+2,y+43))
            d.text((x+6,y+176),sid+'  · 原片参考',font=font,fill='#d4e2f0')
    target=root/FRAME_OUT/'导演剪辑语法_三组真实分镜.jpg';target.parent.mkdir(exist_ok=True,parents=True)
    im.save(target,quality=88)
    return str(target.relative_to(root))

def build_html(root,result):
    root=Path(root)
    cards=result['transitions'];lessons=result['lessons'];design=result['transfer_example']
    data=json.dumps({'transitions':cards,'lessons':lessons,'example':design,'summary':result['summary']},ensure_ascii=False,separators=(',',':')).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    tpl=r'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>电影导演 · 剪辑语言学习实验室</title><style>
    :root{background:#0c1320;color:#e8f1fa;font:15px/1.6 system-ui,'Noto Sans CJK SC','Microsoft YaHei',sans-serif}*{box-sizing:border-box}body{margin:0}header{padding:21px 26px;background:#172538;border-bottom:1px solid #2e4764}h1{font-size:24px;margin:0 0 5px}h2{font-size:18px;color:#f1d3a5;margin:9px 0}h3{font-size:15px;color:#e6c6a0}p{margin:7px 0}small,.muted{color:#aebfd0}a{color:#8ad5ff}.nav{display:flex;gap:14px;flex-wrap:wrap;margin:9px 0}.main{max-width:1480px;margin:0 auto;padding:18px;display:grid;grid-template-columns:minmax(280px,370px) minmax(0,1fr);gap:15px}.pane{background:#172538;border:1px solid #30475f;border-radius:13px;padding:17px;margin-bottom:14px}button,select,input,textarea{font:inherit;border:1px solid #496887;background:#20344a;color:#eaf1f7;border-radius:7px;padding:8px}button{cursor:pointer}button.active{background:#496983;color:white}input,textarea,select{width:100%}textarea{min-height:85px}label{color:#b5cde1;display:block;margin:10px 0 4px}img{max-width:100%;border-radius:7px}.frames{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:9px}.frames img{width:100%;aspect-ratio:1280/534;object-fit:contain;background:#080e17}.scroller{max-height:430px;overflow:auto;display:flex;flex-direction:column;gap:5px}.scroller button{text-align:left}.case{padding:12px;border:1px solid #354b63;border-radius:8px;margin:12px 0}.chips{display:flex;gap:8px;flex-wrap:wrap}.chip{background:#293b52;padding:5px 8px;border-radius:6px}.gold{color:#f5ca92}.warning{color:#e8b788}.shots{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:9px}.shots .card{background:#1d2f46;border:1px solid #35516d;border-radius:9px;padding:9px}.shots .card b{color:#b9d8ef}.shots img{width:100%;aspect-ratio:1280/534;object-fit:cover}.trace{padding:12px;border-left:3px solid #caad7b;background:#1d3043;margin:9px 0}footer{padding:20px;text-align:center;color:#b5c6d9}@media(max-width:850px){.main{grid-template-columns:1fr}.scroller{max-height:240px}}
    </style></head><body><header><h1>导演与编剧 · 电影剪辑语言学习实验室</h1><p>通过真实精品电影，研究<strong>导演为何选择这些镜头、为何此刻剪切、观众获得了什么信息</strong>。切镜不是错误，视觉差异不等于不连贯。</p><div class="nav"><a href="/director">导演镜头卡</a><a href="/longform">完整分镜</a><a href="/cuts">技术切点复核</a><a href="/">制作工作台</a></div></header>
    <main class="main"><aside><section class="pane"><h2>研究范围与真实性</h2><div id="stats"></div><p class="warning">本实验的导演解释属于可核验假设。没有完整对白转写、身份锁定和人工场次确认，不可据此认定剪辑意图已被识别成功。</p></section>
    <section class="pane"><h2>85处镜头衔接</h2><input id="search" placeholder="搜索镜头号，例如 00066" oninput="nav()"><div class="scroller" id="transitions"></div></section></aside>
    <section><div class="pane"><h2>逐切镜导演阅读：对比的是关系，不是像素质量</h2><div id="detail"></div></div>
    <div class="pane"><h2>从影片中研究的三种镜头语法</h2><div id="lessons"></div></div>
    <div class="pane"><h2>迁移试拍：输入原创场景，用学到的语法设计镜头</h2><p class="muted">无付费视频模型。下方是规则驱动的文字分镜规划与自我检查，不是AI画面或真实导演签核。</p><label>原创场景</label><textarea id="brief"></textarea><label>采用哪类电影镜头语法</label><select id="pattern"><option value="suspense_insert">信息插入与反应</option><option value="dialogue_reactions">对话反打与空间重定位</option><option value="spatial_reveal">空间悬念与信息控制</option></select><button onclick="plan()">生成文字分镜 → 自查 → 定向修正</button><div id="transfer"></div></div></section></main><footer>真实影片仅为导演语法参考样本。原片截图不等于AI生成；规则完整不等于艺术质量合格；未经验证不得宣称100%复刻。</footer>
    <script type="application/json" id="dataset">__DATA__</script><script>
    const D=JSON.parse(document.getElementById('dataset').textContent),pairs=D.transitions,lessons=D.lessons;let selected=pairs.find(x=>x.from==='SH_00065')?.id||pairs[0]?.id;const esc=s=>String(s??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');const pic=p=>location.protocol.startsWith('http')?'/file?path='+encodeURIComponent(p):p;
    const specs={'UNKNOWN':'尚未判断','SPATIAL_ESTABLISH_TO_DETAIL':'空间→细节','INSERT_SHOT':'信息插入','REACTION_SHOT':'反应镜头','SHOT_REVERSE_SHOT':'正反打','RE_ESTABLISH':'重建空间','ACTION_MATCH':'动作匹配','EYELINE_MATCH':'视线匹配','PARALLEL_MONTAGE':'平行蒙太奇','TEMPORAL_ELLIPSIS':'时间省略','RHYTHMIC_CONTRAST':'视觉对位','SCENE_TRANSITION':'场景转换','OTHER':'其他'};
    document.getElementById('stats').innerHTML=`<div class="chips"><span class="chip">参考镜头 ${D.summary.reference_shots}</span><span class="chip">相邻切镜 ${D.summary.cut_relations}</span><span class="chip">目视分析案例 ${D.summary.provisional_lessons}</span><span class="chip">AI复刻验收 0</span></div><p class="muted">已观察的具体切镜假设 ${D.summary.provisional_pair_hypotheses}处，其余仍待剧情理解。所有标签均是<strong>学习假设</strong>。</p>`;
    function nav(){const q=document.getElementById('search').value.trim().toLowerCase();document.getElementById('transitions').innerHTML=pairs.filter(p=>p.id.toLowerCase().includes(q)).map(p=>`<button class="${selected===p.id?'active':''}" onclick="pick('${p.id}')">${esc(p.from)} → ${esc(p.to)} <small>${esc(p.director_interpretation.type)}</small></button>`).join('')};function pick(id){selected=id;nav();let p=pairs.find(z=>z.id===id);if(!p)return;let s=p.director_interpretation;document.getElementById('detail').innerHTML=`<h3>${esc(p.from)} → ${esc(p.to)} · ${p.cut_time_sec.toFixed(2)}秒</h3><div class="frames"><div><small>切前原片 OUT</small><img src="${pic(p.out_frame)}"></div><div><small>切后原片 IN</small><img src="${pic(p.in_frame)}"></div></div><p class="gold"><b>待检验的剪辑功能：</b>${esc(specs[s.type]||s.type)}</p><p>${esc(s.primary_hypothesis)}</p><p class="muted">另一种可能：${esc(s.alternative_explanation)}</p><p>亮度绝对差 ${p.proxies.brightness_abs_difference}；色彩代理差 ${p.proxies.lab_color_difference_proxy}。<b>这些只描述变化，绝不是电影质量扣分。</b></p><p>原片音轨：${esc(p.sound_at_cut.status)}；切前RMS ${esc(p.sound_at_cut.rms_before??'无')} → 切后RMS ${esc(p.sound_at_cut.rms_after??'无')}；频谱代理相似度 ${esc(p.sound_at_cut.spectral_shape_cosine_proxy??'无')}。<small>只是声学线索，不等于确认声桥、对白或音乐。</small></p><p class="muted">切点是算法建议，镜头本身可能需要二次复核。</p><label>剪辑关系</label><select id="relation">${Object.entries(specs).map(([k,v])=>`<option ${s.type===k?'selected':''} value="${k}">${v}</option>`).join('')}</select><label>对导演意图的推断</label><textarea id="hypothesis">${esc(s.primary_hypothesis)}</textarea><label>证据或待复核点（音轨／视线／动作／剧情）</label><textarea id="evidence"></textarea><label>复核人员</label><input id="reviewer" placeholder="可填写复核人或角色"><button onclick="save()">保存学习判断（不代表生成画面通过）</button><p id="notice" class="muted"></p>`;
    let reviews=D.summary.saved_reviews||{};if(reviews[id]){document.getElementById('relation').value=reviews[id].relation;document.getElementById('hypothesis').value=reviews[id].hypothesis;document.getElementById('evidence').value=reviews[id].evidence;document.getElementById('reviewer').value=reviews[id].reviewer}}
    async function save(){const p={id:selected,relation:document.getElementById('relation').value,hypothesis:document.getElementById('hypothesis').value,evidence:document.getElementById('evidence').value,reviewer:document.getElementById('reviewer').value};if(!location.protocol.startsWith('http')){let a=document.createElement('a'),b=new Blob([JSON.stringify(p,null,2)],{type:'application/json'});a.href=URL.createObjectURL(b);a.download=selected+'_editorial_review.json';a.click();return}const notice=document.getElementById('notice');try{const r=await fetch('/api/editorial-decision',{method:'POST',headers:{'Content-Type':'application/json','X-Director-Token':'__CSRF__'},body:JSON.stringify(p)});let j=await r.json();if(!r.ok)throw Error(j.error);D.summary.saved_reviews[p.id]=j;notice.textContent='学习判断已保存，未授权镜头复刻通过。修订 '+j.revision}catch(e){notice.textContent='保存失败：'+e.message}}
    function renderLessons(){document.getElementById('lessons').innerHTML=lessons.map(l=>`<div class="case"><h3>${esc(l.title)}</h3><div class="shots">${l.shots.map((s,i)=>`<div class="card"><img src="${pic(l.reference_mid_frames[i])}"><small>${esc(s)} · 原片参考</small></div>`).join('')}</div><p><b>画面可观察：</b>${esc(l.observable)}</p><p><b>导演语法假设：</b>${esc(l.hypothesis)}</p><p class="muted">其他解释：${esc(l.alternatives.join('；'))}</p><p><b>必须核实：</b>${esc(l.verify.join('；'))}</p><p class="gold">迁移拍摄规律：${esc(l.teachable_rule)}</p><p>原创迁移示例：${esc(l.transfer)}</p><small>这不是导演真实意图的确定性识别。</small></div>`).join('')}
    const ex=D.example;document.getElementById('brief').value=ex.brief;document.getElementById('pattern').value=ex.chosen_grammar;
    function renderPlan(v){document.getElementById('transfer').innerHTML=`<div class="trace"><b>自审轨迹</b>：初稿 ${v.iteration_trace[0].technical_review.structural_check_passed}/${v.iteration_trace[0].technical_review.structural_check_total} 项结构规则 → 修改后 ${v.iteration_trace[1].technical_review.structural_check_passed}/${v.iteration_trace[1].technical_review.structural_check_total} 项。<br><small>注意：这是规则完整度，不是导演质量评分。</small></div><div class="shots">${v.iteration_trace[1].shots.map(s=>`<div class="card"><b>${esc(s.id)} · ${esc(s.beat)} · ${s.duration_s}秒</b><p>${esc(s.narrative_purpose)}</p><p class="muted">本场景语境：${esc(s.source_specific_scenario_cues?.place)}；角色：${esc(s.source_specific_scenario_cues?.people)}；关键物：${esc(s.source_specific_scenario_cues?.key_object)}</p><small>机位：${esc(s.camera)}<br>表演：${esc(s.acting)}<br>切镜原因：${esc(s.cut_reason)}<br>声音：${esc(s.sound_cue)}</small></div>`).join('')}</div><p class="muted">仍需真正审查：${esc(v.required_final_checks.join('；'))}</p><button onclick="downloadPlan()">下载分镜JSON</button>`;window.lastPlan=v}
    function downloadPlan(){let a=document.createElement('a'),b=new Blob([JSON.stringify(window.lastPlan,null,2)],{type:'application/json'});a.href=URL.createObjectURL(b);a.download='original_scene_director_plan.json';a.click()}
    async function plan(){let brief=document.getElementById('brief').value,pattern=document.getElementById('pattern').value;if(brief.length<3){alert('请输入原创场景');return}if(!location.protocol.startsWith('http')){alert('离线只显示预置案例；启动本地工作台后可为任意原创场景重新规划。');return}try{let r=await fetch('/api/editorial-design',{method:'POST',headers:{'Content-Type':'application/json','X-Director-Token':'__CSRF__'},body:JSON.stringify({brief,pattern})});let j=await r.json();if(!r.ok)throw Error(j.error);renderPlan(j)}catch(e){alert(e.message)}}nav();pick(selected);renderLessons();renderPlan(ex);
    </script></body></html>'''
    (root/'EDITORIAL_DIRECTOR_LAB.html').write_text(tpl.replace('__DATA__',data),encoding='utf-8')
    return 'EDITORIAL_DIRECTOR_LAB.html'

def run(root=BASE):
    root=Path(root).resolve()
    cards=read_json(root/'output/director_lab/director_cards.json',[])
    if len(cards)<2:raise RuntimeError('Run director_craft.py first')
    cases=case_studies(root);pairs=transition_dataset(root,cards)
    historical=read_json(root/'data/editorial_director_reviews.json',{})
    saved={p['id']:historical[p['id']] for p in pairs if p['id'] in historical and
           [p['out_sha256'],p['in_sha256']]==historical[p['id']].get('source_hashes')}
    for p in pairs:
        if p['id'] in saved:
            e=saved[p['id']]
            if [p['out_sha256'],p['in_sha256']]==e.get('source_hashes'):p['human_review']=e
    example=design_scene('现代科研站深夜收到失联探测器发来的信号。值班工程师先看到异常，再与同伴判断是否启动封锁。','suspense_insert')
    output=root/FRAME_OUT;output.mkdir(parents=True,exist_ok=True)
    summary={'source_sha256':read_json(root/'data/project_manifest.json',{}).get('source_sha256'),
      'reference_shots':len(cards),'cut_relations':len(pairs),'provisional_lessons':len(cases),
      'provisional_pair_hypotheses':sum(p['director_interpretation']['type']!='UNKNOWN' for p in pairs),
      'verified_cut_intentions':0,'director_grade_recreation_approvals':0,
      'paid_video_model_calls':0,'external_model_calls':0,
      'sound_cut_measurements':sum(p['sound_at_cut']['status']=='MEASURED_REFERENCE_ONLY' for p in pairs),
      'film_cut_visual_change_quality_penalty':0,
      'saved_reviews':{k:v for k,v in saved.items() if k in {p['id'] for p in pairs}},
      'provenance':'REAL_FILM_REFERENCE_AND_PRELIMINARY_EDITORIAL_HYPOTHESES',
      'note':'导演镜头语言的理解假设，尚不代表编剧和导演真实创作意图已被证明。'}
    write_json(output/'transitions.json',pairs)
    write_json(output/'director_lessons.json',cases)
    write_json(output/'original_scene_rehearsal.json',example)
    board=build_study_board(root,cases)
    result={'summary':summary,'transitions':pairs,'lessons':cases,'transfer_example':example,'study_board':board}
    build_html(root,result)
    write_json(output/'acceptance.json',{**{k:v for k,v in summary.items() if k!='saved_reviews'},
       'board_path':board,'html':'EDITORIAL_DIRECTOR_LAB.html',
       'source_reference_stills_not_generated':True,'narrative_semantics_director_approved':False,
       'original_scene_structural_test':example['iteration_trace'][-1]['technical_review']})
    return {**{k:v for k,v in summary.items() if k!='saved_reviews'},'study_board':board,'page':'EDITORIAL_DIRECTOR_LAB.html'}

if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('command',choices=('run','status','plan'),nargs='?',default='run')
    ap.add_argument('--brief',default='现代科研站深夜收到失联探测器发来的信号。值班工程师先看到异常，再与同伴判断是否启动封锁。')
    ap.add_argument('--pattern',choices=PATTERNS,default='suspense_insert')
    a=ap.parse_args()
    if a.command=='run':print(json.dumps(run(),ensure_ascii=False,indent=2))
    elif a.command=='status':print(json.dumps(read_json(BASE/FRAME_OUT/'acceptance.json',{}),ensure_ascii=False,indent=2))
    else:print(json.dumps(design_scene(a.brief,a.pattern),ensure_ascii=False,indent=2))
