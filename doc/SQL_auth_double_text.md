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


## api_key を使用した版のみ用意されている関数

-------------------------------
-- 10. pc_name を取得する関数
-------------------------------
CREATE OR REPLACE FUNCTION get_pc_name_by_user(
    p_api_key TEXT,
    p_user_id UUID,
    p_pc_id UUID
)
RETURNS TEXT AS $$
DECLARE
    is_valid BOOLEAN;
    v_pc_name TEXT;
BEGIN
    -- APIキーの検証
    is_valid := validate_user_api_key_ext(p_user_id, p_api_key);
    IF NOT is_valid THEN
        RAISE EXCEPTION 'Invalid API key for user %', p_user_id;
    END IF;

    -- pc_name の取得
    SELECT user_pcs.pc_name INTO v_pc_name
    FROM user_pcs
    WHERE user_pcs.user_id = p_user_id AND user_pcs.pc_id = p_pc_id;

    -- 取得できなかった場合の処理
    IF v_pc_name IS NULL THEN
        RAISE EXCEPTION 'No matching PC found for user_id % and pc_id %', p_user_id, p_pc_id;
    END IF;

    RETURN v_pc_name;
END;
$$ LANGUAGE plpgsql;

-------------------------------
-- 11. check_user_exists_by_api の関数
-------------------------------
CREATE OR REPLACE FUNCTION check_user_exists_by_api(
    p_api_key TEXT,
    p_user_id UUID
)
RETURNS BOOLEAN AS $$
DECLARE
    is_valid BOOLEAN;
    user_exists BOOLEAN;
BEGIN
    -- APIキーの検証
    is_valid := validate_user_api_key_ext(p_user_id, p_api_key);
    IF NOT is_valid THEN
        RAISE EXCEPTION 'Invalid API key for user %', p_user_id;
    END IF;

    -- ユーザーの存在確認
    SELECT EXISTS (
        SELECT 1
        FROM users_watch_time
        WHERE users_watch_time.user_id = p_user_id
    ) INTO user_exists;

    RETURN user_exists;
END;
$$ LANGUAGE plpgsql;

-------------------------------
-- 12. get_default_time_by_api の関数
-------------------------------
CREATE OR REPLACE FUNCTION get_default_time_by_api(
    p_api_key TEXT,
    p_user_id UUID
)
RETURNS INTEGER AS $$
DECLARE
    is_valid BOOLEAN;
    v_default_time INTEGER;
BEGIN
    -- APIキーの検証
    is_valid := validate_user_api_key_ext(p_user_id, p_api_key);
    IF NOT is_valid THEN
        RAISE EXCEPTION 'Invalid API key for user %', p_user_id;
    END IF;

    -- default_time の取得
    SELECT users_watch_time.default_time INTO v_default_time
    FROM users_watch_time
    WHERE users_watch_time.user_id = p_user_id;

    -- 取得できなかった場合の処理
    IF v_default_time IS NULL THEN
        RAISE EXCEPTION 'No default time found for user_id %', p_user_id;
    END IF;

    RETURN v_default_time;
END;
$$ LANGUAGE plpgsql;

-------------------------------
-- 13. get_total_added_minutes_by_api の関数
-------------------------------
CREATE OR REPLACE FUNCTION get_total_added_minutes_by_api(
    p_api_key TEXT,
    p_user_id UUID,
    p_start_time TIMESTAMPTZ,
    p_end_time TIMESTAMPTZ
)
RETURNS INTEGER AS $$
DECLARE
    is_valid BOOLEAN;
    v_total_minutes INTEGER;
BEGIN
    -- APIキーの検証
    is_valid := validate_user_api_key_ext(p_user_id, p_api_key);
    IF NOT is_valid THEN
        RAISE EXCEPTION 'Invalid API key for user %', p_user_id;
    END IF;

    -- 追加された時間の合計を取得
    SELECT COALESCE(SUM(added_minutes), 0) INTO v_total_minutes
    FROM watch_time_log
    WHERE user_id = p_user_id
    AND created_at >= p_start_time
    AND created_at < p_end_time;

    RETURN v_total_minutes;
