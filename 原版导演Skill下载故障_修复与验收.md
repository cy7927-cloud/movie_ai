# 原版导演 Agent Skill 下载故障 · 实际修复与验收

## 修复原因

此前的 `professional_skill_adapter.py` 只执行 `git clone --depth 1`。当前执行沙箱的网络策略为 `caas_packages_only`；`github.com`、`api.github.com`、`codeload.github.com` 均不能 DNS 解析，也无法建立公网 IP 直连。不是原作者仓库缺失，更不是《妖猫传》学习素材不支持。

这次已核实官方 GitHub 来源确实可读取，另一个网页通道能够读取两家仓库的原版 `SKILL.md`，但是这个网页读取工具**不能向当前隔离工程容器写文件**。因此本机不能诚实地标记上游为已安装。

## 已完成的修复

1. 保留原始 Git clone 下载方式。
2. 增加 GitHub 官方 `api.github.com/repos/{owner}/{repo}/zipball/main` 下载方式。
3. 增加 GitHub 官方 `codeload.github.com/{owner}/{repo}/zip/refs/heads/main` 下载方式。
4. 增加 GitHub `git/trees/main?recursive=1` 加 `raw.githubusercontent.com`（优先）或 `git/blobs/{SHA}`（回退）的逐文件恢复方式。该方式校验原始 Git Blob SHA-1，避免代理途中发生内容替换；只恢复需要的完整 Skill 文件夹及共享字段规范。
5. 增加 `--archive` 选项，支持用联网电脑下载完整源码 ZIP，再到离线环境安装，不依赖 GitHub 网络。
6. 导入时校验 LICENSE、指定的原版 SKILL.md、SKILL.md 链接的参考文件、ZIP 目录安全和文件大小上限；拒绝伪造根目录、路径穿越、符号链接和不完整安装。
7. 不执行上游作者的脚本，不修改已存在的安装目录。

## 在你的联网 Windows 电脑上直接执行

双击项目根目录 `安装上游专业影视Skills.bat`，它会自动尝试上述官方来源并完成《妖猫传》原片证据包的关联检查。

如果你的 Windows 也无法访问上述三个官方站点：

- [Open Film Skills 完整源代码 ZIP](https://github.com/62656456/ai-film-skills/archive/refs/heads/main.zip)，保存为 `upstream_zips/ai-film-skills-main.zip`。
- [Film Production Skills 完整源代码 ZIP](https://github.com/zhangzhangco/film-production-skills/archive/refs/heads/main.zip)，保存为 `upstream_zips/film-production-skills-main.zip`。

再双击一次 `安装上游专业影视Skills.bat`。

也可独立运行：

```powershell
python professional_skill_adapter.py install --repo open-film-skills --archive upstream_zips/ai-film-skills-main.zip
python professional_skill_adapter.py install --repo film-production-skills --archive upstream_zips/film-production-skills-main.zip
python professional_skill_adapter.py doctor
python professional_skill_adapter.py prepare-film
python professional_skill_adapter.py prepare-original
```

## 本次真实验收

- 当前工程 105 个 Python 自动化测试通过（包括 GitHub ZIP API、本地 ZIP、安全性、Git Blob SHA 验证以及原《妖猫传》工程回归）。
- 官方 GitHub API 和 ZIP 在本沙箱的**实际下载仍被网络策略阻止**；测试中完整原版 Skill 的安装状态没有被虚假改为成功。
- 离线验收是使用**合成的上游仓库结构作为安装夹具**，用来验证安装器确实能够安全安装，而不是把合成夹具冒充原版技能。
- Skill 的成功安装只是第一层：还需要兼容的 AI Agent 宿主真正读取其完整指令，针对真实电影镜头生成结果，并用原片画面和声音验证；与电影的实际理解质量不能混为一谈。

## 注意

上游 `Open Film Skills` 的 `ai-storyboard-director` 包含参考文档、脚本和资产；**只下载 `SKILL.md` 不能视为完整安装**。这次的离线导入要求原仓库完整 ZIP，不会把我仿写的导演模板冒充原版源码。
