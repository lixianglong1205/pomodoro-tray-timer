[Setup]
AppId={{9A6D1269-9955-4E32-9ACF-4E47F4E7B0F3}
AppName=Pomodoro Tray Timer
AppVersion=0.1.0
AppPublisher=Pomodoro Tray Timer
DefaultDirName={pf}\pomodoro-tray-timer
DefaultGroupName=Pomodoro Tray Timer
OutputDir=..\dist-installer
OutputBaseFilename=pomodoro-tray-timer-setup
Compression=lzma
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64
DisableProgramGroupPage=yes

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加任务"; Flags: unchecked

[Files]
Source: "..\dist\pomodoro-tray-timer\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Pomodoro Tray Timer"; Filename: "{app}\pomodoro-tray-timer.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\Pomodoro Tray Timer"; Filename: "{app}\pomodoro-tray-timer.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\pomodoro-tray-timer.exe"; Description: "启动 Pomodoro Tray Timer"; Flags: nowait postinstall skipifsilent

[Code]
var
  DataDirPage: TInputDirWizardPage;

function SettingsIniPath(): string;
begin
  Result := ExpandConstant('{userappdata}\pomodoro-tray-timer\settings.ini');
end;

function DefaultDataDir(): string;
begin
  Result := ExpandConstant('{userappdata}\pomodoro-tray-timer\data');
end;

procedure InitializeWizard();
var
  IniPath: string;
  PrevDataDir: string;
begin
  IniPath := SettingsIniPath();
  PrevDataDir := GetIniString('app', 'DataDir', '', IniPath);
  if PrevDataDir = '' then
    PrevDataDir := DefaultDataDir();

  DataDirPage := CreateInputDirPage(
    wpSelectDir,
    '数据保存目录',
    '请选择配置/历史的保存位置',
    '程序会把 config.json 与 history.csv 写入该目录。建议保持默认；如需放到网盘同步目录，也可以在这里选择。',
    False,
    ''
  );
  DataDirPage.Add('数据目录:');
  DataDirPage.Values[0] := PrevDataDir;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  IniPath: string;
  DataDir: string;
  Content: string;
begin
  if CurStep <> ssInstall then
    Exit;

  DataDir := DataDirPage.Values[0];
  if DataDir = '' then
    DataDir := DefaultDataDir();
  DataDir := RemoveBackslashUnlessRoot(DataDir);
  ForceDirectories(DataDir);

  IniPath := SettingsIniPath();
  ForceDirectories(ExtractFileDir(IniPath));
  Content := '[app]' + #13#10 + 'DataDir=' + DataDir + #13#10;
  SaveStringToFile(IniPath, Content, False);
end;

