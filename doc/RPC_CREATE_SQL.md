auth_test_user_records
pc_activity
pc_activity_2
user_pcs
user_records
users_watch_time
watch_time_log

-- pc_activity_2 テーブルのRLS設定
ALTER TABLE public.pc_activity_2 ENABLE ROW LEVEL SECURITY;
ALTER TABLE pc_activity_2 ADD COLUMN id SERIAL PRIMARY KEY;

CREATE POLICY "ユーザーは自分のレコードのみアクセス可能" ON public.pc_activity_2
    FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- pc_activity テーブルのRLS設定
ALTER TABLE public.pc_activity ENABLE ROW LEVEL SECURITY;

CREATE POLICY "ユーザーは自分のレコードのみアクセス可能" ON public.pc_activity
    FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- user_pcs テーブルのRLS設定
ALTER TABLE public.user_pcs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "ユーザーは自分のPCレコードのみアクセス可能" ON public.user_pcs
    FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- users_watch_time テーブルのRLS設定
ALTER TABLE public.users_watch_time ENABLE ROW LEVEL SECURITY;

CREATE POLICY "ユーザーは自分の視聴時間設定のみアクセス可能" ON public.users_watch_time
    FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- watch_time_log テーブルのRLS設定
ALTER TABLE public.watch_time_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY "ユーザーは自分の視聴時間ログのみアクセス可能" ON public.watch_time_log
    FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- user_records テーブルのRLS設定
ALTER TABLE public.user_records ENABLE ROW LEVEL SECURITY;

CREATE POLICY "ユーザーは自分のレコードのみアクセス可能" ON public.user_records
    FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- auth_test_user_records テーブルのRLS設定
CREATE OR REPLACE FUNCTION auth_test_register_user_record(_user_id UUID)
RETURNS SETOF auth_test_user_records
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    INSERT INTO auth_test_user_records (user_id)
    VALUES (_user_id)
    RETURNING *;
END;
$$;

-- get_pc_name関数
CREATE OR REPLACE FUNCTION get_pc_name(p_pc_id UUID)
RETURNS TEXT
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_pc_name TEXT;
BEGIN
    SELECT pc_name INTO v_pc_name
    FROM user_pcs
    WHERE pc_id = p_pc_id;
    
    RETURN v_pc_name;
END;
$$;

