
# SQL 定義と使用例

本ドキュメントは、PC利用時間や視聴時間の記録・解析システムに関する各テーブルおよび関数の定義、並びに実際の使用例を示します。最新の定義内容（Supabase に登録されたユーザー定義ルーチン一覧を参照）をもとに記述しています。

---

## 1. テーブルの基本仕様

### 1.1 pc_activity_2：PC利用時間記録テーブル
- **カラム**
  - `pc_id` (UUID)：PC識別子
  - `user_id` (UUID)：ユーザー識別子
  - `minutes_time_jst` (INTEGER)：JSTの00:00からの経過分数（テーブル側で自動計算）
  - `created_at` (TIMESTAMP WITH TIME ZONE)：レコード作成時（UTC）
  - `created_at_jst` (TIMESTAMP WITH TIME ZONE)：レコード作成時（JST、デフォルト値：CURRENT_TIMESTAMP AT TIME ZONE 'JST'）
- **制約**
  - `(pc_id, user_id, minutes_time_jst)` の組み合わせは一意

### 1.2 users_watch_time：ユーザーのデフォルト視聴時間設定テーブル
- **カラム**
  - `user_id` (UUID)：ユーザー識別子
  - `default_time` (INTEGER)：デフォルト視聴時間（分）
  - `created_at_jst` (TIMESTAMP WITH TIME ZONE)：レコード作成時（JST）

### 1.3 watch_time_log：追加視聴時間記録テーブル
- **カラム**
  - `user_id` (UUID)：ユーザー識別子
  - `added_minutes` (INTEGER)：追加された視聴時間（分）
  - `created_at` (TIMESTAMP WITH TIME ZONE)：レコード作成時（UTC）
  - `created_at_jst` (TIMESTAMP WITH TIME ZONE)：レコード作成時（JST、デフォルト値：CURRENT_TIMESTAMP AT TIME ZONE 'JST'）

---

## 2. テーブルの作成

```sql:doc/SQL_text.md
-- pc_activity_2テーブルの作成
CREATE TABLE pc_activity_2 (
    pc_id UUID NOT NULL,
    user_id UUID NOT NULL,
    minutes_time_jst INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at_jst TIMESTAMP WITH TIME ZONE DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'JST'),
    CONSTRAINT pc_activity_2_unique_combination UNIQUE (pc_id, user_id, minutes_time_jst)
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

### 2.1 テーブルの修正

```sql:doc/SQL_text.md
-- users_watch_timeテーブルにJST列を追加し、既存データを更新
ALTER TABLE users_watch_time
ADD COLUMN created_at_jst TIMESTAMP WITH TIME ZONE;

UPDATE users_watch_time
SET created_at_jst = created_at AT TIME ZONE 'JST';

ALTER TABLE users_watch_time
ALTER COLUMN created_at_jst SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'JST');


-- watch_time_logテーブルにJST列を追加し、既存データを更新
ALTER TABLE watch_time_log
ADD COLUMN created_at_jst TIMESTAMP WITH TIME ZONE;

UPDATE watch_time_log
SET created_at_jst = created_at AT TIME ZONE 'JST';

ALTER TABLE watch_time_log
ALTER COLUMN created_at_jst SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'JST');
```

---

## 3. FUNCTION の作成

ここでは、テーブル操作、時間計算、利用時間および視聴時間の集計・解析等に用いる関数の定義例を示します。

### 3.1 分を時刻文字列に変換する補助関数

```sql:doc/SQL_text.md
CREATE OR REPLACE FUNCTION minutes_to_time(minutes INTEGER)
RETURNS TEXT AS $$
BEGIN
    RETURN LPAD((minutes / 60)::TEXT, 2, '0') || LPAD((minutes % 60)::TEXT, 2, '0');
END;
$$ LANGUAGE plpgsql;
```

*説明：与えられた分数を "HHMM" 形式（例："09:30"）の文字列に変換します。*

### 3.2 PC活動記録自動計算用トリガー関数

```sql:doc/SQL_text.md
CREATE OR REPLACE FUNCTION calculate_minutes_time_jst()
RETURNS TRIGGER AS $$
BEGIN
    NEW.minutes_time_jst :=
        EXTRACT(HOUR FROM NEW.created_at_jst)::integer * 60 +
        EXTRACT(MINUTE FROM NEW.created_at_jst)::integer;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

