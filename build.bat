@echo off
echo ==========================================
echo Activation de l'environnement virtuel...
echo ==========================================
call venv\Scripts\activate.bat

echo ==========================================
echo Nettoyage des anciens dossiers...
echo ==========================================
rmdir /s /q build
rmdir /s /q dist

echo ==========================================
echo Compilation de Laser Studio Pro (Mode Onedir)...
echo ==========================================
pyinstaller --onedir --windowed --name LaserStudioPro --icon=laser_studio_pro.ico --add-data "laser_studio_pro_banner.png;." --add-data "laser_studio_pro_512.png;." --add-data "buy_me_a_coffee.png;." --add-data "stencil_studio;stencil_studio" --paths "C:\Users\Bonnevie\Desktop\Log-gravure\laser-studio-pro-propre\venv\Lib\site-packages" --collect-submodules serial --hidden-import=serial main.py

echo ==========================================
echo Copie du fichier icone dans le dossier dist...
echo ==========================================
copy laser_studio_pro.ico dist\LaserStudioPro\

echo ==========================================
echo Termine ! Le dossier dist\LaserStudioPro est pret.
echo ==========================================
pause