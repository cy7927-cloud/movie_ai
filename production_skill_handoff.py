#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Production handoff and media provenance for an original, *not reference-film* scene.

Semantics follow upstream film-production-skills plan-camera-shots and
review-and-assemble instructions. Source image is an independently generated
AI storyboard contact sheet, NEVER user-uploaded movie reference frames.

All camera coordinates and asset appearances are PROPOSALS: they are a
production planning baseline, not measurements of the source movie.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from PIL import Image, ImageStat

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'output' / 'real_production_pilot'
ASSET_ROOT = OUT / 'generated_stills'
SOURCE = OUT / 'ai_generated_storyboard_contact_sheet.png'
SCENE_FILE = ROOT / 'data' / 'gpt_director_scene.json'

ASSETS = {
    'ENV_OBSERVATORY': {'kind':'environment','locked_design':'凌晨失联观测站控制室：终端在右、左后方通往走廊的门、右后方服务器机柜；冷青灰灯光','source':'original_scene_stage_map'},
    'CHAR_A': {'kind':'character','locked_design':'调查员A，深蓝外套、短黑发，右侧终端前，不佩戴门禁卡','source':'director_character_proposal'},
    'CHAR_B': {'kind':'character','locked_design':'管理员B，深灰工装、短发，携带黑色文件夹，藏有金属门禁卡','source':'director_character_proposal'},
    'PROP_CONSOLE': {'kind':'prop','locked_design':'右侧监视终端，有断线时间和远程会话状态','source':'story_fact'},
    'PROP_FOLDER': {'kind':'prop','locked_design':'B手持黑色文件夹，能遮挡门禁卡','source':'story_fact'},
    'PROP_BADGE': {'kind':'prop','locked_design':'银灰色金属门禁卡，B持有，A不得在镜头内无依据看到','source':'story_fact'},
}

# Coordinates are measured in a *proposed* 6m x 5m local studio layout.
# A at (3.8,1.1), doorway at (0.6,3.8), corridor beyond (0.2,4.8).
CAMERAS = {
    'S01': {'camera_position_m':[0.5,3.2,1.5], 'aim_point_m':[3.3,1.5,1.4], 'focal_length_mm':28, 'movement':'locked', 'focus_target':'A@console', 'axis_side':'south'},
    'S02': {'camera_position_m':[3.0,1.8,1.45],'aim_point_m':[3.8,1.1,1.30],'focal_length_mm':50,'movement':'locked','focus_target':'A hand and upper log','axis_side':'south'},
    'S03': {'camera_position_m':[3.5,1.6,1.5],'aim_point_m':[3.9,1.2,1.42],'focal_length_mm':85,'movement':'locked','focus_target':'lower REMOTE_LOGIN status','axis_side':'south'},
    'S04': {'camera_position_m':[1.8,2.7,1.45],'aim_point_m':[0.6,3.8,1.5],'focal_length_mm':40,'movement':'locked','focus_target':'B crossing doorway','axis_side':'south'},
    'S05': {'camera_position_m':[1.15,3.6,1.2],'aim_point_m':[1.0,3.5,1.0],'focal_length_mm':85,'movement':'locked','focus_target':'B hand, badge, folder','axis_side':'south'},
    'S06': {'camera_position_m':[2.9,2.25,1.48],'aim_point_m':[2.3,2.55,1.45],'focal_length_mm':40,'movement':'locked','focus_target':'A and B in two-shot','axis_side':'south'},
    'S07': {'camera_position_m':[3.2,2.1,1.55],'aim_point_m':[3.7,1.2,1.5],'focal_length_mm':85,'movement':'locked','focus_target':'A eyes; B shoulder in left foreground','axis_side':'south'},
}

# Locked prop transitions are specific to the approved story; no fabricated
# unlocking/remote-login disclosure can be introduced at media stage.
PROP_STATES = {
 'S01': ({'badge':'in B possession, concealed','folder':'held by B','console':'offline alert'},{'badge':'in B possession, concealed','folder':'held by B','console':'offline alert'}),
 'S02': ({'badge':'in B possession, concealed','folder':'held by B','console':'offline alert'}, {'badge':'in B possession, concealed','folder':'held by B','console':'post-offline log visible to A'}),
 'S03': ({'badge':'in B possession, concealed','folder':'held by B','console':'post-offline log visible to A'}, {'badge':'in B possession, concealed','folder':'held by B','console':'remote login visible to viewer ONLY'}),
 'S04': ({'badge':'in B possession, concealed','folder':'held by B','console':'remote login viewer ONLY'}, {'badge':'in B possession, concealed','folder':'held by B','console':'remote login viewer ONLY'}),
 'S05': ({'badge':'in B possession, concealed','folder':'held by B','console':'remote login viewer ONLY'}, {'badge':'under folder lower flap, hidden from A','folder':'held by B','console':'remote login viewer ONLY'}),
 'S06': ({'badge':'under folder lower flap, hidden from A','folder':'held by B','console':'remote login viewer ONLY'}, {'badge':'under folder lower flap, hidden from A','folder':'held by B','console':'remote login viewer ONLY'}),
 'S07': ({'badge':'under folder lower flap, hidden from A','folder':'held by B','console':'remote login viewer ONLY'}, {'badge':'under folder lower flap, hidden from A','folder':'held by B','console':'remote login viewer ONLY'}),
}

