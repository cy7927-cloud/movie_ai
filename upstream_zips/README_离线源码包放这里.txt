把从官方 GitHub 下载的 **完整仓库** 源码 ZIP 放到此文件夹，不要用单个 SKILL.md 替代。

官方来源：
1. https://github.com/62656456/ai-film-skills/archive/refs/heads/main.zip
   保存名称为：ai-film-skills-main.zip
2. https://github.com/zhangzhangco/film-production-skills/archive/refs/heads/main.zip
   保存名称为：film-production-skills-main.zip

然后双击项目根目录的「安装上游专业影视Skills.bat」。

安装器支持 git clone -> 官方 GitHub ZIP API -> 官方 codeload -> 官方 Git Blob 内容 API。
上述所有网络路线均失败时才需要手动下载 ZIP；ZIP 只解包校验，不执行来源仓库的任何脚本。

也可以执行：
python professional_skill_adapter.py install --repo open-film-skills --archive upstream_zips/ai-film-skills-main.zip
python professional_skill_adapter.py install --repo film-production-skills --archive upstream_zips/film-production-skills-main.zip
python professional_skill_adapter.py doctor
