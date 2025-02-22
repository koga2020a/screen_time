
| 関数名                         | 引数                                                                                                                                       | 内部で利用しているテーブル                                                  |
| ------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------- |
| **minutes_to_time**            | `minutes INTEGER`                                                                                                                          | なし                                                                      |
| **append_pc_activity**         | `p_pc_id UUID, p_user_id UUID, p_minutes int[]`                                                                                            | なし<br>※内部では `unnest()` を用いて配列を展開しているだけ                    |
| **delete_pc_activity**         | `p_pc_id UUID, p_user_id UUID, p_minutes int[]`                                                                                            | `pc_activity_2`                                                           |
| **get_total_watch_time**       | `target_user_id UUID, target_date DATE`                                                                                                   | `watch_time_log`<br>`users_watch_time`                                      |
| **get_daily_activity_count**   | `target_user_id UUID, target_date DATE`                                                                                                   | `pc_activity_2`                                                           |
| **analyze_time_difference**    | `target_user_id UUID, target_date DATE`                                                                                                   | `pc_activity_2`<br>※また、内部で `get_total_watch_time` を利用しており、間接的に `watch_time_log` と `users_watch_time` も参照 |
| **get_time_ranges_by_pc**       | `target_user_id UUID, target_pc_id UUID, target_date DATE`                                                                                 | `pc_activity_2`                                                           |
| **get_time_ranges_by_user**     | `target_user_id UUID, target_date DATE`                                                                                                   | `pc_activity_2`                                                           |
| **insert_continuous_activity** | `target_user_id UUID, target_pc_id UUID, start_time TEXT, end_time TEXT, target_date DATE`                                                   | なし<br>※`generate_series` などの関数を利用しているが、データベーステーブルへの直接の SELECT は無し |
| **update_jst_timestamp**       | （引数なし・トリガー関数として呼び出される）                                                                                              | なし                                                                      |
| **get_pc_name**                | `p_pc_id UUID`                                                                                                                             | `user_pcs`                                                                |




### 1. テーブルの作成

#### 1.1 **pc_activity_2** テーブル

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
````

#### 1.2 **users_watch_time** テーブル

````sql:doc/SQL_text.md
-- 【users_watch_time テーブル】
-- ユーザーごとのデフォルト視聴時間（分）を管理します。
CREATE TABLE users_watch_time (
    user_id UUID NOT NULL,  -- ユーザー識別子
    default_time INTEGER NOT NULL,  -- ユーザーが設定したデフォルト視聴時間（分）
    created_at_jst TIMESTAMP WITH TIME ZONE DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'JST'),  -- レコード作成時刻 (JST)
    api_key TEXT
);
````

#### 1.3 **watch_time_log** テーブル

````sql:doc/SQL_text.md
-- 【watch_time_log テーブル】
-- ユーザーの追加視聴時間を記録するテーブルです。
CREATE TABLE watch_time_log (
    user_id UUID NOT NULL,
    added_minutes INTEGER NOT NULL,
    memo TEXT,
    input_minutes integer,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at_jst TIMESTAMP WITH TIME ZONE DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'JST')
);
````

#### 1.4 テーブルの修正（既存テーブルの JST 列更新）

````sql:doc/SQL_text.md
-- 【users_watch_time テーブルの修正】
-- created_at_jst カラムを追加し、既存データの UTC 時刻から JST を計算して更新します。
ALTER TABLE users_watch_time
ADD COLUMN created_at_jst TIMESTAMP WITH TIME ZONE;

UPDATE users_watch_time
SET created_at_jst = created_at AT TIME ZONE 'JST';

ALTER TABLE users_watch_time
ALTER COLUMN created_at_jst SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'JST');


-- 【watch_time_log テーブルの修正】
-- created_at_jst カラムを追加し、既存データを JST 表記に更新します。
ALTER TABLE watch_time_log
ADD COLUMN created_at_jst TIMESTAMP WITH TIME ZONE;

UPDATE watch_time_log
SET created_at_jst = created_at AT TIME ZONE 'JST';

ALTER TABLE watch_time_log
ALTER COLUMN created_at_jst SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'JST');
````

---

### 2. FUNCTION の作成

