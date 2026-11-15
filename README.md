## 最新：密集分镜全片段导演学习（只研究原片，不编造新剧本）

- 用用户原始视频SHA核验 776.477 秒真实素材；0.25秒取帧3106张，0.5秒原分辨率取帧1553张。
- **13个分钟段落**进行目视观察（已覆盖00:00–12:56），**52个15秒段落**运行画面亮度、差分、声音电平代理，另有**15个重点专业导演研究段落**。
- 专业 `director-agent`、`ai-storyboard-director`、`plan-camera-shots` 和 `review-and-assemble` 仅作为现成上游专业能力入口，绝不新建或修改 SKILL.md，激活档案不等于宿主原生执行。
- 研究主页面：`http://127.0.0.1:8766/dense-style-study/`，离线可双击：`output/dense_film_style_study/index.html`。
- 命令：`python production_cli.py dense-film-style-status` 查看数据状态；如有全帧密集素材，可运行 `python film_style_dense_study.py --dense <密集素材目录>` 重建研究数据。
- 片源只有用户提供的12分56秒，不是《妖猫传》整部电影；没有对白语义转录、真实摄像机参数或导演本人意图认证。


## 电影风格学习 → 激活原版专业导演 Skill（新增）

**本次不创建、不修改任何 `SKILL.md`。** 以用户上传的《妖猫传》776秒片段作为风格证据：`data/film_style_evidence_annotations.json` 记录 GPT 对两段实片的可证伪分析（595–616秒信息悬念、617–653秒空间与人物走位），`style_activation_engine.py` 从真实视频逐时间点核对18张参考图，并计算亮度等可审计像素代理；这些代理不能用来声称已知导演意图或已复刻电影色彩。

```bash
python production_cli.py compare-film-style
python production_cli.py learn-film-style
python production_cli.py prepare-style-script --script "我的新剧本.txt" --mode audience_first_suspense
python production_cli.py prepare-style-script --script "我的新剧本.txt" --mode blocking_space_reveal
python production_cli.py serve
```

- 浏览器：`http://127.0.0.1:8766/style-lab`；档案：`output/film_style_activation/妖猫传_风格激活配置.json`。
- 两个可选风格模式不是从零新造的Skill，而是**给官方 `director-agent`、`ai-storyboard-director`、`plan-camera-shots` 和 `review-and-assemble` 的激活任务与镜头约束**；源剧本始终由 `structure-screenplay` 阶段先保留事实。
- 现有《失联观测站》32秒原创场景用于可重复的A/B测试：导演方案、S03和S04摄影焦点及镜头选择发生变化，原剧情、人物走位、时长不变；模式B尚未生成对应图片，不得复用模式A的旧图片验收。
- 任意另一部电影要先有**这部电影自己的**观察帧、案例文件及风格注释：`python style_activation_engine.py learn --reference 新电影.mp4 --case-file 新电影案例.json --frame-dir 证据帧目录 --style-spec 新电影注释.json --output 风格包.json`。没有实片证据时禁止直接使用《妖猫传》的片段标签生成新电影风格档案。
- 当前仅有原版 `plan-camera-shots`、`review-and-assemble` 核心文档的官方Git SHA核验本地副本，**没有原版专业Agent在ChatGPT宿主的原生执行**；新剧本任务已生成，只能声明为待运行。专业规则负责工作流程，不等于GPT权重已训练，也不等于影片导演质量验收通过。

# 最新：现成专业影视Skill × 7镜原创AI分镜真实试制（保留阻断）

当前新增 `production_skill_handoff.py`、`official_skill_source_audit.py`、`build_original_animatic.py` 和网页 `/production-pilot`。源头是上游开源 `plan-camera-shots` 与 `review-and-assemble` 的**已校验原版Skill正文**，不是本地开发的新导演Agent；完整上游原版包尚未成功原生安装。

```bash
python production_cli.py production-pilot
python production_cli.py serve
# 浏览器 http://127.0.0.1:8766/production-pilot
# 浏览器 http://127.0.0.1:8766/skill-acceptance
```

