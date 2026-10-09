@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
title mathbank GitHub upload
set REPO=https://github.com/iruroda/mathbank.git

echo ==================================================
echo  mathbank -> GitHub upload
echo  folder: %cd%
echo ==================================================
echo.

where git >nul 2>nul
if errorlevel 1 (
  if exist "%ProgramFiles%\Git\cmd\git.exe" set "PATH=%ProgramFiles%\Git\cmd;%PATH%"
)
where git >nul 2>nul
if errorlevel 1 (
  echo [0/5] git is not installed - installing with winget ^(takes a minute^)...
  winget install --id Git.Git -e --source winget --accept-package-agreements --accept-source-agreements
  if exist "%ProgramFiles%\Git\cmd\git.exe" set "PATH=%ProgramFiles%\Git\cmd;%PATH%"
)
where git >nul 2>nul
if errorlevel 1 (
  echo [ERROR] git install failed or winget is missing.
  echo   Install by hand: https://git-scm.com/download/win  then run this file again.
  goto :fail
)

if not exist ".git" (
  echo [1/5] git init
  git init
  if errorlevel 1 goto :fail
)

git branch -M main
git config user.name >nul 2>nul || git config user.name "iruroda"
git config user.email >nul 2>nul || git config user.email "iruroda@gmail.com"

git remote get-url origin >nul 2>nul
if errorlevel 1 (
  git remote add origin %REPO%
) else (
  git remote set-url origin %REPO%
)

echo [2/5] git add
git add -A
if errorlevel 1 goto :fail

echo [3/5] git commit
git commit -m "add 2023-2026 exams (56 exams, 3856 problems)"
rem nothing-to-commit is not an error

echo [4/5] git push  (a browser window may ask you to sign in to GitHub)
git push -u origin main
if not errorlevel 1 goto :ok

echo.
echo [push rejected] trying to merge with what is already on GitHub...
git pull origin main --allow-unrelated-histories --no-edit -X ours
if errorlevel 1 goto :fail
echo [5/5] git push (retry)
git push -u origin main
if errorlevel 1 goto :fail

:ok
echo.
echo ==================================================
echo  SUCCESS - upload finished
echo ==================================================
pause
exit /b 0

:fail
echo.
echo ##################################################
echo  FAILED - take a screenshot of this window
echo  (error code: %errorlevel%)
echo ##################################################
echo.
git status -sb
echo.
git remote -v
pause
exit /b 1
