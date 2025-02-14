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

# .envファイルから環境変数をロード
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_API_KEY = os.getenv("SUPABASE_API_KEY")

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
    # UUID 形式の場合はそのまま返す
    if is_valid_uuid(pc_identifier):
        return pc_identifier

    # pc_name で user_pcs を検索
    url = (
        f"{SUPABASE_URL}/rest/v1/user_pcs"
        f"?user_id=eq.{user_id}&pc_name=eq.{pc_identifier}&select=pc_id"
    )
    response = requests.get(url, headers=HEADERS)
    if not response.text.strip():
        return None

    data = response.json()
    if not data:
        return None

    # pc_name が一意である前提で先頭を返す
    return data[0]["pc_id"]

def get_pc_name_from_pc_id(user_id, pc_id):
    """
    user_pcs から pc_id に対応する pc_name を取得して返す。
    該当がなければ None を返す。
    """
    url = (
        f"{SUPABASE_URL}/rest/v1/user_pcs"
        f"?user_id=eq.{user_id}&pc_id=eq.{pc_id}&select=pc_name"
    )
    response = requests.get(url, headers=HEADERS)
    if not response.text.strip():
        return None
    data = response.json()
    if not data:
        return None
    return data[0]["pc_name"]

def check_user_exists(user_id):
    """users_watch_time テーブルに指定された user_id が存在するか確認します。"""
    url = f"{SUPABASE_URL}/rest/v1/users_watch_time?user_id=eq.{user_id}&select=user_id"
    response = requests.get(url, headers=HEADERS)
    return bool(response.text.strip() and response.json())

