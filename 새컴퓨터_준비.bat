@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
title mathbank - setup / update small working copy
set REPO=https://github.com/iruroda/mathbank.git

echo ==================================================
echo  mathbank - small working copy (about 40MB, no old PDFs)
echo  place: %cd%\mathbank
echo ==================================================
echo.

where git >nul 2>nul
if errorlevel 1 (
  if exist "%ProgramFiles%\Git\cmd\git.exe" set "PATH=%ProgramFiles%\Git\cmd;%PATH%"
)
where git >nul 2>nul
if errorlevel 1 (
  echo [0] git is not installed - installing with winget...
  winget install --id Git.Git -e --source winget --accept-package-agreements --accept-source-agreements
  if exist "%ProgramFiles%\Git\cmd\git.exe" set "PATH=%ProgramFiles%\Git\cmd;%PATH%"
)
where git >nul 2>nul
if errorlevel 1 (
  echo [ERROR] git install failed. Install by hand: https://git-scm.com/download/win
  goto :end
)

if exist mathbank\.git (
  echo [update] mathbank folder already exists - pulling latest from GitHub...
  cd mathbank
  git pull origin main
  goto :done
)

echo [1/2] git clone (data/tools/js only, old PDFs are not downloaded)
git clone --depth 1 --filter=blob:none --sparse %REPO% mathbank
if errorlevel 1 goto :fail
cd mathbank
echo [2/2] choose folders to keep
git sparse-checkout set data tools js icons vendor pdf/2026
if errorlevel 1 goto :fail

:done
echo.
echo ==================================================
echo  DONE. Connect the "mathbank" folder to Claude, paste 작업기록.md, and say what to add.
echo  New exam PDFs go in mathbank\pdf\^<year^>\ . Upload with 깃허브_업로드.bat.
echo ==================================================
goto :end

:fail
echo.
echo [FAILED] see the messages above.

:end
echo.
pause