#### 2.1 分を時刻文字列に変換する補助関数

````sql:doc/SQL_text.md
-- 【minutes_to_time 関数】
-- 引数の分数を 2 桁ずつの "HHMM" 形式に変換します。
-- 例: 570 → "09570"（※コロンを入れる場合は適宜書式変更してください）
CREATE OR REPLACE FUNCTION minutes_to_time(minutes INTEGER)
RETURNS TEXT AS $$
BEGIN
    -- 時間部分: 分を 60 で割った値、分部分: 除算の余りを 0 埋めで連結
    RETURN LPAD((minutes / 60)::TEXT, 2, '0') || LPAD((minutes % 60)::TEXT, 2, '0');
END;
$$ LANGUAGE plpgsql;
````

#### 2.2 PC 活動記録追加用関数: **append_pc_activity**

````sql:doc/SQL_text.md
-- 【append_pc_activity 関数】
-- 指定された PC とユーザーの活動時刻リスト（分単位：int[]）から、
-- 当日の活動レコードを自動生成して挿入します。各レコードは自動で
-- created_at, created_at_jst, created_date_jst を設定します。
CREATE OR REPLACE FUNCTION append_pc_activity(
  p_pc_id uuid,
  p_user_id uuid,
  p_minutes int[]
) RETURNS SETOF pc_activity_2 AS $$
DECLARE
  base_date date := (CURRENT_TIMESTAMP AT TIME ZONE 'JST')::date;  -- 本日（JST）の日付を取得
  ts_jst timestamp;  -- ※今回は使用していませんが、拡張用の変数
BEGIN
  RETURN QUERY
  INSERT INTO pc_activity_2(
    pc_id,
    user_id,
    minutes_time_jst,
    created_at,
    created_at_jst,
    created_date_jst
  )
  SELECT 
         p_pc_id,                              -- 指定された PC ID
         p_user_id,                            -- 指定されたユーザー ID
         m,                                    -- 配列から展開した分数
         -- created_at: base_date に m 分加算後、JST の時刻を UTC 表記に変換
         ((base_date::timestamp + (m * interval '1 minute')) AT TIME ZONE 'JST'),
         -- created_at_jst: base_date に m 分加算（JST のローカル時刻）
         (base_date::timestamp + (m * interval '1 minute')),
         base_date                             -- 作成日（JST 日付）
  FROM unnest(p_minutes) as m  -- 配列を展開して各分を取得
  ON CONFLICT DO NOTHING         -- ユニーク制約違反時は挿入せずスルー
  RETURNING *;                   -- 挿入したレコードを返す
END;
$$ LANGUAGE plpgsql;
````

#### 2.3 当日の活動レコード削除関数: **delete_pc_activity**

````sql:doc/SQL_text.md
-- 【delete_pc_activity 関数】
-- 本日分の活動記録のうち、指定された PC・ユーザー・分数に一致するレコードを削除します。
CREATE OR REPLACE FUNCTION delete_pc_activity(
  p_pc_id uuid,
  p_user_id uuid,
  p_minutes int[]
) RETURNS SETOF pc_activity_2 AS $$
DECLARE
  base_date date := (CURRENT_TIMESTAMP AT TIME ZONE 'JST')::date;  -- 現在の JST 日付
BEGIN
  RETURN QUERY
  DELETE FROM pc_activity_2
  WHERE pc_id = p_pc_id
    AND user_id = p_user_id
    AND created_date_jst = base_date  -- 本日分のレコードのみ対象
    AND minutes_time_jst IN (SELECT unnest(p_minutes))  -- 指定された分数のレコードを削除
  RETURNING *;  -- 削除されたレコードを返す
END;
$$ LANGUAGE plpgsql;
````

#### 2.4 利用時間・視聴時間の集計・解析関数

##### 2.4.1 **get_total_watch_time**

