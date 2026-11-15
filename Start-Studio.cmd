@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\start_workbench.ps1" -Python "%~dp0.venv\Scripts\python.exe" -Port 8780
if errorlevel 1 pause
