; 環境変数の読み込み
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

; 環境変数の読み込み
envVars := ReadEnvFile(A_ScriptDir "\.env")
global user_id := envVars["user_id"]
global user_id_ApiKey := envVars["user_id_ApiKey"]
global pc_id := envVars["pc_id"]
global pc_name := envVars["pc_name"]

; Pythonパスをグローバル変数として設定
global pythonPath := FileExist(A_ScriptDir "\venv") 
    ? A_ScriptDir "\venv\Scripts\python.exe" 
    : "python"

global isAbleWatchFile := A_ScriptDir "\is_able_watch.txt"
global scResultTimeFile := A_ScriptDir "\sc_result_time.txt"
global lidStatusLogFile := A_ScriptDir "\lid_status_log.txt"
global previousLidStatus := ""  ; 前回の状態を保存するグローバル変数

; グローバル変数の追加（ファイル上部に追加）
global lastSleepTime := 0

; 起動時に中間ファイルを削除する
FileDelete, %isAbleWatchFile%
FileDelete, %scResultTimeFile%_giant
FileDelete, %scResultTimeFile%_hover
FileDelete, %A_ScriptDir%\lid_status.txt

#Persistent
#NoEnv
#SingleInstance Force
SetTimer, MainLoop, 10000  ; 10秒ごとに `MainLoop` を実行
SetTimer, CheckWatchWindowPosition, 3000  ; 3秒ごとに マウス位置を移動、ウィンドウ最前面処理 `CheckWatchWindowPosition` を実行

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
    test := IsLidClosed()
    if (test) {
        FormatTime, currentTime,, yyyy/MM/dd HH:mm:ss
        FileAppend, %currentTime% - close`n, %A_ScriptDir%\lid_status_close_history.txt
        return  ; 蓋が閉じているなら何もしない
    }
    GoSub, CheckFile
    GoSub, CheckWatchTime
return

CheckFile:
    ; PC活動ログの記録
    Run, %pythonPath% %A_ScriptDir%\sclog.py log-pc-activity %user_id% %pc_id% --api-key %user_id_ApiKey%, , Hide
    ; 視聴可能状態の確認
    Run, %pythonPath% %A_ScriptDir%\sclog.py is-able-watch %user_id% -o %isAbleWatchFile% --api-key %user_id_ApiKey%, , Hide
    Sleep, 3000
    FileRead, fileContent, %isAbleWatchFile%
    fileContent := Trim(fileContent)
    if (fileContent = "F") {
        if (A_ComputerName ~= "DESKTOP-ZZZUQMUFI6a" ) {
            ; 画面の幅と高さを取得
            SysGet, MonitorWorkArea, MonitorWorkArea
            ; 画面の右下に表示（右端から20ピクセル、下端から40ピクセル）
            CoordMode, ToolTip, Screen
            ToolTip, %watchTimeContent_giant%, % MonitorWorkAreaRight - 20, % MonitorWorkAreaBottom - 40
        } else {
            Send, {Esc}
            Sleep, 300
            ; Windowsキーを送信
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
;            Gui, WatchWindow:Add, Button, x1000 y800 w200 h40 gSleepButton, 2分抑止
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
        ToolTip  ; ToolTipを消去
    }
return

CheckWatchTime:
    Run, %pythonPath% %A_ScriptDir%\sclog.py check-usage %user_id% --message-mode fileout_only_message -o %scResultTimeFile% --encoding sjis --api-key %user_id_ApiKey%, , Hide
    Sleep, 3000

    FileRead, watchTimeContent_giant, %scResultTimeFile%_giant
    watchTimeContent_giant := Trim(watchTimeContent_giant)

    FileRead, watchTimeContent_hover, %scResultTimeFile%_hover
    watchTimeContent_hover := Trim(watchTimeContent_hover)

    Menu, Tray, Tip, % "PC : " pc_name  " | 視聴時間: " watchTimeContent_hover
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
    ; PowerShell を実行して蓋の状態を取得
    RunWait, cmd /c PowerShell -Command "$status = (Get-WmiObject -Namespace root\WMI -Class WmiMonitorBasicDisplayParams).Active; if ($status -eq $true) { 'Lid Open' } else { 'Lid Closed' }" > %A_ScriptDir%\lid_status.txt, , Hide
    FileRead, lidStatus, %A_ScriptDir%\lid_status.txt
    lidStatus := Trim(lidStatus)
    
    if (lidStatus ~= "Lid Open") {
        return False  ; 蓋が開いている
    }
    if (lidStatus ~= "Lid Closed") {
        return True  ; 蓋が閉じている
    }
    return False  ; 蓋が開いているとみなす

    FormatTime, currentTime,, yyyy/MM/dd HH:mm:ss
    
    ; WmiMonitorBasicDisplayParamsで画面の状態を確認
    ;RunWait, cmd /c PowerShell -Command "$monitor = Get-WmiObject -Namespace root\WMI -Class WmiMonitorBasicDisplayParams; $status = if ($monitor.Active -eq $true) { 'Lid Open' } else { 'Lid Closed' }; Write-Output 'Status: ' $status; Write-Output 'Raw: '; $monitor | Format-List *" > %A_ScriptDir%\monitor_status.txt, , Hide
    ;FileRead, monitorStatus, %A_ScriptDir%\monitor_status.txt

    ; 状態を判定（Active = Trueなら開いている）
    RegExMatch(monitorStatus, "Active\s+:\s+[^\r\n]+", match)
    if (!InStr(match, "True") && match != "" && match != "`n") {
        FormatTime, currentTime, %A_Now%, yyyy/MM/dd HH:mm:ss
        FileAppend, % currentTime . "`n" . match . "`n", %A_ScriptDir%\lid_TEST_TEST.txt
    }
    isLidClosed := !(monitorStatus ~= "Active\s+:\s+True")
    
    ; 状態が変化した場合のみログを記録
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
    
    ; 既存のログを読み込む
    FileRead, existingLog, %lidStatusLogFile%
    
    ; 新しいエントリを先頭に追加
    newLog := logEntry . existingLog
    
    ; ログを行単位で分割
    logLines := StrSplit(newLog, "`n", "`r")
    
    ; 最新の60行だけを保持
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
    
    ; ファイルに書き込む
    FileDelete, %lidStatusLogFile%
    FileAppend, %truncatedLog%, %lidStatusLogFile%
}