````sql:doc/SQL_text.md
-- 【get_total_watch_time 関数】
-- 指定ユーザーの特定日の追加視聴時間（watch_time_log）および
-- 最新のデフォルト視聴時間（users_watch_time）を集計し、
-- 総合的な視聴可能時間を計算します。
CREATE OR REPLACE FUNCTION get_total_watch_time(
    target_user_id UUID,
    target_date DATE
)
RETURNS TABLE (
    total_added_minutes BIGINT,  -- 当日の追加視聴時間合計（分）
    default_time INTEGER,          -- 最新のデフォルト視聴時間（分）
    total_time BIGINT              -- 総視聴可能時間（追加 + デフォルト）
) AS $$
BEGIN
    RETURN QUERY
    WITH added_time AS (
        -- watch_time_log から指定日付の追加視聴時間を集計
        SELECT COALESCE(SUM(added_minutes), 0) AS sum_added_minutes
        FROM watch_time_log
        WHERE user_id = target_user_id
          AND DATE(created_at_jst) = target_date
    ),
    default_watch_time AS (
        -- users_watch_time から最新の default_time を取得
        SELECT uwt.default_time
        FROM users_watch_time uwt
        WHERE uwt.user_id = target_user_id
        ORDER BY uwt.created_at_jst DESC
        LIMIT 1
    )
    SELECT 
        at.sum_added_minutes,
        COALESCE(dwt.default_time, 0),  -- default_time が NULL の場合は 0 とする
        at.sum_added_minutes + COALESCE(dwt.default_time, 0)
    FROM added_time at
    CROSS JOIN default_watch_time dwt;
END;
$$ LANGUAGE plpgsql;
````

##### 2.4.2 **get_daily_activity_count**

````sql:doc/SQL_text.md
-- 【get_daily_activity_count 関数】
-- 指定ユーザーの特定日付における、ユニークな活動分数（minutes_time_jst）の
-- 件数を集計して返します。
CREATE OR REPLACE FUNCTION get_daily_activity_count(
    target_user_id UUID,
    target_date DATE
)
RETURNS TABLE (
    activity_count BIGINT  -- ユニークな利用分数の件数
) AS $$
BEGIN
    RETURN QUERY
    SELECT COUNT(DISTINCT minutes_time_jst)
    FROM pc_activity_2
    WHERE user_id = target_user_id
      AND DATE(created_at_jst) = target_date;
END;
$$ LANGUAGE plpgsql;
````

##### 2.4.3 **analyze_time_difference**