*説明：pc_activity_2への挿入時に、created_at_jstから分単位の利用時間を計算します。*

### 3.3 利用時間・視聴時間の集計・解析関数

#### 3.3.1 get_total_watch_time
```sql:doc/SQL_text.md
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

*説明：指定ユーザーの当日の追加視聴時間（watch_time_log）とデフォルト視聴時間（users_watch_time）を合算し、全体の視聴可能時間を算出します。*

#### 3.3.2 get_daily_activity_count
```sql:doc/SQL_text.md
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

*説明：指定日付における、ユーザーのPC利用記録（重複しない分数）の総数を返します。*

#### 3.3.3 analyze_time_difference
```sql:doc/SQL_text.md
CREATE OR REPLACE FUNCTION analyze_time_difference(
    target_user_id UUID,
    target_date DATE
)
RETURNS TABLE (
    unique_minutes BIGINT,
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
        activity_minutes.unique_minutes - watch_time_total.total_time as time_difference
    FROM activity_minutes
    CROSS JOIN watch_time_total;
END;
$$ LANGUAGE plpgsql;
```

*説明：実際の利用時間（ユニークな活動分数）と設定された視聴可能時間との差分を計算し、視聴可能か否かの判断に利用します。*

### 3.4 PC利用時間分布取得関数

#### 3.4.1 get_time_ranges_by_pc
```sql:doc/SQL_text.md
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
SELECT minutes_to_time(range_start) || '-' || minutes_to_time(range_end) AS time_range
FROM ranges;
$$ LANGUAGE SQL;
```

*説明：指定したPCに対する利用記録を、連続した区間ごとに "HH:MM-HH:MM" の形式で返します。*

#### 3.4.2 get_time_ranges_by_user
```sql:doc/SQL_text.md
CREATE OR REPLACE FUNCTION get_time_ranges_by_user(
    target_user_id UUID,
    target_date DATE
)
RETURNS TABLE (
    pc_id UUID,
    activity_count BIGINT,
    time_ranges TEXT[]
) AS $$
WITH ordered_data AS (
    SELECT 
        pc_id,
        minutes_time_jst,
        LAG(minutes_time_jst) OVER (PARTITION BY pc_id ORDER BY minutes_time_jst) AS prev_time
    FROM (
        SELECT DISTINCT pc_id, minutes_time_jst
        FROM pc_activity_2
        WHERE user_id = target_user_id
          AND DATE(created_at_jst) = target_date
    ) t
), grouped AS (
    SELECT pc_id, minutes_time_jst,
           minutes_time_jst - ROW_NUMBER() OVER (PARTITION BY pc_id ORDER BY minutes_time_jst) as grp
    FROM ordered_data
), ranges AS (
    SELECT pc_id,
           MIN(minutes_time_jst) as range_start,
           MAX(minutes_time_jst) as range_end
    FROM grouped
    GROUP BY pc_id, grp
), activity_counts AS (
    SELECT pc_id, COUNT(DISTINCT minutes_time_jst) as activity_count
    FROM pc_activity_2
    WHERE user_id = target_user_id
      AND DATE(created_at_jst) = target_date
    GROUP BY pc_id
), formatted AS (
    SELECT pc_id,
           array_agg(
             minutes_to_time(range_start) || '-' || minutes_to_time(range_end)
             ORDER BY range_start
           ) as time_ranges
    FROM ranges
    GROUP BY pc_id
)
SELECT a.pc_id, a.activity_count, f.time_ranges
FROM activity_counts a
JOIN formatted f ON a.pc_id = f.pc_id;
$$ LANGUAGE SQL;
```

*説明：対象ユーザーの各PCごとに、利用記録の連続した時間帯と総利用回数を集計して返します。*

### 3.5 連続した活動レコードを挿入する関数

