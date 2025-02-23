# SQLシステム構成一覧

## 1. テーブル構造

### 1.1 メインテーブル
- **pc_activity_2**: PC利用記録テーブル
  - PC識別子、ユーザー識別子、利用時間（分）を管理
  - JST対応のタイムスタンプカラムを保持
  - 同一日付・PC・ユーザー・分数の重複を防止するユニーク制約

- **users_watch_time**: ユーザー視聴時間設定テーブル
  - デフォルト視聴時間（分）を管理
  - APIキー認証機能を追加
  - PCの名前を管理

- **watch_time_log**: 視聴時間ログテーブル
  - 追加視聴時間の記録を管理
  - 入力された元の分数も保持
  - メモ機能を追加
  - JST対応のタイムスタンプを保持

### 1.2 認証関連テーブル
- **auth_test_user_records**: ユーザー認証テストテーブル
  - ユーザーIDと最終ログイン時刻を管理
  - Row Level Security (RLS) 対応
  - auth.usersテーブルとの外部キー制約

## 2. ストアドファンクション

### 2.1 基本機能
- **minutes_to_time**: 分を時刻文字列（HHMM形式）に変換
- **append_pc_activity**: PC利用記録の追加
- **delete_pc_activity**: PC利用記録の削除
- **update_jst_timestamp**: JSTタイムスタンプの更新
- **get_pc_name**: PC識別子からPC名を取得

### 2.2 分析機能
- **get_total_watch_time**: 総視聴時間の計算（デフォルト時間＋追加時間）
- **get_daily_activity_count**: 日別活動カウント取得
- **analyze_time_difference**: 利用時間と設定時間の差分分析
- **get_time_ranges_by_pc**: PC別の利用時間帯取得
- **get_time_ranges_by_user**: ユーザー別の利用時間帯取得（時間帯の結合処理を含む）

### 2.3 API認証機能
- **validate_user_api_key_ext**: APIキーの検証
- **get_user_api_key**: ユーザーのAPIキー取得
- **get_default_time_by_api**: APIキー認証付きデフォルト時間取得
- 各基本機能のAPIキー認証付きラッパー関数群

## 3. トリガー
- **set_minutes_time_jst**: pc_activity_2テーブルの分数自動計算
- **update_auth_test_user_records_updated_at**: 更新日時の自動設定
- **trg_auth_test_update_created_at_jst**: JST作成日時の自動設定

## 4. セキュリティ設定
- Row Level Security (RLS) ポリシー
- APIキーによる認証システム
- ユーザー権限の適切な設定
- パスワードリセット機能の実装

関連するコードブロックの参照:

```23:36:doc/SQL_text.md
````sql:doc/SQL_text.md
-- 【pc_activity_2 テーブル】
-- このテーブルは、各 PC 利用レコードを記録します。
-- レコードは PC 識別子 (pc_id)、ユーザー識別子 (user_id)、
-- 利用時間（JST の 00:00 からの経過分数）などを保持しています。
CREATE TABLE pc_activity_2 (
    pc_id UUID NOT NULL,                      -- PC の識別子
    user_id UUID NOT NULL,                    -- ユーザーの識別子
    minutes_time_jst INTEGER NOT NULL,        -- 利用時間を分単位で記録（後でトリガーにより自動計算）
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP, -- レコード生成時刻 (UTC)
    created_at_jst TIMESTAMPTZ DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'JST'), -- レコード生成時刻 (JST)
    created_date_jst DATE DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'JST')::DATE, -- JST の日付のみ
    CONSTRAINT pc_activity_2_unique_combination UNIQUE (created_date_jst, pc_id, user_id, minutes_time_jst) -- ユニーク制約：同一日付・PC・ユーザー・分数の重複を防止
);
```



```1:13:doc/SQL_auth_test.md
-- ユーザーレコードテーブルの作成
CREATE TABLE public.auth_test_user_records (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL,
    last_login TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_user
        FOREIGN KEY (user_id)
        REFERENCES auth.users (id)
        ON DELETE CASCADE,
    CONSTRAINT auth_test_user_records_user_id_key UNIQUE (user_id)
);
```



```13:28:doc/SQL_auth_double_text.md
CREATE OR REPLACE FUNCTION validate_user_api_key_ext(
    target_user_id UUID,
    provided_api_key TEXT
)
RETURNS BOOLEAN AS $$
DECLARE
    stored_api_key TEXT;
BEGIN
    SELECT api_key INTO stored_api_key
    FROM users_watch_time
    WHERE user_id = target_user_id;

    -- stored_api_key が NULL（ユーザーが存在しない場合など）のときは false を返す
    RETURN COALESCE(stored_api_key = provided_api_key, false);
END;
$$ LANGUAGE plpgsql;
```

CREATE INDEX idx_pc_activity_2_user_date ON public.pc_activity_2 USING btree (user_id, created_at_jst)