SHOT_ASSETS = {
 'S01':['ENV_OBSERVATORY','CHAR_A','CHAR_B','PROP_CONSOLE'],
 'S02':['ENV_OBSERVATORY','CHAR_A','PROP_CONSOLE'],
 'S03':['ENV_OBSERVATORY','PROP_CONSOLE'],
 'S04':['ENV_OBSERVATORY','CHAR_A','CHAR_B','PROP_FOLDER'],
 'S05':['ENV_OBSERVATORY','CHAR_A','CHAR_B','PROP_FOLDER','PROP_BADGE'],
 'S06':['ENV_OBSERVATORY','CHAR_A','CHAR_B','PROP_FOLDER','PROP_CONSOLE'],
 'S07':['ENV_OBSERVATORY','CHAR_A','CHAR_B','PROP_CONSOLE'],
}

# A visual critic checks semantic adherence, not whether the PNG is decodable.
# These observations are from actual visual inspection of the generated contact
# sheet and should NEVER be attributed to the model's own self-ratings.
VISUAL_QA = {
 'S01': ('REVIEW_REQUIRED',['图中B已站在敞开的入口内或门槛附近；需要复核其最初是否仍在走廊，而非提前入场']),
 'S02': ('REVIEW_REQUIRED',['日志画面内容由图像生成器创造；显示的时间戳和原剧本的断线时刻没有逐字符对照依据']),
 'S03': ('REVIEW_REQUIRED',['画面为远程会话状态，需与S02原本的日志时间矛盾建立可读的文字因果']),
 'S04': ('VISUALLY_PLAUSIBLE',['B站在门口并握有文件夹，尚需视频动作才能验证连续跨门槛走位']),
 'S05': ('VISUALLY_PLAUSIBLE',['门禁卡可见于文件夹边缘，A处在虚焦背景；需验证角色是否确实看不见']),
 'S06': ('REVIEW_REQUIRED',['两名演员相对位置与此前总体一致，但人物面容需进行身份一致性核验']),
 'S07': ('REJECTED',['剧情要求A目光转回终端上部；图像里A明显看向左侧前景人物，动作方向不符，需要重新生成']),
}


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for buf in iter(lambda:f.read(1024*1024),b''):h.update(buf)
    return h.hexdigest()


