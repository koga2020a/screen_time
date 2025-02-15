# テーブルの基本仕様

## テーブルの基本仕様

【テーブル構成】

pc_activity_2：PC利用時間記録


pc_id (UUID)：PC識別子
user_id (UUID)：ユーザー識別子
minutes_time_jst (int)：00:00からの経過分数（自動計算）
created_at：UTC時刻
created_at_jst：JST時刻
※pc_id、user_id、minutes_time_jstの組み合わせは一意


users_watch_time：ユーザーの視聴時間設定


user_id (UUID)：ユーザー識別子
default_time (int)：デフォルト視聴時間（分）
created_at_jst：JST時刻


watch_time_log：追加視聴時間記録


user_id (UUID)：ユーザー識別子
added_minutes (int)：追加された視聴時間（分）
created_at：UTC時刻
created_at_jst：JST時刻-- テーブルの基本仕様


## 概要
PC Activity and Watch Time Tracking System
概要
PCの利用時間を記録・分析し、ユーザーごとの視聴時間設定と実際の利用時間を比較分析するためのシステムです。
テーブル構造
1. pc_activity_2
PCの利用時間を分単位で記録するテーブル
カラム名型説明pc_idUUIDPC識別子user_idUUIDユーザー識別子minutes_time_jstINTEGERJST 00:00からの経過分数（自動計算）created_atTIMESTAMP WITH TIME ZONEレコード作成時刻（UTC）created_at_jstTIMESTAMP WITH TIME ZONEレコード作成時刻（JST）
2. users_watch_time
ユーザーごとのデフォルト視聴時間設定テーブル
カラム名型説明user_idUUIDユーザー識別子default_timeINTEGERデフォルトの視聴時間（分）created_at_jstTIMESTAMP WITH TIME ZONEレコード作成時刻（JST）
3. watch_time_log
視聴時間の追加記録テーブル
カラム名型説明user_idUUIDユーザー識別子added_minutesINTEGER追加された視聴時間（分）created_atTIMESTAMP WITH TIME ZONEレコード作成時刻（UTC）created_at_jstTIMESTAMP WITH TIME ZONEレコード作成時刻（JST）



## テーブルの作成

### 基礎かも

```sql
-- テーブルの作成
CREATE TABLE pc_activity_2 (
    pc_id UUID NOT NULL,
    user_id UUID NOT NULL,
    minutes_time_jst INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at_jst TIMESTAMP WITH TIME ZONE DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'JST'),
    
    -- pc_id, user_id, minutes_time_jstの組み合わせの一意制約
    CONSTRAINT pc_activity_2_unique_combination 
    UNIQUE (pc_id, user_id, minutes_time_jst)
);

-- インデックスの作成（検索パフォーマンス向上のため）
CREATE INDEX idx_pc_activity_2_user_date 
ON pc_activity_2 (user_id, created_at_jst);

-- 特定のユーザーの指定日のminutes_time_jstレコード数を取得するクエリ
CREATE OR REPLACE FUNCTION get_daily_activity_count(
    target_user_id UUID,
    target_date DATE
)
RETURNS TABLE (
    activity_count BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT COUNT(DISTINCT minutes_time_jst)
    FROM pc_activity_2
    WHERE user_id = target_user_id
    AND DATE(created_at_jst) = target_date;
END;
$$ LANGUAGE plpgsql;

-- 使用例：
-- 特定のユーザーの2024-02-15の活動記録数を取得
SELECT * FROM get_daily_activity_count('your-user-uuid-here', '2024-02-15');

-- または直接SQLで取得する場合：
SELECT COUNT(DISTINCT minutes_time_jst) as activity_count
FROM pc_activity_2
WHERE user_id = 'your-user-uuid-here'
AND DATE(created_at_jst) = '2024-02-15';
```


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

## テーブルの修正

