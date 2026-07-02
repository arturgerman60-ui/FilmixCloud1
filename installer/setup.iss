; ==========================================================================
; FunPay AutoResponder — Inno Setup installer script
; Requires Inno Setup 6+  (https://jrsoftware.org/isdl.php)
;
; Build the app first (build.bat) so dist\FunPayAutoResponder exists, then:
;   iscc installer\setup.iss
; ==========================================================================

#define AppName        "FunPay AutoResponder"
#define AppVersion     "1.0.0"
#define AppPublisher   "FunPay AutoResponder"
#define AppExeName     "FunPayAutoResponder.exe"
#define AppId          "{{9E2F5B41-7C1D-4A3E-9B2A-FUNPAY000001}"

[Setup]
AppId={#AppId}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
DisableDirPage=no
OutputDir=..\dist\installer
OutputBaseFilename=FunPayAutoResponder-Setup-{#AppVersion}
SetupIconFile=..\src\assets\icons\app.ico
UninstallDisplayIcon={app}\{#AppExeName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64compatible
; A larger banner/wizard image can be dropped in as WizardImageFile / WizardSmallImageFile

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon";  Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checkedonce
Name: "startupicon";  Description: "Запускать при входе в Windows / Start with Windows"; GroupDescription: "Автозапуск / Autostart"; Flags: unchecked

[Files]
; Bundle the entire PyInstaller one-folder output.
Source: "..\dist\FunPayAutoResponder\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}";              Filename: "{app}\{#AppExeName}"
Name: "{group}\Удалить {#AppName}";      Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}";        Filename: "{app}\{#AppExeName}"; Tasks: desktopicon
Name: "{userstartup}\{#AppName}";        Filename: "{app}\{#AppExeName}"; Tasks: startupicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Leave user data (settings/logs) untouched by default; uncomment to purge:
; Type: filesandordirs; Name: "{userappdata}\FunPayAutoResponder"

[Code]
// Warn the user that the app automates a third-party service.
procedure InitializeWizard();
begin
  // Placeholder for custom wizard pages (e.g. a EULA/usage-notice page).
end;
