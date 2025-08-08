#!/usr/bin/env python3
import sys
import argparse
import requests
import uuid
import json
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import os
import urllib.parse

# jpholidayを導入して祝日判定
try:
    import jpholiday
    JPHOLIDAY_AVAILABLE = True
except ImportError:
    JPHOLIDAY_AVAILABLE = False
    print("Warning: jpholiday is not installed. Holiday detection will be disabled.")
    print("Please install it using: pip install jpholiday")

# ノートPCの蓋の状態を検出するためにWMIを追加
try:
    import wmi
    WMI_AVAILABLE = True
except ImportError:
    WMI_AVAILABLE = False

# .envファイルから環境変数をロード
load_dotenv()

# グローバル変数として環境変数を設定
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_API_KEY = os.getenv("SUPABASE_API_KEY")
USER_API_KEY = os.getenv("user_id_ApiKey")  # .envファイルの変数名に合わせる

HEADERS = {
    "apikey": SUPABASE_API_KEY,
    "Authorization": f"Bearer {SUPABASE_API_KEY}",
    "Content-Type": "application/json",
}

# JST（日本標準時、UTC+9）の定義（固定オフセット）
JST = timezone(timedelta(hours=9), name="JST")

def is_valid_uuid(value):
    """指定された文字列が UUID 形式かどうかチェックします。"""
    try:
        uuid.UUID(value, version=4)
        return True
    except ValueError:
        return False

def get_pc_id_from_user(user_id, pc_identifier):
    """
    pc_identifier が UUID 形式の場合はそれをそのまま返す。
    そうでない場合は pc_identifier を pc_name とみなし、user_pcs から該当する pc_id を取得して返す。
    見つからなければ None を返す。
    """
    if is_valid_uuid(pc_identifier):
        return pc_identifier

    try:
        url_rpc = f"{SUPABASE_URL}/rest/v1/rpc/get_pc_id_by_name_and_user"
        payload = {
            "p_api_key": USER_API_KEY,
            "p_user_id": user_id,
            "p_pc_name": pc_identifier
        }
        response = requests.post(url_rpc, headers=HEADERS, json=payload)
        if response.status_code == 400 and "Invalid API key" in response.text:
            return None
            
        if not response.text.strip():
            return None
            
        return response.text.strip('"')  # Supabaseは文字列を引用符付きで返すため、それを除去
    except Exception:
        return None

def get_pc_name_from_pc_id(user_id, pc_id):
    """
    user_pcs から pc_id に対応する pc_name を取得して返す。
    該当がなければ None を返す。
    """
    try:
        url_rpc = f"{SUPABASE_URL}/rest/v1/rpc/get_pc_name_by_user"
        payload = {
            "p_api_key": USER_API_KEY,
            "p_user_id": user_id,
            "p_pc_id": pc_id
        }
        response = requests.post(url_rpc, headers=HEADERS, json=payload)

        if response.status_code == 400 and "Invalid API key" in response.text:
            return None
            
        if not response.text.strip():
            return None
            
        return response.text.strip('"')  # Supabaseは文字列を引用符付きで返すため、それを除去
    except Exception:
        return None

def check_user_exists(user_id):
    """users_watch_time テーブルに指定された user_id が存在するか確認します。"""
    try:
        url_rpc = f"{SUPABASE_URL}/rest/v1/rpc/check_user_exists_by_api"
        payload = {
            "p_api_key": USER_API_KEY,
            "p_user_id": user_id
        }
        response = requests.post(url_rpc, headers=HEADERS, json=payload)
        
        if response.status_code == 400 and "Invalid API key" in response.text:
            return False
            
        if not response.text.strip():
            return False
            
        return response.json()
    except Exception:
        return False

def get_activity_time():
    """
    現在時刻を JST (日本標準時) で取得し、
    その日の 0:00 (JST) からの経過分数を返します。
    ※pc_activity_2ではminutes_time_jstは自動計算されるため、本関数はログ確認用に残しています。
    """
    now = datetime.now(JST)
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    minutes_since_midnight = int((now - midnight).total_seconds() / 60)
    return minutes_since_midnight

def get_today_range_utc():
    """
    当日のUTCの開始時刻と終了時刻をISO8601形式（タイムゾーン情報付き）で返します。
    JSTの日付で当日を判定し、UTCに変換します。
    """
    now_jst = datetime.now(JST)
    start_jst = now_jst.replace(hour=0, minute=0, second=0, microsecond=0)
    end_jst = start_jst + timedelta(days=1)
    start_utc = start_jst.astimezone(timezone.utc)
    end_utc = end_jst.astimezone(timezone.utc)
    return start_utc.isoformat(), end_utc.isoformat()

