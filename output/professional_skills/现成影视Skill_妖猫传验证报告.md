# 《妖猫传》 × 现成专业影视 Skill：真实验证记录

> 本报告由 GPT 对照公开的原版 Skill 执行规范进行实片学习和创作试验；**并非已经运行外部 Agent 框架/技能代码**。当前容器无法解析 github.com，原版仓库未能拉取。所有参考画面来自用户提供的 776.477 秒片段，不是完整电影。

## 1. 专业来源（不是自造的导演方法）

- **[director-agent](https://github.com/62656456/ai-film-skills/blob/main/skills/director-agent/SKILL.md)**：人物行动、表演与观众信息先后；尊重已定剧情，不由镜头推测导演真实意图。
- **[ai-storyboard-director](https://github.com/62656456/ai-film-skills/blob/main/skills/ai-storyboard-director/SKILL.md)**：从观看任务选择机位与切镜；走位和摄影同设计，不预设固定镜头数；只做当前阶段。
- **[plan-camera-shots](https://github.com/zhangzhangco/film-production-skills/blob/main/skills/plan-camera-shots/SKILL.md)**：摄影机空间基线、动作初始与末端状态、轴线、时间、服化道与道具状态。
- **[review-and-assemble](https://github.com/zhangzhangco/film-production-skills/blob/main/skills/review-and-assemble/SKILL.md)**：生成媒体需要真实物理文件和可追溯Take；没生成的媒体不得审核通过或宣称可出片。

专业 Skill 是指导 GPT 工作的规范；不是已训练好的电影视觉模型。ShotTransformer 是可选的景别/机位分类器；FilmAgent 是不同规模的多Agent框架，这次均未部署，不能把它们写作“成功运行”。

## 2. 《妖猫传》实片的两个学习案例

### CASE_A · 595–616秒
**已核对可见画面：**暗处人物在黑猫镜头之前出现；中间穿插红衣人群、猫和远处入口，随后回到暗处人物。
**学习的专业方法：**观众可获得超出角色的信息，但必须分开事实、角色知情范围、可能的并行空间。
**其他解释：**猫也可能只是独立意象/不同空间的悬念点，不能靠相邻画面强行确立视线关系。
**不能断言：**猫被暗处人物看见；这些镜头全部是相同地点或实时连续；导演意图已确认。
**待核验：**前后声轨与对白、全动态视线与方向、场景实际地理关系。
**画面证据时间戳：**597.2, 600.2, 604.4, 607.8, 611.2, 614.0 秒。

### CASE_B · 617–653秒
**已核对可见画面：**遮挡外景、隔窗室内、门口人物、入室、两人同框、一个人离开后另一人独处。
**学习的专业方法：**以可见走位作为镜头结构：入画/跨门槛/共享场域/出画；固定人物与机位空间基线。
**其他解释：**走位也可能是多次跳切、省略时间或中立的场景交代。
**不能断言：**只是标准正反打；所有切点都是无时间省略的连续行为；对白引发人物离开已证实。
**待核验：**连续动作与精确切点、声音桥/对白、轴线和场景布局。
**画面证据时间戳：**617.3, 620.0, 624.0, 628.5, 633.8, 640.1, 646.0, 652.7 秒。

## 3. 将学到的方法迁移到同一原创场景：两个导演选择

**共同前提：**原创《失联观测站》，32秒；两套保留同样的人物、走位、时长、结局约束，避免另换场景伪造进步。

| 方案 | 第8—11秒摄影与信息控制 | 观众比A多知道什么 | 结构审查 |
|---|---|---|---|
| A · 观众先知 | 屏幕下角可读“REMOTE LOGIN ACTIVE”插入特写 | 已见远程登录事实；之后也见藏卡 | 0 个问题 |
| B · 共同困惑 | 屏幕下角反光遮挡，延续A的异常时间戳观察 | 暂不知道远程登录；之后仍见藏卡 | 0 个问题 |

两种都可能有戏剧效果：A更容易形成观众超前信息，B更贴近人物的未知。**没有观众盲评或实拍成片，不能判 A 比 B 好，也不能判 B 比 A 好。**

## 4. 验证边界

- 原片 SHA256 已验证，18张观察帧的文件与时间戳均验证。原片并未被当作需要修复的问题影片。
- 两套原创分镜的时间、走位与角色知情规则通过现有工程结构审查；这并不等于达到院线导演质量。
- 尚缺：原片声音对白语义、关键人物视线与精确轴线、上游原版 Skill 安装、真正生成的原创分镜画面、第三方盲评。
- 本轮没有把原片截图冒充AI生成，没有调用付费视频模型，没有对 GPT 进行权重训练。

## 5. 将原版 Skill 真正接入工程（需可访问 GitHub 的环境）

在工程根目录执行：
```powershell
python professional_skill_adapter.py install --repo open-film-skills
python professional_skill_adapter.py install --repo film-production-skills
python professional_skill_adapter.py doctor
python professional_skill_adapter.py prepare-film
python professional_skill_adapter.py prepare-original
```

这会拉取 **原作者 Git 仓库及其 SKILL.md**，而不是我仿写的替代品；只下载，不执行上游脚本。下载成功后，电影案例会关联原版 Skill 文件与 SHA256，供支持 Agent Skills 的宿主逐项调用。