END;
$$ LANGUAGE plpgsql;

-------------------------------
-- 14. get_total_usage_minutes_by_api の関数
-------------------------------
CREATE OR REPLACE FUNCTION get_total_usage_minutes_by_api(
    p_api_key TEXT,
    p_user_id UUID,
    p_start_time TIMESTAMPTZ,
    p_end_time TIMESTAMPTZ
)
RETURNS INTEGER AS $$
DECLARE
    is_valid BOOLEAN;
    v_total_minutes INTEGER;
BEGIN
    -- APIキーの検証
    is_valid := validate_user_api_key_ext(p_user_id, p_api_key);
    IF NOT is_valid THEN
        RAISE EXCEPTION 'Invalid API key for user %', p_user_id;
    END IF;

    -- 重複を除いた利用分数を取得
    SELECT COUNT(DISTINCT minutes_time_jst) INTO v_total_minutes
    FROM pc_activity_2
    WHERE user_id = p_user_id
    AND created_at >= p_start_time
    AND created_at < p_end_time;

    RETURN v_total_minutes;
END;
$$ LANGUAGE plpgsql;

-------------------------------
-- 15. get_pc_id_by_name_and_user の関数
-------------------------------
CREATE OR REPLACE FUNCTION get_pc_id_by_name_and_user(
    p_api_key TEXT,
    p_user_id UUID,
    p_pc_name TEXT
)
RETURNS UUID AS $$
DECLARE
    is_valid BOOLEAN;
    v_pc_id UUID;
BEGIN
    -- APIキーの検証
    is_valid := validate_user_api_key_ext(p_user_id, p_api_key);
    IF NOT is_valid THEN
        RAISE EXCEPTION 'Invalid API key for user %', p_user_id;
    END IF;

    -- pc_id の取得
    SELECT pc_id INTO v_pc_id
    FROM user_pcs
    WHERE user_id = p_user_id AND pc_name = p_pc_name;

    RETURN v_pc_id;
END;
$$ LANGUAGE plpgsql;

-------------------------------
-- 16. get_pc_activity_minutes_by_api の関数
-------------------------------
CREATE OR REPLACE FUNCTION get_pc_activity_minutes_by_api(
    p_api_key TEXT,
    p_user_id UUID,
    p_start_time TIMESTAMPTZ,
    p_end_time TIMESTAMPTZ
)
RETURNS TABLE (minutes_time_jst INTEGER) AS $$
DECLARE
    is_valid BOOLEAN;
BEGIN
    -- APIキーの検証
    is_valid := validate_user_api_key_ext(p_user_id, p_api_key);
    IF NOT is_valid THEN
        RAISE EXCEPTION 'Invalid API key for user %', p_user_id;
    END IF;

    RETURN QUERY
    SELECT pc_activity_2.minutes_time_jst
    FROM pc_activity_2
    WHERE user_id = p_user_id
    AND created_at >= p_start_time
    AND created_at < p_end_time
    ORDER BY minutes_time_jst;
END;
$$ LANGUAGE plpgsql;

-------------------------------
-- 17. get_pc_activity_minutes_by_pc_and_api の関数
-------------------------------
CREATE OR REPLACE FUNCTION get_pc_activity_minutes_by_pc_and_api(
    p_api_key TEXT,
    p_user_id UUID,
    p_pc_id UUID,
    p_start_time TIMESTAMPTZ,
    p_end_time TIMESTAMPTZ
)
RETURNS TABLE (minutes_time_jst INTEGER) AS $$
DECLARE
    is_valid BOOLEAN;
BEGIN
    -- APIキーの検証
    is_valid := validate_user_api_key_ext(p_user_id, p_api_key);
    IF NOT is_valid THEN
        RAISE EXCEPTION 'Invalid API key for user %', p_user_id;
    END IF;

    RETURN QUERY
    SELECT pc_activity_2.minutes_time_jst
    FROM pc_activity_2
    WHERE user_id = p_user_id
    AND pc_id = p_pc_id
    AND created_at >= p_start_time
    AND created_at < p_end_time
    ORDER BY minutes_time_jst;
END;
$$ LANGUAGE plpgsql;
