@echo off
chcp 65001 >nul
cd /d "%~dp0"
if "%~1"=="" (
  echo 请将自己的新剧本TXT路径作为第一个参数传入。
  echo 示例: "选择参考电影风格_生成专业Skill任务.bat" "D:\scripts\new_story.txt" audience_first_suspense
  echo 模式可选: audience_first_suspense 或 blocking_space_reveal
  exit /b 2
)
set "MODE=%~2"
if "%MODE%"=="" set "MODE=audience_first_suspense"
python production_cli.py prepare-style-script --script "%~1" --mode "%MODE%"
if errorlevel 1 exit /b %errorlevel%
echo.
echo 任务已在 output\film_style_activation\新剧本_原版Skill激活任务.json 中准备。
echo 注意: 这只是原版专业Skill的待执行任务，不是声称已经执行或完成拍摄。
