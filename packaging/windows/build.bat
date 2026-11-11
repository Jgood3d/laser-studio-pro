@echo off
setlocal EnableExtensions
rem Build depuis la RACINE du depot (remonte de packaging\windows).
cd /d "%~dp0..\.."

echo ==========================================
echo  Laser Studio Pro — packaging\windows\build.bat
echo  (delegate au build.bat racine)
echo ==========================================

if not exist "build.bat" (
    echo [ERREUR] build.bat racine introuvable.
    pause
    exit /b 1
)
call build.bat