def get_activity_time():
    """
    現在時刻を JST (日本標準時) で取得し、
    その日の 0:00 (JST) からの経過分数を返します。
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

def log_pc_activity(user_id, pc_identifier, return_result=False):
    """
    PCアクティビティを記録します。
    pc_identifier は UUID もしくは pc_name を受け取り、
    対応する pc_id を取得した上で pc_activity に登録します。
    """
    # user_id が正しいかチェック
    if not is_valid_uuid(user_id):
        result = f"エラー: user_id ({user_id}) は正しいUUID形式ではありません"
        return result if return_result else print(result)

    # user が存在するかチェック
    if not check_user_exists(user_id):
        result = f"エラー: user_id ({user_id}) は users_watch_time に存在しません"
        return result if return_result else print(result)

    # pc_identifier が UUID でなければ pc_name とみなして pc_id を検索
    pc_id = get_pc_id_from_user(user_id, pc_identifier)
    if not pc_id:
        result = (
            f"エラー: 指定されたPC (\"{pc_identifier}\") が見つかりません。"
            "UUID または既存の pc_name を指定してください。"
        )
        return result if return_result else print(result)

    # PCアクティビティを記録
    activity_time = get_activity_time()
    url = f"{SUPABASE_URL}/rest/v1/pc_activity"
    data = {"user_id": user_id, "pc_id": pc_id, "activity_time": activity_time}
    print(data)
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

def check_watch_time(user_id, return_result=False):
    """
    ユーザの残り視聴可能時間を取得します。
    （users_watch_time.default_time + watch_time_log の合計 - 当日全PCの利用済み分数（重複は1分として））
    """
    try:
        url_watch_time = f"{SUPABASE_URL}/rest/v1/users_watch_time?user_id=eq.{user_id}&select=default_time"
        response = requests.get(url_watch_time, headers=HEADERS)
        watch_data = response.json() if response.text.strip() else []
        if not watch_data:
            result = json.dumps({"error": "User not found"}, ensure_ascii=False)
            return result if return_result else print(result)
        default_time = watch_data[0]["default_time"]

        # 今日のUTC範囲（JSTの日付に対応）を取得して、watch_time_log をフィルタリングします。
        start, end = get_today_range_utc()
        start_enc = urllib.parse.quote(start, safe="")
        end_enc = urllib.parse.quote(end, safe="")
        url_watch_log = (
            f"{SUPABASE_URL}/rest/v1/watch_time_log?user_id=eq.{user_id}"
            f"&created_at=gte.{start_enc}&created_at=lt.{end_enc}"
            f"&select=added_minutes"
        )
        response = requests.get(url_watch_log, headers=HEADERS)
        log_data = response.json() if response.text.strip() else []
        total_added_minutes = sum(log["added_minutes"] for log in log_data)
        total_allowed = default_time + total_added_minutes

        start, end = get_today_range_utc()
        start_enc = urllib.parse.quote(start, safe="")
        end_enc = urllib.parse.quote(end, safe="")
        url_activity = (
            f"{SUPABASE_URL}/rest/v1/pc_activity?user_id=eq.{user_id}"
            f"&created_at=gte.{start_enc}&created_at=lt.{end_enc}&select=activity_time"
        )
        response = requests.get(url_activity, headers=HEADERS)
        activity_data = response.json() if response.text.strip() else []
        unique_minutes_used = len({row["activity_time"] for row in activity_data})
        remaining = total_allowed - unique_minutes_used

        res = {
            "success": True,
            "allowed_watch_time_minutes": total_allowed,
            "used_minutes": unique_minutes_used,
            "remaining_minutes": remaining,
            "has_time": remaining > 0
        }
        result = json.dumps(res, ensure_ascii=False)
    except Exception:
        result = "E"
    return result if return_result else print(result)

def get_total_usage(user_id, return_result=False):
    """
    当日の全PCでの利用済み分数（重複は1分として）と、その分数を HH:MM 形式（例："01:15"）のリストで返します。
    """
    try:
        start, end = get_today_range_utc()
        start_enc = urllib.parse.quote(start, safe="")
        end_enc = urllib.parse.quote(end, safe="")
        url = f"{SUPABASE_URL}/rest/v1/pc_activity?user_id=eq.{user_id}" \
              f"&created_at=gte.{start_enc}&created_at=lt.{end_enc}&select=activity_time"
        response = requests.get(url, headers=HEADERS)
        data = response.json() if response.text.strip() else []
        unique_minutes = {row["activity_time"] for row in data}
        total_usage = len(unique_minutes)
        usage_times = [f"{m // 60:02d}:{m % 60:02d}" for m in sorted(unique_minutes)]
        res = {
            "success": True,
            "total_usage_minutes": total_usage,
            "usage_times": usage_times
        }
        result = json.dumps(res, ensure_ascii=False)
    except Exception:
        result = "E"
    return result if return_result else print(result)

def get_pc_usage(user_id, pc_identifier, return_result=False):
    """
    指定PCの当日の利用済み分数（重複は1分として）と、利用時刻（HH:MM形式）のリストを返します。
    pc_identifier は UUID もしくは pc_name を受け取り、最終的に対応する pc_id を使って検索します。
    結果に pc_name も含めて返します。
    """
    try:
        # pc_identifier が UUID 形式でなければ pc_name とみなして pc_id を取得
        pc_id = get_pc_id_from_user(user_id, pc_identifier)
        if not pc_id:
            result = json.dumps({
                "error": f"指定されたPC (\"{pc_identifier}\") が見つかりません。"
            }, ensure_ascii=False)
            return result if return_result else print(result)

        # 逆に pc_id から pc_name を取得
        pc_name = get_pc_name_from_pc_id(user_id, pc_id) or pc_id

        start, end = get_today_range_utc()
        start_enc = urllib.parse.quote(start, safe="")
        end_enc = urllib.parse.quote(end, safe="")
        url = f"{SUPABASE_URL}/rest/v1/pc_activity?user_id=eq.{user_id}&pc_id=eq.{pc_id}" \
              f"&created_at=gte.{start_enc}&created_at=lt.{end_enc}&select=activity_time"
        response = requests.get(url, headers=HEADERS)
        data = response.json() if response.text.strip() else []
        unique_minutes = {row["activity_time"] for row in data}
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

def get_allowed_time(user_id, return_result=False):
    """
    ユーザのその日の視聴可能時間（users_watch_time.default_time + watch_time_log の合計）を返します。
    """
    try:
        url_watch_time = f"{SUPABASE_URL}/rest/v1/users_watch_time?user_id=eq.{user_id}&select=default_time"
        response = requests.get(url_watch_time, headers=HEADERS)
        watch_data = response.json() if response.text.strip() else []
        if not watch_data:
            result = json.dumps({"error": "User not found"}, ensure_ascii=False)
            return result if return_result else print(result)
        default_time = watch_data[0]["default_time"]

        # 今日のUTC範囲でwatch_time_logをフィルタリング
        start, end = get_today_range_utc()
        start_enc = urllib.parse.quote(start, safe="")
        end_enc = urllib.parse.quote(end, safe="")
        url_watch_log = (
            f"{SUPABASE_URL}/rest/v1/watch_time_log?user_id=eq.{user_id}"
            f"&created_at=gte.{start_enc}&created_at=lt.{end_enc}"
            f"&select=added_minutes"
        )
        response = requests.get(url_watch_log, headers=HEADERS)
        log_data = response.json() if response.text.strip() else []
        total_added = sum(log["added_minutes"] for log in log_data)
        allowed = default_time + total_added
        res = {"success": True, "allowed_watch_time_minutes": allowed}
        result = json.dumps(res, ensure_ascii=False)
    except Exception:
        result = "E"
    return result if return_result else print(result)

def check_usage(user_id, message_mode="normal", return_result=False):
    """
    当日全PCでの利用済み分数（重複は1分として）と視聴可能時間を比較し、
    範囲内か超過かを "within allowed" or "exceeded allowed" として返します。

    :param message_mode:
        - "normal": 従来通りのJSON (英語ステータス) のみ
        - "hover":  AHKマウスホバー表示用に、日本語メッセージを追加
        - "giant":  時間超過時の大きな警告ウィンドウ向けに、日本語メッセージを追加
        - "fileout": 3ファイル出力用（内部的には JSON を返します）
        - "fileout_only_message": message_jp のみを書き込み想定
    """
    try:
        start, end = get_today_range_utc()
        start_enc = urllib.parse.quote(start, safe="")
        end_enc = urllib.parse.quote(end, safe="")
        url = f"{SUPABASE_URL}/rest/v1/pc_activity?user_id=eq.{user_id}" \
              f"&created_at=gte.{start_enc}&created_at=lt.{end_enc}&select=activity_time"
        response = requests.get(url, headers=HEADERS)
        data = response.json() if response.text.strip() else []
        unique_minutes = {row["activity_time"] for row in data}
        total_usage = len(unique_minutes)

        url_watch_time = f"{SUPABASE_URL}/rest/v1/users_watch_time?user_id=eq.{user_id}&select=default_time"
        response_w = requests.get(url_watch_time, headers=HEADERS)
        watch_data = response_w.json() if response_w.text.strip() else []
        if not watch_data:
            result = json.dumps({"error": "User not found"}, ensure_ascii=False)
            return result if return_result else print(result)
        default_time = watch_data[0]["default_time"]

        # 今日のUTC範囲でwatch_time_logをフィルタリング
        start, end = get_today_range_utc()
        start_enc = urllib.parse.quote(start, safe="")
        end_enc = urllib.parse.quote(end, safe="")
        url_watch_log = (
            f"{SUPABASE_URL}/rest/v1/watch_time_log?user_id=eq.{user_id}"
            f"&created_at=gte.{start_enc}&created_at=lt.{end_enc}"
            f"&select=added_minutes"
        )
        response_log = requests.get(url_watch_log, headers=HEADERS)
        log_data = response_log.json() if response_log.text.strip() else []
        total_added = sum(log["added_minutes"] for log in log_data)
        allowed = default_time + total_added
        status = "within allowed" if total_usage <= allowed else "exceeded allowed"

        res = {
            "success": True,
            "total_usage_minutes": total_usage,
            "allowed_watch_time_minutes": allowed,
            "status": status
        }

        if message_mode in ["hover", "giant"]:
            if status == "within allowed":
                remain = allowed - total_usage  # 残り分数
                if message_mode == "hover":
                    msg_jp = f"あと {remain} 分視聴可能です。"
                else:
                    msg_jp = (
                        f"現在 {total_usage} 分使用中、視聴可能時間は合計 {allowed} 分です。\n"
                        f"まだ {remain} 分余裕があります。"
                    )
            else:
                exceed = total_usage - allowed  # 超過分数
                if message_mode == "hover":
                    msg_jp = f"視聴時間を {exceed} 分 超過しています。"
                else:
                    msg_jp = (
                        f"あなたの視聴時間は {total_usage} 分で、許容 {allowed} 分を {exceed} 分超えています。\n"
                        "至急、視聴を止めてください！"
                    )
            res["message_jp"] = msg_jp
        elif message_mode in ["fileout", "fileout_only_message"]:
            res["message_jp"] = res.get("message_jp", "")

        result = json.dumps(res, ensure_ascii=False)
    except Exception:
        result = "E"
    return result if return_result else print(result)

def is_able_watch(user_id, return_result=False):
    """
    当日全PCでの利用済み分数とその日の視聴可能時間を比較し、
    視聴可能なら 'T'、超過なら 'F'、エラー時は 'E' を返します。
    """
    try:
        url_watch_time = f"{SUPABASE_URL}/rest/v1/users_watch_time?user_id=eq.{user_id}&select=default_time"
        resp_watch = requests.get(url_watch_time, headers=HEADERS)
        if resp_watch.status_code != 200:
            result = "E"
        else:
            watch_data = resp_watch.json() if resp_watch.text.strip() else []
            if not watch_data:
                result = "E"
            else:
                default_time = watch_data[0]["default_time"]
                # 今日のUTC範囲でwatch_time_logをフィルタリング
                start, end = get_today_range_utc()
                start_enc = urllib.parse.quote(start, safe="")
                end_enc = urllib.parse.quote(end, safe="")
                url_watch_log = (
                    f"{SUPABASE_URL}/rest/v1/watch_time_log?user_id=eq.{user_id}"
                    f"&created_at=gte.{start_enc}&created_at=lt.{end_enc}"
                    f"&select=added_minutes"
                )
                resp_log = requests.get(url_watch_log, headers=HEADERS)
                if resp_log.status_code != 200:
                    result = "E"
                else:
                    log_data = resp_log.json() if resp_log.text.strip() else []
                    total_added = sum(item["added_minutes"] for item in log_data)
                    allowed = default_time + total_added

                    start, end = get_today_range_utc()
                    start_enc = urllib.parse.quote(start, safe="")
                    end_enc = urllib.parse.quote(end, safe="")
                    url_activity = (
                        f"{SUPABASE_URL}/rest/v1/pc_activity?user_id=eq.{user_id}"
                        f"&created_at=gte.{start_enc}&created_at=lt.{end_enc}&select=activity_time"
                    )
                    resp_activity = requests.get(url_activity, headers=HEADERS)
                    if resp_activity.status_code != 200:
                        result = "E"
                    else:
                        activity_data = resp_activity.json() if resp_activity.text.strip() else []
                        total_usage = len({row["activity_time"] for row in activity_data})
                        result = "T" if total_usage <= allowed else "F"
    except Exception:
        result = "E"
    return result if return_result else print(result)

def insert_watch_log(user_id, added_minutes, return_result=False):
    """
    watch_time_log テーブルに added_minutes の値を挿入します。（マイナスの値も可能）
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
    # 標準出力の文字コードを変更（Python 3.7+）
    # WindowsコンソールでCP932を使う場合などのための対策。
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

