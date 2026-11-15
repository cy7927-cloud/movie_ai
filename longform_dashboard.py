#!/usr/bin/env python3
"""Create offline director station for 12-minute source: shot browser, references and actual candidate availability."""
import base64,csv,html,json
from pathlib import Path
import numpy as np
import cv2

def build_dashboard(root):
    root=Path(root); data=root/'data';output=root/'output';output.mkdir(exist_ok=True)
    manifest=json.loads((data/'project_manifest.json').read_text(encoding='utf-8'))
    info=json.loads((data/'shot_features.json').read_text(encoding='utf-8'))
    rows=list(csv.DictReader((data/'shots_source.csv').open(encoding='utf-8')))
    # Avoid misidentifying the target/reference frames as AI-generated candidates.
    shots=[]
    for i,row in enumerate(rows):
        feat=info['features'][i]
        shots.append({'id':row['shot_id'],'t':float(row['start_sec']),'duration':float(row['duration_sec']),
           'refs':{a:row[a.lower()] for a in ['IN','MID','OUT']},
           'visual':feat['visual'],'motion':feat['optical_flow'],'audio_rms':feat['audio_rms'],
           'group':feat['visual_group_proposal'],
           'candidate':'NONE_GENERATED','director_signoff':'NOT_APPROVED',
           'boundary':'UNVERIFIED',
           'intent':'UNKNOWN_NEEDS_INTERPRETATION'})
    js=json.dumps({'shots':shots,'manifest':{k:manifest[k] for k in ['duration_seconds','shot_count','reference_anchor_count','source_scope','reference_resolution']},'audio':info['audio']},ensure_ascii=False).replace('</','<\\/')
    page='''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>AI电影导演 | 正片分镜工作台</title><style>
:root{color-scheme:dark}body{margin:0;background:#0c111c;color:#e6ebf4;font:14px/1.55 -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}header{padding:22px 26px;background:#111b2e;border-bottom:1px solid #2a3f5c;position:sticky;top:0;z-index:10}h1{font-size:22px;margin:0 0 8px}p{margin:4px 0}.sub{color:#9db1c9}.stats{display:flex;flex-wrap:wrap;gap:9px;margin-top:14px}.pill{padding:7px 11px;border:1px solid #2a4564;border-radius:9px;background:#17263b}strong{color:#fff}.warn{color:#ffcf82}.layout{display:grid;grid-template-columns:300px 1fr;min-height:calc(100vh - 145px)}aside{border-right:1px solid #26364d;max-height:calc(100vh - 165px);overflow:auto;position:sticky;top:160px;padding:14px}.search{width:100%;padding:11px;background:#172336;color:#fff;border:1px solid #33495f;border-radius:7px;box-sizing:border-box}.shot{cursor:pointer;border:1px solid #26384d;border-radius:8px;padding:10px;margin:8px 0;background:#111a2b}.shot:hover,.shot.active{border-color:#7faaff;background:#1c2f47}.shot .meta{color:#91a5bd;font-size:12px}main{padding:23px;min-width:0}.stitle{font-size:22px;font-weight:700;margin-bottom:7px}.tag{display:inline-block;margin:4px 5px 4px 0;padding:3px 9px;border-radius:7px;background:#263e56;font-size:12px}.grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin-top:14px}.frame{border:1px solid #314762;border-radius:9px;overflow:hidden;background:#101c2a}.frame img{width:100%;display:block;object-fit:contain;background:#060b12;aspect-ratio:2.4}.frame label{display:block;padding:7px 12px;background:#1d2c41;font-weight:bold}.card{border:1px solid #2a3d59;padding:16px;border-radius:9px;background:#101b2c;margin-top:15px}h3{margin:0 0 11px;font-size:16px}.kv{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}.kv>div{padding:9px;border-radius:6px;background:#15243a}.kv small{display:block;color:#90a7c0}.buttons{display:flex;gap:10px;flex-wrap:wrap;margin:16px 0}.buttons button,.buttons a{background:#315d95;border:none;color:#fff;padding:10px 15px;border-radius:8px;cursor:pointer;text-decoration:none;font-size:14px}button:disabled{opacity:.3;cursor:default}.status{border-left:3px solid #df9940;padding-left:12px;color:#edc892}.notes{color:#a9b8ce}a{color:#b2d1ff}code{background:#22344c;padding:3px 5px;border-radius:4px}@media(max-width:850px){.layout{display:block}aside{max-height:200px;position:static;border-bottom:1px solid #26364d}.grid{grid-template-columns:1fr}.kv{grid-template-columns:1fr}main{padding:14px}} </style></head><body>
<header><h1>AI电影导演 · 正片分镜与导演验收控制台</h1><p class="sub">真实视频拆镜 → IN / MID / OUT 目标分镜 → 独立AI重绘 → 自动审查 → 定向返工 → 验收；以下图片均为原片参考，并非生成成果。</p><div class="stats" id="stats"></div></header>
<div class="layout"><aside><input class="search" id="search" placeholder="检索镜头ID、时间、场景候选..." aria-label="检索镜头"><div id="list"></div></aside><main><div id="detail"></div></main></div>
<script>const DB=__DATA__;const shots=DB.shots;const $=id=>document.getElementById(id);let current=0;
const esc=x=>String(x).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));const stamp=s=>`${String(Math.floor(s/60)).padStart(2,'0')}:${String(Math.floor(s%60)).padStart(2,'0')}`;
const base=(location.protocol==='file:'?'data/references/':'/file?path=data/references/');const img=(s,a)=>base+encodeURIComponent(s.refs[a]);
$('stats').innerHTML=`<span class="pill">片段时长 <strong>${stamp(DB.manifest.duration_seconds)}</strong></span><span class="pill">候选镜头 <strong>${shots.length}</strong></span><span class="pill">原片分镜 <strong>${shots.length*3}</strong></span><span class="pill">AI独立生成 <strong class="warn">0</strong></span><span class="pill">导演已验收 <strong class="warn">0</strong></span><span class="pill">视频生成费用 <strong>0</strong></span>`;
function listing(){let q=$('search').value.trim().toLowerCase();$('list').innerHTML=shots.map((s,i)=>({...s,i})).filter(s=>(s.id+' '+s.group+' '+stamp(s.t)).toLowerCase().includes(q)).map(s=>`<div class="shot ${s.i===current?'active':''}" onclick="select(${s.i})"><strong>${esc(s.id)}</strong><div class="meta">${stamp(s.t)} · ${s.duration.toFixed(1)}秒 · ${esc(s.group)}</div><div class="meta warn">待独立生成 / 待导演验收</div></div>`).join('')||'<p>没有匹配的镜头</p>'}
function select(i){current=i;const s=shots[i];const V=s.visual;let m=s.motion;
$('detail').innerHTML=`<div class="stitle">${esc(s.id)} <span class="tag">${stamp(s.t)}–${stamp(s.t+s.duration)}</span> <span class="tag">${esc(s.group)}</span></div><p class="status">镜头边界：启发式、未人工核验 ｜ AI分镜：尚未生成 ｜ 人物身份与导演语义：未验收</p><div class="grid">${['IN','MID','OUT'].map(a=>`<div class="frame"><label>原片目标分镜 ${a}</label><img src="${img(s,a)}" alt="${a}帧" loading="lazy"></div>`).join('')}</div><div class="buttons"><a href="${img(s,'MID')}" download>保存目标中帧</a><button onclick="copyCommand()">复制此镜头生成工单命令</button><a href="./output/shot_work_orders.jsonl" target="_blank">批量工单数据</a></div><div class="card"><h3>已测量的画面特征（非导演语义）</h3><div class="kv"><div><small>平均相对亮度</small>${V.luminance}</div><div><small>画面对比度代理</small>${V.contrast}</div><div><small>平均饱和度</small>${V.saturation}</div><div><small>边缘密度</small>${V.edge_density}</div><div><small>视觉注意力估计中心</small>${V.visual_attention_proxy_xy.join(', ')}</div><div><small>音频能量 RMS</small>${s.audio_rms}</div></div><p class="notes">图像边缘中心不等于角色位置；Haar人脸、色彩和光流不能证明身份、表演或摄影机轨迹。</p></div><div class="card"><h3>镜头运动线索</h3><p>${esc(m.label)} · 光流矢量 [${m.flow_median_xy.join(', ')}]</p><p class="notes">${esc(m.warning)}</p></div><div class="card"><h3>导演生产门禁</h3><p>① 人工/视觉模型核验戏剧目的、镜头及资产约束 → ② 独立图片模型重绘 IN/MID/OUT → ③ 自动图像质检、角色身份及跨帧连续性 → ④ 定向返工并存档 → ⑤ 导演签核后锁定分镜。</p><p class="status">目前未达到生成验收要求，严禁将此参考图当成AI成片。</p></div>`; listing();}
function copyCommand(){const s=shots[current];const cmd=`python director.py run --shot ${s.id} --anchor MID --dry-run`;if(navigator.clipboard)navigator.clipboard.writeText(cmd).then(()=>alert('已复制：'+cmd)).catch(()=>prompt('复制命令',cmd));else prompt('复制命令',cmd)}
$('search').oninput=listing;select(0);
</script></body></html>'''
    dest=root/'PROJECT_STORYBOARD_REPORT.html';dest.write_text(page.replace('__DATA__',js),encoding='utf-8')
    return dest

if __name__=='__main__':build_dashboard(Path(__file__).resolve().parent)
