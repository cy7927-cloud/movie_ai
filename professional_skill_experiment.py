#!/usr/bin/env python3
"""Two-camera-language experiments, grounded in film and public upstream Skill rules.

This is GPT's MANUAL application of documented upstream techniques, not an
execution of external SKILL.md.  No film director intent is asserted.
"""
from __future__ import annotations
import copy
import hashlib
import html
import json
from pathlib import Path

import professional_skill_adapter as upstream
from gpt_director_study import audit, load

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'output' / 'professional_skills'

PUBLIC_METHODS = {
    'director-agent': {
        'repository': 'https://github.com/62656456/ai-film-skills',
        'source': 'https://github.com/62656456/ai-film-skills/blob/main/skills/director-agent/SKILL.md',
        'method': '人物行动、表演与观众信息先后；尊重已定剧情，不由镜头推测导演真实意图',
    },
    'ai-storyboard-director': {
        'repository': 'https://github.com/62656456/ai-film-skills',
        'source': 'https://github.com/62656456/ai-film-skills/blob/main/skills/ai-storyboard-director/SKILL.md',
        'method': '从观看任务选择机位与切镜；走位和摄影同设计，不预设固定镜头数；只做当前阶段',
    },
    'plan-camera-shots': {
        'repository': 'https://github.com/zhangzhangco/film-production-skills',
        'source': 'https://github.com/zhangzhangco/film-production-skills/blob/main/skills/plan-camera-shots/SKILL.md',
        'method': '摄影机空间基线、动作初始与末端状态、轴线、时间、服化道与道具状态',
    },
    'review-and-assemble': {
        'repository': 'https://github.com/zhangzhangco/film-production-skills',
        'source': 'https://github.com/zhangzhangco/film-production-skills/blob/main/skills/review-and-assemble/SKILL.md',
        'method': '生成媒体需要真实物理文件和可追溯Take；没生成的媒体不得审核通过或宣称可出片',
    },
}


def audience_track(scene, shots):
    # Analyze the authored shot metadata rather than guessing actual audience reaction.
    result = []
    audience = set(scene['initial_audience_knowledge'])
    character = {name: set(facts) for name, facts in scene['initial_character_knowledge'].items()}
    for shot in shots:
        audience.update(shot.get('revealed_to_audience', []))
        for actor, facts in shot.get('learned_by_character', {}).items():
            character[actor].update(facts)
        result.append({'shot': shot['id'], 'start_s': shot['start_s'], 'end_s': shot['end_s'],
                       'audience_known': sorted(audience),
                       'character_known': {k: sorted(v) for k, v in character.items()},
                       'audience_advantage_over_A': sorted(audience - character['A'])})
    return result


def make_alternate(original):
    # Both schemes use the same 32-second original script and spatial layout.
    # Alternate differs *only* in whether a new login clue is revealed to viewers.
    shots = copy.deepcopy(original)
    s = next(s for s in shots if s['id'] == 'S03')
    assert s.get('revealed_to_audience') == ['REMOTE_LOGIN']
    s.update({
        'camera': '固定机位，终端右侧的调查员手部近景，屏幕下角被反光遮蔽',
        'actor_action': 'A手指停在断线后的异常时间戳，屏幕下角的登录状态因反光不可读；不新增调查信息',
        'revealed_to_audience': [],
        'learned_by_character': {},
        'dramatic_purpose': '让观众与A都暂时看不到远程登录细节，突出共同困惑而非信息先知',
        'cut_reason': '以门外脚步声衔接B入场；保留A对已知时间矛盾的注意',
        'sound': '持续的机器低频声，远处门廊脚步声逐步靠近'
    })
    return shots