def produce():
    if not SOURCE.is_file():raise FileNotFoundError('No independently generated AI contact sheet at '+str(SOURCE))
    payload=json.loads(SCENE_FILE.read_text(encoding='utf-8'))
    scene=payload['scene']
    shots=payload['revised_shots']
    assert len(shots)==7
    ASSET_ROOT.mkdir(parents=True,exist_ok=True)
    image=Image.open(SOURCE).convert('RGB')
    w,h=image.size
    assert w>=1200 and h>=700
    for n in range(7):
        c=n%4;r=n//4
        left=round(c*w/4);right=round((c+1)*w/4)
        top=round(r*h/2);bottom=round((r+1)*h/2)
        image.crop((left,top,right,bottom)).save(ASSET_ROOT/f'S{n+1:02d}_AI_CANDIDATE.png',compress_level=6)
    segments=[]; reviews=[]
    for shot in shots:
        k=shot['id'];cam=CAMERAS[k]
        bindings=SHOT_ASSETS[k]
        assert all(v in ASSETS for v in bindings)
        start,end=PROP_STATES[k]
        media=ASSET_ROOT/f'{k}_AI_CANDIDATE.png'
        with Image.open(media) as im:
            stat=ImageStat.Stat(im.convert('L'))
            brightness=round(stat.mean[0],1)
            width,height=im.size
        state,notes=VISUAL_QA[k]
        segment={
            'id':k, 'upstream_beat_id':'BEAT_'+k,
            'camera_explicit_position':cam['camera_position_m'],
            'camera_position':{'unit':'m','x':cam['camera_position_m'][0],'y':cam['camera_position_m'][1],'z':cam['camera_position_m'][2]},
            'camera_target':{'unit':'m','xyz':cam['aim_point_m']},
            'lens_focal_length_mm':cam['focal_length_mm'],
            'camera_movement':cam['movement'],'focus_target':cam['focus_target'],
            'axis_side':cam['axis_side'],
            'asset_bindings':bindings, 'props_at_start':start, 'props_at_end':end,
            'positions_at_start':shot['positions_at_start'],
            'positions_at_end':shot['positions_at_end'],
            'actor_action':shot['actor_action'],
            'sound':shot['sound'], 'dramatic_purpose':shot['dramatic_purpose'],
            'cut_reason':shot['cut_reason'],
            'start_s':shot['start_s'],'end_s':shot['end_s'],
            'dominant_action_chain':shot['actor_action'],
            'state_source':'approved_existing_gpt_director_scene',
            'camera_geometry_provenance':'director_proposed_local_stage_not_measured_from_film',
            'image_generation_ref':{'image_type':'independently_ai_generated_original_scene','contact_sheet_sha256':digest(SOURCE),
                'candidate_path':str(media.relative_to(ROOT)), 'candidate_sha256':digest(media),
                'origin':'one AI-generated 4x2 storyboard sheet, sliced into seven candidates; NOT seven independent runs'},
        }
        segments.append(segment)
        reviews.append({'shot_id':k,'candidate_path':str(media.relative_to(ROOT)),
            'candidate_sha256':digest(media),'status':state,'notes':notes,
            'technical':{'decodable':True,'width':width,'height':height,'mean_brightness':brightness},
            'selected_for_final':False,'human_approved':False,'visual_review_based_on_actual_candidate':True})
    issues=[]
    if not all(shots[i]['end_s']==shots[i+1]['start_s'] for i in range(6)):
        issues.append('TEMPORAL_GAP')
    if shots[0]['start_s']!=0.0 or shots[-1]['end_s']!=scene['target_duration_s']:
        issues.append('TOTAL_DURATION')
    for s in segments:
        for key in ('camera_position','focus_target','asset_bindings','upstream_beat_id','props_at_start','props_at_end'):
            if not s.get(key):issues.append(s['id']+'_'+key)
    camera={'skill':'plan-camera-shots','source_skill_repository':'https://github.com/zhangzhangco/film-production-skills',
        'project_id':scene['id'],'duration_s':scene['target_duration_s'],'assets':ASSETS,
        'spatial_baselines':{'coordinate_system':'relative proposed stage, meters','console':[3.8,1.1],
            'corridor':[0.2,4.8],'doorway':[0.6,3.8], 'stage_width_m':6.0,'stage_depth_m':5.0},
        'continuity_rules':['A remains at console through scene','B travels corridor → doorway only','badge never seen by A','remote login never seen by A'],
        'segments':segments,'preflight':{'pass':not issues,'issues':issues,'provisional_geometry':True,
            'user_approval_pending':True}}
    review={'skill':'review-and-assemble','source_skill_repository':'https://github.com/zhangzhangco/film-production-skills',
        'generated_media_type':'ORIGINAL_AI_STORYBOARD_STILLS_NOT_FILM','contact_sheet_sha256':digest(SOURCE),
        'candidate_count':len(reviews),'generation_run_count':1,'reviews':reviews,
        'pass_count':sum(x['status']=='VISUALLY_PLAUSIBLE' for x in reviews),
        'revision_count':sum(x['status']!='VISUALLY_PLAUSIBLE' for x in reviews),
        'human_approved_count':0,'editorial_export':{'status':'BLOCKED','reason':'No selected human-approved video takes, and S07 storyboard rejected'},
        'warning':'Contact sheet crops are original AI imagery, not movie frames; film export remains blocked.'}
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'professional_camera_handoff.json').write_text(json.dumps(camera,ensure_ascii=False,indent=2),encoding='utf-8')
    (OUT/'independent_media_review.json').write_text(json.dumps(review,ensure_ascii=False,indent=2),encoding='utf-8')
    return camera,review

if __name__=='__main__':
    c,r=produce()
    print(json.dumps({'camera_preflight':c['preflight'],'original_generated_stills':r['candidate_count'],
        'visually_plausible_not_final':r['pass_count'],'need_revision':r['revision_count'],
        'human_approved':r['human_approved_count'],'export':r['editorial_export']['status']},ensure_ascii=False,indent=2))