```sql:doc/SQL_text.md
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
    -- 時刻を分単位に変換
    start_minutes := (EXTRACT(HOUR FROM start_time::TIME) * 60 + EXTRACT(MINUTE FROM start_time::TIME))::INTEGER;
    end_minutes := (EXTRACT(HOUR FROM end_time::TIME) * 60 + EXTRACT(MINUTE FROM end_time::TIME))::INTEGER;
    
    -- 指定範囲の連続レコードを挿入
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
        target_date + (minute * INTERVAL '1 minute') + (start_time::TIME - (start_minutes * INTERVAL '1 minute'))
    FROM minutes;
    
    GET DIAGNOSTICS inserted_count = ROW_COUNT;
    RETURN inserted_count;
END;
$$ LANGUAGE plpgsql;
```

*説明：指定した時刻範囲内で、1分間隔の活動レコードを自動生成して挿入します。*

### 3.6 その他の補助関数

#### 3.6.1 update_jst_timestamp
```sql:doc/SQL_text.md
CREATE OR REPLACE FUNCTION update_jst_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.created_at_jst = NEW.created_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Tokyo';
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

*説明：レコードの挿入または更新時に、UTCのタイムスタンプからJSTへの変換を行います。*

---

## 3.7 pc_name 取得用関数

```sql:doc/SQL_text.md
CREATE OR REPLACE FUNCTION get_pc_name(p_pc_id UUID)
RETURNS TEXT AS $$
DECLARE
    v_pc_name TEXT;
BEGIN
    SELECT pc_name INTO v_pc_name
    FROM user_pcs
    WHERE pc_id = p_pc_id;
    
    RETURN v_pc_name;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 使用例:
-- SELECT get_pc_name('your-pc-id-uuid-here');
```


## 4. トリガーの作成

```sql:doc/SQL_text.md
-- pc_activity_2テーブル挿入時に分計算用関数を呼び出すトリガー作成
CREATE TRIGGER set_minutes_time_jst
    BEFORE INSERT ON pc_activity_2
    FOR EACH ROW
    EXECUTE FUNCTION calculate_minutes_time_jst();
```

---

## 5. 使用例

### 5.1 利用レコードの挿入例

```sql:doc/SQL_text.md
-- シンプルな挿入例（minutes_time_jstは自動計算）
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
```

### 5.2 活動記録・視聴時間の集計例

```sql:doc/SQL_text.md
-- 特定ユーザーの2024-02-15の日付における活動数を取得
SELECT * FROM get_daily_activity_count(
    'user-123e4567-e89b-12d3-a456-111111111111'::uuid,
    '2024-02-15'
);

-- 連続活動レコードを生成する例
SELECT insert_continuous_activity(
    'user-123e4567-e89b-12d3-a456-111111111111'::uuid,
    '123e4567-e89b-12d3-a456-426614174000'::uuid,
    '09:30',
    '10:45',
    '2024-02-15'
);
```

### 5.3 視聴時間の解析例

```sql:doc/SQL_text.md
-- 合計視聴時間と実利用時間の差分を取得する例
SELECT * FROM analyze_time_difference(
    'user-123e4567-e89b-12d3-a456-111111111111'::uuid,
    '2024-02-15'
);
```

---

## 補足

- 本ドキュメントに記載のSQL定義は Supabase 上の PostgreSQL 環境を前提としています。  
- `created_at_jst` の値は、デフォルト指定やトリガー機能（calculate_minutes_time_jst、update_jst_timestamp）によって自動計算されます。  
- 各関数の使用例は、CLIツール（例：sclog.py）や Web クライアント（例：sc_time_viewer_8.html）から呼び出され、実際の集計・解析処理で利用されます。

---

以上が、実際の使い方や各定義の出力内容を反映した最新の **SQL_text.md** の内容例です。
``` 

この修正例は、各テーブルや関数の定義、トリガーの作成、そして利用例を包括的にまとめ、実際の運用に沿った内容となっています。必要に応じて、お使いの環境や最新の定義に合わせてさらに微調整してください。
