#!/usr/bin/env python3
"""Evidence-based acceptance matrix; never convert static target extraction into AI reconstruction success."""
import csv,html,json,sqlite3
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def report():
    import director as d,product_engine as q
    d.bootstrap()
    man=json.loads((ROOT/'data/project_manifest.json').read_text(encoding='utf-8'))
    obs=json.loads((ROOT/'data/asset_bible_observations.json').read_text(encoding='utf-8')) if (ROOT/'data/asset_bible_observations.json').is_file() else {}
    cut=json.loads((ROOT/'data/cut_detector_crosscheck.json').read_text(encoding='utf-8')) if (ROOT/'data/cut_detector_crosscheck.json').is_file() else {}
    with d.connect() as c:
        tasks=c.execute('SELECT * FROM tasks').fetchall();attempts=c.execute('SELECT COUNT(*) FROM attempts').fetchone()[0]
        valid=sum(q.best_valid_attempt(c,t) is not None for t in tasks)
        reviews=[q.shot_review(c,s[0]) for s in c.execute('SELECT DISTINCT shot_id FROM tasks ORDER BY shot_id')]
        signed=sum(s['is_fully_approved'] for s in reviews)
    sections=[
     ('原片逆向工程','部分完成','实际切镜候选、原片IN/MID/OUT、高分辨率参考、音频能量、光流和抽样视觉特征；叙事理解及切点未确认。'),
     ('电影资产圣经','未完成','采集可能的人脸观测和视觉场景分组，但无法自动确认角色身份、服装版本或空间资产。'),
     ('导演分镜重建','部分完成','每个镜头均有目标三帧、时间码和生成工单；景别、戏剧目的、视线、动作起止点需要可靠语义验证。'),
     ('三维预演','未完成','当前二维光流只能作为线索；尚无可验证的三维角色走位或摄影机轨迹。'),
     ('多模型镜头生产','接口完成、真实未验收','ComfyUI和云图片API接入口及模拟闭环存在；未生成本项目的独立AI候选分镜。视频模型未接入。'),
     ('表演与声音精修','未完成','仅测量源音频能量与原片镜头时序；对白转写、精确口型、动作表情和混音未完成。'),
     ('自动质量回归','部分完成','图像技术对照、返工规则、版本记忆和硬门禁可运行，需真正生成候选后才能验证改善程度。'),
     ('全片剪辑与终审','未完成','正式AI成片导出被拒绝；只有原片参考和工单，不存在独立复刻成片。'),
    ]
    stages=''.join('<tr><td>'+html.escape(a)+'</td><td>'+html.escape(b)+'</td><td>'+html.escape(c)+'</td></tr>' for a,b,c in sections)
    summary={'source_duration_s':man['duration_seconds'],'shot_candidates':man['shot_count'],
      'reference_storyboards':len(tasks),'candidate_attempts':attempts,
      'current_valid_generated_storyboard_candidates':valid,
      'director_passed_shots':signed,'model_verified_video_shots':0,
      'heursitic_visual_group_proposals':obs.get('visual_location_proposals') and len(obs['visual_location_proposals']) or 0,
      'possible_face_observations':obs.get('possible_face_observations',0),
      'verified_actor_identities':0,'verified_3d_assets':0,
      'independent_second_detector_count':cut.get('ffmpeg_candidate_cut_count'),
      'cut_detection_matches':cut.get('agreements_0_45_seconds'),
      'test_truth':'Code tests assess software controls; they do NOT prove film recreation quality',
      'quality_conclusion':'NOT_ACCEPTED_FOR_AI_FILM_RECONSTRUCTION'}
    (ROOT/'output/FINAL_ACCEPTANCE.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    template='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>电影自主迭代 · 真实验收报告</title><style>body{max-width:1180px;padding:24px;margin:auto;background:#0d1421;color:#e8edf7;font:16px/1.6 system-ui,'Microsoft YaHei',sans-serif}a{color:#9acafd}.section{background:#162236;padding:20px;margin:16px 0;border:1px solid #30475c;border-radius:11px}.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}.stats div{background:#1e314d;padding:14px;border-radius:10px}b{font-size:23px}table{width:100%;border-collapse:collapse}td,th{text-align:left;border-bottom:1px solid #33465e;padding:12px;vertical-align:top}td:first-child{min-width:145px}td:nth-child(2){min-width:120px}.warn{color:#ffd495}@media(max-width:750px){.stats{grid-template-columns:1fr 1fr}table{font-size:13px}}</style><h1>AI电影导演 · 正片分镜生产验收</h1><p class="warn">本报告只对应用户上传的12分56秒影片片段。原片静帧、技术评分、人物检测框和静态预演，都不得充当AI已经自主复刻的证据。</p><div class="stats"><div>影片长度<br><b>12:56</b></div><div>候选镜头<br><b>__SHOTS__</b></div><div>原片参考帧<br><b>__REFS__</b></div><div>导演完整通过<br><b>__PASSED__</b></div></div><div class="section"><h2>按最初八个工业生产阶段审计</h2><table><tr><th>生产阶段</th><th>验收结论</th><th>真实证据与未完成项</th></tr>__STAGES__</table></div><div class="section"><h2>当前已经完成的分镜前置工作</h2><p>抽取 __REFS__ 张1280×534原片参考关键帧，建立 __SHOTS__ 个候选镜头的导演生产工单，并抽取源音频能量、颜色、二维光流、__FACES__ 个可能的人脸观测与 __GROUPS__ 个视觉分组候选。所有切镜边界均需复核。</p><p>第二种FFmpeg切镜算法检测到 __FFMPEG__ 个候选时间点；与主算法在0.45秒内匹配 __MATCH__ 个。两个算法的候选不一致，不能宣称自动拆镜100%准确。</p></div><div class="section"><h2>真正的核心门禁</h2><p>生成模型未连接或模型失败时，AI候选数量保持0；原片参考图不会自动变成生成图。即使技术图像相似度高，也不能绕过人物身份、导演意图和最终签核。没有全镜头通过就禁止独立AI成片导出。</p><p><a href="../PROJECT_STORYBOARD_REPORT.html">浏览全部真实分镜</a> · <a href="shot_work_orders.jsonl">查看全部生产任务</a> · <a href="../README.md">安装与生产说明</a></p></div></html>'''
    vals={'__STAGES__':stages,'__SHOTS__':str(summary['shot_candidates']),'__REFS__':str(summary['reference_storyboards']),
      '__PASSED__':str(signed),'__FACES__':str(summary['possible_face_observations']),
      '__GROUPS__':str(summary['heursitic_visual_group_proposals']),
      '__FFMPEG__':str(cut.get('ffmpeg_candidate_cut_count','未运行')),
      '__MATCH__':str(cut.get('agreements_0_45_seconds','未运行'))}
    for a,b in vals.items():template=template.replace(a,b)
    (ROOT/'output/FINAL_ACCEPTANCE.html').write_text(template,encoding='utf-8')
    return summary
if __name__=='__main__':print(json.dumps(report(),ensure_ascii=False,indent=2))