; === 以下、タスクトレイの Exit 機能用コード ===

AttemptExit:
    Gui, Destroy  ; 既存のGUIを破棄
    Gui, +AlwaysOnTop  ; GUIを最前面に表示
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

; 新しい関数の追加（ファイル末尾に追加）
SleepButton:
    currentTime := A_Now
    if (lastSleepTime = 0) {
        lastSleepTime := currentTime
        ; タイマーを一時停止
        SetTimer, MainLoop, Off
        SetTimer, CheckWatchWindowPosition, Off
        Gui, WatchWindow:Destroy
        Sleep, 120000  ; 2分間スリープ
        ; タイマーを再開
        SetTimer, MainLoop, 20000
        SetTimer, CheckWatchWindowPosition, 5000
        return
    }

    timeDiff := currentTime
    EnvSub, timeDiff, lastSleepTime, Minutes
    
    if (timeDiff < 30) {
        remaining := 30 - timeDiff
        ; MsgBoxの代わりにGUIを更新
        GuiControl,, WatchTimeText, 前回の抑止から30分経過していません。`nあと%remaining%分お待ちください。
        GuiControl,, WatchTimeText2, 前回の抑止から30分経過していません。`nあと%remaining%分お待ちください。
        return
    }
    
    lastSleepTime := currentTime
    ; タイマーを一時停止
    SetTimer, MainLoop, Off
    SetTimer, CheckWatchWindowPosition, Off
    Gui, WatchWindow:Destroy
    Sleep, 120000  ; 2分間スリープ
    ; タイマーを再開
    SetTimer, MainLoop, 20000
    SetTimer, CheckWatchWindowPosition, 5000
return
