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

global isAbleWatchFile := A_ScriptDir "\is_able_watch.txt"
global scResultTimeFile := A_ScriptDir "\sc_result_time.txt"
global lidStatusLogFile := A_ScriptDir "\lid_status_log.txt"
global previousLidStatus := ""  ; �O��̏�Ԃ�ۑ�����O���[�o���ϐ�

; �N�����ɒ��ԃt�@�C�����폜����
FileDelete, %isAbleWatchFile%
FileDelete, %scResultTimeFile%_giant
FileDelete, %scResultTimeFile%_hover
FileDelete, %A_ScriptDir%\lid_status.txt

#Persistent
#NoEnv
#SingleInstance Force
SetTimer, MainLoop, 20000  ; 20�b���Ƃ� `MainLoop` �����s

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
        return  ; �W�����Ă���Ȃ牽�����Ȃ�
    }
    GoSub, CheckFile
    GoSub, CheckWatchTime
return

CheckFile:
    Run, python %A_ScriptDir%\sclog.py log-pc-activity %user_id% %pc_id% --api-key %user_id_ApiKey%, , Hide
    Run, python %A_ScriptDir%\sclog.py is-able-watch %user_id% -o %isAbleWatchFile% --api-key %user_id_ApiKey%, , Hide
    Sleep, 3000
    FileRead, fileContent, %isAbleWatchFile%
    fileContent := Trim(fileContent)
    if (fileContent = "F") {
        if (A_ComputerName ~= "DESKTOP-UQMUFI6") {
            ; ��ʂ̕��ƍ������擾
            SysGet, MonitorWorkArea, MonitorWorkArea
            ; ��ʂ̉E���ɕ\���i�E�[����20�s�N�Z���A���[����40�s�N�Z���j
            CoordMode, ToolTip, Screen
            ToolTip, %watchTimeContent_giant%, % MonitorWorkAreaRight - 20, % MonitorWorkAreaBottom - 40
        } else {
            if WinExist("WatchWindow") {
                Gui, WatchWindow:Destroy
            }
            Gui, WatchWindow:New, +AlwaysOnTop, WatchWindow
            Gui, WatchWindow:Color, 0xCCCCCC
            Gui, WatchWindow:Show, x100 w2300 h900, WatchWindow
            Gui, WatchWindow:Font, s20
            Gui, WatchWindow:Add, Text, Center vWatchTimeText, %watchTimeContent_giant%
            Gui, WatchWindow:Show, , WatchWindow
        }
    } else if (fileContent = "T") {
        if WinExist("WatchWindow") {
            Gui, WatchWindow:Destroy
        }
        ToolTip  ; ToolTip������
    }
return

CheckWatchTime:
    Run, python %A_ScriptDir%\sclog.py check-usage %user_id% --message-mode fileout_only_message -o %scResultTimeFile% --encoding sjis --api-key %user_id_ApiKey%, , Hide
    Sleep, 3000

    FileRead, watchTimeContent_giant, %scResultTimeFile%_giant
    watchTimeContent_giant := Trim(watchTimeContent_giant)

    FileRead, watchTimeContent_hover, %scResultTimeFile%_hover
    watchTimeContent_hover := Trim(watchTimeContent_hover)

    Menu, Tray, Tip, % "��������: " watchTimeContent_hover
return

IsLidClosed() {
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
