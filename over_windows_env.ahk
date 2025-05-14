; ���ϐ��̓ǂݍ���
ReadEnvFile(filePath) {
    FileRead, content, %filePath%
    vars := {}
    Loop, Parse, content, `n, `r
    {
        if (A_LoopField = "")
            continue
        parts := StrSplit(A_LoopField, "=", " `t")
        if (parts.Length() >= 2)
            vars[parts[1]] := parts[2]
    }
    return vars
}

; ���ϐ��̓ǂݍ���
envVars := ReadEnvFile(A_ScriptDir "\.env")
global user_id := envVars["user_id"]
global user_id_ApiKey := envVars["user_id_ApiKey"]
global pc_id := envVars["pc_id"]
global pc_name := envVars["pc_name"]

; Python�p�X���O���[�o���ϐ��Ƃ��Đݒ�
global pythonPath := FileExist(A_ScriptDir "\venv") 
    ? A_ScriptDir "\venv\Scripts\python.exe" 
    : "python"

global isAbleWatchFile := A_ScriptDir "\is_able_watch.txt"
global scResultTimeFile := A_ScriptDir "\sc_result_time.txt"
global lidStatusLogFile := A_ScriptDir "\lid_status_log.txt"
global previousLidStatus := ""  ; �O��̏�Ԃ�ۑ�����O���[�o���ϐ�

; �O���[�o���ϐ��̒ǉ��i�t�@�C���㕔�ɒǉ��j
global lastSleepTime := 0

; �N�����ɒ��ԃt�@�C�����폜����
FileDelete, %isAbleWatchFile%
FileDelete, %scResultTimeFile%_giant
FileDelete, %scResultTimeFile%_hover
FileDelete, %A_ScriptDir%\lid_status.txt

#Persistent
#NoEnv
#SingleInstance Force
SetTimer, MainLoop, 10000  ; 10�b���Ƃ� `MainLoop` �����s
SetTimer, CheckWatchWindowPosition, 3000  ; 3�b���Ƃ� �}�E�X�ʒu���ړ��A�E�B���h�E�őO�ʏ��� `CheckWatchWindowPosition` �����s

; �^�X�N�g���C�̃��j���[�ݒ�iExit���j���[��ǉ��j
Menu, Tray, NoStandard
Menu, Tray, Add, Exit, AttemptExit  ; �^�X�N�g���C�ɁuExit�v��ǉ�
Menu, Tray, Default, Exit        ; �E�N���b�N���̃f�t�H���g������uExit�v�ɐݒ�
Menu, Tray, Tip, ��������...

global watchTimeContent_giant := "���擾"
global watchTimeContent_hover := "���擾"

; �N������ `CheckWatchTime` �����s
GoSub, CheckWatchTime

return

MainLoop:
    test := IsLidClosed()
    if (test) {
        FormatTime, currentTime,, yyyy/MM/dd HH:mm:ss
        FileAppend, %currentTime% - close`n, %A_ScriptDir%\lid_status_close_history.txt
        return  ; �W�����Ă���Ȃ牽�����Ȃ�
    }
    GoSub, CheckFile
    GoSub, CheckWatchTime
return

CheckFile:
    ; PC�������O�̋L�^
    Run, %pythonPath% %A_ScriptDir%\sclog.py log-pc-activity %user_id% %pc_id% --api-key %user_id_ApiKey%, , Hide
    ; �����\��Ԃ̊m�F
    Run, %pythonPath% %A_ScriptDir%\sclog.py is-able-watch %user_id% -o %isAbleWatchFile% --api-key %user_id_ApiKey%, , Hide
    Sleep, 3000
    FileRead, fileContent, %isAbleWatchFile%
    fileContent := Trim(fileContent)
    if (fileContent = "F") {
        if (A_ComputerName ~= "DESKTOP-ZZZUQMUFI6a" ) {
            ; ��ʂ̕��ƍ������擾
            SysGet, MonitorWorkArea, MonitorWorkArea
            ; ��ʂ̉E���ɕ\���i�E�[����20�s�N�Z���A���[����40�s�N�Z���j
            CoordMode, ToolTip, Screen
            ToolTip, %watchTimeContent_giant%, % MonitorWorkAreaRight - 20, % MonitorWorkAreaBottom - 40
        } else {
            Send, {Esc}
            Sleep, 300
            ; Windows�L�[�𑗐M
            Send, {LWin}
            Send, {RWin}
            Sleep, 300
            Send, {Esc}
            Sleep, 300
            if WinExist("WatchWindow") {
                Gui, WatchWindow:Destroy
            }
            CoordMode, Mouse, Screen
            MouseGetPos, mouseX, mouseY
            if (mouseX <= 550 && mouseY >= 700) {
                MouseMove, 600, 600
            }
            Gui, WatchWindow:New, +AlwaysOnTop -Caption -SysMenu, WatchWindow
            Gui, WatchWindow:Color, 0xCCCCCC
            Gui, WatchWindow:Show, x0 y120 w1640 h1200, WatchWindow
            Gui, WatchWindow:Font, s20
            Gui, WatchWindow:Add, Text, Center vWatchTimeText, %watchTimeContent_giant%
            Gui, WatchWindow:Add, Button, x1000 y800 w200 h40 gSleepButton, 1���}�~
            Gui, WatchWindow:Show, , WatchWindow
;            WinSet, ExStyle, +0x00000008, WatchWindow
;            WinSet, ExStyle, +0x00000080, WatchWindow
;            WinSet, ExStyle, +0x08000000, WatchWindow
        }
    } else if (fileContent = "T") {
        if WinExist("WatchWindow") {
            Gui, WatchWindow:Destroy
        }
        ;lastSleepTime := 0
        ToolTip  ; ToolTip������
    }
return

CheckWatchTime:
    Run, %pythonPath% %A_ScriptDir%\sclog.py check-usage %user_id% --message-mode fileout_only_message -o %scResultTimeFile% --encoding sjis --api-key %user_id_ApiKey%, , Hide
    Sleep, 3000

    FileRead, watchTimeContent_giant, %scResultTimeFile%_giant
    watchTimeContent_giant := Trim(watchTimeContent_giant)

    FileRead, watchTimeContent_hover, %scResultTimeFile%_hover
    watchTimeContent_hover := Trim(watchTimeContent_hover)

    Menu, Tray, Tip, % "PC : " pc_name  " | ��������: " watchTimeContent_hover
return

CheckWatchWindowPosition:
    if WinExist("WatchWindow") {
;	WinSet, AlwaysOnTop, On, WatchWindow
;        WinSet, Bottom,, WatchWindow
        WinSet, Top,, WatchWindow
        WinActivate, WatchWindow

        CoordMode, Mouse, Screen
        MouseGetPos, mouseX, mouseY
        if (mouseX <= 550 && mouseY >= 700) {
            MouseMove, 600, 600
        }
    }
return

IsLidClosed() {
    ; PowerShell �����s���ĊW�̏�Ԃ��擾
    RunWait, cmd /c PowerShell -Command "$status = (Get-WmiObject -Namespace root\WMI -Class WmiMonitorBasicDisplayParams).Active; if ($status -eq $true) { 'Lid Open' } else { 'Lid Closed' }" > %A_ScriptDir%\lid_status.txt, , Hide
    FileRead, lidStatus, %A_ScriptDir%\lid_status.txt
    lidStatus := Trim(lidStatus)
    
    if (lidStatus ~= "Lid Open") {
        return False  ; �W���J���Ă���
    }
    if (lidStatus ~= "Lid Closed") {
        return True  ; �W�����Ă���
    }
    return False  ; �W���J���Ă���Ƃ݂Ȃ�

    FormatTime, currentTime,, yyyy/MM/dd HH:mm:ss
    
    ; WmiMonitorBasicDisplayParams�ŉ�ʂ̏�Ԃ��m�F
    ;RunWait, cmd /c PowerShell -Command "$monitor = Get-WmiObject -Namespace root\WMI -Class WmiMonitorBasicDisplayParams; $status = if ($monitor.Active -eq $true) { 'Lid Open' } else { 'Lid Closed' }; Write-Output 'Status: ' $status; Write-Output 'Raw: '; $monitor | Format-List *" > %A_ScriptDir%\monitor_status.txt, , Hide
    ;FileRead, monitorStatus, %A_ScriptDir%\monitor_status.txt

    ; ��Ԃ𔻒�iActive = True�Ȃ�J���Ă���j
    RegExMatch(monitorStatus, "Active\s+:\s+[^\r\n]+", match)
    if (!InStr(match, "True") && match != "" && match != "`n") {
        FormatTime, currentTime, %A_Now%, yyyy/MM/dd HH:mm:ss
        FileAppend, % currentTime . "`n" . match . "`n", %A_ScriptDir%\lid_TEST_TEST.txt
    }
    isLidClosed := !(monitorStatus ~= "Active\s+:\s+True")
    
    ; ��Ԃ��ω������ꍇ�̂݃��O���L�^
    if (previousLidStatus != isLidClosed) {
        statusText := isLidClosed ? "Lid Closed" : "Lid Open"
        LogLidStatus(statusText)
        previousLidStatus := isLidClosed
    }

    return isLidClosed
}

LogLidStatus(status) {
    FormatTime, currentTime,, yyyy/MM/dd HH:mm:ss
    logEntry := currentTime . " - " . status . "`n"
    
    ; �����̃��O��ǂݍ���
    FileRead, existingLog, %lidStatusLogFile%
    
    ; �V�����G���g����擪�ɒǉ�
    newLog := logEntry . existingLog
    
    ; ���O���s�P�ʂŕ���
    logLines := StrSplit(newLog, "`n", "`r")
    
    ; �ŐV��60�s������ێ�
    truncatedLog := ""
    lineCount := 0
    Loop, % logLines.Length() {
        if (lineCount >= 60)
            break
        if (logLines[A_Index] != "") {
            truncatedLog .= logLines[A_Index] . "`n"
            lineCount++
        }
    }
    
    ; �t�@�C���ɏ�������
    FileDelete, %lidStatusLogFile%
    FileAppend, %truncatedLog%, %lidStatusLogFile%
}

; === �ȉ��A�^�X�N�g���C�� Exit �@�\�p�R�[�h ===

AttemptExit:
    Gui, Destroy  ; ������GUI��j��
    Gui, +AlwaysOnTop  ; GUI���őO�ʂɕ\��
    Gui, Add, Text,, �I������ɂ͓��͂��Ă�������:
    Gui, Add, Edit, vExitInput Password  ; ���͂��}�X�N�i�p�X���[�h���j
    Gui, Add, Button, Default gCheckExit, �m�F
    Gui, Show,, �I���m�F

    SetTimer, AutoCloseGui, -10000  ; 10�b��ɃE�B���h�E�����
Return

CheckExit:
    Gui, Submit, NoHide
    If (ExitInput == "del") {  ; ���m�� "del" ����͂����ꍇ�̂ݏI��
        ExitApp
    } Else {
        MsgBox, ���͂��Ԉ���Ă��܂��B�I���ł��܂���B
    }
Return

AutoCloseGui:
    Gui, Destroy  ; 10�b��ɃE�B���h�E�����
Return

; �V�����֐��̒ǉ��i�t�@�C�������ɒǉ��j
SleepButton:
    currentTime := A_Now
    if (lastSleepTime = 0) {
        lastSleepTime := currentTime
        ; �^�C�}�[���ꎞ��~
        SetTimer, MainLoop, Off
        SetTimer, CheckWatchWindowPosition, Off
        Gui, WatchWindow:Destroy
        Sleep, 60000  ; 1���ԃX���[�v
        ; �^�C�}�[���ĊJ
        SetTimer, MainLoop, 20000
        SetTimer, CheckWatchWindowPosition, 5000
        return
    }

    timeDiff := currentTime
    EnvSub, timeDiff, lastSleepTime, Minutes
    
    if (timeDiff < 30) {
        remaining := 30 - timeDiff
        ; MsgBox�̑����GUI���X�V
        GuiControl,, WatchTimeText, �O��̗}�~����30���o�߂��Ă��܂���B`n����%remaining%�����҂����������B
        GuiControl,, WatchTimeText2, �O��̗}�~����30���o�߂��Ă��܂���B`n����%remaining%�����҂����������B
        return
    }
    
    lastSleepTime := currentTime
    ; �^�C�}�[���ꎞ��~
    SetTimer, MainLoop, Off
    SetTimer, CheckWatchWindowPosition, Off
    Gui, WatchWindow:Destroy
    Sleep, 60000  ; 1���ԃX���[�v
    ; �^�C�}�[���ĊJ
    SetTimer, MainLoop, 20000
    SetTimer, CheckWatchWindowPosition, 5000
return
