global screenTimeDir := "c:\src\screen_time"
global user_id := "b4e45080-6c59-43e0-a644-ecbf07eace02"
global pc_id := "9e7ec6df-31af-4e88-ba60-66783d50bc08"
global isAbleWatchFile := screenTimeDir "\is_able_watch.txt"
global scResultTimeFile := screenTimeDir "\sc_result_time.txt"

#Persistent
#NoEnv
#SingleInstance Force
SetTimer, CheckFile, 20000  ; 20�b���ƂɎ��s
SetTimer, CheckWatchTime, 20000  ; 20�b���Ƃ� `check-watch-time` �����s
Menu, Tray, Tip, ��������...  ; ����c�[���`�b�v
global watchTimeContent_giant := "���擾"
global watchTimeContent_hover := "���擾"

; �N������ `CheckWatchTime` �����s
GoSub, CheckWatchTime

return

CheckFile:
    ; Python�X�N���v�g�����s�icmd�E�B���h�E���\���j
    Run, python %screenTimeDir%\sclog.py log-pc-activity %user_id% %pc_id%, , Hide
    Run, python %screenTimeDir%\sclog.py is-able-watch %user_id% -o %isAbleWatchFile%, , Hide

    ; 3�b�ҋ@
    Sleep, 3000

    ; �t�@�C���̒��g��ǂݍ��݁i�]���ȋ󔒂������j
    FileRead, fileContent, %isAbleWatchFile%
    fileContent := Trim(fileContent)
    
    if (fileContent = "F")
    {
        if WinExist("WatchWindow")
        {
            Gui, WatchWindow:Destroy
        }
            ; �E�B���h�E�̍쐬�i�őO�ʁj
            Gui, WatchWindow:New, +AlwaysOnTop, WatchWindow
            Gui, WatchWindow:Color, 0xCCCCCC
            Gui, WatchWindow:Show, x100 w2300 h900, WatchWindow
            Gui, WatchWindow:Font, s20  ; �t�H���g�T�C�Y��傫������
            Gui, WatchWindow:Add, Text, Center vWatchTimeText,  %watchTimeContent_giant%  ; ����̂� `Add, Text`
            Gui, WatchWindow:Show, , WatchWindow
    }
    else if (fileContent = "T")
    {
        if WinExist("WatchWindow") ; GUI ���\������Ă���Ƃ������j��a
        {
            Gui, WatchWindow:Destroy
        }
    }
return

CheckWatchTime:
    ; `check-watch-time` �����s
    Run, python %screenTimeDir%\sclog.py check-usage %user_id% --message-mode fileout_only_message -o %scResultTimeFile% --encoding sjis , , Hide

    ; 3�b�ҋ@
    Sleep, 3000

    ; ���ʂ�ϐ��Ɋi�[
    FileRead, watchTimeContent_giant, %scResultTimeFile%_giant
    watchTimeContent_giant := Trim(watchTimeContent_giant)

    FileRead, watchTimeContent_hover, %scResultTimeFile%_hover
    watchTimeContent_hover := Trim(watchTimeContent_hover)

    ; �^�X�N�g���C�̃c�[���`�b�v���X�V
    Menu, Tray, Tip, % "��������: " watchTimeContent_hover
return
