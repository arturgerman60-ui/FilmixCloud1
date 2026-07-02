; Inno Setup — собирает FunPayAssistant-Setup.exe из готового .exe.
; Компиляция: iscc build\installer.iss  (после PyInstaller)

#define AppName "FunPay Assistant"
#define AppVersion "1.0.0"
#define AppExe "FunPayAssistant.exe"

[Setup]
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=FunPay Assistant
DefaultDirName={autopf}\FunPayAssistant
DefaultGroupName=FunPay Assistant
DisableProgramGroupPage=yes
OutputDir=..\dist_installer
OutputBaseFilename=FunPayAssistant-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest

[Languages]
Name: "ru"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "en"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Создать ярлык на рабочем столе"; GroupDescription: "Дополнительно:"

[Files]
Source: "..\dist\{#AppExe}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\FunPay Assistant"; Filename: "{app}\{#AppExe}"
Name: "{userdesktop}\FunPay Assistant"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "Запустить FunPay Assistant"; Flags: nowait postinstall skipifsilent