原创《失联观测站》一次AI图像生成得到7格实拍风格静态分镜，裁切成7张单镜头候选，另有**32秒静帧预演**。摄影数据包含7镜镜头起止时间、相机提议坐标/焦点/焦距、演员走位、资产ID、道具起止状态；7/7交接字段预检通过。**独立视觉审片只有2镜初步可用，4镜待复核，S07直接拒收；全部未获正式签核，因此真正成片仍被阻断。** 原片86镜复刻任务不计入这7张原创图。

完整审计：[三项专业Skill缺口_真实修复与剩余阻断.md](三项专业Skill缺口_真实修复与剩余阻断.md)。

---

# GPT作为导演主体：以《妖猫传》真实片段继续学习（本轮）

这轮不接别的模型，也不把新增测试数当作导演能力。GPT实际观察了上传影片中**595–616秒**和**617–653秒**两段连续影像，提炼“多空间/意象的信息分配”与“入场→靠近→同框→离场的行动调度”两种可证伪导演语言假设。18张原片截图带时间戳、哈希、可见事实、其他解释和待核实项目（未听懂/转写对白不声称已理解）。完整素材只是**776.477秒上传片段，绝非完整院线正片**。

运行：

```bash
python production_cli.py gpt-director-study
python production_cli.py serve
# 打开 http://127.0.0.1:8766/gpt-director-study
```

也可以直接双击 `GPT_DIRECTOR_FILM_STUDY.html`（须保持根目录与 output/ 文件结构）。导演观察结果记录在 `data/gpt_director_cases.json`，原创《失联观测站》两稿记录在 `data/gpt_director_scene.json`。程序 `gpt_director_study.py` 的 `audit` 子命令接受符合上述场景格式的JSON镜头数组；它不会调用任何外部生成模型。

原创分镜的GPT导演第一稿出现了人物知情越权、镜头时空矛盾等问题；第二稿按导演叙事目标改写，程序只核验可检测结构，不宣称视听艺术合格。镜头和演员真实空间关系、对白含义、电影真正导演意图、独立图像/视频产出、专业导演质量签核**仍未完成**。**这不是GPT模型权重更新**，是可持续复查的导演学习记录和创作审核系统。

---

> **新增：自建云端 Qwen3VL-8B 已接入**。请先阅读 [专用远程视觉模型_使用说明.md](专用远程视觉模型_使用说明.md)，Windows 可运行 `一键验证远程导演模型.bat`。API Key 不保存在工程内；公网健康检查已验证，真实 POST 推理仍需在可联网机器执行。

# AI电影导演 · 图像优先自主迭代完整项目程序（真实12分56秒影片测试）

## 已验证：可替换预训练导演模型/Agent/Skill对照实验（零视频模型）

本轮直接查证并筛选7个外部项目（Qwen3-VL、ShotTransformer、FilmAgent、Open Film Skills、Film Production Skills、MovieNet、AVA-Encoder）。新模块 `director_model_hub.py` 将本次真实电影的3组剪辑案例与13组独立镜头三帧导出成**16项有原片SHA证据的可复现模型实验**。运行 `python production_cli.py director-model-benchmark` 导出任务，查看 `output/model_research_lab/导演模型实验室.html`，启动工作台后也可访问 `/director-model-lab`。

可选 `ollama pull qwen3-vl:4b` 和 `ollama serve` 后，调用 `python director_model_hub.py run-local --task LESSON_LESSON_01` 对真实参考帧进行本地视觉分析。结果会永久标记为未核验导演假设；没有真实模型则阻断，不会虚报通过。**本环境没有本地Ollama实例，因此本次真实预训练模型推理为0；只证明程序与基准接口已可执行。**《导演模型集成与验收说明.md》列出模型/Skill/Agent区别、安装方式、审查边界。


本目录是**可执行的本地电影分镜导演工作台与生产工程**，不是“AI已经成功复刻整部《妖猫传》”。
你的最终目标：输入参考电影或剧本，系统逆向理解导演表达、形成资产圣经与镜头任务、自动生产静态分镜、自动审查与定向返工，先通过人物/美术/空间/摄影等静态门禁，再做三维预演、动态表演、视频生成和完整音画剪辑，并能反复验证及复用工作流。