def run():
    source, cases, frames = upstream.validate_film_evidence()
    scene_data = load(ROOT / 'data' / 'gpt_director_scene.json')
    scene = scene_data['scene']
    shots_a = scene_data['revised_shots']
    shots_b = make_alternate(shots_a)
    audit_a = audit(scene, shots_a)
    audit_b = audit(scene, shots_b)
    track_a = audience_track(scene, shots_a)
    track_b = audience_track(scene, shots_b)
    assert audit_a['issue_count'] == 0
    assert audit_b['issue_count'] == 0
    assert 'REMOTE_LOGIN' in track_a[2]['audience_advantage_over_A']
    assert 'REMOTE_LOGIN' not in track_b[2]['audience_advantage_over_A']
    assert 'REMOTE_LOGIN' not in track_b[-1]['character_known']['A']
    assert [s['id'] for s in shots_a] == [s['id'] for s in shots_b]
    assert all(a['start_s'] == b['start_s'] and a['end_s'] == b['end_s'] for a,b in zip(shots_a,shots_b))

    study = [
        {
            'case_id': 'CASE_A',
            'film_window': '595–616秒',
            'evidence_key_seconds': [597.2, 600.2, 604.4, 607.8, 611.2, 614.0],
            'evidence_summary': '暗处人物在黑猫镜头之前出现；中间穿插红衣人群、猫和远处入口，随后回到暗处人物',
            'craft_to_test': '观众可获得超出角色的信息，但必须分开事实、角色知情范围、可能的并行空间',
            'source_methods': ['director-agent','ai-storyboard-director'],
            'not_justified': ['猫被暗处人物看见','这些镜头全部是相同地点或实时连续','导演意图已确认'],
            'alternative': '猫也可能只是独立意象/不同空间的悬念点，不能靠相邻画面强行确立视线关系',
            'further_evidence': ['前后声轨与对白','全动态视线与方向','场景实际地理关系'],
        },
        {
            'case_id': 'CASE_B',
            'film_window': '617–653秒',
            'evidence_key_seconds': [617.3,620.0,624.0,628.5,633.8,640.1,646.0,652.7],
            'evidence_summary': '遮挡外景、隔窗室内、门口人物、入室、两人同框、一个人离开后另一人独处',
            'craft_to_test': '以可见走位作为镜头结构：入画/跨门槛/共享场域/出画；固定人物与机位空间基线',
            'source_methods': ['ai-storyboard-director','plan-camera-shots'],
            'not_justified': ['只是标准正反打','所有切点都是无时间省略的连续行为','对白引发人物离开已证实'],
            'alternative': '走位也可能是多次跳切、省略时间或中立的场景交代',
            'further_evidence': ['连续动作与精确切点','声音桥/对白','轴线和场景布局'],
        },
    ]
    plan = {
        'study_source': 'USER_UPLOADED_FILM_776_SECOND_EXCERPT',
        'source_sha256': source['sha256'],
        'public_upstream_methods': PUBLIC_METHODS,
        'method_application_status': 'GPT_MANUAL_REVIEW_OF_PUBLISHED_SKILL_RULES',
        'native_upstream_skill_execution': False,
        'upstream_install_status': upstream.status(),
        'film_evidence_frames_verified': sum(len(v) for v in frames.values()),
        'film_studies': study,
        'original_scene': {'title': scene['title'], 'duration_s': scene['target_duration_s'],
                           'source': 'data/gpt_director_scene.json',
                           'script_changes': False,
                           'variants': [
                               {'name': 'A_观众先知', 'shots': shots_a, 'audit': audit_a, 'information_path': track_a,
                                'hypothesized_effect': '观众提前看见登录事实、藏卡动作；人物仍只能从异常时间戳推理，可能造成悬念'},
                               {'name': 'B_共同困惑', 'shots': shots_b, 'audit': audit_b, 'information_path': track_b,
                                'hypothesized_effect': '登录事实暂时遮蔽；观众与A对技术线索更接近，可能增加共同困惑，但仍先知藏卡'},
                           ],
                           'which_is_artistically_better': 'UNVERIFIED_NEEDS_VIEWABLE_FILM_AND_BLIND_REVIEW',
                           'camera_axis_3d_verified': False,
                           'actual_generated_original_stills': 0,
                           'actual_generated_original_video': 0},
    }
    OUT.mkdir(parents=True,exist_ok=True)
    upstream.write_json(OUT / 'film_skill_audit_experiment.json',plan)
    write_report(plan)
    return {'film_source_verified':True,'reference_frames_verified':sum(len(x) for x in frames.values()),
            'public_professional_methods_applied':len(PUBLIC_METHODS),
            'upstream_native_skills_installed':sum(x['installed'] for x in (j for repo in upstream.status().values() for j in repo['skills'])),
            'creative_variants_compared':2,
            'both_variants_structural_pass':all(v['audit']['issue_count']==0 for v in plan['original_scene']['variants']),
            'artistic_quality_verified':False,
            'report':'output/professional_skills/现成影视Skill_妖猫传验证报告.md'}


