; CollabTrans Windows Installer Script for Inno Setup
; This script creates a professional Windows installer

#define MyAppName "CollabTrans"
#define MyAppVersion "2.0.0"
#define MyAppPublisher "CollabTrans Team"
#define MyAppURL "https://github.com/your-repo/collabtrans"
#define MyAppExeName "CollabTrans-2.0.0-win.exe"
#define MyAppFullExeName "CollabTrans_full-2.0.0-win.exe"

[Setup]
; NOTE: The value of AppId uniquely identifies this application.
; Do not use the same AppId value in installers for other applications.
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
DisableDirPage=no
DisableProgramGroupPage=no
LicenseFile=LICENSE
OutputDir=build\installer
OutputBaseFilename=CollabTrans-{#MyAppVersion}-Windows-Installer
SetupIconFile=collabtrans.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "chinesesimp"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode

[Files]
; Application files
Source: "dist\{#MyAppExeName}"; DestDir: "{app}\bin"; Flags: ignoreversion
Source: "dist\{#MyAppFullExeName}"; DestDir: "{app}\bin"; Flags: ignoreversion; Check: FileExists(ExpandConstant('{app}\bin\{#MyAppFullExeName}'))

; Configuration templates
Source: "global_config.json"; DestDir: "{app}\config"; Flags: ignoreversion
Source: "local_secrets.json.template"; DestDir: "{app}\config"; Flags: ignoreversion
Source: "app_config.json.template"; DestDir: "{app}\config"; Flags: ignoreversion

; Additional templates if they exist
Source: "local_config.json.template"; DestDir: "{app}\config"; Flags: ignoreversion; Check: FileExists(ExpandConstant('{app}\config\local_config.json.template'))
Source: "app_config.json"; DestDir: "{app}\config"; Flags: ignoreversion; Check: FileExists(ExpandConstant('{app}\config\app_config.json'))

; Launcher scripts
Source: "tools\windows\collabtrans.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "tools\windows\collabtrans-full.bat"; DestDir: "{app}"; Flags: ignoreversion

; Documentation
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "LICENSE"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName} Lite"; Filename: "{app}\collabtrans.bat"; WorkingDir: "{app}"
Name: "{group}\{#MyAppName} Full"; Filename: "{app}\collabtrans-full.bat"; WorkingDir: "{app}"; Check: FileExists(ExpandConstant('{app}\collabtrans-full.bat'))
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName} Lite"; Filename: "{app}\collabtrans.bat"; WorkingDir: "{app}"; Tasks: desktopicon
Name: "{autodesktop}\{#MyAppName} Full"; Filename: "{app}\collabtrans-full.bat"; WorkingDir: "{app}"; Tasks: desktopicon; Check: FileExists(ExpandConstant('{app}\collabtrans-full.bat'))
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName} Lite"; Filename: "{app}\collabtrans.bat"; WorkingDir: "{app}"; Tasks: quicklaunchicon

[Run]
Filename: "{app}\collabtrans.bat"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent

[Code]
var
  ConfigDirPage: TInputDirWizardPage;

procedure InitializeWizard;
begin
  // Create a custom page for configuration directory selection
  ConfigDirPage := CreateInputDirPage(wpSelectDir,
    'Configuration Directory', 'Where should configuration files be stored?',
    'Please select the directory where CollabTrans configuration files will be stored.' + #13#10 + #13#10 +
    'The default location is C:\Users\Public\collabtrans, which allows all users to access the configuration.',
    False, '');
  ConfigDirPage.Add('Configuration directory:');
  ConfigDirPage.Values[0] := ExpandConstant('{commonappdata}\collabtrans');
end;

function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result := False;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if CurPageID = ConfigDirPage.ID then
  begin
    // Validate the configuration directory
    if not DirExists(ConfigDirPage.Values[0]) then
    begin
      if not CreateDir(ConfigDirPage.Values[0]) then
      begin
        MsgBox('Cannot create the configuration directory. Please select a different location.', mbError, MB_OK);
        Result := False;
      end;
    end;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ConfigDir: String;
  ConfigFiles: TArrayOfString;
  I: Integer;
begin
  if CurStep = ssPostInstall then
  begin
    ConfigDir := ConfigDirPage.Values[0];
    
    // Copy configuration files to the selected directory
    SetArrayLength(ConfigFiles, 3);
    ConfigFiles[0] := 'global_config.json';
    ConfigFiles[1] := 'local_secrets.json.template';
    ConfigFiles[2] := 'app_config.json.template';
    
    for I := 0 to GetArrayLength(ConfigFiles) - 1 do
    begin
      if FileExists(ExpandConstant('{app}\config\' + ConfigFiles[I])) then
      begin
        if not FileExists(ConfigDir + '\' + ConfigFiles[I]) then
        begin
          FileCopy(ExpandConstant('{app}\config\' + ConfigFiles[I]), ConfigDir + '\' + ConfigFiles[I], False);
        end;
      end;
    end;
    
    // Create local_secrets.json from template if it doesn't exist
    if not FileExists(ConfigDir + '\local_secrets.json') then
    begin
      if FileExists(ConfigDir + '\local_secrets.json.template') then
      begin
        FileCopy(ConfigDir + '\local_secrets.json.template', ConfigDir + '\local_secrets.json', False);
      end;
    end;
    
    // Create app_config.json from template if it doesn't exist
    if not FileExists(ConfigDir + '\app_config.json') then
    begin
      if FileExists(ConfigDir + '\app_config.json.template') then
      begin
        FileCopy(ConfigDir + '\app_config.json.template', ConfigDir + '\app_config.json', False);
      end
      else if FileExists(ExpandConstant('{app}\config\app_config.json')) then
      begin
        FileCopy(ExpandConstant('{app}\config\app_config.json'), ConfigDir + '\app_config.json', False);
      end;
    end;
  end;
end;

function InitializeUninstallProgressForm(): Boolean;
begin
  Result := True;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  ConfigDir: String;
  Response: Integer;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    ConfigDir := ExpandConstant('{commonappdata}\collabtrans');
    if DirExists(ConfigDir) then
    begin
      Response := MsgBox('Do you want to remove the configuration files?' + #13#10 + #13#10 +
        'Configuration directory: ' + ConfigDir + #13#10 +
        'This will delete all your settings and API keys.', mbConfirmation, MB_YESNO);
      if Response = IDYES then
      begin
        DelTree(ConfigDir, True, True, True);
      end;
    end;
  end;
end;
