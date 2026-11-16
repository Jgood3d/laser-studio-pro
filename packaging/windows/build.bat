@echo off
rem  Ce fichier peut etre lance depuis packaging\windows\ ou depuis la racine du projet :
rem  on se place toujours a la racine (le dossier qui contient main.py).
cd /d "%~dp0..\.."
if not exist main.py cd /d "%~dp0"
if not exist main.py (
    echo ERREUR : main.py introuvable. Lance ce script depuis le projet Laser Studio Pro.
    pause
    exit /b 1
)

rem  --ci : compilation automatique (GitHub Actions) : Python deja installe, pas de pause finale.
echo ==========================================
echo Activation de l'environnement virtuel...
echo ==========================================
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
) else (
    echo Pas de venv : Python du systeme.
)

echo ==========================================
echo Nettoyage des anciens dossiers...
echo ==========================================
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo ==========================================
echo Compilation de Laser Studio Pro (dossier)...
echo ==========================================
rem  Reglages de compilation (fichiers embarques : resources et Stencil Studio, modules declares,
rem  filtre des fichiers inutiles : modules Qt QML, traductions d'autres langues...) : dans
rem  packaging\pyinstaller\LaserStudioPro.spec, partage avec Linux. Resultat : dossier dist\LaserStudioPro.
set LSP_ONEFILE=0
pyinstaller --noconfirm packaging\pyinstaller\LaserStudioPro.spec

echo ==========================================
echo Copie du fichier icone dans le dossier dist...
echo ==========================================
copy src\laser_studio\resources\laser_studio_pro.ico dist\LaserStudioPro\

echo ==========================================
echo Termine ! Le dossier dist\LaserStudioPro est pret.
echo ==========================================
if /i not "%~1"=="--ci" pause
