#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif

[Setup]
AppId={{CBC79BD3-BEB9-5D20-83DB-985DE0B26D13}
AppName=AeroStudio
AppVersion={#AppVersion}
AppPublisher=Muslims in Tech
DefaultDirName={localappdata}\Programs\AeroStudio
DefaultGroupName=AeroStudio
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=AeroStudio-Setup
SetupIconFile=codrone_studio.ico
UninstallDisplayIcon={app}\AeroStudio.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Files]
Source: "..\dist\AeroStudio\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\AeroStudio"; Filename: "{app}\AeroStudio.exe"
Name: "{autodesktop}\AeroStudio"; Filename: "{app}\AeroStudio.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Run]
Filename: "{app}\AeroStudio.exe"; Description: "Launch AeroStudio"; Flags: nowait postinstall skipifsilent
