#!/usr/bin/env python3
import sys
import argparse
import requests
import uuid
import json
from datetime import datetime
from dotenv import load_dotenv
import os

# .envファイルから環境変数をロード
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_API_KEY = os.getenv("SUPABASE_API_KEY")

# 動作確認のための出力（必要に応じて削除してください）
#print("SUPABASE_URL:", SUPABASE_URL)
#print("SUPABASE_API_KEY:", SUPABASE_API_KEY)

HEADERS = {
    "apikey": SUPABASE_API_KEY,
    "Authorization": f"Bearer {SUPABASE_API_KEY}",
    "Content-Type": "application/json",
}

def get_activity_time():
    """現在時刻を、その日の 0:00 からの経過分数に変換します。"""
    now = datetime.utcnow()
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    minutes_since_midnight = int((now - midnight).total_seconds() / 60)
    return minutes_since_midnight

def is_valid_uuid(value):
    """指定された文字列が UUID 形式かどうかチェックします。"""
    try:
        uuid.UUID(value, version=4)
        return True
    except ValueError:
        return False

def check_user_exists(user_id):
    """users_watch_time テーブルに指定された user_id が存在するか確認します。"""
    url = f"{SUPABASE_URL}/rest/v1/users_watch_time?user_id=eq.{user_id}&select=user_id"
    response = requests.get(url, headers=HEADERS)
    return bool(response.text.strip() and response.json())

def log_pc_activity(user_id, pc_id, return_result=False):
    """PCアクティビティを記録します。PC とユーザの UUID を受け取り、現在時刻（その日の経過分数）を記録します。"""
    if not is_valid_uuid(user_id):
        result = f"エラー: user_id ({user_id}) は正しいUUID形式ではありません"
        return result if return_result else print(result)
    if not is_valid_uuid(pc_id):
        result = f"エラー: pc_id ({pc_id}) は正しいUUID形式ではありません"
        return result if return_result else print(result)
    if not check_user_exists(user_id):
        result = f"エラー: user_id ({user_id}) は users_watch_time に存在しません"
        return result if return_result else print(result)
    activity_time = get_activity_time()
    url = f"{SUPABASE_URL}/rest/v1/pc_activity"
    data = {"user_id": user_id, "pc_id": pc_id, "activity_time": activity_time}
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
    （users_watch_time.default_time ＋ watch_time_log の合計 － 全PCの利用済み分数（重複は1分として））
    """
    try:
        url_watch_time = f"{SUPABASE_URL}/rest/v1/users_watch_time?user_id=eq.{user_id}&select=default_time"
        response = requests.get(url_watch_time, headers=HEADERS)
        watch_data = response.json() if response.text.strip() else []
        if not watch_data:
            result = json.dumps({"error": "User not found"}, ensure_ascii=False)
            return result if return_result else print(result)
        default_time = watch_data[0]["default_time"]

        url_watch_log = f"{SUPABASE_URL}/rest/v1/watch_time_log?user_id=eq.{user_id}&select=added_minutes"
        response = requests.get(url_watch_log, headers=HEADERS)
        log_data = response.json() if response.text.strip() else []
        total_added_minutes = sum([log["added_minutes"] for log in log_data])
        total_allowed = default_time + total_added_minutes

        url_activity = f"{SUPABASE_URL}/rest/v1/pc_activity?user_id=eq.{user_id}&select=activity_time"
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
    全PCでの利用済み分数（重複は1分として）と、その分数を HH:MM 形式（例："01:15"）のリストで返します。
    """
    try:
        url = f"{SUPABASE_URL}/rest/v1/pc_activity?user_id=eq.{user_id}&select=activity_time"
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

def get_pc_usage(user_id, pc_id, return_result=False):
    """
    特定PCの利用済み分数（重複は1分として）と、利用時刻（HH:MM形式）のリストを返します。
    """
    try:
        url = f"{SUPABASE_URL}/rest/v1/pc_activity?user_id=eq.{user_id}&pc_id=eq.{pc_id}&select=activity_time"
        response = requests.get(url, headers=HEADERS)
        data = response.json() if response.text.strip() else []
        unique_minutes = {row["activity_time"] for row in data}
        total_usage = len(unique_minutes)
        usage_times = [f"{m // 60:02d}:{m % 60:02d}" for m in sorted(unique_minutes)]
        res = {
            "success": True,
            "pc_usage_minutes": total_usage,
            "usage_times": usage_times
        }
        result = json.dumps(res, ensure_ascii=False)
    except Exception:
        result = "E"
    return result if return_result else print(result)

def get_allowed_time(user_id, return_result=False):
    """
    ユーザのその日の視聴可能時間（users_watch_time.default_time ＋ watch_time_log の合計）を返します。
    """
    try:
        url_watch_time = f"{SUPABASE_URL}/rest/v1/users_watch_time?user_id=eq.{user_id}&select=default_time"
        response = requests.get(url_watch_time, headers=HEADERS)
        watch_data = response.json() if response.text.strip() else []
        if not watch_data:
            result = json.dumps({"error": "User not found"}, ensure_ascii=False)
            return result if return_result else print(result)
        default_time = watch_data[0]["default_time"]

        url_watch_log = f"{SUPABASE_URL}/rest/v1/watch_time_log?user_id=eq.{user_id}&select=added_minutes"
        response = requests.get(url_watch_log, headers=HEADERS)
        log_data = response.json() if response.text.strip() else []
        total_added = sum(log["added_minutes"] for log in log_data)
        allowed = default_time + total_added
        res = {"success": True, "allowed_watch_time_minutes": allowed}
        result = json.dumps(res, ensure_ascii=False)
    except Exception:
        result = "E"
    return result if return_result else print(result)