def get_today_range_jst():
    """
    当日のJST上の開始時刻と終了時刻（ISO8601形式）を返します。
    例: ('2024-02-15T00:00:00+09:00', '2024-02-16T00:00:00+09:00')
    """
    now_jst = datetime.now(JST)
    start_jst = now_jst.replace(hour=0, minute=0, second=0, microsecond=0)
    end_jst = start_jst + timedelta(days=1)
    return start_jst.isoformat(), end_jst.isoformat()

def is_lid_closed():
    """ノートPCの蓋が閉じられているかどうかをチェックします。
    WMIが利用可能でなければFalseを返します。"""
    if not WMI_AVAILABLE:
        return False
    
    try:
        w = wmi.WMI(namespace="root\\WMI")
        lid_state = w.ExecQuery("SELECT * FROM WmiMonitorBasicDisplayParams")
        return len(lid_state) == 0  # 画面が検出できない = 蓋が閉じている可能性
    except Exception:
        return False

def log_pc_activity(user_id, pc_identifier, return_result=False):
    """
    PCアクティビティ（利用時間）を記録します。
    pc_identifier は UUID または pc_name を受け取り、対応する pc_id を取得後、
    新テーブルpc_activity_2にユーザとPCの組み合わせを登録します。
    
    ※新仕様では、minutes_time_jst はテーブル側で自動計算されるため、値の送信は不要です。
    
    ノートPCの蓋が閉じられている場合は処理を中断します。
    """
    # ノートPCの蓋が閉じられているかチェック
    if is_lid_closed():
        # lid_status_logs.txtに日時と現象を記録
        try:
            now = datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S")
            log_message = f"{now} - 蓋が閉じられています。PCアクティビティのログ記録を中断しました。\n"
            with open("lid_status_logs.txt", "a", encoding="utf-8") as log_file:
                log_file.write(log_message)
        except Exception as e:
            print(f"ログファイルへの書き込みに失敗しました: {str(e)}")
            
        result = "蓋が閉じられているため、PCアクティビティのログ記録を中断します。"
        return result if return_result else print(result)

    if not is_valid_uuid(user_id):
        result = f"エラー: user_id ({user_id}) は正しいUUID形式ではありません"
        return result if return_result else print(result)

    if not check_user_exists(user_id):
        result = f"エラー: user_id ({user_id}) は users_watch_time に存在しません"
        return result if return_result else print(result)

    pc_id = get_pc_id_from_user(user_id, pc_identifier)
    if not pc_id:
        result = (
            f"エラー: 指定されたPC (\"{pc_identifier}\") が見つかりません。"
            "UUID または既存の pc_name を指定してください。"
        )
        return result if return_result else print(result)

    url = f"{SUPABASE_URL}/rest/v1/pc_activity_2"
    data = {"user_id": user_id, "pc_id": pc_id}
    print(data)
    response = requests.post(url, json=data, headers=HEADERS)
    if response.text.strip():
        try:
            res_json = response.json()
            result = json.dumps(res_json, ensure_ascii=False)
        except requests.exceptions.JSONDecodeError:
            result = f"APIレスポンス（JSONでデコードできない）: {response.text}"
    else:
        result = "APIレスポンス: (空のレスポンス 追記のみ)"
    return result if return_result else print(result)

def get_pc_activity_minutes_by_pc(user_id, pc_id, start_time, end_time):
    """指定されたPCの特定期間の利用時間（minutes_time_jst）のリストを取得します。"""
    try:
        url_rpc = f"{SUPABASE_URL}/rest/v1/rpc/get_pc_activity_minutes_by_pc_and_api"
        payload = {
            "p_api_key": USER_API_KEY,
            "p_user_id": user_id,
            "p_pc_id": pc_id,
            "p_start_time": start_time,
            "p_end_time": end_time
        }
        response = requests.post(url_rpc, headers=HEADERS, json=payload)
        
        if response.status_code == 400 and "Invalid API key" in response.text:
            return []
            
        if not response.text.strip():
            return []
            
        return response.json()
    except Exception:
        return []

def get_pc_usage(user_id, pc_identifier, return_result=False):
    try:
        pc_id = get_pc_id_from_user(user_id, pc_identifier)
        if not pc_id:
            result = json.dumps({
                "error": f"指定されたPC (\"{pc_identifier}\") が見つかりません。"
            }, ensure_ascii=False)
            return result if return_result else print(result)

        pc_name = get_pc_name_from_pc_id(user_id, pc_id) or pc_id

        start, end = get_today_range_utc()
        activity_data = get_pc_activity_minutes_by_pc(user_id, pc_id, start, end)
        unique_minutes = {row["minutes_time_jst"] for row in activity_data}
        total_usage = len(unique_minutes)
        usage_times = [f"{m // 60:02d}:{m % 60:02d}" for m in sorted(unique_minutes)]
        
        res = {
            "success": True,
            "pc_name": pc_name,
            "pc_usage_minutes": total_usage,
            "usage_times": usage_times
        }
        result = json.dumps(res, ensure_ascii=False)
    except Exception:
        result = "E"
    return result if return_result else print(result)