```sql
-- users_watch_timeテーブルにJST列を追加
ALTER TABLE users_watch_time
ADD COLUMN created_at_jst TIMESTAMP WITH TIME ZONE;

-- 既存のデータに対してJST時刻を設定
UPDATE users_watch_time
SET created_at_jst = created_at AT TIME ZONE 'JST';

-- created_at_jstのデフォルト値を設定
ALTER TABLE users_watch_time
ALTER COLUMN created_at_jst SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'JST');

-- watch_time_logテーブルにJST列を追加
ALTER TABLE watch_time_log
ADD COLUMN created_at_jst TIMESTAMP WITH TIME ZONE;

-- 既存のデータに対してJST時刻を設定
UPDATE watch_time_log
SET created_at_jst = created_at AT TIME ZONE 'JST';

-- created_at_jstのデフォルト値を設定
ALTER TABLE watch_time_log
ALTER COLUMN created_at_jst SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'JST');
```







# FUNCTION の作成

## 明示的にテーブルエイリアスを指定する

```sql
CREATE OR REPLACE FUNCTION get_total_watch_time(
    target_user_id UUID,
    target_date DATE
)
RETURNS TABLE (
    total_added_minutes BIGINT,
    default_time INTEGER,
    total_time BIGINT
) AS $$
BEGIN
    RETURN QUERY
    WITH added_time AS (
        SELECT COALESCE(SUM(added_minutes), 0) AS sum_added_minutes
        FROM watch_time_log
        WHERE user_id = target_user_id
        AND DATE(created_at_jst) = target_date
    ),
    default_watch_time AS (
        SELECT uwt.default_time
        FROM users_watch_time uwt
        WHERE uwt.user_id = target_user_id
        ORDER BY uwt.created_at_jst DESC
        LIMIT 1
    )
    SELECT 
        at.sum_added_minutes,
        COALESCE(dwt.default_time, 0),
        at.sum_added_minutes + COALESCE(dwt.default_time, 0)
    FROM added_time at
    CROSS JOIN default_watch_time dwt;
END;
$$ LANGUAGE plpgsql;
```




## 日付とユーザーIDでの時間差分析を取得する関数

```sql
-- 日付とユーザーIDでの時間差分析を取得する関数
CREATE OR REPLACE FUNCTION analyze_time_difference(
    target_user_id UUID,
    target_date DATE
)
RETURNS TABLE (
    unique_minutes_count BIGINT,
    total_watch_time BIGINT,
    time_difference BIGINT
) AS $$
BEGIN
    RETURN QUERY
    WITH watch_time_total AS (
        SELECT total_time
        FROM get_total_watch_time(target_user_id, target_date)
    ),
    activity_minutes AS (
        SELECT COUNT(DISTINCT minutes_time_jst) as unique_minutes
        FROM pc_activity_2
        WHERE user_id = target_user_id
        AND DATE(created_at_jst) = target_date
    )
    SELECT 
        activity_minutes.unique_minutes,
        watch_time_total.total_time,
        activity_minutes.unique_minutes - watch_time_total.total_time as difference
    FROM activity_minutes
    CROSS JOIN watch_time_total;
END;
$$ LANGUAGE plpgsql;
```

## minutes_time_jst計算用の関数作成

### minutes_time_jst計算用の関数作成
```sql
-- minutes_time_jst計算用の関数作成
CREATE OR REPLACE FUNCTION calculate_minutes_time_jst()
RETURNS TRIGGER AS $$
BEGIN
    -- created_at_jstから時刻部分を抽出し、分に変換
    NEW.minutes_time_jst := 
        EXTRACT(HOUR FROM NEW.created_at_jst)::integer * 60 +
        EXTRACT(MINUTE FROM NEW.created_at_jst)::integer;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

### テーブルの再作成

```sql
-- テーブルの再作成
CREATE TABLE pc_activity_2 (
    pc_id UUID NOT NULL,
    user_id UUID NOT NULL,
    minutes_time_jst INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at_jst TIMESTAMP WITH TIME ZONE DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'JST'),
    
    -- pc_id, user_id, minutes_time_jstの組み合わせの一意制約
    CONSTRAINT pc_activity_2_unique_combination 
        UNIQUE (pc_id, user_id, minutes_time_jst)
    );