当前提供**真正可运行的静态前置生产系统**，其余功能按真实完成情况标注。没有AI图像模型时不会假装已经重绘，没有视频模型时照样可以做原片分析、静态分镜、自动工单、候选导入、逐轮技术比较及门禁管理。

## 最新实测：导演与编剧的镜头语言学习实验室（视频生成费用为零）

这次把**专业电影的剪辑与镜头安排当作学习对象**，而不是把画面变化标成“影片错误”。来自上传的12分56秒素材的86张候选镜头构建了85条相邻剪辑关系（**切镜边界是待复核的算法划分**）。针对93秒连续样本，精选3组真实分镜观察和9条镜头关系假设，分别研究：人物→黑猫→人物、环境→人物→环境、僧人→对方→僧人→双人／空间。

```bash
python production_cli.py editing-study
python production_cli.py serve
# 浏览器： http://127.0.0.1:8766/editing
```

- `EDITORIAL_DIRECTOR_LAB.html`：单独离线打开也能看真实镜头剪辑分析、三组原片镜头语法、预置原创场景试拍分镜；启动本地服务后可记录逐切镜解释及输入任何原创场景。
- `output/editorial_language/transitions.json`：85条原片镜头连接的低层证据、开放假设、备选解释；**光色/亮度差异不计入原电影质量缺陷**。
- `output/editorial_language/director_lessons.json`：3份可核实导演案例，逐一标注画面可观察内容、可能的导演用意、反向解释和必须查证的证据。
- `output/editorial_language/导演剪辑语法_三组真实分镜.jpg`：来自真实素材的镜头语法观察图，**不是独立AI重绘**。
- `output/editorial_language/original_scene_rehearsal.json`：原创科幻场景的“欠约束初稿→规则自查→补齐镜头功能/表演/声音/切镜的新版”结构化导演试拍；这是**规则型文字分镜结构检查**，不是AI学会了电影艺术或真实制片成功。
- 剪辑关系的人工核验可保存至 `data/editorial_director_reviews.json`，哈希绑定源图片；不能借此审批生成镜头或成片。
- 尚未完成影片对白转写、导演意图验证、演员身份与三维调度、独立生成图片验收、动态拍摄。任何导演假设必须按时间码、视线、音轨、剧情再次核对。

## 导演工作台（2026-11-14 新增，真正基于视频参考分析）

专项验收：`导演工作专项验收报告.md`；典型分镜对照：`output/director_lab/五镜头导演参考对照.jpg`。

```bash
python production_cli.py director-review
python production_cli.py serve
```

浏览器打开 `http://127.0.0.1:8766/director`，也可以直接打开 `DIRECTOR_DESK.html`（离线只能导出修改JSON；本地服务可真正保存导演决策）。

- 从 **86个候选镜头的258张原片全分辨率参考帧**建立导演工作卡，记录二维摄影线索、画面视觉焦点、明暗结构、节奏、身份锁定状态及应当审查的动作/场景/剪辑项目。
- 在93秒连续挑战段落采样 **372张**低分辨率原片图像，核对画面突变、切点二算法支持及同一镜头疑似漏切，优先阻断错误镜头切分。结果位于 `output/director_lab/`，绝不自动把突变认作真实切镜。
- 对20个样本镜头加入**基于真实分镜目视检查的导演阅读草稿**，内容涉及黑猫走位、石洞光亮出口、对话反打、人物站位等；这些是待导演核验的假设，不是AI自动完整理解剧情。
- 可编辑“戏剧目的/走位/表演/机位/切镜/空间/身份/美术/声音”九项导演指令；保存会将已有依赖旧指令的审片结果失效，**不会自动签核AI成片**。
- 提供逐镜导演生产工单 `output/director_lab/director_shot_work_orders.jsonl`，供本地图片模型、预演模块或其他合法模型调用。
- 不接入付费视频模型，不把原片抽帧称为AI生成，**当前新项目0个复刻镜头正式通过**。

## 一、这次新视频的实际结果