def get_total_usage_minutes(user_id, start_time, end_time):
    """指定された期間の利用済み分数（重複を除く）を取得します。"""
    try:
        url_rpc = f"{SUPABASE_URL}/rest/v1/rpc/get_total_usage_minutes_by_api"
        payload = {
            "p_api_key": USER_API_KEY,
            "p_user_id": user_id,
            "p_start_time": start_time,
            "p_end_time": end_time
        }
        response = requests.post(url_rpc, headers=HEADERS, json=payload)
        
        if response.status_code == 400 and "Invalid API key" in response.text:
            return 0
            
        if not response.text.strip():
            return 0
            
        return response.json()
    except Exception:
        return 0

def get_allowed_time(user_id, return_result=False):
    """
    ユーザのその日の視聴可能時間（users_watch_time.default_time + watch_time_log の合計）を返します。
    """
    try:
        # default_time の取得
        default_time = get_default_time(user_id)
        if default_time is None:
            result = json.dumps({"error": "User not found"}, ensure_ascii=False)
            return result if return_result else print(result)

        start, end = get_today_range_utc()
        total_added_minutes = get_total_added_minutes(user_id, start, end)
        allowed = default_time + total_added_minutes

        # 利用済み分数の取得（pc_activity_2 の minutes_time_jst を参照）
        total_usage = get_total_usage_minutes(user_id, start, end)
        if total_usage == 0 and isinstance(total_usage, str) and total_usage == "E":
            result = "E"
        else:
            result = "T" if total_usage <= allowed else "F"
    except Exception:
        result = "E"
    return result if return_result else print(result)

def insert_watch_log(user_id, added_minutes, return_result=False):
    """
    watch_time_log テーブルに added_minutes の値を挿入します。（正・負どちらも可能）
    """
    if not is_valid_uuid(user_id):
        result = f"エラー: user_id ({user_id}) は正しいUUID形式ではありません"
        return result if return_result else print(result)
    url = f"{SUPABASE_URL}/rest/v1/watch_time_log"
    data = {"user_id": user_id, "added_minutes": added_minutes}
    response = requests.post(url, json=data, headers=HEADERS)
    if response.text.strip():
        try:
            res_json = response.json()
            result = json.dumps(res_json, ensure_ascii=False)
        except requests.exceptions.JSONDecodeError:
            result = f"APIレスポンス（JSONでデコードできない）: {response.text}"
    else:
        result = "APIレスポンス: (空のレスポンス)"
    return result if return_result else print(result)

def output_result(result, output_file, output_encoding="utf-8"):
    """
    出力ファイルが指定されていればそのファイルへ指定エンコードで出力し、
    指定がなければ標準出力へ出力します。
    """
    try:
        sys.stdout.reconfigure(encoding=output_encoding)
    except Exception:
        pass

    if output_file:
        try:
            with open(output_file, "w", encoding=output_encoding) as f:
                f.write(result)
        except Exception:
            print("E")
        else:
            print(result)
    else:
        print(result)

def is_holiday_or_weekend(date=None):
    """
    指定された日付が休日（土日または祝日）かどうかを判定します。
    
    Args:
        date: 日付オブジェクト。Noneの場合は現在日時を使用。
    
    Returns:
        bool: 休日の場合はTrue、平日の場合はFalse
    """
    if date is None:
        date = datetime.now(JST).date()
    elif isinstance(date, datetime):
        date = date.date()
    
    # 土曜日(5)または日曜日(6)
    if date.weekday() >= 5:
        return True
    
    # 祝日判定（jpholidayがインストールされている場合のみ）
    if JPHOLIDAY_AVAILABLE:
        return jpholiday.is_holiday(date)
    
    # jpholidayがない場合は土日のみ休日判定
    return False

