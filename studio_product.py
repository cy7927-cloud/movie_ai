#!/usr/bin/env python3
"""Offline-first interactive Director Studio. No paid or external calls from this UI.

All file operations are local and bound to 127.0.0.1 by default.
Image generation API is available separately in director.py with explicit approvals.
"""
import re,argparse,base64,hashlib,json,os,secrets,threading,urllib.parse
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
import cv2,numpy as np
import director as d
import product_engine as engine
import local_model_bridge as bridge
JOBS={}
JOBS_LOCK=threading.Lock()

MAX_BODY=18*1024*1024
LOCK=threading.RLock()
TOKEN=secrets.token_urlsafe(25)

PAGE=r'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Film Director Studio · 自主迭代工作台</title>
<style>
:root{--bg:#0b1019;--surface:#161e2b;--surface2:#1c2838;--border:#344356;--primary:#9ed6ed;--txt:#edf4fc;--muted:#a9b9ca;--warn:#e3b46d;--err:#ee8e85;--good:#7cddb1}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--txt);font-family:ui-sans-serif,'Noto Sans CJK SC','Microsoft YaHei',system-ui,sans-serif}button,input,textarea,select{font:inherit}button{cursor:pointer;background:#263b50;color:var(--txt);border:1px solid #567289;border-radius:8px;padding:9px 12px}button:hover{background:#334d65}button:disabled{opacity:.45;cursor:default}.primary{background:#174a64;border-color:#347c94}input,textarea,select{background:#121c2a;color:var(--txt);border:1px solid #526479;border-radius:7px;padding:8px;width:100%;min-width:0}textarea{min-height:88px;resize:vertical}a{color:var(--primary)}.top{height:auto;min-height:72px;padding:12px 22px;border-bottom:1px solid var(--border);display:flex;align-items:center;gap:22px;background:#101826;flex-wrap:wrap}.brand{font-size:20px;font-weight:700;letter-spacing:.02em}.sub{color:var(--muted);font-size:12px}.kpis{display:flex;gap:12px;margin-left:auto;flex-wrap:wrap}.kpis span{font-size:13px;white-space:nowrap}.kpis b{font-size:18px;color:#d4eefa;margin-right:5px}.shell{display:grid;grid-template-columns:265px minmax(390px,1fr) 320px;height:calc(100vh - 75px);min-height:580px}.side,.right{background:#111b29;padding:15px;overflow-y:auto}.side{border-right:1px solid var(--border)}.right{border-left:1px solid var(--border)}.middle{padding:18px;overflow:auto}.pane-title{font-size:13px;color:#aabaca;text-transform:uppercase;letter-spacing:.07em;margin:16px 0 9px}.shot-list{display:flex;flex-direction:column;gap:6px;margin-top:12px}.shot{display:flex;align-items:center;justify-content:space-between;gap:5px;padding:11px;border-radius:9px;background:#1a2635;border:1px solid transparent;text-align:left}.shot.active{border-color:#67a9c5;background:#1c3b4f}.shot small{color:#acc0cc;font-size:10px}.minor{font-size:12px;color:var(--muted)}.section{border:1px solid var(--border);border-radius:12px;padding:15px;margin-bottom:14px;background:var(--surface)}.stack{display:flex;align-items:center;justify-content:space-between;gap:9px;flex-wrap:wrap}.tab{border-radius:7px;border:1px solid var(--border);background:#253446;padding:5px 9px;font-size:12px}.tab.active{background:#2e637d;border-color:#83a6be}.columns{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.frame{width:100%;aspect-ratio:16/9;background:#091017;border-radius:8px;object-fit:contain}.board{background:#0d1622;border:1px solid #293d53;padding:10px;border-radius:10px}.board small{display:block;color:var(--muted);margin-bottom:5px}.status{font-size:11px;color:var(--warn);border:1px solid #66583b;padding:4px 7px;border-radius:99px}.good{color:var(--good)}.warn{color:var(--warn)}.err{color:var(--err)}.muted{color:var(--muted)}.chip{font-size:12px;border-radius:7px;background:#26354a;padding:6px 8px}.actions{display:flex;flex-wrap:wrap;gap:6px;margin:10px 0}.history{max-height:255px;overflow:auto}.version{font-size:12px;padding:8px;border-bottom:1px solid #354455}.issue{border-left:3px solid #eeb475;padding:6px 10px;margin:9px 0;background:#203041;font-size:12px}.issue b{display:block;margin-bottom:5px}.field{margin:10px 0}.field label{font-size:12px;color:var(--muted);display:block;margin-bottom:5px}#notice{position:fixed;bottom:16px;left:50%;transform:translateX(-50%);background:#234157;color:white;border:1px solid #5e8299;padding:10px 16px;border-radius:9px;display:none;z-index:100;max-width:90vw}.footer{font-size:12px;color:#b4c4d2;line-height:1.6}.loading{opacity:.65}@media(max-width:1100px){.shell{grid-template-columns:210px minmax(0,1fr);height:auto}.right{grid-column:2;border-left:0;border-top:1px solid var(--border)}.middle{overflow:visible}.side{max-height:85vh}}@media(max-width:650px){.shell{display:block}.side{max-height:270px;border-right:0;border-bottom:1px solid var(--border)}.shot-list{display:grid;grid-template-columns:repeat(3,minmax(0,1fr))}.shot{padding:8px}.middle,.right{padding:12px}.columns{grid-template-columns:1fr}.top{padding:12px}.kpis{margin-left:0}}
</style></head><body>
<div class="top"><div><div class="brand">FILM DIRECTOR <span style="color:#80c5e3">STUDIO</span></div><div class="sub">电影导演自主迭代 · 图像优先 / 视频后置 / 每轮可追溯 · <a href="/longform" target="_blank" style="color:#80c5e3">打开完整正片分镜总览</a></div></div><div class="kpis" id="kpis"><span>加载中…</span></div></div>
<div class="shell"><aside class="side"><div class="stack"><b>镜头目录</b><button onclick="refreshAll()" title="刷新">刷新</button></div><div class="field"><input id="search" oninput="drawList()" placeholder="搜索镜头号"></div><div class="field"><select id="filter" onchange="drawList()"><option value="all">全部镜头</option><option value="candidate">已有候选</option><option value="missing">待独立生成</option><option value="approved">已签核</option></select></div><div class="shot-list" id="shotList"></div><div class="footer" style="margin-top:16px">新电影项目：<code>python production_cli.py import-film /路径/电影.mp4 --out /新项目</code>。镜头边界需复核。</div></aside>
<main class="middle"><div class="stack"><div><div class="sub">镜头导演工作台</div><h2 id="shotTitle" style="margin:3px 0 5px">请选择镜头</h2><div class="minor" id="shotMeta"></div></div><div id="anchorTabs"></div></div>
<section class="section"><div class="stack"><b>目标分镜 ↔ 当前最佳候选</b><span class="status" id="anchorStatus">待加载</span></div><p class="minor">左图来自原片，右图必须来自独立候选或其明确标记的本地修正。无法验证身份、导演意图时绝不自动通过。</p><div class="columns"><div class="board"><small>原片参考帧</small><img id="refImage" class="frame"></div><div class="board"><small id="candidateLabel">尚未生成候选</small><img id="candidateImage" class="frame"></div></div><div class="actions"><button onclick="openFile('reference')">查看原始帧</button><button onclick="openFile('candidate')">查看候选图</button><button onclick="openBoard()">差异审查板</button><button onclick="copyPrompt()">复制下一轮重绘指令</button></div></section>
<section class="section"><div class="stack"><b>三帧连续性审查</b><span class="minor">IN / MID / OUT</span></div><div class="columns" style="grid-template-columns:repeat(3,minmax(0,1fr))" id="triple"></div><div id="continuity" class="minor" style="margin-top:10px"></div></section>
<section class="section"><div class="stack"><b>迭代与审查记录</b><button onclick="showHistory()">展开记录</button></div><div class="history" id="history"></div></section></main>
<aside class="right"><div class="pane-title">导演意图及资产约束</div><div class="field"><label>该镜头讲什么？</label><textarea id="intent" placeholder="镜头戏剧目的、人物情绪、观众应获得的信息"></textarea></div><div class="field"><label>人物站位 / 视线 / 服装 / 场景约束</label><textarea id="annotations" placeholder="导演约束，可填写一整段文字"></textarea></div><button class="primary" onclick="saveSpec()">保存镜头规范（更改即使旧审核失效）</button>
<div class="pane-title">图片优先：生成与返工</div><div class="actions"><button class="primary" onclick="dryRun()">生成重绘指令（免费）</button><button onclick="document.getElementById('upload').click()">导入生成好的图片</button><input id="upload" type="file" accept="image/png,image/jpeg,image/webp" style="display:none" onchange="uploadImage(this)"><button onclick="refine()">自动安全修正 · 最多2轮</button><button id="localBtn" onclick="startLocal()" disabled>本地AI自动生成+自审</button></div><div class="minor" id="localState">检测本地图像模型…</div><p class="minor">本工作台**不自动触发任何付费调用**。可把重绘指令交给图片生成模型，再将候选图导入；真实API生成需在终端显式设置额度与权限。</p>
<div class="pane-title">失败原因与返工指令</div><div id="issues"><p class="minor">请选择已有候选的镜头。</p></div>
<div class="pane-title">全片级验收</div><div class="actions"><button onclick="exportPlan()">导出全部生成工单</button><button onclick="runAudit()">全片分镜审查</button><button onclick="batchRefine()">已有候选批量安全返工</button><button onclick="exportGate()">检查成片导出门禁</button></div><div id="globalAudit" class="minor">当前优先级：静态分镜的自我迭代，不花视频生成费。</div><div class="footer">**真实性标注**：上传视频与参考帧不是AI生成；二维分数不是人物身份、空间调度或导演意图证明。正式导出必须通过各镜头三帧签核。</div></aside></div><div id="notice"></div>
<script>
const TOKEN='__CSRF__';let shotList=[],shot=null,anchor='MID',detail=null,apiBase='';
function toast(m){let x=document.getElementById('notice');x.textContent=m;x.style.display='block';setTimeout(()=>x.style.display='none',5500)}
async function api(route,payload){const o={};if(payload!==undefined){o.method='POST';o.headers={'Content-Type':'application/json','X-Director-Token':TOKEN};o.body=JSON.stringify(payload)}const r=await fetch(route,o);const j=await r.json();if(!r.ok)throw new Error(j.error||r.statusText);return j}
function uri(p){return p?'/file?path='+encodeURIComponent(p):''}
async function refreshAll(){try{const j=await api('/api/tasks');shotList=j.shots;document.getElementById('kpis').innerHTML=`<span><b>${j.shot_count}</b>镜头</span><span><b>${j.task_count}</b>分镜卡</span><span><b>${j.with_candidate}</b>已有候选</span><span><b>${j.approved}</b>已签核</span><span><b>0</b>AI成片镜头</span>`;drawList();if(!shot&&shotList.length)shot=shotList[0].id;await loadShot()}catch(e){toast('加载失败：'+e.message)}}
function drawList(){let q=document.getElementById('search').value.toLowerCase(),f=document.getElementById('filter').value;let filtered=shotList.filter(x=>(!q||x.id.toLowerCase().includes(q))&&(f==='all'||(f==='candidate'&&x.candidates>0)||(f==='missing'&&x.candidates===0)||(f==='approved'&&x.approved===3)));document.getElementById('shotList').innerHTML=filtered.map(x=>`<button class="shot ${x.id===shot?'active':''}" onclick="selectShot('${x.id}')"><span>${x.id}<small style="display:block">${x.start.toFixed(1)}s · ${x.duration.toFixed(1)}s</small></span><small>${x.candidates}/3</small></button>`).join('')||'<div class="minor">无匹配镜头</div>'}
async function selectShot(s){shot=s;anchor='MID';drawList();await loadShot()}
async function loadShot(){if(!shot)return;try{detail=await api('/api/shot?shot='+encodeURIComponent(shot));document.getElementById('shotTitle').textContent=shot;document.getElementById('shotMeta').textContent=`${detail.start.toFixed(2)}秒开始 · ${detail.duration.toFixed(2)}秒 · 3张目标分镜`;document.getElementById('anchorTabs').innerHTML=['IN','MID','OUT'].map(a=>`<button class="tab ${a===anchor?'active':''}" onclick="setAnchor('${a}')">${a}</button>`).join(' ');renderShot()}catch(e){toast(e.message)}}
function setAnchor(a){anchor=a;loadShot()}
function item(){return detail?.anchors?.find(x=>x.anchor===anchor)}
function renderShot(){const a=item();if(!a)return;document.getElementById('refImage').src=uri(a.reference);document.getElementById('candidateImage').src=a.best?uri(a.best.candidate):'';document.getElementById('candidateImage').alt=a.best?'最佳技术候选图':'尚未有真实独立生成的候选';document.getElementById('candidateLabel').textContent=a.best?`当前技术最佳 · ${a.best.provider} · ${a.best.metrics.technical_score?.toFixed(3)??'未知'}`:'无候选（不能用原片充数）';document.getElementById('anchorStatus').textContent=a.status;document.getElementById('intent').value=a.intent||'';document.getElementById('annotations').value=a.constraints?.director_annotations?.blocking_notes||'';document.getElementById('issues').innerHTML=(a.best?.issues||[]).map(i=>`<div class="issue"><b>${escapeHtml(i.kind)} · ${escapeHtml(i.severity)}</b><div>${escapeHtml(i.description)}</div><div class="minor">下一轮：${escapeHtml(i.fix)}</div></div>`).join('')||'<p class="minor">尚无候选或尚无问题诊断。</p>';document.getElementById('history').innerHTML=a.history.map(h=>`<div class="version">第${h.cycle}轮 · ${escapeHtml(h.provider)} · SSIM ${h.metrics.ssim??'-'} · 技术分 ${h.metrics.technical_score??'-'}<div class="minor">${escapeHtml(h.verdict)}</div></div>`).join('')||'<p class="minor">该分镜还没有任何候选迭代。</p>';document.getElementById('triple').innerHTML=detail.anchors.map(v=>`<div class="board"><small>${v.anchor} · ${v.best?'有候选':'仅参考'}</small><img class="frame" src="${uri(v.best?v.best.candidate:v.reference)}"></div>`).join('');document.getElementById('continuity').textContent=(detail.cross_anchor_checks||[]).map(i=>i.anchors.join('→')+': '+i.status+(i.deviation_lab?' (亮度/色彩变化偏差 '+i.deviation_lab.toFixed(1)+')':'')).join(' ｜ ');}
function escapeHtml(s){return String(s||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function openFile(which){const a=item();let p=which==='reference'?a.reference:a.best?.candidate;if(!p)return toast('尚无候选');window.open(uri(p),'_blank')}
function openBoard(){const a=item();if(!a.best)return toast('还没有候选图');window.open(uri(a.best.board),'_blank')}
function showHistory(){document.getElementById('history').scrollIntoView({behavior:'smooth'})}
async function saveSpec(){try{const a=item(),c={...(a.constraints||{})};c.director_annotations={...(c.director_annotations||{}),blocking_notes:document.getElementById('annotations').value};await api('/api/annotate',{task_id:a.id,intent:document.getElementById('intent').value,constraints:c});toast('镜头规范已保存；旧审核若依赖旧规范则已失效');await loadShot()}catch(e){toast('保存失败：'+e.message)}}
async function dryRun(){try{const r=await api('/api/dryrun',{task_id:item().id});promptValue=r.prompt;await navigator.clipboard.writeText(r.prompt).catch(()=>{});toast('已生成下一轮重绘指令并尝试复制。长度 '+r.prompt.length+' 字符');showPrompt(r.prompt)}catch(e){toast(e.message)}}let promptValue='';function showPrompt(s){document.getElementById('globalAudit').innerHTML=`<b>最新重绘指令</b><textarea readonly style="min-height:160px">${escapeHtml(s)}</textarea>`}function copyPrompt(){dryRun()}
async function uploadImage(el){try{const f=el.files[0];if(!f)return;if(f.size>12*1024*1024)throw new Error('图片不得超过12 MB');const b64=await new Promise((yes,no)=>{let r=new FileReader();r.onload=()=>yes(String(r.result).split(',')[1]);r.onerror=no;r.readAsDataURL(f)});let r=await api('/api/import',{task_id:item().id,filename:f.name,b64});toast('图像已入库，结果：'+r.verdict);await refreshAll()}catch(e){toast('导入失败：'+e.message)}finally{el.value=''}}
async function refine(){if(!item()?.best)return toast('没有生成候选，不能凭原片自动造图。');try{const r=await api('/api/refine',{task_id:item().id,steps:2});toast('安全修正：'+r.count+'轮；无明确改善会自动停止。');await refreshAll()}catch(e){toast(e.message)}}
async function runAudit(){try{const j=await api('/api/audit');const s=j.stats;document.getElementById('globalAudit').textContent=`已审查 ${s.shots} 镜头 / ${s.frames} 帧，已有候选 ${s.anchors_with_candidates} 张，全部签核镜头 ${s.shots_fully_approved}，跨帧对比 ${s.cross_anchor_pairs_measured} 组。AI视频生成：0。`;toast('全片审查完成；已保存 production_audit.json')}catch(e){toast(e.message)}}
async function exportPlan(){try{let j=await api('/api/plan',{});toast(`导出 ${j.count} 个生成工单，保存在 output/`)}catch(e){toast(e.message)}}
async function batchRefine(){try{const r=await api('/api/batch-local',{limit:5,steps:2});toast('完成 '+r.length+' 条已有候选的本地迭代；不调用图片/视频付费模型');await refreshAll()}catch(e){toast(e.message)}}
async function checkLocal(){try{const v=await api('/api/local-model-status');const ok=v.available&&v.connected;document.getElementById('localBtn').disabled=!ok;document.getElementById('localState').textContent=ok?'本地模型已连接：可用本机资源自动生成（不含语义验收）':'本地模型未连接。配置 local_model_config.json 与本机 ComfyUI 后启用。';}catch(e){document.getElementById('localState').textContent=e.message}}
async function startLocal(){try{const r=await api('/api/local-run',{task_id:item().id,max_rounds:3});toast('本地模型任务已启动：'+r.job_id);pollLocal(r.job_id)}catch(e){toast('无法启动：'+e.message)}}
async function pollLocal(id){for(let i=0;i<180;i++){await new Promise(r=>setTimeout(r,2000));try{const s=await api('/api/job-status?id='+encodeURIComponent(id));document.getElementById('localState').textContent='任务 '+id.slice(0,8)+'：'+s.status+(s.error?' / '+s.error:'');if(s.status==='done'||s.status==='error'){toast(s.status==='done'?'本地图片生成完成；仍需导演语义审核':'本地生成失败：'+s.error);await refreshAll();return}}catch(e){toast(e.message);return}}}
async function exportGate(){try{const j=await api('/api/export-gate',{});document.getElementById('globalAudit').textContent=`合成门禁 ${j.result}：已签核 ${j.eligible_shots??0}/${j.total_shots??0} 镜头；未签核不得作为AI成片输出。`;toast('合成门禁：'+j.result)}catch(e){toast(e.message)}}
refreshAll();checkLocal();
</script></body></html>'''

# The review UI links to the evidence-oriented, independently-audited reference card dashboard.
PAGE=PAGE.replace('<div class="shell">', '<div style="padding:9px 20px;background:#152638;border-bottom:1px solid #365371"><a style="color:#b2dcff" href="/evidence">打开导演证据与93秒连续场景验收台（零视频生成）</a>　·　<a style="color:#b2dcff" href="/cuts">切镜分歧复核</a>　·　<a style="color:#f3d29d" href="/director">导演语言与表演工作台</a>　·　<a style="color:#b2dcff" href="/longform">查看86个原片镜头</a>　·　<a style="color:#f3d29d" href="/gpt-director-study">GPT导演｜《妖猫传》逐帧学习</a>　·　<a style="color:#ffdf9d" href="/skill-acceptance">全功能真实验收（专业Skill）</a>　·　<a style="color:#b2edc4" href="/production-pilot">7镜原创AI分镜实测</a>　·　<a style="color:#b9d1ff" href="/style-lab">电影风格→专业Skill激活对照</a>　·　<a style="color:#f3d29d" href="/dense-style-study/">全片段密集导演研究</a></div><div class="shell">')

class Handler(BaseHTTPRequestHandler):
    server_version='DirectorStudio/1.0'
    def log_message(self,format,*args):
        if not self.path.startswith('/file?'):super().log_message(format,*args)
    def send_json(self,ob,status=200):
        raw=json.dumps(ob,ensure_ascii=False).encode('utf-8')
        self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(raw)))
        self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(raw)
    def do_GET(self):
      try:
        url=urllib.parse.urlparse(self.path);query=urllib.parse.parse_qs(url.query)
        if url.path=='/dense-style-study/' or url.path.startswith('/dense-style-study/'):
            # Read-only, strict allowlist for the actual user-supplied film study.
            suffix=urllib.parse.unquote(url.path.removeprefix('/dense-style-study/'))
            if suffix in ('', 'index.html'):
                suffix='index.html'
            elif suffix in ('film_study_data.json','professional_skill_activation.json','evidence_manifest.json','导演密集研究与专业Skill激活_真实报告.md'):
                pass
            elif re.fullmatch(r'evidence/(?:minute/minute_\d{2}|15sec/window_\d{2}|frames/\d{4}s)\.jpg',suffix):
                pass
            else:
                return self.send_json({'error':'Not an allowed dense-style-study resource'},403)
            source=d.BASE/'output/dense_film_style_study'/suffix
            if not source.is_file():return self.send_json({'error':'Dense study media missing'},404)
            ctype=('text/html; charset=utf-8' if suffix.endswith('.html') else
                   'application/json; charset=utf-8' if suffix.endswith('.json') else
                   'text/markdown; charset=utf-8' if suffix.endswith('.md') else 'image/jpeg')
            raw=source.read_bytes();self.send_response(200)
            self.send_header('Content-Type',ctype)
            self.send_header('Content-Length',str(len(raw)))
            self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Content-Security-Policy',"default-src 'self' 'unsafe-inline' data:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
            self.end_headers();self.wfile.write(raw);return
        if url.path=='/':
            blob=PAGE.replace('__CSRF__',TOKEN).encode('utf-8')
            self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(blob)))
            self.send_header('Content-Security-Policy',"default-src 'self' 'unsafe-inline' data:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
            self.end_headers();self.wfile.write(blob);return
        if url.path in ('/evidence','/evidence-data','/acceptance','/shot-orders','/cuts','/director','/director-data','/editing','/editing-data','/director-model-lab','/gpt-director-study','/gpt-director-data','/skill-acceptance','/skill-acceptance-json','/skill-acceptance-report','/production-pilot','/production-pilot-json','/production-pilot-review','/style-lab','/style-profile-json','/style-comparison-json'):
            route={'/evidence':('DIRECTOR_EVIDENCE.html','text/html; charset=utf-8'),
               '/evidence-data':('output/evidence/director_evidence.json','application/json; charset=utf-8'),
               '/acceptance':('output/FINAL_ACCEPTANCE.html','text/html; charset=utf-8'),
               '/shot-orders':('output/shot_work_orders.jsonl','application/x-ndjson; charset=utf-8'),
               '/cuts':('output/cut_review/index.html','text/html; charset=utf-8'),
               '/director':('DIRECTOR_DESK.html','text/html; charset=utf-8'),
               '/director-data':('output/director_lab/DIRECTOR_LAB_ACCEPTANCE.json','application/json; charset=utf-8'),
               '/editing':('EDITORIAL_DIRECTOR_LAB.html','text/html; charset=utf-8'),
               '/editing-data':('output/editorial_language/acceptance.json','application/json; charset=utf-8'),
               '/director-model-lab':('output/model_research_lab/导演模型实验室.html','text/html; charset=utf-8'),
               '/gpt-director-study':('GPT_DIRECTOR_FILM_STUDY.html','text/html; charset=utf-8'),
               '/gpt-director-data':('output/gpt_director_study/study_and_rehearsal.json','application/json; charset=utf-8'),
               '/skill-acceptance':('output/skill_end_to_end_acceptance/完整成品验收仪表盘.html','text/html; charset=utf-8'),
               '/skill-acceptance-json':('output/skill_end_to_end_acceptance/acceptance.json','application/json; charset=utf-8'),
               '/skill-acceptance-report':('output/skill_end_to_end_acceptance/完整成品验收报告.md','text/markdown; charset=utf-8'),
               '/production-pilot':('output/real_production_pilot/导演专业Skill_七镜真实生产与验收.html','text/html; charset=utf-8'),
               '/production-pilot-json':('output/real_production_pilot/professional_camera_handoff.json','application/json; charset=utf-8'),
               '/production-pilot-review':('output/real_production_pilot/independent_media_review.json','application/json; charset=utf-8'),
               '/style-lab':('output/film_style_activation/电影风格_专业Skill激活对照实验.html','text/html; charset=utf-8'),
               '/style-profile-json':('output/film_style_activation/妖猫传_风格激活配置.json','application/json; charset=utf-8'),
               '/style-comparison-json':('output/film_style_activation/对照验收.json','application/json; charset=utf-8')}
            filename,mime=route[url.path];page=d.BASE/filename
            if not page.is_file():return self.send_json({'error':'Run python production_cli.py evidence first'},404)
            raw=page.read_bytes()
            if url.path in ('/cuts','/director','/editing'): raw=raw.replace(b'__CSRF__',TOKEN.encode('ascii'))
            self.send_response(200);self.send_header('Content-Type',mime)
            self.send_header('Content-Length',str(len(raw)))
            self.send_header('Content-Security-Policy',"default-src 'self' 'unsafe-inline' data:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
            self.end_headers();self.wfile.write(raw);return
        if url.path.startswith('/production-pilot/'):  # media-only, narrow allowlist
            rel=urllib.parse.unquote(url.path.removeprefix('/production-pilot/'))
            allowed=('ai_generated_storyboard_contact_sheet.png','AI分镜静帧预演_非成片.mp4')
            if rel in allowed:
                source=d.BASE/'output/real_production_pilot'/rel
            elif re.fullmatch(r'generated_stills/S0[1-7]_AI_CANDIDATE\.png',rel):
                source=d.BASE/'output/real_production_pilot'/rel
            else:
                return self.send_json({'error':'Invalid pilot media'},403)
            if not source.is_file():return self.send_json({'error':'Pilot media missing'},404)
            raw=source.read_bytes()
            self.send_response(200)
            self.send_header('Content-Type','video/mp4' if source.suffix=='.mp4' else 'image/png')
            self.send_header('Content-Length',str(len(raw)))
            self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff')
            self.end_headers();self.wfile.write(raw);return
        if url.path=='/longform':
            page=d.BASE/'PROJECT_STORYBOARD_REPORT.html'
            if not page.is_file():return self.send_json({'error':'Longform report not available yet'},404)
            raw=page.read_bytes()
            self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8')
            self.send_header('Content-Length',str(len(raw)))
            self.send_header('Content-Security-Policy',"default-src 'self' 'unsafe-inline' data:; object-src 'none'; frame-ancestors 'none'")
            self.end_headers();self.wfile.write(raw);return
        if url.path.startswith('/gpt_director_study/source_frames/'):
            fname=urllib.parse.unquote(url.path.rsplit('/',1)[-1])
            if not re.fullmatch(r'CASE_[AB]_[0-9]{2}_[0-9]+\.[0-9]s\.jpg',fname):
                return self.send_json({'error':'Invalid reference frame filename'},403)
            file=d.BASE/'output/gpt_director_study/source_frames'/fname
            if not file.is_file():return self.send_json({'error':'Frame missing'},404)
            raw=file.read_bytes();self.send_response(200)
            self.send_header('Content-Type','image/jpeg');self.send_header('Content-Length',str(len(raw)))
            self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(raw);return
        if url.path.startswith('/output/gpt_director_study/'):
            # Only public reference thumbnails produced by the user's film-study module.
            rel=urllib.parse.unquote(url.path.lstrip('/'))
            resolved=(d.BASE/rel).resolve()
            public=(d.BASE/'output/gpt_director_study').resolve()
            if public not in resolved.parents or resolved.suffix.lower() not in ('.jpg','.jpeg','.png','.webp'):
                return self.send_json({'error':'Invalid director-study image'},403)
            if not resolved.is_file():return self.send_json({'error':'Image missing'},404)
            raw=resolved.read_bytes();self.send_response(200)
            self.send_header('Content-Type','image/jpeg' if resolved.suffix.lower() in ('.jpg','.jpeg') else 'image/png')
            self.send_header('Content-Length',str(len(raw)));self.send_header('Cache-Control','no-store')
            self.end_headers();self.wfile.write(raw);return
        if url.path=='/cut-image':
            name=query.get('name',[''])[0]
            if not re.fullmatch(r'cut_disagreements_page_[0-9]{2}\.jpg',name):return self.send_json({'error':'Invalid image'},403)
            f=d.BASE/'output/cut_review'/name
            if not f.is_file():return self.send_json({'error':'Not found'},404)
            raw=f.read_bytes();self.send_response(200);self.send_header('Content-Type','image/jpeg');self.send_header('Content-Length',str(len(raw)))
            self.end_headers();self.wfile.write(raw);return
        if url.path=='/api/tasks':
            with LOCK,d.connect() as c:
                rows=c.execute('SELECT shot_id, MIN(start_sec) start, MAX(duration) duration FROM tasks GROUP BY shot_id ORDER BY start').fetchall()
                status=[];total_candidates=0;total_approved=0
                for row in rows:
                    shots=c.execute('SELECT * FROM tasks WHERE shot_id=?',(row['shot_id'],)).fetchall()
                    candidates=sum(engine.best_valid_attempt(c,t) is not None for t in shots)
                    approved=sum(t['status']=='STORYBOARD_APPROVED' for t in shots)
                    status.append({'id':row['shot_id'],'start':float(row['start']),'duration':float(row['duration']),
                        'candidates':candidates,'approved':approved});total_candidates+=candidates;total_approved+=approved
                self.send_json({'shots':status,'shot_count':len(status),'task_count':len(status)*3,'with_candidate':total_candidates,'approved':total_approved});return
        if url.path=='/api/shot':
            shot=query.get('shot',[''])[0]
            if not shot or len(shot)>64:return self.send_json({'error':'shot not found'},404)
            with LOCK,d.connect() as c:
                review=engine.shot_review(c,shot)
                if not review:return self.send_json({'error':'shot not found'},404)
                tasks=c.execute('SELECT * FROM tasks WHERE shot_id=? ORDER BY CASE anchor WHEN "IN" THEN 0 WHEN "MID" THEN 1 ELSE 2 END',(shot,)).fetchall()
                review['start']=float(tasks[0]['start_sec']);review['duration']=float(tasks[0]['duration']);
                for i,t in enumerate(tasks):
                    h=c.execute('SELECT * FROM attempts WHERE task_id=? ORDER BY id',(t['id'],)).fetchall()
                    best=engine.best_valid_attempt(c,t)
                    review['anchors'][i].update({'intent':t['intent'],'constraints':d.read_json(t['constraints'],{}),
                     'history':[{'cycle':z['cycle'],'provider':z['provider'],'metrics':d.read_json(z['metrics'],{}),'verdict':z['verdict'],'prompt':z['prompt']} for z in h],
                     'best':({**{'candidate':best['candidate'],'provider':best['provider'],'metrics':d.read_json(best['metrics'],{}),'issues':d.read_json(best['issues'],{})},
                       'board':d.rel(d.OUT/'boards'/shot/t['anchor']/f'round_{best["cycle"]:02}.jpg')} if best else None)})
                self.send_json(review);return
        if url.path=='/api/local-model-status':
            return self.send_json(bridge.get_status())
        if url.path=='/api/job-status':
            jid=query.get('id',[''])[0]
            with JOBS_LOCK:
                job=JOBS.get(jid)
                return self.send_json(dict(job) if job else {'error':'Job not found'},200 if job else 404)
        if url.path=='/api/audit':
            with LOCK:self.send_json(engine.project_audit());return
        if url.path=='/file':
            name=query.get('path',[''])[0]
            if not name or Path(name).is_absolute():return self.send_json({'error':'Invalid media path'},403)
            resolved=(d.BASE/name).resolve()
            roots=[d.REF.resolve(),(d.DATA/'candidates').resolve(),(d.OUT/'boards').resolve(),(d.OUT/'previews').resolve(),(d.OUT/'evidence').resolve(),(d.OUT/'director_lab').resolve()]
            if not any(resolved==rt or rt in resolved.parents for rt in roots):return self.send_json({'error':'Not a public asset'},403)
            if resolved.suffix.lower() not in ('.jpg','.jpeg','.png','.webp','.mp4') or not resolved.is_file():return self.send_json({'error':'File not found'},404)
            mime={'.jpg':'image/jpeg','.jpeg':'image/jpeg','.png':'image/png','.webp':'image/webp','.mp4':'video/mp4'}[resolved.suffix.lower()]
            self.send_response(200);self.send_header('Content-Type',mime);self.send_header('Content-Length',str(resolved.stat().st_size));self.send_header('Cache-Control','no-store');self.end_headers()
            with resolved.open('rb') as f:
                while True:
                    chunk=f.read(256*1024)
                    if not chunk:break
                    self.wfile.write(chunk)
            return
        self.send_json({'error':'Not found'},404)
      except Exception as e:self.send_json({'error':str(e)[:500]},500)

    def do_POST(self):
      try:
        if self.headers.get('X-Director-Token')!=TOKEN:return self.send_json({'error':'Local auth token missing'},403)
        origin=self.headers.get('Origin','')
        if origin and origin not in ('http://127.0.0.1:'+str(self.server.server_port),'http://localhost:'+str(self.server.server_port)):
            return self.send_json({'error':'Origin is not allowed'},403)
        size=int(self.headers.get('Content-Length','0'))
        if size<1 or size>MAX_BODY:return self.send_json({'error':'Invalid request size'},413)
        payload=json.loads(self.rfile.read(size).decode('utf-8'))
        path=urllib.parse.urlparse(self.path).path
        if path=='/api/editorial-decision':
            import editorial_intelligence as edit
            with LOCK:
                result=edit.save_director_edit(d.BASE, str(payload.get('id','')),
                    str(payload.get('relation','')),str(payload.get('hypothesis','')),
                    str(payload.get('evidence','')),str(payload.get('reviewer','')))
            return self.send_json(result)
        if path=='/api/editorial-design':
            import editorial_intelligence as edit
            return self.send_json(edit.design_scene(str(payload.get('brief','')),
                                                  str(payload.get('pattern','suspense_insert'))))
        if path=='/api/director-notes':
            import director_craft as craft
            with LOCK:r=craft.safe_notes(str(payload.get('shot_id','')),payload.get('notes',{}))
            return self.send_json(r)
        if path=='/api/cut-decision':
            import cut_review as cuts
            with LOCK:r=cuts.mark(str(payload.get('id','')),str(payload.get('decision','')),
                str(payload.get('reviewer','')),str(payload.get('reason','')))
            return self.send_json(r)
        if path=='/api/local-run':
            state=bridge.get_status()
            if not(state.get('available') and state.get('connected')):
                return self.send_json({'error':'Local image generator not configured or unreachable.'},400)
            tid=str(payload.get('task_id',''))
            rounds=max(1,min(5,int(payload.get('max_rounds',3))))
            with JOBS_LOCK:
                if any(j['status']=='running' for j in JOBS.values()):
                    return self.send_json({'error':'Another local model job is running.'},409)
                jobid=secrets.token_hex(12)
                JOBS[jobid]={'status':'running','task_id':tid,'generated':0}
            def worker():
                try:
                    result=bridge.local_self_iterate(tid,rounds)
                    with JOBS_LOCK:JOBS[jobid]={'status':'done','task_id':tid,'generated':result['generated'], 'approved':False}
                except Exception as e:
                    with JOBS_LOCK:JOBS[jobid]={'status':'error','task_id':tid,'error':str(e)[:500]}
            threading.Thread(target=worker,daemon=True).start()
            return self.send_json({'job_id':jobid,'status':'running','provider':'LOCAL_ONLY'})
        if path=='/api/plan':return self.send_json(d.export_plan())
        if path=='/api/audit':return self.send_json(engine.project_audit())
        if path=='/api/export-gate':return self.send_json(engine.export_cut())
        if path=='/api/batch-local':
            limit=max(1,min(10,int(payload.get('limit',5))));steps=max(1,min(3,int(payload.get('steps',2))))
            with LOCK:r=engine.batch_local_refine(limit,steps)
            return self.send_json(r)
        tid=str(payload.get('task_id',''))
        if not tid or len(tid)>90 or ':' not in tid:return self.send_json({'error':'Invalid task id'},400)
        with LOCK,d.connect() as c:
            task=c.execute('SELECT * FROM tasks WHERE id=?',(tid,)).fetchone()
            if not task:return self.send_json({'error':'Task not found'},404)
            if path=='/api/annotate':
                r=d.rebase_spec(c,tid,payload.get('intent',''),payload.get('constraints',{}));return self.send_json(r)
            if path=='/api/dryrun':
                prev=c.execute('SELECT * FROM attempts WHERE task_id=? ORDER BY id DESC LIMIT 1',(tid,)).fetchone()
                prompt=d.build_prompt(task,d.read_json(prev['issues'],[]) if prev else None,prev,d.history_for(c,task['shot_id']),'reference')
                return self.send_json({'prompt':prompt,'paid_calls':0,'status':'DRYRUN_ONLY'})
            if path=='/api/import':
                raw=base64.b64decode(payload.get('b64',''),validate=True)
                if len(raw)>12*1024*1024 or not raw:raise ValueError('Image file missing or >12MB')
                arr=np.frombuffer(raw,dtype=np.uint8);im=cv2.imdecode(arr,cv2.IMREAD_COLOR)
                if im is None or im.ndim!=3 or min(im.shape[:2])<64 or max(im.shape[:2])>8192:
                    raise ValueError('Invalid image geometry')
                dest=d.OUT/'imports'/(hashlib.sha256(raw).hexdigest()+'.png')
                dest.parent.mkdir(parents=True,exist_ok=True)
                cv2.imwrite(str(dest),im)
                r=d.store_attempt(c,tid,dest,'manual_import','unverified_external_image','independent',
                     'Candidate supplied by user. Independent provenance was not cryptographically verified.')
                return self.send_json(r)
            if path=='/api/refine':
                r=d.safe_local_refinement(c,tid,max(1,min(3,int(payload.get('steps',2)))))
                return self.send_json({'count':len(r),'results':r})
        self.send_json({'error':'Unknown action'},404)
      except (ValueError,KeyError,RuntimeError) as e:self.send_json({'error':str(e)[:400]},400)
      except Exception as e:self.send_json({'error':str(e)[:400]},500)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--port',type=int,default=8766);p.add_argument('--host',default='127.0.0.1')
    args=p.parse_args()
    if args.host not in ('127.0.0.1','localhost'):
        raise SystemExit('For privacy, studio only binds to 127.0.0.1 (local machine).')
    d.bootstrap();d.render_report();engine.project_audit()
    server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
    print(f'Film Director Studio running at http://127.0.0.1:{server.server_port} (CTRL+C to stop)')
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
if __name__=='__main__':main()
