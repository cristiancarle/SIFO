; Archivo de configuración para Inno Setup
; Compilar con: iscc SIFO_installer.iss

[Setup]
AppName=SIFO
AppVersion=1.0.0
AppPublisher=SIFO
AppPublisherURL=https://example.com
AppSupportURL=https://example.com
AppUpdatesURL=https://example.com
DefaultDirName={commonpf64}\SIFO
DefaultGroupName=SIFO
OutputDir=.
OutputBaseFilename=SIFO-Setup
Compression=lzma
SolidCompression=yes
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64
UninstallDisplayIcon={app}\SIFO.exe
CreateAppDir=yes
CreateUninstallRegKey=yes
LicenseFile=./LICENSE.txt

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Files]
Source: ".\dist\SIFO\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\SIFO"; Filename: "{app}\SIFO.exe"; WorkingDir: "{app}"
Name: "{commondesktop}\SIFO"; Filename: "{app}\SIFO.exe"; WorkingDir: "{app}"

[Run]
Filename: "{app}\SIFO.exe"; Description: "Abrir SIFO"; Flags: nowait postinstall skipifsilent
