@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
title Incheon-Ansan Event Finder
cd /d "%~dp0"

set PY=
where py >nul 2>&1 && set PY=py
if "%PY%"=="" (where python >nul 2>&1 && set PY=python)
if "%PY%"=="" (where python3 >nul 2>&1 && set PY=python3)

if "%PY%"=="" (
  echo.
  echo [!] Python not found.
  echo     Install it from https://www.python.org/downloads/ and run this again.
  echo.
  pause
  exit /b 1
)

%PY% "%~dp0run.py"

if errorlevel 1 (
  echo.
  pause
)
