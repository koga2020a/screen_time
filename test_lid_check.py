import ctypes
import time
#import win32gui
import wmi
from datetime import datetime

LOG_FILE = "lid_status_log.txt"

# Windowsの電源状態を取得
class SYSTEM_POWER_STATUS(ctypes.Structure):
    _fields_ = [
        ("ACLineStatus", ctypes.c_byte),
        ("BatteryFlag", ctypes.c_byte),
        ("BatteryLifePercent", ctypes.c_byte),
        ("Reserved1", ctypes.c_byte),
        ("BatteryLifeTime", ctypes.c_ulong),
        ("BatteryFullLifeTime", ctypes.c_ulong)
    ]

def get_power_status():
    status = SYSTEM_POWER_STATUS()
    ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(status))
    return "Battery" if status.ACLineStatus == 0 else "AC Power"

# スクリーンの状態を取得
#def is_screen_off():
#    return not bool(win32gui.GetForegroundWindow())

# WMIを使ってディスプレイの状態を取得
def is_lid_closed():
    w = wmi.WMI(namespace="root\\WMI")
    try:
        lid_state = w.ExecQuery("SELECT * FROM WmiMonitorBasicDisplayParams")
        return len(lid_state) == 0  # 画面が検出できない = 蓋が閉じている可能性
    except Exception as e:
        return f"Error: {e}"

# ログをファイルに追記
def log_lid_status():
    with open(LOG_FILE, "a") as log:
        while True:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            power_status = get_power_status()
            screen_status = "" #"Off" if is_screen_off() else "On"
            lid_status = "Closed" if is_lid_closed() else "Open"

            log_entry = f"{now} | Power: {power_status} | Screen: {screen_status} | Lid: {lid_status}\n"
            print(log_entry.strip())  # コンソールにも表示
            log.write(log_entry)
            log.flush()  # すぐに書き込む

            time.sleep(5)  # 5秒ごとにチェック

# 実行
log_lid_status()