| 内容 | 本次真实值 |
|---|---|
| 输入视频 | `data/source_video.mp4`（用户本次上传） |
| 时长 / 分辨率 / 帧率 | 776.477秒（12:56），1280×534，30fps |
| 视频包含音轨 | 是，AAC |
| 主算法候选镜头 | **86**，**未人工确认切点** |
| 参考分镜 | **258张**，86镜头×IN/MID/OUT，1280×534解码静帧 |
| 第二算法候选切点 | 94处；主算法中66处与其在0.45秒内对齐（非真值认证） |
| 暂存的视觉场景分组 | 18组，**不是真实场次标注** |
| 可能的人脸观测 | 30处，**不是角色身份识别** |
| 参考镜头内画面变化基线 | 172对；相邻镜头参考基线85对 |
| 由AI独立生成的本项目分镜 | **0**（需要真实图片模型连接/生成图片导入） |
| 导演完整验收的镜头 | **0** |
| AI生成的视频镜头 | **0** |

> 文件长度只有12分56秒，是原片的一段视频，不是整部两小时电影。此前124秒预告的历史数字、候选图和审查结果**没有混入新项目**。

## 二、安装和操作（无视频生成费用）

**Windows：** 安装Python 3.10+，解压后双击 `start_windows.bat`。

**Linux/macOS：** 安装Python 3.10+、FFmpeg，解压后执行：

```bash
bash start_linux_mac.sh
```

浏览器：

- `http://127.0.0.1:8766`：**可交互导演工作台**，逐张看原片和AI候选、修改导演目标、导入生成图、自动评分、局部修正、生成新提示、查询历史、检查成片门禁。
- `http://127.0.0.1:8766/longform`：**全片候选镜头与IN/MID/OUT参考图**，所有镜头可检索和查看。
- 也可以直接双击 `PROJECT_STORYBOARD_REPORT.html`：离线浏览258张分镜，需保持原有文件夹相对路径不变。
- 双击 `START_HERE.html`：入口说明。

第一次运行如没有依赖，将安装 `requirements.txt` 的基础离线图像模块；**不自动安装/调用付费视频模型**。新导入的视频分析依赖 FFmpeg 和 FFprobe。

## 三、一个统一命令入口

```bash
# 真实项目进度（不会把原片截图计入AI产出）
python production_cli.py status

# 校验全片镜头、三帧、跨帧和导演审批门禁
python production_cli.py audit

# 输出全部258张分镜的独立重绘任务
python production_cli.py export-jobs

# 对视觉资产作非身份式观测索引
python production_cli.py assets

# 启动本地导演工作台
python production_cli.py serve

# 导入另一段电影，独立建立新项目
python production_cli.py import-film /path/to/other_video.mp4 --out /path/to/new_project

# 自动化回归测试
python -m unittest discover -s tests -v
```

新视频导入时会自动生成镜头候选、原片三帧、分镜卡、色彩/光影/二维光流、音频能量、视觉分组、人脸观测、独立数据库和生产工单。不同电影**不共享**旧的数据库或人物身份。

## 四、生产链怎样真正自主迭代

1. **原片逆向目标：** 先在 `PROJECT_STORYBOARD_REPORT.html` 查看镜头、审查边界。`data/project_manifest.json`、`data/shot_features.json` 保存源视频哈希、参考帧、光色和运动线索；这些是技术测量，**不是导演理解的最终答案**。
2. **导演指令与锁定资产：** 在工作台逐镜头填写戏剧目的、人物站位、服装和场景。任何导演约束改变都会使已有的对应审核失效。`data/asset_bible_observations.json` 只有非可靠身份观测，未确认的角色不得自动声称“锁定”。
3. **图片优先生成：** 在工作台点击“生成重绘指令”（免费）并复制给图像模型，或配置本机ComfyUI自动生产。
4. **AI候选导入与自审：** 真实重新生成的图片通过“导入生成好的图片”进入工程；分数与历史记录、技术差异、错误原因自动保存；不会将参考截图登记为独立AI复刻。
5. **定向返工循环：** 有候选时可以进行无付费的安全光色/整体构图修改。真正的AI重绘迭代需连接可用本地图像生成模型，程序会使用上一轮批注与失败历史重新生成，设有最大轮数与预算限制。
6. **独立模型审核（可选）：** 本地Ollama视觉模型可以提供语义审核，但它也可能误判。角色身份、动作空间和导演意图必须得到可靠的外部证据或终审才能签核。
7. **三帧及跨镜头验收：** 只有当IN/MID/OUT均有有效的候选和当前导演签核后，才可进入静态动态预演。参考视频相邻帧统计**不等于**生成内容连续性合格。
8. **成片门禁：** 当前0镜头通过；正式AI成片输出被拒绝。不将原片重编码、原片截图切换、算法动画冒充“AI生成电影”。