-- get_total_watch_time関数
CREATE OR REPLACE FUNCTION get_total_watch_time(
    target_user_id UUID,
    target_date DATE
)
RETURNS TABLE (
    total_added_minutes BIGINT,
    default_time INTEGER,
    total_time BIGINT
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
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
$$;

-- analyze_time_difference関数
CREATE OR REPLACE FUNCTION analyze_time_difference(
    target_user_id UUID,
    target_date DATE
)
RETURNS TABLE (
    unique_minutes BIGINT,
    total_watch_time BIGINT,
    time_difference BIGINT
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
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
$$;

-- get_time_ranges_by_user関数
CREATE OR REPLACE FUNCTION get_time_ranges_by_user(
    target_user_id UUID,
    target_date DATE
)
RETURNS TABLE (
    pc_id UUID,
    activity_count BIGINT,
    time_ranges TEXT[]
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
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
END;
$$;

-- get_watch_time_logs関数
CREATE OR REPLACE FUNCTION get_watch_time_logs(
    p_user_id UUID,
    p_start_time TIMESTAMPTZ,
    p_end_time TIMESTAMPTZ
)
RETURNS TABLE (
    created_at_jst TIMESTAMPTZ,
    input_minutes INTEGER,
    added_minutes INTEGER,
    memo TEXT
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    IF auth.uid() != p_user_id THEN
        RAISE EXCEPTION 'Unauthorized access';
    END IF;

    RETURN QUERY
    SELECT wtl.created_at_jst,
           wtl.input_minutes,
           wtl.added_minutes,
           wtl.memo
    FROM watch_time_log wtl
    WHERE wtl.user_id = p_user_id
      AND wtl.created_at >= p_start_time
      AND wtl.created_at < p_end_time
    ORDER BY wtl.created_at_jst DESC;
END;
$$;

-- insert_watch_time_log関数
CREATE OR REPLACE FUNCTION insert_watch_time_log(
    p_user_id UUID,
    p_added_minutes INTEGER,
    p_input_minutes INTEGER DEFAULT NULL,
    p_memo TEXT DEFAULT NULL
)
RETURNS SETOF watch_time_log
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    IF auth.uid() != p_user_id THEN
        RAISE EXCEPTION 'Unauthorized access';
    END IF;

    RETURN QUERY
    INSERT INTO watch_time_log (
        user_id,
        added_minutes,
        input_minutes,
        memo,
        created_at,
        created_at_jst
    )
    VALUES (
        p_user_id,
        p_added_minutes,
        COALESCE(p_input_minutes, p_added_minutes),
        p_memo,
        NOW(),
        (NOW() AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Tokyo')
    )
    RETURNING *;
END;
$$;

-- insert_continuous_activity関数
CREATE OR REPLACE FUNCTION insert_continuous_activity(
    target_user_id UUID,
    target_pc_id UUID,
    start_time TEXT,
    end_time TEXT,
    target_date DATE
)
RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    start_minutes INTEGER;
    end_minutes INTEGER;
    inserted_count INTEGER;
BEGIN
    IF auth.uid() != target_user_id THEN
        RAISE EXCEPTION 'Unauthorized access';
    END IF;

    start_minutes := (EXTRACT(HOUR FROM start_time::TIME) * 60 + EXTRACT(MINUTE FROM start_time::TIME))::INTEGER;
    end_minutes := (EXTRACT(HOUR FROM end_time::TIME) * 60 + EXTRACT(MINUTE FROM end_time::TIME))::INTEGER;
    
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
        target_date + (minute * INTERVAL '1 minute') + (start_time::TIME - (start_minutes * INTERVAL '1 minute'));

    GET DIAGNOSTICS inserted_count = ROW_COUNT;
    RETURN inserted_count;
END;
$$;

-- append_pc_activity関数
CREATE OR REPLACE FUNCTION append_pc_activity(
    p_pc_id UUID,
    p_user_id UUID,
    p_minutes INTEGER[]
)
RETURNS SETOF pc_activity_2
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    base_date DATE := (CURRENT_TIMESTAMP AT TIME ZONE 'JST')::DATE;
BEGIN
    IF auth.uid() != p_user_id THEN
        RAISE EXCEPTION 'Unauthorized access';
    END IF;

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
        p_pc_id,
        p_user_id,
        m,
        ((base_date::TIMESTAMP + (m * INTERVAL '1 minute')) AT TIME ZONE 'JST'),
        (base_date::TIMESTAMP + (m * INTERVAL '1 minute')),
        base_date
    FROM unnest(p_minutes) as m
    ON CONFLICT DO NOTHING
    RETURNING *;
END;
$$;

-- delete_pc_activity関数
CREATE OR REPLACE FUNCTION delete_pc_activity(
    p_pc_id UUID,
    p_user_id UUID,
    p_minutes INTEGER[]
)
RETURNS SETOF pc_activity_2
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    base_date DATE := (CURRENT_TIMESTAMP AT TIME ZONE 'JST')::DATE;
BEGIN
    IF auth.uid() != p_user_id THEN
        RAISE EXCEPTION 'Unauthorized access';
    END IF;

    RETURN QUERY
    DELETE FROM pc_activity_2
    WHERE pc_id = p_pc_id
      AND user_id = p_user_id
      AND created_date_jst = base_date
      AND minutes_time_jst = ANY(p_minutes)
    RETURNING *;
END;
$$;

-- get_user_pcs関数
CREATE OR REPLACE FUNCTION get_user_pcs(p_user_id UUID)
RETURNS SETOF user_pcs
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    IF auth.uid() != p_user_id THEN
        RAISE EXCEPTION 'Unauthorized access';
    END IF;

    RETURN QUERY
    SELECT *
    FROM user_pcs
    WHERE user_id = p_user_id;
END;
$$;
