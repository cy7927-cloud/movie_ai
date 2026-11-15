# 《妖猫传》GPT导演：专业Skill三项缺口真实修复与剩余阻断

这是针对上轮三个 BLOCKED 项的实证，不把程序测试通过等同于导演能力成熟。

## 1. 原版开源专业Skill —— 部分解决，原生宿主安装仍然阻断

- 已从 GitHub 官方Git内容API取得并按 Git Blob SHA-1 校验 **6份真实上游文件**，包括 `film-production-skills` 的原版 `plan-camera-shots/SKILL.md`、`review-and-assemble/SKILL.md`、MIT许可证和相关 `field-guide.md`。
- 文件位于 `external_skills/film-production-skills/`，逐文件校验报告 `output/real_production_pilot/original_professional_skill_sources.json`。
- GPT使用了这两份原版Skill指令定义的摄影交接、证据链、退修和导演审片边界。**没有假称已经在宿主内通过原生 Skill 运行时调用。**
- **仍未完成**：完整上游两个库的源码、全部JSON Schema、`director-agent`/`ai-storyboard-director` 完整依赖安装。这个阻断仍保留在成品验收仪表盘；当前容器禁止对GitHub官方站点建立出站TCP连接。

## 2. 摄影与分镜交接 —— 实现了7镜真实可读取的数据合同

源：`data/gpt_director_scene.json` 32秒原创短片《失联观测站》，在真实学习《妖猫传》两段片段后形成的独立原创场景，不是直接复刻《妖猫传》。

运行 `python production_cli.py production-pilot`：

- 每一镜有摄影机三维位置（提议场地坐标，单位米）、焦点对象、镜头焦距、机位轴线侧、起止时码。
- 每一镜有 `BEAT_Sxx` 编号、资产锁定 ID、A/B演员动作与起止位置、门禁卡与文件夹的道具状态、声效、切镜理由。
- **7/7结构预检通过**。场地坐标仅为导演建议，不是从原片测得的现场物理数据，也不意味着已确定设备/演员或影片质量通过。

输出：`output/real_production_pilot/professional_camera_handoff.json`。

## 3. 原创AI分镜画面 —— 第一次真正产生了媒体，但正式审片尚未通过

- 完成 **1次真实AI图像生成**：`ai_generated_storyboard_contact_sheet.png`，严格区分原创场景与用户提供的《妖猫传》原片。
- 一张4列×2行的画面总板，前7格裁成7张独立PNG；**不是7次独立生成**。
- 每个镜头文件有SHA256，7张图均能解码并关联到对应机位、动作、导演目的及资产。
- **2张视觉上初步可用（仍需签核），4张待复核，1张 S07 拒收**：S07人物眼神方向不符合原剧本“看回终端”，不能因模型画面精致而放行。
- 产出 `AI分镜静帧预演_非成片.mp4`，ffprobe确认时长**32秒**；仅是7张静帧按剧本时长拼接，不是7条运动镜头，更不是正式电影。
- 人工签核0张；影视作品最终导出 **BLOCKED**。原电影86个复刻镜头的258张参考图属于另一任务集，尚未有被验收的原创复刻画面。

输出：`output/real_production_pilot/导演专业Skill_七镜真实生产与验收.html` 和 `output/real_production_pilot/independent_media_review.json`。

## 运行与测试

```bash
python production_cli.py production-pilot
python build_original_animatic.py
python skill_product_acceptance.py
python -m unittest discover -s tests -p 'test_*.py' -q
python production_cli.py serve
```

本地工作台：`http://127.0.0.1:8766/production-pilot`（七镜媒体）和 `/skill-acceptance`（完整真实阻断）。

此轮核心不是追求测试数量，而是使之前**0张AI画面和0份生成级摄影合同**的缺口分别得到真实媒体和可审核的专业交接记录；完整原版Skill原生安装、人物一致性签核、真实动态电影制作仍不通过。