def main():
    parser = argparse.ArgumentParser(
        description=(
            "Screen Time Management CLI\n\n"
            "このスクリプトは、PCのアクティビティログ、視聴時間ログの管理および利用状況の照会機能を提供します。\n"
            "各コマンドは必須パラメータとして user_id（および pc_id/pc_name や added_minutes 等）を受け取り、\n"
            "オプションで --output (-o) を指定すると、結果を指定されたファイルに出力します。\n"
            "エラー発生時は 'E'、視聴可能なら 'T'、超過していれば 'F' などの結果を返します。"
        ),
        formatter_class=argparse.RawTextHelpFormatter
    )
    subparsers = parser.add_subparsers(title="コマンド", dest="command", required=True)

    # log-pc-activity コマンド
    parser_log_pc = subparsers.add_parser(
        "log-pc-activity",
        help="指定したユーザとPC (UUIDまたはpc_name) を用いて、現在時刻を記録します。"
    )
    parser_log_pc.add_argument("user_id", help="ユーザID (UUID)")
    parser_log_pc.add_argument(
        "pc_identifier",
        help="PC ID (UUID) もしくは user_pcs の pc_name"
    )
    parser_log_pc.add_argument("--output", "-o", help="結果出力先ファイル (省略時は標準出力)")

    # check-watch-time コマンド
    parser_check_watch = subparsers.add_parser(
        "check-watch-time",
        help="ユーザの残り視聴可能時間を取得します。\n(ユーザの default_time + watch_time_log の合計 - 全PCの利用済み分数)"
    )
    parser_check_watch.add_argument("user_id", help="ユーザID (UUID)")
    parser_check_watch.add_argument("--output", "-o", help="結果出力先ファイル (省略時は標準出力)")

    # get-total-usage コマンド
    parser_total_usage = subparsers.add_parser(
        "get-total-usage",
        help="当日の全PCでの利用済み分数（重複は1分として）と利用時刻 (HH:MM形式) を取得します。"
    )
    parser_total_usage.add_argument("user_id", help="ユーザID (UUID)")
    parser_total_usage.add_argument("--output", "-o", help="結果出力先ファイル (省略時は標準出力)")

    # get-pc-usage コマンド
    parser_pc_usage = subparsers.add_parser(
        "get-pc-usage",
        help="指定したPC (UUIDまたはpc_name) の利用済み分数（重複は1分として）と利用時刻 (HH:MM形式) を取得します。"
    )
    parser_pc_usage.add_argument("user_id", help="ユーザID (UUID)")
    parser_pc_usage.add_argument(
        "pc_identifier",
        help="PC ID (UUID) もしくは user_pcs の pc_name"
    )
    parser_pc_usage.add_argument("--output", "-o", help="結果出力先ファイル (省略時は標準出力)")

    # get-allowed-time コマンド
    parser_allowed_time = subparsers.add_parser(
        "get-allowed-time",
        help="その日の視聴可能時間 (default_time + watch_time_log の合計) を取得します。"
    )
    parser_allowed_time.add_argument("user_id", help="ユーザID (UUID)")
    parser_allowed_time.add_argument("--output", "-o", help="結果出力先ファイル (省略時は標準出力)")

    # check-usage コマンド
    parser_check_usage = subparsers.add_parser(
        "check-usage",
        help="全PCの利用済み分数と視聴可能時間を比較し、範囲内か超過かを返します。"
    )
    parser_check_usage.add_argument("user_id", help="ユーザID (UUID)")
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
    # ここでエンコード指定を追加
    parser_check_usage.add_argument(
        "--encoding",
        choices=["cp932", "sjis"],
        default=None,
        help="出力時のエンコードを指定します（cp932 または sjis）。省略時は utf-8。"
    )
    parser_check_usage.add_argument("--output", "-o", help="結果出力先ファイル (省略時は標準出力)")

    # is-able-watch コマンド
    parser_is_able = subparsers.add_parser(
        "is-able-watch",
        help=(
            "全PCの利用済み分数とその日の視聴可能時間を比較し、\n"
            "視聴可能なら 'T'、超過していれば 'F'、エラー時は 'E' を返します。"
        )
    )
    parser_is_able.add_argument("user_id", help="ユーザID (UUID)")
    parser_is_able.add_argument("--output", "-o", help="結果出力先ファイル (省略時は標準出力)")

    # insert-watch-log コマンド
    parser_insert_watch = subparsers.add_parser(
        "insert-watch-log",
        help="watch_time_log テーブルに added_minutes の値を挿入します。（正・負どちらも可能）"
    )
    parser_insert_watch.add_argument("user_id", help="ユーザID (UUID)")
    parser_insert_watch.add_argument("added_minutes", type=int, help="追加する分数（マイナス値も可）")
    parser_insert_watch.add_argument("--output", "-o", help="結果出力先ファイル (省略時は標準出力)")

    args = parser.parse_args()

    if args.command == "log-pc-activity":
        result = log_pc_activity(args.user_id, args.pc_identifier, return_result=True)
        output_result(result, args.output)

    elif args.command == "check-watch-time":
        result = check_watch_time(args.user_id, return_result=True)
        output_result(result, args.output)

    elif args.command == "get-total-usage":
        result = get_total_usage(args.user_id, return_result=True)
        output_result(result, args.output)

    elif args.command == "get-pc-usage":
        result = get_pc_usage(args.user_id, args.pc_identifier, return_result=True)
        output_result(result, args.output)

    elif args.command == "get-allowed-time":
        result = get_allowed_time(args.user_id, return_result=True)
        output_result(result, args.output)

    elif args.command == "check-usage":
        msg_mode = args.message_mode
        user_id = args.user_id
        # エンコード設定（指定が無ければ utf-8）
        out_enc = args.encoding or "utf-8"

        if msg_mode == "fileout":
            if args.output:
                for mode in ["hover", "giant", "normal"]:
                    res = check_usage(user_id, message_mode=mode, return_result=True)
                    out_filename = f"{args.output}_{mode}"
                    try:
                        with open(out_filename, "w", encoding=out_enc) as f:
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
                        success = data.get("success", "")
                        total_usage_minutes = data.get("total_usage_minutes", "")
                        allowed_watch_time_minutes = data.get("allowed_watch_time_minutes", "")
                        status = data.get("status", "")
                        message_jp = data.get("message_jp", "")
                        line = (
                            f"{mode},{success},{total_usage_minutes},"
                            f"{allowed_watch_time_minutes},{status},{message_jp}"
                        )
                    except Exception:
                        line = f"{mode},E,,,,"
                    print(line)

        elif msg_mode == "fileout_only_message":
            if args.output:
                for mode in ["hover", "giant", "normal"]:
                    res = check_usage(user_id, message_mode=mode, return_result=True)
                    out_filename = f"{args.output}_{mode}"
                    try:
                        data = json.loads(res)
                        # message_jp を取得。なければ空文字列
                        message_jp = data.get("message_jp", "")
                    except Exception:
                        message_jp = "E"

                    try:
                        with open(out_filename, "w", encoding=out_enc) as f:
                            f.write(message_jp)
                        print(f"Output to {out_filename}:")
                        print(message_jp)
                        print("-----")
                    except Exception:
                        print("E")
            else:
                # CSV形式で標準出力へ (mode,message_jp のみ)
                header = "mode,message_jp"
                print(header)
                for mode in ["hover", "giant", "normal"]:
                    res = check_usage(user_id, message_mode=mode, return_result=True)
                    try:
                        data = json.loads(res)
                        message_jp = data.get("message_jp", "")
                        line = f"{mode},{message_jp}"
                    except Exception:
                        line = f"{mode},E"
                    print(line)

        else:
            # 通常の check_usage
            result = check_usage(user_id, message_mode=msg_mode, return_result=True)
            output_result(result, args.output, out_enc)

    elif args.command == "is-able-watch":
        result = is_able_watch(args.user_id, return_result=True)
        output_result(result, args.output)

    elif args.command == "insert-watch-log":
        result = insert_watch_log(args.user_id, args.added_minutes, return_result=True)
        output_result(result, args.output)

if __name__ == "__main__":
    main()