def check_morning_restriction(user_id):
    """
    平日（土日祝日以外）の午前の特別な利用制限をチェックします。
    
    戻り値:
        tuple: (制限が有効かどうか, 制限理由)
        例: (True, "平日の午前7時30分から正午までは利用できません")
        
    制限条件:
    1. 平日の午前7時30分から午前11時59分の間の利用
    2. 平日の午前1時から午前11時59分の間に21分以上の利用
    """
    now_jst = datetime.now(JST)
    
    return False, ""    # 暫定処理で、平日もOKにする
    # 休日（土日祝日）の場合は制限なし
    if is_holiday_or_weekend(now_jst):
        return False, ""
    
    current_hour = now_jst.hour
    current_minute = now_jst.minute
    
    # 午前7時30分から午前11時59分の間なら制限
    if (7 <= current_hour < 12) and (current_hour > 7 or current_minute >= 30):
        return True, "平日の午前7時30分から正午までは利用できません"
    
    # 午前1時から午前11:59の間の利用が21分以上かをチェック
    start, end = get_today_range_utc()
    morning_activity = get_morning_usage(user_id, 1, 12)
    
    if morning_activity >= 21:
        return True, "平日の午前1時から正午までの利用が21分を超えています"
    
    # どの条件にも当てはまらない場合は制限なし
    return False, ""