## 五、本地图像模型接入：不需要付费视频API

你可以自己在本机安装 **ComfyUI** 和合法取得的图像模型权重，将API格式工作流放进本目录，复制 `local_model_config.example.json` 为 `local_model_config.json`，填写 `workflow_json`、`prompt_node`，需要参考图或上一轮候选时配置相应图片载入节点。默认ComfyUI地址 `http://127.0.0.1:8188`。

```bash
python local_model_bridge.py doctor
python local_model_bridge.py run --shot SH_00002 --anchor MID --max-rounds 3
```

接入并且本机实际运行模型以后，系统才会获取独立生成的图片，执行“生成→审查→返工→重新生成”的真实闭环。**接口通过模拟测试，不意味着已经在这份影片上完成合格的多轮重绘**。没有配置模型时，按钮自动禁用，绝不会假装进行了生成。

本机可选Ollama多模态视觉模型独立判断。参考格式在现有 `local_model_config.example.json` 与 `local_vision_bridge.py` 中。工作流自定义节点可能自行联网，请自行核验。

## 六、导出与原片参考预演

```bash
python product_engine.py audit
python product_engine.py animatic
# 上述默认正式输出必须有全部镜头三帧签核；现在会返回 BLOCKED

# 只有在想检查镜头节奏时，可选生成15秒明确标记的原片静帧预演：
python product_engine.py animatic --reference-previs --max-seconds 15
```

原片参考预演带永久“REFERENCE ONLY - NOT AI GENERATED”水印，是原片镜头节奏预演，**不是AI复刻成片**。

## 七、目录说明

- `data/source_video.mp4` — 本次用户实际上传的视频（没有增删原片帧）
- `data/references/` — 258张全分辨率原片关键帧
- `data/director.sqlite3` — 每张分镜的目标、候选、版本、评价、记忆和签核
- `data/shots_source.csv` — 86个候选镜头起止与三张参考帧
- `data/project_manifest.json` — 源视频哈希、时长、切镜算法状态、显式零AI产出声明
- `data/cut_detector_crosscheck.json` — 两种切镜算法对照（自动切点都非事实真值）
- `data/shot_features.json` — 图像特征、二维光流、音轨能量、视觉分组候选
- `data/asset_bible_observations.json` — 未确认的人脸与场景资产观测
- `data/continuity_reference.json` — 172对镜头内、85对相邻镜头的原片光色连续性参考基线
- `output/contact_sheets/` — 全部镜头联系表，方便肉眼复核
- `output/shot_work_orders.jsonl` — 258条独立图片生成与审核工单
- `PROJECT_STORYBOARD_REPORT.html` — 离线全片分镜总览
- `output/FINAL_ACCEPTANCE.html` — 八阶段真实能力验收；不虚报通过率
- `tests/` — 此片段的新项目回归测试；`tests_legacy_preview/`是旧124秒预告专用测试（仅归档）

## 八、与最初最终目标的差距（明确而非包装）

当前版本有了可执行长片段分镜生产基础：导入、镜头与目标三帧、镜头工作台、素材源哈希、待生成工单、本地模型接口、逐轮图像技术质检、返工与状态、正式导出硬门禁。

**还没有真正完成**：跨镜头人物身份确认、真实角色与场景资产圣经、完整剧本与对白理解、准确三维摄影机与人物调度、AI静态重绘批量验收、复杂特效复现、动态表演/口型/音轨同步、视频模型镜头生产，以及完整电影复刻。没有可运行的图像模型或者真实AI重绘的素材，不能完成分镜生产的最终质量证明；但不接视频模型**不妨碍**先完成前面的静态电影工业工程及验收数据。

同样需要确保对版权影像、演员肖像、声音及外传第三方服务有必要的权限。默认全部数据留在本机，不主动将这份影片上传到外部API。

## 九、可选本地AI导演分析（无视频生成费用）

