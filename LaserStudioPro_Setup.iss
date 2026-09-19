; ============================================================================
; Script Inno Setup — Laser Studio Pro
; ============================================================================
; Ce script transforme ton .exe autonome (produit par PyInstaller) en un
; véritable installeur Windows : menu Démarrer, raccourci Bureau (optionnel),
; désinstalleur propre listé dans "Applications installées".
;
; UTILISATION :
;   1. Installe Inno Setup (gratuit) : https://jrsoftware.org/isdl.php
;   2. Assure-toi d'avoir déjà compilé LaserStudioPro.exe avec PyInstaller
;      (dist\LaserStudioPro.exe doit exister), avec l'icône :
;         pyinstaller --noconfirm --onefile --windowed ^
;             --icon="laser_studio_pro.ico" --name "LaserStudioPro" app.py
;   3. Ouvre ce fichier .iss avec Inno Setup (double-clic ou "Ouvrir avec").
;   4. Clique sur "Compiler" (ou F9).
;   5. L'installeur final apparaît dans le dossier "Output" à côté de ce
;      script : LaserStudioPro_Setup.exe — c'est ce fichier que tu distribues.
; ============================================================================

#define MyAppName "Laser Studio Pro"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Toi-même"
#define MyAppExeName "LaserStudioPro.exe"

[Setup]
AppId={{8F2B1A4E-6C3D-4E9A-9B7A-LASERSTUDIOPRO}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
; Icône affichée dans le panneau "Programmes et fonctionnalités" de Windows
UninstallDisplayIcon={app}\{#MyAppExeName}
; Dossier où sera créé l'installeur final (LaserStudioPro_Setup.exe)
OutputDir=Output
OutputBaseFilename=LaserStudioPro_Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
; Pas besoin des droits administrateur (installation dans le dossier
; utilisateur) ; passe à "admin" si tu préfères installer pour tous les
; utilisateurs dans Program Files.
PrivilegesRequired=lowest

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "desktopicon"; Description: "Créer un raccourci sur le Bureau"; GroupDescription: "Raccourcis supplémentaires :"

[Files]
; Adapte ce chemin si ton .exe compilé se trouve ailleurs.
Source: "dist\LaserStudioPro.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "laser_studio_pro.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\laser_studio_pro.ico"
Name: "{group}\Désinstaller {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\laser_studio_pro.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Lancer {#MyAppName}"; Flags: nowait postinstall skipifsilent
