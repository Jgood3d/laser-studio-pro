[Setup]
AppName=Laser Studio Pro
AppVersion=2026.10
; Propose par défaut le dossier dans Program Files, mais l'utilisateur pourra le changer
DefaultDirName={autopf}\LaserStudioPro
; S'assure que la page de sélection du dossier s'affiche bien pendant l'installation
DisableDirPage=no
DefaultGroupName=Laser Studio Pro

; --- DOSSIER ET NOM DU FICHIER SETUP GÉNÉRÉ ---
; Chemin relatif au dossier de ce script (packaging\windows\) : Setup-LSP a la racine du projet.
OutputDir=..\..\Setup-LSP
OutputBaseFilename=LaserStudioPro_Setup

Compression=lzma
SolidCompression=yes
; Chemin relatif au dossier de ce script (packaging\windows\).
SetupIconFile=..\..\resources\laser_studio_pro.ico

[Files]
; Copie tout le contenu du dossier généré par PyInstaller (dist\LaserStudioPro, voir build.bat) vers le dossier de destination
Source: "..\..\dist\LaserStudioPro\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Laser Studio Pro"; Filename: "{app}\LaserStudioPro.exe"; IconFilename: "{app}\laser_studio_pro.ico"
Name: "{autodesktop}\Laser Studio Pro"; Filename: "{app}\LaserStudioPro.exe"; IconFilename: "{app}\laser_studio_pro.ico"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Créer un raccourci sur le Bureau"; GroupDescription: "Tâches supplémentaires"; Flags: unchecked