global screenTimeDir := "c:\src\screen_time"
global user_id := "b4e45080-6c59-43e0-a644-ecbf07eace02"
global pc_id := "4e27bdfa-83f9-437f-a06b-0fc108c99039"  ; gam
global isAbleWatchFile := screenTimeDir "\is_able_watch.txt"
global scResultTimeFile := screenTimeDir "\sc_result_time.txt"

#Persistent
#NoEnv
#SingleInstance Force
SetTimer, MainLoop, 20000  ; 20秒ごとに `MainLoop` を実行

Menu, Tray, Tip, 初期化中...
global watchTimeContent_giant := "未取得"
global watchTimeContent_hover := "未取得"

; 起動時に `CheckWatchTime` を実行
GoSub, CheckWatchTime

return

MainLoop:
    if (IsLidClosed()) {
        return  ; 蓋が閉じているなら何もしない
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
        if WinExist("WatchWindow") {
            Gui, WatchWindow:Destroy
        }
        Gui, WatchWindow:New, +AlwaysOnTop, WatchWindow
        Gui, WatchWindow:Color, 0xCCCCCC
        Gui, WatchWindow:Show, x100 w2300 h900, WatchWindow
        Gui, WatchWindow:Font, s20
        Gui, WatchWindow:Add, Text, Center vWatchTimeText, %watchTimeContent_giant%
        Gui, WatchWindow:Show, , WatchWindow
    } else if (fileContent = "T") {
        if WinExist("WatchWindow") {
            Gui, WatchWindow:Destroy
        }
    }
return

CheckWatchTime:
    Run, python %screenTimeDir%\sclog.py check-usage %user_id% --message-mode fileout_only_message -o %scResultTimeFile% --encoding sjis , , Hide
    Sleep, 3000

    FileRead, watchTimeContent_giant, %scResultTimeFile%_giant
    watchTimeContent_giant := Trim(watchTimeContent_giant)

    FileRead, watchTimeContent_hover, %scResultTimeFile%_hover
    watchTimeContent_hover := Trim(watchTimeContent_hover)

    Menu, Tray, Tip, % "視聴時間: " watchTimeContent_hover
return

IsLidClosed() {
    ; PowerShell を実行して蓋の状態を取得
    RunWait, cmd /c PowerShell -Command "$status = (Get-WmiObject -Namespace root\WMI -Class WmiMonitorBasicDisplayParams).Active; if ($status -eq $true) { 'Lid Open' } else { 'Lid Closed' }" > %screenTimeDir%\lid_status.txt, , Hide
    FileRead, lidStatus, %screenTimeDir%\lid_status.txt
    lidStatus := Trim(lidStatus)
    
    ; または方法3: StringCompare使用
    if (lidStatus ~= "Lid Open") {
        ;msgbox, リッドが開いています
        return False  ; リッドが開いている
    }
    if (lidStatus ~= "Lid Closed") {
        ;msgbox, リッドが閉じています
       return True  ; リッドが閉じている
    }
    ;msgbox, %lidStatus%
    return False  ; リッドが開いている
}