def get_morning_usage(user_id, start_hour, end_hour):
    """午前の特定時間帯（start_hour から end_hour まで）の利用時間を分単位で取得します。"""
    try:
        start, end = get_today_range_utc()
        activity_data = get_pc_activity_minutes_by_pc(user_id, None, start, end)
        
        # 時間帯でフィルタリング
        morning_minutes = set()
        for activity in activity_data:
            minutes_time = activity.get("minutes_time_jst", 0)
            hour = (minutes_time // 60) % 24
            if start_hour <= hour < end_hour:
                morning_minutes.add(minutes_time)
        
        return len(morning_minutes)
    except Exception:
        return 0

def get_total_added_minutes(user_id, start_time, end_time):
    """指定された期間の追加視聴時間の合計を取得します。"""
    try:
        url_rpc = f"{SUPABASE_URL}/rest/v1/rpc/get_total_watch_time"
        payload = {
            "p_api_key": USER_API_KEY,
            "target_user_id": user_id,
            "target_date": datetime.fromisoformat(start_time).astimezone(JST).date().isoformat()
        }
        response = requests.post(url_rpc, headers=HEADERS, json=payload)
        
        if response.status_code == 400 and "Invalid API key" in response.text:
            print("Error 1 at get_total_added_minutes")
            return 0
            
        if not response.text.strip():
            print('Error 2 at get_total_added_minutes')
            return 0
            
        data = response.json()
        if not data or len(data) == 0:
            print('Error 3 at get_total_added_minutes')
            return 0
            
        # get_total_watch_timeの戻り値から total_added_minutes を取得
        print(data)
        print( datetime.fromisoformat(start_time).astimezone(JST).date().isoformat())
        return data[0].get('total_added_minutes', 0)
    except Exception:
        print('Error 4')
        return 0

# 追加許可時間ログを取得 (watch_time_log テーブル)
def get_watch_time_logs(user_id, start_time, end_time):
    """
    指定期間の watch_time_log のレコードを取得します。
    返り値は JSON のリストです。
    """
    try:
        url_rpc = f"{SUPABASE_URL}/rest/v1/rpc/get_watch_time_logs"
        payload = {
            "p_user_id": user_id,
            "p_start_time": start_time,
            "p_end_time": end_time
        }
        response = requests.post(url_rpc, headers=HEADERS, json=payload)
        if response.status_code == 400 and "Invalid API key" in response.text:
            return []
        if not response.text.strip():
            return []
        return response.json()
    except Exception:
        return []

def get_default_time(user_id):
    """users_watch_time テーブルから指定されたユーザーのdefault_timeを取得します。"""
    try:
        url_rpc = f"{SUPABASE_URL}/rest/v1/rpc/get_total_watch_time"
        payload = {
            "p_api_key": USER_API_KEY,
            "target_user_id": user_id,
            "target_date": datetime.now(JST).date().isoformat()
        }
        response = requests.post(url_rpc, headers=HEADERS, json=payload)
        
        if response.status_code == 400 and "Invalid API key" in response.text:
            return None
            
        if not response.text.strip():
            return None
            
        data = response.json()
        if not data or len(data) == 0:
            return None
            
        # get_total_watch_timeの戻り値から default_time を取得
        return data[0].get('default_time', None)
    except Exception:
        return None

def check_usage(user_id, message_mode="normal", return_result=False):
    """
    全PCの利用済み分数と視聴可能時間を比較し、許容範囲内か超過かを返します。

    パラメータ:
      user_id (str): ユーザID (UUID)
      message_mode (str): メッセージ出力形式 ("normal", "hover", "giant", "fileout", "fileout_only_message")
      return_result (bool): 結果を返す場合は True、標準出力の場合は False

    戻り値:
      JSON文字列（または print 出力）
      例:
        {
           "success": True,
           "total_usage_minutes": 300,
           "allowed_watch_time_minutes": 480,
           "status": "within allowed",
           "message_jp": "利用時間は許容範囲内です。あと 180 分の視聴が可能です。"
        }
    """
    try:
        # default_time の取得
        default_time = get_default_time(user_id)
        if default_time is None:
            result = json.dumps({"error": "User not found"}, ensure_ascii=False)
            return result if return_result else print(result)

        # 平日の午前の特別な制限をチェック
        morning_restriction_active, morning_restriction_reason = check_morning_restriction(user_id)

        # 当日のUTC範囲（JSTの日付に対応）を取得
        start, end = get_today_range_utc()
        total_added_minutes = get_total_added_minutes(user_id, start, end)
        allowed_time = default_time + total_added_minutes

        # 利用済み分数の取得
        total_usage = get_total_usage_minutes(user_id, start, end)

        # 超過分数の計算
        if total_usage > allowed_time:
            excess_minutes = total_usage - allowed_time
            # 超過分を減算
            insert_watch_log(user_id, -excess_minutes, return_result=False)

        difference = allowed_time - total_usage  # 正の値: 残り分数, 負の値: 超過分数

        # 特別な時間帯制限がある場合は強制的に超過状態にする
        if morning_restriction_active:
            status = "exceeded allowed"
        else:
            status = "within allowed" if total_usage <= allowed_time else "exceeded allowed"

        # message_mode に応じた日本語メッセージの生成
        if message_mode == "normal":
            if morning_restriction_active:
                message_jp = f"{morning_restriction_reason}"
            elif total_usage <= allowed_time:
                message_jp = f"利用時間は許容範囲内です。あと {difference} 分の視聴が可能です。"
            else:
                message_jp = f"利用時間が視聴可能時間を {-difference} 分超過しています。"
        elif message_mode == "hover":
            if morning_restriction_active:
                message_jp = f"制限中: {morning_restriction_reason}"
            elif total_usage <= allowed_time:
                message_jp = f"許容内 ({difference})"
            else:
                message_jp = f"超過 ({-difference})"
        elif message_mode == "giant":
            if morning_restriction_active:
                message_jp = f"警告！{morning_restriction_reason}！"
            elif total_usage <= allowed_time:
                message_jp = f"視聴可能：残り {difference} 分。"
            else:
                message_jp = f"警告！利用時間が {-difference} 分超過中です！"
        elif message_mode in ["fileout", "fileout_only_message"]:
            if morning_restriction_active:
                message_jp = f"{morning_restriction_reason}"
            elif total_usage <= allowed_time:
                message_jp = f"利用時間は許容範囲内です。あと {difference} 分の視聴が可能です。"
            else:
                message_jp = f"利用時間が視聴可能時間を {-difference} 分超過しています。"
        else:
            if morning_restriction_active:
                message_jp = f"{morning_restriction_reason}"
            elif total_usage <= allowed_time:
                message_jp = f"利用時間は許容範囲内です。あと {difference} 分の視聴が可能です。"
            else:
                message_jp = f"利用時間が視聴可能時間を {-difference} 分超過しています。"

        # === 追加許可時間情報を付加 ===
        logs = get_watch_time_logs(user_id, start, end)
        added_logs = [log for log in logs if log.get("added_minutes", 0) > 0]
        total_added_detail = sum(log.get("added_minutes", 0) for log in added_logs)
        if total_added_detail > 0:
            if message_mode == "hover":
                # 1行で合計のみ追加
                message_jp += f" / 追加 {total_added_detail}分"
            elif message_mode == "giant":
                # Giant 表示は縦並びレイアウト
                # 1行目: 超過または残り時間
                diff_line = (
                    f"残り {difference} 分" if difference >= 0 else f"超過 {-difference} 分"
                )
                lines = [diff_line, "", f"総追加 {total_added_detail} 分", ""]
                # 各ログを時刻+追加分数で縦並び
                for log in added_logs:
                    ts = log.get("created_at_jst") or log.get("created_at") or ""
                    try:
                        ts_dt = datetime.fromisoformat(ts)
                        if ts_dt.tzinfo is None:
                            ts_dt = ts_dt.replace(tzinfo=JST)
                        ts_dt = ts_dt.astimezone(JST)
                        ts_str = ts_dt.strftime("%H:%M")
                    except Exception:
                        ts_str = ""
                    lines.append(f"{ts_str} +{log.get('added_minutes',0)}分")
                message_jp = "\n".join(lines)
            elif message_mode in ["fileout", "fileout_only_message"]:
                message_jp += f" (追加 {total_added_detail}分)"

        res = {
            "success": True,
            "total_usage_minutes": total_usage,
            "allowed_watch_time_minutes": allowed_time,
            "status": status,
            "message_jp": message_jp
        }
        result = json.dumps(res, ensure_ascii=False)
    except Exception:
        result = "E"
    return result if return_result else print(result)

def is_able_watch(user_id, return_result=False):
    """
    全PCの実際利用分数とその日の設定視聴可能総分数（default_time + watch_time_logの合算）との差分を取得し、
    視聴可能なら 'T'（実利用が設定内）、超過なら 'F'、エラー発生時は 'E' を返します。
    """
    try:
        # 平日の午前の特別な制限をチェック
        is_restricted, _ = check_morning_restriction(user_id)
        if is_restricted:
            result = "F"
            return result if return_result else print(result)

        # JST の当日の日付 (YYYY-MM-DD形式) を取得
        now_jst = datetime.now(JST)
        target_date = now_jst.strftime("%Y-%m-%d")

        # Supabase RPC 呼び出し URL (analyze_time_difference を利用)
        url_rpc = f"{SUPABASE_URL}/rest/v1/rpc/analyze_time_difference"
        payload = {
            "p_api_key": USER_API_KEY,
            "target_user_id": user_id,
            "target_date": target_date
        }
        response = requests.post(url_rpc, headers=HEADERS, json=payload)
        
        # エラーレスポンスのチェック
        if response.status_code == 400 and "Invalid API key" in response.text:
            result = "E"
            return result if return_result else print(result)
            
        data = response.json() if response.text.strip() else None

        if not data or len(data) == 0 or "time_difference" not in data[0]:
            result = "E"
            return result if return_result else print(result)
        
        row = data[0]
        time_difference = row["time_difference"]
        
        result = "T" if time_difference <= 0 else "F"
    except Exception as e:
        print(f"Error: {str(e)}")  # デバッグ用
        result = "E"
    return result if return_result else print(result)

def main():
    # .envファイルから設定値を読み込む
    default_user_id = os.getenv("user_id")
    default_pc_id = os.getenv("pc_id")
    default_api_key = os.getenv("user_id_ApiKey")
    
    # グローバルオプション用の親パーサー
    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument(
        "--api-key",
        help="ユーザーのAPI key（省略時は環境変数 USER_API_KEY または user_id_ApiKey を使用）"
    )
    parent_parser.add_argument(
        "--user-id",
        help="ユーザID (UUID)（省略時は環境変数 user_id を使用）"
    )
    parent_parser.add_argument(
        "--pc-id",
        help="PC ID (UUID)（省略時は環境変数 pc_id を使用）"
    )
    
    # メインパーサーの設定
    parser = argparse.ArgumentParser(
        description=(
            "Screen Time Management CLI\n\n"
            "このスクリプトは、PCのアクティビティログ、視聴時間ログの管理および利用状況の照会機能を提供します。\n"
            "各コマンドは必須パラメータとして user_id（および pc_id/pc_name や added_minutes 等）を受け取り、\n"
            "オプションで --output (-o) を指定すると、結果を指定されたファイルに出力します。\n"
            "エラー発生時は 'E'、視聴可能なら 'T'、超過していれば 'F' などの結果を返します。"
        ),
        formatter_class=argparse.RawTextHelpFormatter,
        parents=[parent_parser]
    )
    
    subparsers = parser.add_subparsers(title="コマンド", dest="command", required=True)
    
    # 各サブコマンドの設定（必要なオプションはそのまま）
    parser_log_pc = subparsers.add_parser(
        "log-pc-activity",
        help="指定したユーザとPC (UUIDまたはpc_name) を用いて、現在時刻を記録します。",
        parents=[parent_parser]
    )
    parser_log_pc.add_argument(
        "user_id",
        nargs="?",
        default=None,
        help="ユーザID (UUID)（省略時は --user-id オプションまたは環境変数 user_id を使用）"
    )
    parser_log_pc.add_argument(
        "pc_identifier",
        nargs="?",
        default=None,
        help="PC ID (UUID) もしくは user_pcs の pc_name（省略時は --pc-id オプションまたは環境変数 pc_id を使用）"
    )
    parser_log_pc.add_argument("--output", "-o", help="結果出力先ファイル (省略時は標準出力)")
    
    parser_check_watch = subparsers.add_parser(
        "check-watch-time",
        help="ユーザの残り視聴可能時間を取得します。\n(ユーザの default_time + watch_time_log の合計 - 全PCの利用済み分数)",
        parents=[parent_parser]
    )
    parser_check_watch.add_argument(
        "user_id",
        nargs="?",
        default=None,
        help="ユーザID (UUID)（省略時は --user-id オプションまたは環境変数 user_id を使用）"
    )
    parser_check_watch.add_argument("--output", "-o", help="結果出力先ファイル (省略時は標準出力)")
    
    parser_total_usage = subparsers.add_parser(
        "get-total-usage",
        help="当日の全PCでの利用済み分数（重複は1分として）と利用時刻 (HH:MM形式) を取得します。",
        parents=[parent_parser]
    )
    parser_total_usage.add_argument(
        "user_id",
        nargs="?",
        default=None,
        help="ユーザID (UUID)（省略時は --user-id オプションまたは環境変数 user_id を使用）"
    )
    parser_total_usage.add_argument("--output", "-o", help="結果出力先ファイル (省略時は標準出力)")
    
    parser_pc_usage = subparsers.add_parser(
        "get-pc-usage",
        help="指定したPC (UUIDまたはpc_name) の利用済み分数（重複は1分として）と利用時刻 (HH:MM形式) を取得します。",
        parents=[parent_parser]
    )
    parser_pc_usage.add_argument("user_id", help="ユーザID (UUID)")
    parser_pc_usage.add_argument("pc_identifier", help="PC ID (UUID) もしくは user_pcs の pc_name")
    parser_pc_usage.add_argument("--output", "-o", help="結果出力先ファイル (省略時は標準出力)")
    
    parser_allowed_time = subparsers.add_parser(
        "get-allowed-time",
        help="その日の視聴可能時間 (default_time + watch_time_log の合計) を取得します。",
        parents=[parent_parser]
    )
    parser_allowed_time.add_argument("user_id", help="ユーザID (UUID)")
    parser_allowed_time.add_argument("--output", "-o", help="結果出力先ファイル (省略時は標準出力)")
    
    parser_check_usage = subparsers.add_parser(
        "check-usage",
        help="全PCの利用済み分数と視聴可能時間を比較し、範囲内か超過かを返します。",
        parents=[parent_parser]
    )
    parser_check_usage.add_argument(
        "user_id",
        nargs="?",
        default=None,
        help="ユーザID (UUID)（省略時は --user-id オプションまたは環境変数 user_id を使用）"
    )
    parser_check_usage.add_argument(
        "--message-mode",
        choices=["normal", "hover", "giant", "fileout", "fileout_only_message"],
        default="normal",
        help=(
            "日本語メッセージの出力形式を指定します。\n"
            " normal: 従来どおり\n"
            " hover:  AHK用のマウスホバー表示に最適化された短いメッセージ\n"
            " giant:  超過時に大きな警告を出す想定のメッセージ\n"
            " fileout: 3ファイル出力 (_hover, _giant, _normal)\n"
            " fileout_only_message: 3ファイル出力（ただし message_jp のみを書き込み）\n"
            "  -o が無い場合は CSV 形式で3種をまとめて出力"
        )
    )
    parser_check_usage.add_argument(
        "--encoding",
        choices=["cp932", "sjis"],
        default=None,
        help="出力時のエンコードを指定します（cp932 または sjis）。省略時は utf-8。"
    )
    parser_check_usage.add_argument("--output", "-o", help="結果出力先ファイル (省略時は標準出力)")
    
    parser_is_able = subparsers.add_parser(
        "is-able-watch",
        help=(
            "全PCの実際利用分数とその日の設定視聴可能総分数（default_time + watch_time_logの合算）との差分を取得し、\n"
            "視聴可能なら 'T'（実利用が設定内）、超過なら 'F'、エラー発生時は 'E' を返します。"
        ),
        parents=[parent_parser]
    )
    parser_is_able.add_argument(
        "user_id",
        nargs="?",
        default=None,
        help="ユーザID (UUID)（省略時は --user-id オプションまたは環境変数 user_id を使用）"
    )
    parser_is_able.add_argument("--output", "-o", help="結果出力先ファイル (省略時は標準出力)")
    
    parser_insert_watch = subparsers.add_parser(
        "insert-watch-log",
        help="watch_time_log テーブルに added_minutes の値を挿入します。（正・負どちらも可能）",
        parents=[parent_parser]
    )
    parser_insert_watch.add_argument("user_id", help="ユーザID (UUID)")
    parser_insert_watch.add_argument("added_minutes", type=int, help="追加する分数（マイナス値も可）")
    parser_insert_watch.add_argument("--output", "-o", help="結果出力先ファイル (省略時は標準出力)")
    
    args = parser.parse_args()
    
    # API keyの設定（コマンドライン > 環境変数の順）
    global api_key
    api_key = args.api_key or USER_API_KEY or default_api_key
    if not api_key:
        print("エラー: API keyが指定されていません。--api-key オプションまたは環境変数 USER_API_KEY/user_id_ApiKey を設定してください。")
        sys.exit(1)
    
    # 各コマンドごとの引数取得（重複処理を削除）
    if args.command == "log-pc-activity":
        user_id = args.user_id or default_user_id
        pc_identifier = args.pc_identifier or args.pc_id or default_pc_id
        if not user_id:
            print("エラー: user_idが指定されていません。コマンドライン引数、--user-id オプション、または環境変数 user_id を設定してください。")
            sys.exit(1)
        if not pc_identifier:
            print("エラー: PC IDが指定されていません。コマンドライン引数、--pc-id オプション、または環境変数 pc_id を設定してください。")
            sys.exit(1)
        result = log_pc_activity(user_id, pc_identifier, return_result=True)
        output_result(result, args.output)
    
    elif args.command == "check-watch-time":
        user_id = args.user_id or default_user_id
        if not user_id:
            print("エラー: user_idが指定されていません。コマンドライン引数、--user-id オプション、または環境変数 user_id を設定してください。")
            sys.exit(1)
        result = get_allowed_time(user_id, return_result=True)
        output_result(result, args.output)
    
    elif args.command == "get-total-usage":
        user_id = args.user_id or default_user_id
        if not user_id:
            print("エラー: user_idが指定されていません。コマンドライン引数、--user-id オプション、または環境変数 user_id を設定してください。")
            sys.exit(1)
        start, end = get_today_range_utc()
        result = str(get_total_usage_minutes(user_id, start, end))
        output_result(result, args.output)
    
    elif args.command == "get-pc-usage":
        # user_idとpc_identifierは必須位置引数として受け取る
        result = get_pc_usage(args.user_id, args.pc_identifier, return_result=True)
        output_result(result, args.output)
    
    elif args.command == "get-allowed-time":
        user_id = args.user_id or default_user_id
        if not user_id:
            print("エラー: user_idが指定されていません。コマンドライン引数、--user-id オプション、または環境変数 user_id を設定してください。")
            sys.exit(1)
        result = get_allowed_time(user_id, return_result=True)
        output_result(result, args.output)
    
    elif args.command == "check-usage":
        user_id = args.user_id or default_user_id
        if not user_id:
            print("エラー: user_idが指定されていません。コマンドライン引数、--user-id オプション、または環境変数 user_id を設定してください。")
            sys.exit(1)
        msg_mode = args.message_mode
        out_enc = args.encoding or "utf-8"
    
        if msg_mode in ["fileout", "fileout_only_message"]:
            if args.output:
                for mode in ["hover", "giant", "normal"]:
                    res = check_usage(user_id, message_mode=mode, return_result=True)
                    out_filename = f"{args.output}_{mode}"
                    try:
                        with open(out_filename, "w", encoding=out_enc) as f:
                            # fileout_only_messageの場合はmessage_jpのみ書き出す
                            if msg_mode == "fileout_only_message":
                                data = json.loads(res)
                                f.write(data.get("message_jp", "E"))
                            else:
                                f.write(res)
                        print(f"Output to {out_filename}:")
                        print(res)
                        print("-----")
                    except Exception:
                        print("E")
            else:
                header = "mode,success,total_usage_minutes,allowed_watch_time_minutes,status,message_jp"
                print(header)
                for mode in ["hover", "giant", "normal"]:
                    res = check_usage(user_id, message_mode=mode, return_result=True)
                    try:
                        data = json.loads(res)
                        line = (
                            f"{mode},{data.get('success', '')},"
                            f"{data.get('total_usage_minutes', '')},"
                            f"{data.get('allowed_watch_time_minutes', '')},"
                            f"{data.get('status', '')},{data.get('message_jp', '')}"
                        )
                    except Exception:
                        line = f"{mode},E,,,," 
                    print(line)
    
        else:
            result = check_usage(user_id, message_mode=msg_mode, return_result=True)
            output_result(result, args.output, out_enc)
    
    elif args.command == "is-able-watch":
        user_id = args.user_id or default_user_id
        if not user_id:
            print("エラー: user_idが指定されていません。コマンドライン引数、--user-id オプション、または環境変数 user_id を設定してください。")
            sys.exit(1)
        result = is_able_watch(user_id, return_result=True)
        output_result(result, args.output)
    
    elif args.command == "insert-watch-log":
        result = insert_watch_log(args.user_id, args.added_minutes, return_result=True)
        output_result(result, args.output)

if __name__ == "__main__":
    main()
