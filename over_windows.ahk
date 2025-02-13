global screenTimeDir := "c:\src\screen_time"
global user_id := "b4e45080-6c59-43e0-a644-ecbf07eace02"
global pc_id := "9e7ec6df-31af-4e88-ba60-66783d50bc08"
global isAbleWatchFile := screenTimeDir "\is_able_watch.txt"
global scResultTimeFile := screenTimeDir "\sc_result_time.txt"

#Persistent
#NoEnv
#SingleInstance Force
SetTimer, CheckFile, 20000  ; 20秒ごとに実行
SetTimer, CheckWatchTime, 20000  ; 20秒ごとに `check-watch-time` を実行
Menu, Tray, Tip, 初期化中...  ; 初回ツールチップ
global watchTimeContent_giant := "未取得"
global watchTimeContent_hover := "未取得"

; 起動時に `CheckWatchTime` を実行
GoSub, CheckWatchTime

return

CheckFile:
    ; Pythonスクリプトを実行（cmdウィンドウを非表示）
    Run, python %screenTimeDir%\sclog.py log-pc-activity %user_id% %pc_id%, , Hide
    Run, python %screenTimeDir%\sclog.py is-able-watch %user_id% -o %isAbleWatchFile%, , Hide

    ; 3秒待機
    Sleep, 3000

    ; ファイルの中身を読み込み（余分な空白を除去）
    FileRead, fileContent, %isAbleWatchFile%
    fileContent := Trim(fileContent)
    
    if (fileContent = "F")
    {
        if WinExist("WatchWindow")
        {
            Gui, WatchWindow:Destroy
        }
            ; ウィンドウの作成（最前面）
            Gui, WatchWindow:New, +AlwaysOnTop, WatchWindow
            Gui, WatchWindow:Color, 0xCCCCCC
            Gui, WatchWindow:Show, x100 w2300 h900, WatchWindow
            Gui, WatchWindow:Font, s20  ; フォントサイズを大きくする
            Gui, WatchWindow:Add, Text, Center vWatchTimeText,  %watchTimeContent_giant%  ; 初回のみ `Add, Text`
            Gui, WatchWindow:Show, , WatchWindow
    }
    else if (fileContent = "T")
    {
        if WinExist("WatchWindow") ; GUI が表示されているときだけ破棄a
        {
            Gui, WatchWindow:Destroy
        }
    }
return

CheckWatchTime:
    ; `check-watch-time` を実行
    Run, python %screenTimeDir%\sclog.py check-usage %user_id% --message-mode fileout_only_message -o %scResultTimeFile% --encoding sjis , , Hide

    ; 3秒待機
    Sleep, 3000

    ; 結果を変数に格納
    FileRead, watchTimeContent_giant, %scResultTimeFile%_giant
    watchTimeContent_giant := Trim(watchTimeContent_giant)

    FileRead, watchTimeContent_hover, %scResultTimeFile%_hover
    watchTimeContent_hover := Trim(watchTimeContent_hover)

    ; タスクトレイのツールチップを更新
    Menu, Tray, Tip, % "視聴時間: " watchTimeContent_hover
return
