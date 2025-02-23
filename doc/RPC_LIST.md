RPCで記載されている関数一覧を作成します。コードベースから以下の関数を特定しました：

### 基本的なRPC関数
1. `auth_test_register_user_record`
- 引数: `_user_id UUID`
- 説明: ユーザーレコードを登録するための関数

2. `get_pc_name`
- 引数: `p_pc_id UUID`
- 説明: PC IDに対応するPC名を取得する関数

3. `get_total_watch_time`
- 引数: `target_user_id UUID, target_date DATE`
- 説明: ユーザーの総視聴可能時間を計算する関数
- 戻り値: `total_added_minutes`, `default_time`, `total_time`

4. `analyze_time_difference`
- 引数: `target_user_id UUID, target_date DATE`
- 説明: 実際の利用時間と許可された視聴時間の差分を計算
- 戻り値: `unique_minutes`, `total_watch_time`, `time_difference`

5. `get_time_ranges_by_user`
- 引数: `target_user_id UUID, target_date DATE`
- 説明: 指定日付のユーザーの利用時間帯を取得
- 戻り値: `pc_id`, `activity_count`, `time_ranges`

6. `insert_continuous_activity`
- 引数: `target_user_id UUID, target_pc_id UUID, start_time TEXT, end_time TEXT, target_date DATE`
- 説明: 指定時間範囲の活動レコードを一括登録

7. `append_pc_activity`
- 引数: `p_pc_id UUID, p_user_id UUID, p_minutes int[]`
- 説明: PC活動記録を追加

8. `delete_pc_activity`
- 引数: `p_pc_id UUID, p_user_id UUID, p_minutes int[]`
- 説明: PC活動記録を削除

9. `get_user_pcs`
- 引数: `p_user_id UUID`
- 説明: ユーザーに関連付けられたPCリストを取得

### APIキー認証付きRPC関数
10. `get_pc_name_by_user`
- 引数: `p_api_key TEXT, p_user_id UUID, p_pc_id UUID`
- 説明: APIキー認証付きでPC名を取得

11. `get_pc_id_by_name_and_user`
- 引数: `p_api_key TEXT, p_user_id UUID, p_pc_name TEXT`
- 説明: PC名からPC IDを取得

12. `get_pc_activity_minutes_by_api`
- 引数: `p_api_key TEXT, p_user_id UUID, p_start_time TIMESTAMPTZ, p_end_time TIMESTAMPTZ`
- 説明: 指定期間の活動時間（分）を取得

13. `get_pc_activity_minutes_by_pc_and_api`
- 引数: `p_api_key TEXT, p_user_id UUID, p_pc_id UUID, p_start_time TIMESTAMPTZ, p_end_time TIMESTAMPTZ`
- 説明: 特定PCの指定期間の活動時間（分）を取得

14. `get_user_api_key`
- 引数: `p_user_id UUID`
- 説明: ユーザーのAPIキーを取得