````sql:doc/SQL_text.md
-- 【analyze_time_difference 関数】
-- 指定ユーザーの当日のユニークな利用時間 (活動分数) と、
-- 視聴可能な総時間（追加視聴 + デフォルト視聴時間）との差分を計算し返します。
CREATE OR REPLACE FUNCTION analyze_time_difference(
    target_user_id UUID,
    target_date DATE
)
RETURNS TABLE (
    unique_minutes BIGINT,   -- 実際の活動レコード数（ユニークな分）
    total_watch_time BIGINT,   -- 利用可能な視聴時間の総和（分）
    time_difference BIGINT    -- activity_count - total_watch_time の差分
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
````

#### 2.5 PC利用時間分布取得系の関数

##### 2.5.1 **get_time_ranges_by_pc**

````sql:doc/SQL_text.md
-- 【get_time_ranges_by_pc 関数】
-- 指定された PC の当日の利用記録から、連続した利用時間帯を抽出して
-- "HHMM-HHMM" 形式の文字列で返します。
CREATE OR REPLACE FUNCTION get_time_ranges_by_pc(
    target_user_id UUID,
    target_pc_id UUID,
    target_date DATE
)
RETURNS TABLE (
    time_range TEXT  -- 利用時間帯（例："0930-1015"）
) AS $$
WITH grouped_times AS (
    -- 各レコードの分数から、連続性の判定用グループ番号を計算
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
    -- 連続する時間帯ごとに、開始と終了の分数を求める
    SELECT 
        MIN(minutes_time_jst) AS range_start,
        MAX(minutes_time_jst) AS range_end
    FROM grouped_times
    GROUP BY grp
    ORDER BY range_start
)
-- 分を "HHMM" 文字列に変換して、範囲を連結する
SELECT minutes_to_time(range_start) || '-' || minutes_to_time(range_end) AS time_range
FROM ranges;
$$ LANGUAGE SQL;
````

##### 2.5.2 **get_time_ranges_by_user**

````sql:doc/SQL_text.md
-- 【get_time_ranges_by_user 関数】
-- 指定ユーザーの当日の PC 利用記録を、各 PC ごとにまとめ、
-- 各 PC の活動回数と、連続利用の時間帯（配列）を返します。
CREATE OR REPLACE FUNCTION get_time_ranges_by_user(
    target_user_id UUID,
    target_date DATE
)
RETURNS TABLE (
    pc_id UUID,             -- PC の識別子
    activity_count BIGINT,  -- 当該 PC でのユニークな活動分数の数
    time_ranges TEXT[]      -- 各連続した利用区間を示す文字列配列
) AS $$
WITH ordered_data AS (
    -- PC ごとに各活動分数とその直前の値を取得
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
    -- 連続性を判定するために、グループ識別子を計算
    SELECT pc_id, minutes_time_jst,
           minutes_time_jst - ROW_NUMBER() OVER (PARTITION BY pc_id ORDER BY minutes_time_jst) as grp
    FROM ordered_data
), ranges AS (
    -- 各グループごとに開始時刻と終了時刻（分）を取得
    SELECT pc_id,
           MIN(minutes_time_jst) as range_start,
           MAX(minutes_time_jst) as range_end
    FROM grouped
    GROUP BY pc_id, grp
), activity_counts AS (
    -- PC ごとのユニークな活動回数をカウント
    SELECT pc_id, COUNT(DISTINCT minutes_time_jst) as activity_count
    FROM pc_activity_2
    WHERE user_id = target_user_id
      AND DATE(created_at_jst) = target_date
    GROUP BY pc_id
), formatted AS (
    -- 取得した分数を "HHMM-HHMM" 形式の文字列配列へ変換
    SELECT pc_id,
           array_agg(
             minutes_to_time(range_start) || '-' || minutes_to_time(range_end)
             ORDER BY range_start
           ) as time_ranges
    FROM ranges
    GROUP BY pc_id
)
-- activity_counts と formatted を結合して結果を返す
SELECT a.pc_id, a.activity_count, f.time_ranges
FROM activity_counts a
JOIN formatted f ON a.pc_id = f.pc_id;
$$ LANGUAGE SQL;
````

#### 2.6 連続活動レコードを挿入する関数: **insert_continuous_activity**

````sql:doc/SQL_text.md
-- 【insert_continuous_activity 関数】
-- 指定された期間（start_time～end_time, "HH:MM" 形式）において、
-- 1 分間隔の活動レコードを自動生成して挿入します。
CREATE OR REPLACE FUNCTION insert_continuous_activity(
    target_user_id UUID,
    target_pc_id UUID,
    start_time TEXT,  -- 開始時刻 ("HH:MM" 形式)
    end_time TEXT,    -- 終了時刻 ("HH:MM" 形式)
    target_date DATE  -- 対象日付 (YYYY-MM-DD 形式)
)
RETURNS INTEGER AS $$
DECLARE
    start_minutes INTEGER;
    end_minutes INTEGER;
    inserted_count INTEGER;
BEGIN
    -- 開始時刻と終了時刻を「分」に変換
    start_minutes := (EXTRACT(HOUR FROM start_time::TIME) * 60 + EXTRACT(MINUTE FROM start_time::TIME))::INTEGER;
    end_minutes := (EXTRACT(HOUR FROM end_time::TIME) * 60 + EXTRACT(MINUTE FROM end_time::TIME))::INTEGER;
    
    -- generate_series を用いて、指定範囲内の各分を生成しレコードを挿入
    WITH minutes AS (
        SELECT generate_series(start_minutes, end_minutes) AS minute
    )
    INSERT INTO pc_activity_2 (
        pc_id,
        user_id,
        created_at_jst  -- 作成時刻（JST）：トリガーで他のカラムが補完される
    )
    SELECT 
        target_pc_id,
        target_user_id,
        -- 対象日付に、各分数分の時間を足す
        target_date + (minute * INTERVAL '1 minute') + (start_time::TIME - (start_minutes * INTERVAL '1 minute'))
    FROM minutes;
    
    -- 挿入された行数を取得
    GET DIAGNOSTICS inserted_count = ROW_COUNT;
    RETURN inserted_count;  -- 挿入されたレコード数を返す
END;
$$ LANGUAGE plpgsql;
````

#### 2.7 その他の補助関数

##### 2.7.1 **update_jst_timestamp**

````sql:doc/SQL_text.md
-- 【update_jst_timestamp 関数】
-- レコードの挿入または更新時に、UTC のタイムスタンプ (created_at) から
-- JST の時刻 (created_at_jst) を計算して設定するトリガー関数です。
CREATE OR REPLACE FUNCTION update_jst_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.created_at_jst = NEW.created_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Tokyo';
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
````

##### 2.7.2 **get_pc_name**

````sql:doc/SQL_text.md
-- 【get_pc_name 関数】
-- 指定された PC ID に対応する PC 名を user_pcs テーブルから取得して返します。
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
````

---

### 3. トリガーの作成

````sql:doc/SQL_text.md
-- 【トリガー set_minutes_time_jst】
-- pc_activity_2 テーブルにレコード挿入時、calculate_minutes_time_jst 関数を
-- 呼び出して created_at_jst から利用時間（分）を自動計算します。
CREATE TRIGGER set_minutes_time_jst
    BEFORE INSERT ON pc_activity_2
    FOR EACH ROW
    EXECUTE FUNCTION calculate_minutes_time_jst();
````

---

### 4. 使用例

#### 4.1 利用レコード挿入例

````sql:doc/SQL_text.md
-- 簡単な挿入例
-- pc_id と user_id を指定し、その他の値はデフォルト値で自動設定されます。
INSERT INTO pc_activity_2 (
    pc_id,
    user_id
) VALUES (
    '123e4567-e89b-12d3-a456-426614174000'::uuid,
    'user-123e4567-e89b-12d3-a456-111111111111'::uuid
);

-- 特定の時刻（JST）を指定して挿入する例
INSERT INTO pc_activity_2 (
    pc_id,
    user_id,
    created_at_jst
) VALUES (
    '123e4567-e89b-12d3-a456-426614174000'::uuid,
    'user-123e4567-e89b-12d3-a456-111111111111'::uuid,
    '2024-02-15 09:30:00 JST'
);
````

#### 4.2 活動記録・視聴時間の集計例

````sql:doc/SQL_text.md
-- 特定ユーザーの 2024-02-15 の活動回数を集計する例
SELECT * FROM get_daily_activity_count(
    'user-123e4567-e89b-12d3-a456-111111111111'::uuid,
    '2024-02-15'
);

-- 連続活動レコードを自動生成して挿入する例
SELECT insert_continuous_activity(
    'user-123e4567-e89b-12d3-a456-111111111111'::uuid,
    '123e4567-e89b-12d3-a456-426614174000'::uuid,
    '09:30',
    '10:45',
    '2024-02-15'
);
````

#### 4.3 視聴時間の解析例

````sql:doc/SQL_text.md
-- 合計視聴時間と実際の活動時間との差分を解析する例
SELECT * FROM analyze_time_difference(
    'user-123e4567-e89b-12d3-a456-111111111111'::uuid,
    '2024-02-15'
);
````

#### 4.4 時間帯ごとの許可状態を返す関数

````sql:doc/SQL_text.md
CREATE OR REPLACE FUNCTION get_extension_time_ranges(
  target_user_id UUID,
  target_date DATE
)
RETURNS TABLE (
  pc_id UUID,
  time_ranges TEXT[]
) AS $$
BEGIN
  RETURN QUERY
  SELECT 
    wtl.pc_id,
    array_agg(
      to_char(wtl.created_at_jst - (wtl.added_minutes - wtl.input_minutes || ' minutes')::interval, 'HH24:MI') || 
      '-' || 
      to_char(wtl.created_at_jst, 'HH24:MI')
    ) as time_ranges
  FROM watch_time_log wtl
  WHERE wtl.user_id = target_user_id
    AND DATE(wtl.created_at_jst) = target_date
    AND wtl.added_minutes > wtl.input_minutes
  GROUP BY wtl.pc_id;
END;
$$ LANGUAGE plpgsql;
````
