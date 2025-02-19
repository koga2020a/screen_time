global screenTimeDir := "c:\src\screen_time"
global user_id := "616bd16a-d9c1-4c41-8b96-414646d6d218"
global pc_id := "4e27bdfa-83f9-437f-a06b-0fc108c99039"  ; gam
;global pc_id := " 9e7ec6df-31af-4e88-ba60-66783d50bc08"  ; H1
global isAbleWatchFile := screenTimeDir "\is_able_watch.txt"
global scResultTimeFile := screenTimeDir "\sc_result_time.txt"

#Persistent
#NoEnv
#SingleInstance Force
SetTimer, MainLoop, 20000  ; 20秒ごとに `MainLoop` を実行

; タスクトレイのメニュー設定（Exitメニューを追加）
Menu, Tray, NoStandard
Menu, Tray, Add, Exit, AttemptExit  ; タスクトレイに「Exit」を追加
Menu, Tray, Default, Exit        ; 右クリック時のデフォルト動作を「Exit」に設定
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
        if (A_ComputerName ~= "DESKTOP-UQMUFI6") {
            ; 画面の幅と高さを取得
            SysGet, MonitorWorkArea, MonitorWorkArea
            ; 画面の右下に表示（右端から20ピクセル、下端から40ピクセル）
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
        ToolTip  ; ToolTipを消去
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
    
    if (lidStatus ~= "Lid Open") {
        return False  ; 蓋が開いている
    }
    if (lidStatus ~= "Lid Closed") {
       return True  ; 蓋が閉じている
    }
    return False  ; 蓋が開いているとみなす
}

; === 以下、タスクトレイの Exit 機能用コード ===

AttemptExit:
    Gui, Destroy  ; 既存のGUIを破棄
    Gui, Add, Text,, 終了するには入力してください:
    Gui, Add, Edit, vExitInput Password  ; 入力をマスク（パスワード風）
    Gui, Add, Button, Default gCheckExit, 確認
    Gui, Show,, 終了確認

    SetTimer, AutoCloseGui, -10000  ; 10秒後にウィンドウを閉じる
Return

CheckExit:
    Gui, Submit, NoHide
    If (ExitInput == "del") {  ; 正確に "del" を入力した場合のみ終了
        ExitApp
    } Else {
        MsgBox, 入力が間違っています。終了できません。
    }
Return

AutoCloseGui:
    Gui, Destroy  ; 10秒後にウィンドウを閉じる
Return
