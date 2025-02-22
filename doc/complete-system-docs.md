# PC Activity and Watch Time Tracking System

## 概要
PCの利用時間を記録・分析し、ユーザーごとの視聴時間設定と実際の利用時間を比較分析するためのシステムです。

## テーブル構造

### 1. pc_activity_2
PCの利用時間を分単位で記録するテーブル

| カラム名 | 型 | 説明 |
|----------|-----|------|
| pc_id | UUID | PC識別子 |
| user_id | UUID | ユーザー識別子 |
| minutes_time_jst | INTEGER | JST 00:00からの経過分数（自動計算） |
| created_at | TIMESTAMP WITH TIME ZONE | レコード作成時刻（UTC） |
| created_at_jst | TIMESTAMP WITH TIME ZONE | レコード作成時刻（JST） |

### 2. users_watch_time
ユーザーごとのデフォルト視聴時間設定テーブル

| カラム名 | 型 | 説明 |
|----------|-----|------|
| user_id | UUID | ユーザー識別子 |
| default_time | INTEGER | デフォルトの視聴時間（分） |
| created_at | TIMESTAMP WITH TIME ZONE | レコード作成時刻（UTC） |
| created_at_jst | TIMESTAMP WITH TIME ZONE | レコード作成時刻（JST） |

### 3. watch_time_log
視聴時間の追加記録テーブル

| カラム名 | 型 | 説明 |
|----------|-----|------|
| user_id | UUID | ユーザー識別子 |
| added_minutes | INTEGER | 追加された視聴時間（分） |
| created_at | TIMESTAMP WITH TIME ZONE | レコード作成時刻（UTC） |
| created_at_jst | TIMESTAMP WITH TIME ZONE | レコード作成時刻（JST） |

## セットアップ手順

### 1. テーブル作成
```sql
-- pc_activity_2テーブルの作成
CREATE TABLE pc_activity_2 (
    pc_id UUID NOT NULL,
    user_id UUID NOT NULL,
    minutes_time_jst INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at_jst TIMESTAMP WITH TIME ZONE DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'JST'),
    CONSTRAINT pc_activity_2_unique_combination 
    UNIQUE (pc_id, user_id, minutes_time_jst)
);

-- users_watch_timeテーブルの作成
CREATE TABLE users_watch_time (
    user_id UUID NOT NULL,
    default_time INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at_jst TIMESTAMP WITH TIME ZONE DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'JST')
);

-- watch_time_logテーブルの作成
CREATE TABLE watch_time_log (
    user_id UUID NOT NULL,
    added_minutes INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at_jst TIMESTAMP WITH TIME ZONE DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'JST')
);
```

### 2. 関数とトリガーの作成
```sql
-- minutes_time_jst自動計算用のトリガー関数
CREATE OR REPLACE FUNCTION calculate_minutes_time_jst() ...;

-- その他の分析関数
CREATE OR REPLACE FUNCTION get_time_ranges_by_pc() ...;
CREATE OR REPLACE FUNCTION get_time_ranges_by_user() ...;
CREATE OR REPLACE FUNCTION get_total_watch_time() ...;
CREATE OR REPLACE FUNCTION analyze_time_difference() ...;
```

## 基本的な使用例

### 1. PC利用時間の記録
```sql
-- 現在時刻での利用記録
INSERT INTO pc_activity_2 (
    pc_id,
    user_id
) VALUES (
    '123e4567-e89b-12d3-a456-426614174000'::uuid,
    'user-123e4567-e89b-12d3-a456-111111111111'::uuid
);

-- 特定時刻での利用記録
INSERT INTO pc_activity_2 (
    pc_id,
    user_id,
    created_at_jst
) VALUES (
    '123e4567-e89b-12d3-a456-426614174000'::uuid,
    'user-123e4567-e89b-12d3-a456-111111111111'::uuid,
    '2024-02-15 09:30:00 JST'
);
```

### 2. 視聴時間の設定と追加
```sql
-- デフォルト視聴時間の設定
INSERT INTO users_watch_time (
    user_id,
    default_time
) VALUES (
    'user-123e4567-e89b-12d3-a456-111111111111'::uuid,
    480  -- 8時間
);

-- 追加視聴時間の記録
INSERT INTO watch_time_log (
    user_id,
    added_minutes
) VALUES (
    'user-123e4567-e89b-12d3-a456-111111111111'::uuid,
    60   -- 1時間追加
);
```

## 分析機能の使用例

### 1. PC別の利用時間帯取得
```sql
-- 特定PCの利用時間帯
SELECT * FROM get_time_ranges_by_pc(
    'user-123e4567-e89b-12d3-a456-111111111111'::uuid,  -- user_id
    '123e4567-e89b-12d3-a456-426614174000'::uuid,       -- pc_id
    '2024-02-15'::date                                   -- date
);

-- 結果例：
-- time_range
-- --------------
-- 0922-1030
-- 1042-1352
-- 2355-2359
```

### 2. ユーザー別の利用サマリー
```sql
-- ユーザーの全PC利用サマリー
SELECT * FROM get_time_ranges_by_user(
    'user-123e4567-e89b-12d3-a456-111111111111'::uuid,
    '2024-02-15'::date
);

-- 結果例：
-- pc_id                    | activity_count | time_ranges
---------------------------|----------------|---------------------------
-- PC1                     | 25            | {0922-1030,1042-1352}
-- PC2                     | 15            | {1015-1245,1330-1455}
```

### 3. 視聴時間分析
```sql
-- 合計視聴時間の取得
SELECT * FROM get_total_watch_time(
    'user-123e4567-e89b-12d3-a456-111111111111'::uuid,
    '2024-02-15'::date
);

-- 結果例：
-- total_added_minutes | default_time | total_time
-- -------------------|--------------|------------
-- 120                | 480          | 600

-- 実際の利用時間との差分分析
SELECT * FROM analyze_time_difference(
    'user-123e4567-e89b-12d3-a456-111111111111'::uuid,
    '2024-02-15'::date
);

-- 結果例：
-- unique_minutes_count | total_watch_time | time_difference
-- --------------------|------------------|----------------
-- 650                 | 600              | 50
```

## 主な機能一覧

### PC利用時間記録機能
1. **自動時間計算**
   - 関数: `calculate_minutes_time_jst()`
   - 用途: JST時刻から経過分数を自動計算

2. **時間帯分析**
   - 関数: `get_time_ranges_by_pc()`, `get_time_ranges_by_user()`
   - 用途: 連続する利用時間帯の把握

### 視聴時間管理機能
1. **視聴時間集計**
   - 関数: `get_total_watch_time()`
   - 用途: デフォルト時間と追加時間の合計算出

2. **差分分析**
   - 関数: `analyze_time_difference()`
   - 用途: 実際の利用時間と設定時間の比較

## 注意事項
- 時刻はすべてJST（日本標準時）で処理
- minutes_time_jstは0〜1439の範囲（24時間×60分）
- 連続する時間帯は自動的に結合
- PCとユーザーの組み合わせでの重複は排除
- デフォルト時間は最新の設定値が使用される

## バックアップとメンテナンス
1. 定期的なバックアップの推奨
2. インデックスの最適化
3. 古いログデータの保持期間設定

## トラブルシューティング
1. 時刻のずれが発生した場合
   - タイムゾーン設定の確認
   - created_at_jstの再計算

2. パフォーマンスの低下
   - インデックスの再構築
   - 不要なデータの削除