除了手动编辑导演约束，也可以让本机Ollama视觉模型同时读取同镜头的 IN/MID/OUT 三帧，形成叙事、人物站位、服化道、光影和景别的**可审查导演意图草稿**：

```bash
# 本机需已启动Ollama，并安装支持图片输入的视觉模型，如llava等：
python director_intent_model.py --shot SH_00003 --model llava
# 你要主动允许把草稿写进镜头约束，可加 --apply（会使旧审核失效）
python director_intent_model.py --limit 5 --model llava --apply
```

这只向 `127.0.0.1`/`localhost` 发送本机图片；默认不调用云端。没有安装模型时该命令会失败并指出连接原因。模型的理解仍是**推断**，不能凭空证明真实人物身份或准确三维摄影轨迹；当前环境未完成真实Ollama影片批量推理。


## 十、新增：导演级证据、自审门禁与连续片段挑战（不依赖付费视频）

```bash
python production_cli.py evidence
```

打开 `DIRECTOR_EVIDENCE.html`（离线可用）或启动服务器后访问 `http://127.0.0.1:8766/evidence`。

新的证据审查模块实际读取**全部86个镜头的258张原始分辨率参考图**，计算基于稀疏特征/RANSAC的二维画面运动线索（不将其冒充真实3D机位），与现有视觉组、音轨能量、光色基线和人脸检测观测关联，为每个镜头建立详细的可追溯导演卡。

系统从原片选择连续60至120秒、包含多类画面/运动/人物观测的**统一挑战片段**，要求该段所有镜头三帧独立生成与多重审查全部通过后，才可声称静态分镜阶段通过。此片段仅是候选段落，场次、切点、身份、镜头含义未由模型确认。

`output/evidence/calibration/` 中的实验对原片截图**人为损坏光色，再进行统计校正**，用于检测基础质检功能能否发现并修复此类失真。它不算AI重新绘制，不进入生产数据库，也不代表电影复刻完成；不得以其SSIM改善冒充导演能力。

全量证据输出在 `output/evidence/director_evidence.json` 与 `shot_director_cards.jsonl`，包括实际模型候选图数量（哈希有效性校验）、IN/MID/OUT跨帧审查、待审人物/场景和下一轮生产指令。没有接图像模型时真实AI候选仍为0，这会被准确报告。

边界说明：静态参考图只能支持画面光色、分镜构图、部分姿态和场景观察；**人物身份、表演语义、准确运镜、动作时间点、口型和音画同步**不能由这些统计指标证明，也不存在假造的3D预演。


## 十一、双算法切镜分歧的可追溯审查

```bash
python production_cli.py cut-review
```

新模块读取主算法与FFmpeg独立场景检测时间码，按0.45秒阈值一对一配对，不将双算法一致误称为准确率100%。当前影片主算法85个切点、FFmpeg94个切点，66个吻合，**47个候选分歧需复核**。

打开 `output/cut_review/index.html`（离线可看），或访问 `http://127.0.0.1:8766/cuts`，逐个比对切点前后真实画面。已审查的切点可填写确认/驳回/待定及依据，保存在与源视频 SHA-256 绑定的 `data/cut_review_decisions.json`。不会静默修改原镜头ID或绕过既有签核失效门禁。


## 云端开源视觉模型试验（默认无外部请求）

新增 `cloud_director_inference.py`：连接 Groq / OpenRouter / Hugging Face 云端 OpenAI-compatible 多图视觉模型。实际服务可用性和免费额度由第三方决定，不连接任何付费视频模型。

```bash
python cloud_director_inference.py providers
python cloud_director_inference.py prepare --provider groq --task LESSON_LESSON_01
# 设置 GROQ_API_KEY 后才可明确执行真正的外部云调用
python cloud_director_inference.py run --provider groq --task LESSON_LESSON_01
```

准备阶段只在本地处理选定的分镜；实际run阶段会上传最多4张压缩参考静帧到指定第三方，须留意服务商使用条款和影片资料授权。参见 `云端开源导演模型_实际试验记录.md`。无可用API密钥时不得称为已完成真实模型推理。


