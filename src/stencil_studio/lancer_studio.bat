@echo off
rem Stencil Studio seul, dans le navigateur : lance depuis le dossier qui contient stencil_studio\.
cd /d "%~dp0.."
py -m pip install -r stencil_studio\requirements.txt
py -m stencil_studio
pause
