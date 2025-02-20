-- 【users_watch_time テーブルの拡張】
-- 既存のテーブルに api_key カラムを追加（既存機能には影響を与えません）
ALTER TABLE users_watch_time
ADD COLUMN api_key TEXT;





-------------------------------
-- 1. API key の検証用 FUNCTION
-------------------------------
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

-------------------------------
-- 2. append_pc_activity のラッパー関数
-------------------------------
CREATE OR REPLACE FUNCTION append_pc_activity(
    p_api_key TEXT,
    p_pc_id UUID,
    p_user_id UUID,
    p_minutes INT[]
)
RETURNS SETOF pc_activity_2 AS $$
DECLARE
    is_valid BOOLEAN;
BEGIN
    is_valid := validate_user_api_key_ext(p_user_id, p_api_key);
    IF NOT is_valid THEN
        RAISE EXCEPTION 'Invalid API key for user %', p_user_id;
    END IF;
    RETURN QUERY
      SELECT * FROM append_pc_activity(p_pc_id, p_user_id, p_minutes);
END;
$$ LANGUAGE plpgsql;

-------------------------------
-- 3. delete_pc_activity のラッパー関数
-------------------------------
CREATE OR REPLACE FUNCTION delete_pc_activity(
    p_api_key TEXT,
    p_pc_id UUID,
    p_user_id UUID,
    p_minutes INT[]
)
RETURNS SETOF pc_activity_2 AS $$
DECLARE
    is_valid BOOLEAN;
BEGIN
    is_valid := validate_user_api_key_ext(p_user_id, p_api_key);
    IF NOT is_valid THEN
        RAISE EXCEPTION 'Invalid API key for user %', p_user_id;
    END IF;
    RETURN QUERY
      SELECT * FROM delete_pc_activity(p_pc_id, p_user_id, p_minutes);
END;
$$ LANGUAGE plpgsql;

-------------------------------
-- 4. get_total_watch_time のラッパー関数
-------------------------------
CREATE OR REPLACE FUNCTION get_total_watch_time(
    p_api_key TEXT,
    target_user_id UUID,
    target_date DATE
)
RETURNS TABLE (
    total_added_minutes BIGINT,
    default_time INTEGER,
    total_time BIGINT
) AS $$
BEGIN
    IF NOT validate_user_api_key_ext(target_user_id, p_api_key) THEN
        RAISE EXCEPTION 'Invalid API key for user %', target_user_id;
    END IF;
    RETURN QUERY
      SELECT * FROM get_total_watch_time(target_user_id, target_date);
END;
$$ LANGUAGE plpgsql;

-------------------------------
-- 5. get_daily_activity_count のラッパー関数
-------------------------------
CREATE OR REPLACE FUNCTION get_daily_activity_count(
    p_api_key TEXT,
    target_user_id UUID,
    target_date DATE
)
RETURNS TABLE (
    activity_count BIGINT
) AS $$
BEGIN
    IF NOT validate_user_api_key_ext(target_user_id, p_api_key) THEN
        RAISE EXCEPTION 'Invalid API key for user %', target_user_id;
    END IF;
    RETURN QUERY
      SELECT * FROM get_daily_activity_count(target_user_id, target_date);
END;
$$ LANGUAGE plpgsql;

-------------------------------
-- 6. analyze_time_difference のラッパー関数
-------------------------------
CREATE OR REPLACE FUNCTION analyze_time_difference(
    p_api_key TEXT,
    target_user_id UUID,
    target_date DATE
)
RETURNS TABLE (
    unique_minutes BIGINT,
    total_watch_time BIGINT,
    time_difference BIGINT
) AS $$
BEGIN
    IF NOT validate_user_api_key_ext(target_user_id, p_api_key) THEN
        RAISE EXCEPTION 'Invalid API key for user %', target_user_id;
    END IF;
    RETURN QUERY
      SELECT * FROM analyze_time_difference(target_user_id, target_date);
END;
$$ LANGUAGE plpgsql;

-------------------------------
-- 7. get_time_ranges_by_pc のラッパー関数
-------------------------------
CREATE OR REPLACE FUNCTION get_time_ranges_by_pc(
    p_api_key TEXT,
    target_user_id UUID,
    target_pc_id UUID,
    target_date DATE
)
RETURNS TABLE (
    time_range TEXT
) AS $$
BEGIN
    IF NOT validate_user_api_key_ext(target_user_id, p_api_key) THEN
        RAISE EXCEPTION 'Invalid API key for user %', target_user_id;
    END IF;
    RETURN QUERY
      SELECT * FROM get_time_ranges_by_pc(target_user_id, target_pc_id, target_date);
END;
$$ LANGUAGE plpgsql;

-------------------------------
-- 8. get_time_ranges_by_user のラッパー関数
-------------------------------
CREATE OR REPLACE FUNCTION get_time_ranges_by_user(
    p_api_key TEXT,
    target_user_id UUID,
    target_date DATE
)
RETURNS TABLE (
    pc_id UUID,
    activity_count BIGINT,
    time_ranges TEXT[]
) AS $$
BEGIN
    IF NOT validate_user_api_key_ext(target_user_id, p_api_key) THEN
        RAISE EXCEPTION 'Invalid API key for user %', target_user_id;
    END IF;
    RETURN QUERY
      SELECT * FROM get_time_ranges_by_user(target_user_id, target_date);
END;
$$ LANGUAGE plpgsql;

-------------------------------
-- 9. insert_continuous_activity のラッパー関数
-------------------------------
CREATE OR REPLACE FUNCTION insert_continuous_activity(
    p_api_key TEXT,
    target_user_id UUID,
    target_pc_id UUID,
    start_time TEXT,
    end_time TEXT,
    target_date DATE
)
RETURNS INTEGER AS $$
BEGIN
    IF NOT validate_user_api_key_ext(target_user_id, p_api_key) THEN
        RAISE EXCEPTION 'Invalid API key for user %', target_user_id;
    END IF;
    RETURN insert_continuous_activity(target_user_id, target_pc_id, start_time, end_time, target_date);
END;
$$ LANGUAGE plpgsql;
