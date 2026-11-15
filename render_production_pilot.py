from pathlib import Path
import html,json,subprocess
from production_skill_handoff import produce,OUT

def h(x):return html.escape(str(x),quote=True)

cam,rev=produce()
status={r['shot_id']:r for r in rev['reviews']}
cards=[]
for s in cam['segments']:
    r=status[s['id']]
    cname={'VISUALLY_PLAUSIBLE':'候选可用·待签核','REVIEW_REQUIRED':'需要复核','REJECTED':'拒收·必须重做'}[r['status']]
    notes=''.join(f'<li>{h(t)}</li>' for t in r['notes'])
    cards.append(f'''<section class="shot">
    <img alt="{h(s['id'])} AI原创分镜候选" src="generated_stills/{h(s['id'])}_AI_CANDIDATE.png"/>
    <div class="body"><div class="top"><strong>{h(s['id'])} <small>{s['start_s']:g}–{s['end_s']:g}s</small></strong><span class="pill">{h(cname)}</span></div>
    <p><b>镜头动作</b> {h(s['actor_action'])}</p>
    <p><b>摄影</b> {h(s['camera_position'])}m / {s['lens_focal_length_mm']}mm / 对焦：{h(s['focus_target'])}</p>
    <p><b>切镜理由</b> {h(s['cut_reason'])}</p>
    <p><b>声音</b> {h(s['sound'])}</p>
    <p><b>需处理的问题</b></p><ul>{notes}</ul></div></section>''')
page='''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>GPT导演专业Skill·原创分镜真实试制</title><style>
:root{color-scheme:dark}body{background:#111920;color:#f3f4f6;font:15px/1.7 system-ui,-apple-system,"Microsoft Yahei",sans-serif;margin:0}
main{max-width:1220px;margin:auto;padding:24px}h1{font-size:29px;line-height:1.2}h2{font-size:21px}p{margin:7px 0;color:#d0d7dd}
summary{font-weight:bold;cursor:pointer}.lede{color:#aac0cd}.sub{font-size:13px;color:#93a9b8}.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:18px 0}.stat{background:#1c2931;border:1px solid #355064;border-radius:9px;padding:16px}.stat b{display:block;font-size:24px}.stat small{color:#91a6b6}
.panel{background:#1a262e;border:1px solid #355064;border-radius:12px;padding:18px;margin:16px 0}.sheet{width:100%;height:auto;border-radius:5px;display:block}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
.shot{border:1px solid #344757;border-radius:9px;background:#1b2832;overflow:hidden}.shot img{width:100%;aspect-ratio:1/1;object-fit:cover}.shot .body{padding:13px}.top{display:flex;justify-content:space-between;gap:6px;align-items:start}.top small{color:#8cabb9;font-size:12px}.pill{font-size:12px;color:#f1ccaa;white-space:nowrap;border:1px solid #695440;border-radius:20px;padding:2px 8px}ul{padding-left:20px;margin:4px 0}.shot b{color:#dcebf3}a{color:#a2d7fa}video{display:block;width:100%;max-width:1000px} @media(max-width:800px){.grid{grid-template-columns:1fr}.stats{grid-template-columns:repeat(2,1fr)}}
</style></head><body><main>
<h1>专业影视Skill · 原创场景《失联观测站》</h1><p class="lede">源自《妖猫传》研究中的两种导演方法——观众信息提前获知与人物入场调度；不复制原片人物、镜头、场景与电影帧。</p>
<div class="stats"><div class="stat"><b>7</b><small>原创AI静帧候选</small></div><div class="stat"><b>32s</b><small>静态分镜预演</small></div><div class="stat"><b>7/7</b><small>摄影交接字段完整</small></div><div class="stat"><b>0</b><small>人工签核的成片镜头</small></div></div>
<div class="panel"><h2>真实原创AI分镜总板</h2><img class="sheet" src="ai_generated_storyboard_contact_sheet.png" alt="一张AI生成的4x2分镜总板，七格原创镜头，第八格为空"/><p class="sub">一次生成得到一张总板，裁切为7张独立文件；不是7次独立推理。源图SHA已写入摄影交接文件，电影原片截帧未参与候选生成。</p></div>
<div class="panel"><h2>可观看的32秒静态预演</h2><video controls preload="metadata" src="AI分镜静帧预演_非成片.mp4"></video><p class="sub">这是AI静帧时序预演，非AI视频运镜、非真实表演，不可作为最终成片。7张图按各自原分镜时长排列。</p></div>
<div class="panel"><h2>专业摄影与独立审片结果</h2><p>依据开源 <code>plan-camera-shots</code> 和 <code>review-and-assemble</code> 的输入输出职责，记录机位、镜头焦点、人物起止位置、道具状态、资产绑定与不通过原因。几何坐标是此场景的提议值，并非从原片测量。</p><p><a href="professional_camera_handoff.json">摄影执行合同(JSON)</a>　<a href="independent_media_review.json">审片决定(JSON)</a>　<a href="ai_generated_storyboard_contact_sheet.png">AI总板(PNG)</a></p></div>
<div class="grid">'''+''.join(cards)+'''</div><div class="panel"><h2>当前可证实的边界</h2><p>摄影交接通过结构检查，但场景几何仍待制片确认；S07视线明显偏离设定，拒收。原创画面存在且可解码，不等于身份一致性、完整7镜导演质量通过。影片原片的86镜头复刻任务与这7个原创候选是<strong>不同工程任务集</strong>。</p><p>作品导出门禁继续阻断：没有通过签核的动态镜头，不能把静帧预演当最终影片。</p></div></main><script>if(location.protocol==='http:'||location.protocol==='https:'){document.querySelectorAll('img[src],video[src]').forEach(el=>{el.src='/production-pilot/'+el.getAttribute('src');}); document.querySelectorAll('a[href]').forEach(el=>{let href=el.getAttribute('href');if(href==='professional_camera_handoff.json')el.href='/production-pilot-json';else if(href==='independent_media_review.json')el.href='/production-pilot-review';else if(href==='ai_generated_storyboard_contact_sheet.png')el.href='/production-pilot/ai_generated_storyboard_contact_sheet.png';});}</script></body></html>'''
OUT.mkdir(parents=True,exist_ok=True)
(OUT/'导演专业Skill_七镜真实生产与验收.html').write_text(page,encoding='utf-8')
print((OUT/'导演专业Skill_七镜真实生产与验收.html'),len(page))
