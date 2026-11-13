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

echo ==========================================
echo Activation de l'environnement virtuel...
echo ==========================================
call venv\Scripts\activate.bat

echo ==========================================
echo Nettoyage des anciens dossiers...
echo ==========================================
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo ==========================================
echo Compilation de Laser Studio Pro (Mode Onedir)...
echo ==========================================
rem  Images, logo, icone et pack d'icones Breeze : tout le dossier src\laser_studio\resources\ (cherche par find_resource).
rem  Stencil Studio : le dossier est copie en donnees (studio.html, locales, polices...) ET ses modules sont
rem  declares en hidden-import pour que PyInstaller embarque aussi cv2 / numpy / scipy / Pillow qu'ils utilisent
rem  (studio_dialog importe studio a la demande, dans une fonction : on le declare donc explicitement).
rem  QtWebEngine est embarque automatiquement (main.py l'importe en tete).
rem  Le code est dans src\ (paquets laser_studio et laser_common) : --paths src le fait trouver par PyInstaller.
pyinstaller --onedir --windowed --name LaserStudioPro --icon=src\laser_studio\resources\laser_studio_pro.ico ^
 --paths src --add-data "src\laser_studio\resources;resources" ^
 --add-data "stencil_studio;stencil_studio" ^
 --collect-submodules serial --hidden-import=serial ^
 --hidden-import=PyQt6.QtWebEngineWidgets --hidden-import=PyQt6.QtWebEngineCore ^
 --hidden-import=stencil_studio.studio_dialog --hidden-import=stencil_studio.studio_window --hidden-import=stencil_studio.studio ^
 --hidden-import=stencil_studio.core --hidden-import=stencil_studio.engrave --hidden-import=stencil_studio.lightbox ^
 --hidden-import=stencil_studio.lsp_bridge --hidden-import=stencil_studio.subject_ai --hidden-import=stencil_studio.i18n ^
 --hidden-import=scipy.spatial --hidden-import=scipy.ndimage ^
 main.py

echo ==========================================
echo Copie du fichier icone dans le dossier dist...
echo ==========================================
copy src\laser_studio\resources\laser_studio_pro.ico dist\LaserStudioPro\

echo ==========================================
echo Termine ! Le dossier dist\LaserStudioPro est pret.
echo ==========================================
pause
