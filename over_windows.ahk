global screenTimeDir := "c:\src\screen_time"
global user_id := "b4e45080-6c59-43e0-a644-ecbf07eace02"
global pc_id := "4e27bdfa-83f9-437f-a06b-0fc108c99039"  ; gam
; 9e7ec6df-31af-4e88-ba60-66783d50bc08  ; H1
global isAbleWatchFile := screenTimeDir "\is_able_watch.txt"
global scResultTimeFile := screenTimeDir "\sc_result_time.txt"

#Persistent
#NoEnv
#SingleInstance Force
SetTimer, MainLoop, 20000  ; 20�b���Ƃ� `MainLoop` �����s

Menu, Tray, Tip, ��������...
global watchTimeContent_giant := "���擾"
global watchTimeContent_hover := "���擾"

; �N������ `CheckWatchTime` �����s
GoSub, CheckWatchTime

return

MainLoop:
    if (IsLidClosed()) {
        return  ; �W�����Ă���Ȃ牽�����Ȃ�
    }
    GoSub, CheckFile
    GoSub, CheckWatchTime
return

CheckFile:
    Run, python %screenTimeDir%\sclog.py log-pc-activity %user_id% %pc_id%, , Hide
    Run, python %screenTimeDir%\sclog.py is-able-watch %user_id% -o %isAbleWatchFile%, , Hide
    Sleep, 3000

    FileRead, fileContent, %isAbleWatchFile%
    fileContent := Trim(fileContent)
    if (fileContent = "F") {
        if (A_ComputerName ~= "DESKTOP") {
            ; ��ʂ̕��ƍ������擾
            SysGet, MonitorWorkArea, MonitorWorkArea
            ; ��ʂ̉E���ɕ\���i�E�[����20�s�N�Z���A���[����40�s�N�Z���j
            CoordMode, ToolTip, Screen
            ToolTip, %watchTimeContent_giant%, % MonitorWorkAreaRight - 300, % MonitorWorkAreaBottom - 40
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
    Run, python %screenTimeDir%\sclog.py check-usage %user_id% --message-mode fileout_only_message -o %scResultTimeFile% --encoding sjis , , Hide
    Sleep, 3000

    FileRead, watchTimeContent_giant, %scResultTimeFile%_giant
    watchTimeContent_giant := Trim(watchTimeContent_giant)

    FileRead, watchTimeContent_hover, %scResultTimeFile%_hover
    watchTimeContent_hover := Trim(watchTimeContent_hover)

    Menu, Tray, Tip, % "��������: " watchTimeContent_hover
return

IsLidClosed() {
    ; PowerShell �����s���ĊW�̏�Ԃ��擾
    RunWait, cmd /c PowerShell -Command "$status = (Get-WmiObject -Namespace root\WMI -Class WmiMonitorBasicDisplayParams).Active; if ($status -eq $true) { 'Lid Open' } else { 'Lid Closed' }" > %screenTimeDir%\lid_status.txt, , Hide
    FileRead, lidStatus, %screenTimeDir%\lid_status.txt
    lidStatus := Trim(lidStatus)
    
    ; �܂��͕��@3: StringCompare�g�p
    if (lidStatus ~= "Lid Open") {
        ;msgbox, ���b�h���J���Ă��܂�
        return False  ; ���b�h���J���Ă���
    }
    if (lidStatus ~= "Lid Closed") {
        ;msgbox, ���b�h�����Ă��܂�
       return True  ; ���b�h�����Ă���
    }
    ;msgbox, %lidStatus%
    return False  ; ���b�h���J���Ă���
}