```
### トリガーの作成

```sql
-- トリガーの作成
CREATE TRIGGER set_minutes_time_jst
    BEFORE INSERT ON pc_activity_2
    FOR EACH ROW
    EXECUTE FUNCTION calculate_minutes_time_jst();

-- インデックスの作成
CREATE INDEX idx_pc_activity_2_user_date 
ON pc_activity_2 (user_id, created_at_jst);

-- 日付ごとのアクティビティ数を取得する関数
CREATE OR REPLACE FUNCTION get_daily_activity_count(
    target_user_id UUID,
    target_date DATE
)
RETURNS TABLE (
    activity_count BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT COUNT(DISTINCT minutes_time_jst)
    FROM pc_activity_2
    WHERE user_id = target_user_id
    AND DATE(created_at_jst) = target_date;
END;
$$ LANGUAGE plpgsql;
```

## テスト用のデータ挿入と確認例

```sql
-- シンプルな挿入例（minutes_time_jstは自動計算されます）
INSERT INTO pc_activity_2 (
    pc_id,
    user_id
) VALUES (
    '123e4567-e89b-12d3-a456-426614174000'::uuid,
    'user-123e4567-e89b-12d3-a456-111111111111'::uuid
);

-- 特定の時刻を指定して挿入する場合
INSERT INTO pc_activity_2 (
    pc_id,
    user_id,
    created_at_jst
) VALUES (
    '123e4567-e89b-12d3-a456-426614174000'::uuid,
    'user-123e4567-e89b-12d3-a456-111111111111'::uuid,
    '2024-02-15 09:30:00 JST'
);

-- データの確認
SELECT 
    pc_id,
    user_id,
    minutes_time_jst,
    created_at_jst,
    (minutes_time_jst / 60) as hours,
    (minutes_time_jst % 60) as minutes
FROM pc_activity_2
WHERE user_id = 'user-123e4567-e89b-12d3-a456-111111111111'::uuid
ORDER BY created_at_jst DESC;
```




## 分を時刻文字列に変換する補助関数

```sql
-- 分を時刻文字列に変換する補助関数
CREATE OR REPLACE FUNCTION minutes_to_time(minutes INTEGER)
RETURNS TEXT AS $$
BEGIN
    RETURN LPAD((minutes / 60)::TEXT, 2, '0') || 
           LPAD((minutes % 60)::TEXT, 2, '0');
END;
$$ LANGUAGE plpgsql;

-- 特定のPC、ユーザー、日付の時間帯リストを取得する関数
CREATE OR REPLACE FUNCTION get_time_ranges_by_pc(
    target_user_id UUID,
    target_pc_id UUID,
    target_date DATE
)
RETURNS TABLE (
    time_range TEXT
) AS $$
WITH grouped_times AS (
    SELECT minutes_time_jst,
           minutes_time_jst - (ROW_NUMBER() OVER (ORDER BY minutes_time_jst)) AS grp
    FROM (
        SELECT DISTINCT minutes_time_jst
        FROM pc_activity_2
        WHERE user_id = target_user_id
        AND pc_id = target_pc_id
        AND DATE(created_at_jst) = target_date
    ) t
), ranges AS (
    SELECT 
        MIN(minutes_time_jst) AS range_start,
        MAX(minutes_time_jst) AS range_end
    FROM grouped_times
    GROUP BY grp
    ORDER BY range_start
)
SELECT 
    minutes_to_time(range_start) || '-' || minutes_to_time(range_end) AS time_range
FROM ranges;
$$ LANGUAGE SQL;
```



## ユーザのPC利用時間の範囲を取得する

```sql
CREATE OR REPLACE FUNCTION get_time_ranges_by_user(
    target_user_id UUID,
    target_date DATE
)
RETURNS TABLE (
    pc_id UUID,
    activity_count BIGINT,
    time_ranges TEXT[]
) AS $$
WITH grouped_times AS (
    SELECT 
        pc_id,
        minutes_time_jst,
        minutes_time_jst - (ROW_NUMBER() OVER (PARTITION BY pc_id ORDER BY minutes_time_jst)) AS grp
    FROM (
        SELECT DISTINCT pc_id, minutes_time_jst
        FROM pc_activity_2
        WHERE user_id = target_user_id
        AND DATE(created_at_jst) = target_date
    ) t
), ranges AS (
    SELECT 
        pc_id,
        MIN(minutes_time_jst) AS range_start,
        MAX(minutes_time_jst) AS range_end
    FROM grouped_times
    GROUP BY pc_id, grp
), activity_counts AS (
    SELECT 
        pc_id,
        COUNT(DISTINCT minutes_time_jst) as activity_count
    FROM pc_activity_2
    WHERE user_id = target_user_id
    AND DATE(created_at_jst) = target_date
    GROUP BY pc_id
), formatted_ranges AS (
    SELECT 
        pc_id,
        minutes_to_time(range_start) || '-' || minutes_to_time(range_end) as time_range,
        minutes_to_time(range_start) as sorting_key
    FROM ranges
)
SELECT 
    r.pc_id,
    ac.activity_count,
    array_agg(DISTINCT fr.time_range ORDER BY fr.sorting_key) as time_ranges
FROM ranges r
JOIN activity_counts ac ON r.pc_id = ac.pc_id
JOIN formatted_ranges fr ON r.pc_id = fr.pc_id
GROUP BY r.pc_id, ac.activity_count;
$$ LANGUAGE SQL;
```









# 試験用データの作成、テスト

## 指定時間範囲のテストデータを生成する関数

```sql
CREATE OR REPLACE FUNCTION insert_continuous_activity(
    target_user_id UUID,
    target_pc_id UUID,
    start_time TEXT,  -- 'HH:MM' 形式 (例: '09:30')
    end_time TEXT,    -- 'HH:MM' 形式 (例: '10:45')
    target_date DATE  -- 'YYYY-MM-DD' 形式
)
RETURNS INTEGER AS $$
DECLARE
    start_minutes INTEGER;
    end_minutes INTEGER;
    inserted_count INTEGER;
BEGIN
    -- 時刻を分に変換
    start_minutes := (EXTRACT(HOUR FROM start_time::TIME) * 60 + 
                     EXTRACT(MINUTE FROM start_time::TIME))::INTEGER;
    end_minutes := (EXTRACT(HOUR FROM end_time::TIME) * 60 + 
                   EXTRACT(MINUTE FROM end_time::TIME))::INTEGER;

    -- 指定範囲で連続したレコードを挿入
    WITH minutes AS (
        SELECT generate_series(start_minutes, end_minutes) AS minute
    )
    INSERT INTO pc_activity_2 (
        pc_id,
        user_id,
        created_at_jst
    )
    SELECT 
        target_pc_id,
        target_user_id,
        target_date + 
        (minute * INTERVAL '1 minute') + 
        (start_time::TIME - (start_minutes * INTERVAL '1 minute'))
    FROM minutes;

    GET DIAGNOSTICS inserted_count = ROW_COUNT;
    RETURN inserted_count;
END;
$$ LANGUAGE plpgsql;
```


## 使用例

```sql
-- 使用例1: 9:30から10:45までのデータを生成
SELECT insert_continuous_activity(
    'user-123e4567-e89b-12d3-a456-111111111111'::uuid,  -- user_id
    '123e4567-e89b-12d3-a456-426614174000'::uuid,       -- pc_id
    '09:30',                                             -- start_time
    '10:45',                                             -- end_time
    CURRENT_DATE                                         -- target_date
);

-- 使用例2: 特定の日付で14:00から15:30までのデータを生成
SELECT insert_continuous_activity(
    'user-123e4567-e89b-12d3-a456-111111111111'::uuid,
    '123e4567-e89b-12d3-a456-426614174000'::uuid,
    '14:00',
    '15:30',
    '2024-02-15'::date
);

-- 生成されたデータの確認
SELECT 
    minutes_time_jst,
    to_char(created_at_jst, 'HH24:MI') as time,
    created_at_jst::date as date
FROM pc_activity_2
WHERE user_id = 'user-123e4567-e89b-12d3-a456-111111111111'::uuid
    AND created_at_jst::date = '2024-02-15'
ORDER BY created_at_jst;


```