def write_report(plan):
    studies = plan['film_studies']
    variants = plan['original_scene']['variants']
    lines = [
        '# 《妖猫传》 × 现成专业影视 Skill：真实验证记录',
        '',
        '> 本报告由 GPT 对照公开的原版 Skill 执行规范进行实片学习和创作试验；**并非已经运行外部 Agent 框架/技能代码**。当前容器无法解析 github.com，原版仓库未能拉取。所有参考画面来自用户提供的 776.477 秒片段，不是完整电影。',
        '',
        '## 1. 专业来源（不是自造的导演方法）','',
    ]
    for name, value in PUBLIC_METHODS.items():
        lines.append(f'- **[{name}]({value["source"]})**：{value["method"]}。')
    lines += ['', '专业 Skill 是指导 GPT 工作的规范；不是已训练好的电影视觉模型。ShotTransformer 是可选的景别/机位分类器；FilmAgent 是不同规模的多Agent框架，这次均未部署，不能把它们写作“成功运行”。','',
              '## 2. 《妖猫传》实片的两个学习案例','']
    for s in studies:
        lines += [f'### {s["case_id"]} · {s["film_window"]}',
                  f'**已核对可见画面：**{s["evidence_summary"]}。',
                  f'**学习的专业方法：**{s["craft_to_test"]}。',
                  f'**其他解释：**{s["alternative"]}。',
                  '**不能断言：**'+'；'.join(s['not_justified'])+'。',
                  '**待核验：**'+'、'.join(s['further_evidence'])+'。',
                  '**画面证据时间戳：**'+', '.join(map(str,s['evidence_key_seconds']))+' 秒。', '']
    lines += ['## 3. 将学到的方法迁移到同一原创场景：两个导演选择','',
              '**共同前提：**原创《失联观测站》，32秒；两套保留同样的人物、走位、时长、结局约束，避免另换场景伪造进步。', '',
              '| 方案 | 第8—11秒摄影与信息控制 | 观众比A多知道什么 | 结构审查 |',
              '|---|---|---|---|',
              f'| A · 观众先知 | 屏幕下角可读“REMOTE LOGIN ACTIVE”插入特写 | 已见远程登录事实；之后也见藏卡 | {variants[0]["audit"]["issue_count"]} 个问题 |',
              f'| B · 共同困惑 | 屏幕下角反光遮挡，延续A的异常时间戳观察 | 暂不知道远程登录；之后仍见藏卡 | {variants[1]["audit"]["issue_count"]} 个问题 |',
              '',
              '两种都可能有戏剧效果：A更容易形成观众超前信息，B更贴近人物的未知。**没有观众盲评或实拍成片，不能判 A 比 B 好，也不能判 B 比 A 好。**',
              '',
              '## 4. 验证边界','',
              '- 原片 SHA256 已验证，18张观察帧的文件与时间戳均验证。原片并未被当作需要修复的问题影片。',
              '- 两套原创分镜的时间、走位与角色知情规则通过现有工程结构审查；这并不等于达到院线导演质量。',
              '- 尚缺：原片声音对白语义、关键人物视线与精确轴线、上游原版 Skill 安装、真正生成的原创分镜画面、第三方盲评。',
              '- 本轮没有把原片截图冒充AI生成，没有调用付费视频模型，没有对 GPT 进行权重训练。',
              '',
              '## 5. 将原版 Skill 真正接入工程（需可访问 GitHub 的环境）','',
              '在工程根目录执行：',
              '```powershell',
              'python professional_skill_adapter.py install --repo open-film-skills',
              'python professional_skill_adapter.py install --repo film-production-skills',
              'python professional_skill_adapter.py doctor',
              'python professional_skill_adapter.py prepare-film',
              'python professional_skill_adapter.py prepare-original',
              '```',
              '',
              '这会拉取 **原作者 Git 仓库及其 SKILL.md**，而不是我仿写的替代品；只下载，不执行上游脚本。下载成功后，电影案例会关联原版 Skill 文件与 SHA256，供支持 Agent Skills 的宿主逐项调用。',
              '']
    (OUT/'现成影视Skill_妖猫传验证报告.md').write_text('\n'.join(lines),encoding='utf-8')


if __name__ == '__main__':
    print(json.dumps(run(),ensure_ascii=False,indent=2))