def check_usage(user_id, return_result=False):
    """
    全PCでの利用済み分数（重複は1分として）と視聴可能時間を比較し、
    利用が視聴可能時間内なら "within allowed"、超えていれば "exceeded allowed" を返します。
    """
    try:
        url = f"{SUPABASE_URL}/rest/v1/pc_activity?user_id=eq.{user_id}&select=activity_time"
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
        url_watch_log = f"{SUPABASE_URL}/rest/v1/watch_time_log?user_id=eq.{user_id}&select=added_minutes"
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
        result = json.dumps(res, ensure_ascii=False)
    except Exception:
        result = "E"
    return result if return_result else print(result)

def is_able_watch(user_id, return_result=False):
    """
    全PCでの利用済み分数とその日の視聴可能時間を比較し、
    利用が許容内なら "T"、超えていれば "F"、エラー時は "E" を返します。
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
                url_watch_log = f"{SUPABASE_URL}/rest/v1/watch_time_log?user_id=eq.{user_id}&select=added_minutes"
                resp_log = requests.get(url_watch_log, headers=HEADERS)
                if resp_log.status_code != 200:
                    result = "E"
                else:
                    log_data = resp_log.json() if resp_log.text.strip() else []
                    total_added = sum(item["added_minutes"] for item in log_data)
                    allowed = default_time + total_added
                    url_activity = f"{SUPABASE_URL}/rest/v1/pc_activity?user_id=eq.{user_id}&select=activity_time"
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
    watch_time_log テーブルに added_minutes の値を挿入します。（マイナスの値も可能です）
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

def output_result(result, output_file):
    """出力ファイルが指定されていればそのファイルへ、指定がなければ標準出力へ結果を出力します。"""
    if output_file:
        try:
            with open(output_file, "w", encoding="utf-8") as f:
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
            "各コマンドは必須パラメータとして user_id（および pc_id や added_minutes 等）を受け取り、\n"
            "オプションで --output (-o) を指定すると、結果を指定されたファイルに出力します。\n"
            "エラー発生時は 'E'、視聴可能なら 'T'、超過していれば 'F' などの結果を返します。"
        ),
        formatter_class=argparse.RawTextHelpFormatter
    )
    subparsers = parser.add_subparsers(title="コマンド", dest="command", required=True)

    # log-pc-activity コマンド
    parser_log_pc = subparsers.add_parser(
        "log-pc-activity",
        help="指定したユーザとPCのUUIDを用いて、現在時刻を記録します。"
    )
    parser_log_pc.add_argument("user_id", help="ユーザID (UUID)")
    parser_log_pc.add_argument("pc_id", help="PC ID (UUID)")
    parser_log_pc.add_argument("--output", "-o", help="結果出力先ファイル (省略時は標準出力)")

    # check-watch-time コマンド
    parser_check_watch = subparsers.add_parser(
        "check-watch-time",
        help="ユーザの残り視聴可能時間を取得します。\n(ユーザの default_time ＋ watch_time_log の合計 － 全PCの利用済み分数)"
    )
    parser_check_watch.add_argument("user_id", help="ユーザID (UUID)")
    parser_check_watch.add_argument("--output", "-o", help="結果出力先ファイル (省略時は標準出力)")

    # get-total-usage コマンド
    parser_total_usage = subparsers.add_parser(
        "get-total-usage",
        help="全PCでの利用済み分数（重複は1分として）と利用時刻 (HH:MM形式) を取得します。"
    )
    parser_total_usage.add_argument("user_id", help="ユーザID (UUID)")
    parser_total_usage.add_argument("--output", "-o", help="結果出力先ファイル (省略時は標準出力)")

    # get-pc-usage コマンド
    parser_pc_usage = subparsers.add_parser(
        "get-pc-usage",
        help="指定したPCの利用済み分数（重複は1分として）と利用時刻 (HH:MM形式) を取得します。"
    )
    parser_pc_usage.add_argument("user_id", help="ユーザID (UUID)")
    parser_pc_usage.add_argument("pc_id", help="PC ID (UUID)")
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
        help="全PCの利用済み分数と視聴可能時間を比較し、範囲内か超過しているかを返します。"
    )
    parser_check_usage.add_argument("user_id", help="ユーザID (UUID)")
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
        result = log_pc_activity(args.user_id, args.pc_id, return_result=True)
        output_result(result, args.output)
    elif args.command == "check-watch-time":
        result = check_watch_time(args.user_id, return_result=True)
        output_result(result, args.output)
    elif args.command == "get-total-usage":
        result = get_total_usage(args.user_id, return_result=True)
        output_result(result, args.output)
    elif args.command == "get-pc-usage":
        result = get_pc_usage(args.user_id, args.pc_id, return_result=True)
        output_result(result, args.output)
    elif args.command == "get-allowed-time":
        result = get_allowed_time(args.user_id, return_result=True)
        output_result(result, args.output)
    elif args.command == "check-usage":
        result = check_usage(args.user_id, return_result=True)
        output_result(result, args.output)
    elif args.command == "is-able-watch":
        result = is_able_watch(args.user_id, return_result=True)
        output_result(result, args.output)
    elif args.command == "insert-watch-log":
        result = insert_watch_log(args.user_id, args.added_minutes, return_result=True)
        output_result(result, args.output)

if __name__ == "__main__":
    main()
