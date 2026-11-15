@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
echo =====================================================
echo Original Film Skills - Official source installer
 echo Git clone / GitHub archive / official Git blob API / offline ZIP
 echo No downloaded upstream scripts are executed.
echo =====================================================
if not exist "external_skills" mkdir "external_skills"
if exist "upstream_zips\ai-film-skills-main.zip" (
  echo [1/2] Found offline ZIP for Open Film Skills
  python professional_skill_adapter.py install --repo open-film-skills --archive "upstream_zips\ai-film-skills-main.zip"
) else (
  echo [1/2] Download Open Film Skills from official upstream...
  python professional_skill_adapter.py install --repo open-film-skills
)
if exist "upstream_zips\film-production-skills-main.zip" (
  echo [2/2] Found offline ZIP for Film Production Skills
  python professional_skill_adapter.py install --repo film-production-skills --archive "upstream_zips\film-production-skills-main.zip"
) else (
  echo [2/2] Download Film Production Skills from official upstream...
  python professional_skill_adapter.py install --repo film-production-skills
)
echo.
echo [Verify: original Skill source, LICENSE, referenced files]
python professional_skill_adapter.py doctor
python professional_skill_adapter.py prepare-film
python professional_skill_adapter.py prepare-original
echo.
echo If all sources failed: place the two official GitHub source archives
 echo in upstream_zips and run this batch again.
pause