### 2026-11-14：远程 Qwen3VL-8B 实际 GET 推理阶段
用户自建网关已真实返回 5 次电影剪辑与原创电竞镜头导演文本推理。请参看 [五轮实测报告](真实Qwen3VL导演自审_五轮实测.md) 与 [可视化审片实验室](output/gateway_director_lab/真实导演模型_五轮迭代实验室.html)。该模型尚未收到真实电影图片；不代表导演视觉理解或成片质量已通过。
新入口 `python production_cli.py gateway-text-rehearsal --case editorial` 或 `python director_get_rehearsal.py --case all`，需要设置 `DIRECTOR_GATEWAY_API_KEY` 环境变量；GET URL 会被网络中间件记录，建议仅用短期测试token，正常多图推理仍使用POST。


## 专业上游 Skill 驱动的《妖猫传》实片学习（2026-11-14）

专业规范来源：Open Film Skills 的 `director-agent`、`ai-storyboard-director`；Film Production Skills 的 `plan-camera-shots`、`review-and-assemble`，而非新造一套“导演 Skill”。这四个名称链接到相应 GitHub 源码，具体目录由 `professional_skill_adapter.py` 的官方仓库注册表约束。

```bash
python production_cli.py professional-skills-doctor
python production_cli.py professional-skills-prepare
python production_cli.py professional-film-experiment
```

专业实验采用原片595–616秒和617–653秒两组已检查场面，18张带 SHA256 的真实帧、两组导演假设及反证，比较原创《失联观测站》“观众先知”与“共同困惑”两种方案（相同剧本、人物、走位和32秒时长）。完整结论：`output/professional_skills/现成影视Skill_妖猫传验证报告.md`。

要真正下载**上游原版**而非改写 Skill，请在可访问 GitHub 的电脑上执行：

```bash
python professional_skill_adapter.py install --repo open-film-skills
python professional_skill_adapter.py install --repo film-production-skills
python professional_skill_adapter.py doctor
python professional_skill_adapter.py prepare-film
python professional_skill_adapter.py prepare-original
```

下载成功后，工具只读取上游 `SKILL.md` 并校验哈希，**不会执行下载仓库中的任何脚本**。GPT 可以以这些真实 Skill 为指导开展审片、导演方案和正片制作审查。若上游代码未安装，执行包明确显示 `BLOCKED_SKILL_NOT_INSTALLED`；当前容器 `github.com` 域名无法解析，因此此次上游实际运行次数=0、电影级画面与导演艺术质量签核=0。


## 原版专业影视 Skill 下载失败的备用方式（2026-11-14）

已将 `professional_skill_adapter.py` 的单一路径 `git clone` 修复成**四种官方来源及离线导入**。

- `git clone` → GitHub API ZIP → codeload ZIP → GitHub Git Tree + Raw/Blob 分文件 SHA 验证。
- 不能联网时，把完整仓库源码 ZIP 放到 `upstream_zips/`，双击 `安装上游专业影视Skills.bat`；不再依赖从隔离容器直连 GitHub。
- **不执行**仓库中的安装脚本或可执行程序；只将官方原版 Skill 目录下载到 `external_skills/` 并校验引用。
- 本沙箱仍受 `caas_packages_only` 的公网出站限制，**本环境实际安装状态仍为未安装**；离线模拟安装用来验证下载器的正确性，不冒充原版已经运行。

详细命令和官方 ZIP 地址见：`原版导演Skill下载故障_修复与验收.md`。


## 专业影视Skill全成品真实验收（2026-11-14）

```bash
python production_cli.py skill-acceptance
# 浏览本地 studio http://127.0.0.1:8766/skill-acceptance
```

该验收脚本实际核对《妖猫传》776秒片段、18张帧哈希、32秒原创场景7镜头与两个导演策略、6个反例、86镜/258工单、Web API/CSRF、成片导出门禁，并尝试Chromium实景渲染。
**当前结果不等于原版上游 Skill 原生调用**：当 external_skills 没有完整原版文件，仍标记安装阻断。没有独立生成并导演签核的AI分镜、没有成片输出，成片功能不可验收。可视浏览器测试若遇环境策略阻断，记SKIPPED而不是PASS。

验收输出：`output/skill_end_to_end_acceptance/完整成品验收仪表盘.html`、`acceptance.json`、`完整成品验收报告.md`。

# movie_ai
