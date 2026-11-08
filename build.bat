@echo off
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
<<<<<<< HEAD
rem  Stencil Studio : le dossier est copie en donnees (studio.html, locales, polices...) ET ses modules sont
rem  declares en hidden-import pour que PyInstaller embarque aussi cv2 / numpy / scipy / Pillow qu'ils utilisent.
rem  QtWebEngine est embarque automatiquement (main.py l'importe en tete).
pyinstaller --onedir --windowed --name LaserStudioPro --icon=laser_studio_pro.ico ^
 --add-data "laser_studio_pro_banner.png;." --add-data "laser_studio_pro_512.png;." --add-data "buy_me_a_coffee.png;." ^
 --add-data "icons;icons" ^
 --add-data "stencil_studio;stencil_studio" ^
 --paths "C:\Users\Bonnevie\Desktop\Log-gravure\laser-studio-pro-propre\venv\Lib\site-packages" ^
 --collect-submodules serial --hidden-import=serial ^
 --hidden-import=PyQt6.QtWebEngineWidgets --hidden-import=PyQt6.QtWebEngineCore ^
 --hidden-import=stencil_studio.studio_dialog --hidden-import=stencil_studio.studio_window --hidden-import=stencil_studio.studio ^
 --hidden-import=stencil_studio.core --hidden-import=stencil_studio.engrave --hidden-import=stencil_studio.lightbox ^
 --hidden-import=stencil_studio.lsp_bridge --hidden-import=stencil_studio.subject_ai --hidden-import=stencil_studio.i18n ^
 --hidden-import=scipy.spatial --hidden-import=scipy.ndimage ^
 main.py

=======
pyinstaller --onedir --windowed --name LaserStudioPro --icon=laser_studio_pro.ico --add-data "laser_studio_pro_banner.png;." --add-data "laser_studio_pro_512.png;." --add-data "buy_me_a_coffee.png;." --add-data "stencil_studio;stencil_studio" --collect-all PyQt6.QtSvg --collect-all serial --hidden-import=serial --hidden-import=serial.tools.list_ports main.py
>>>>>>> aed42af (feat: description de vos modifications)
echo ==========================================
echo Copie du fichier icone dans le dossier dist...
echo ==========================================
copy laser_studio_pro.ico dist\LaserStudioPro\

echo ==========================================
echo Termine ! Le dossier dist\LaserStudioPro est pret.
echo ==========================================
pause
