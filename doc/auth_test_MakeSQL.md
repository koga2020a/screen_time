CREATE TABLE public.auth_test_user_records (
  user_id uuid PRIMARY KEY,
  created_at timestamptz NOT NULL DEFAULT NOW(),
  created_at_jst text  -- 普通のカラムにする
);

-- トリガー関数の作成
CREATE OR REPLACE FUNCTION auth_test_update_created_at_jst()
RETURNS trigger AS $$
BEGIN
  NEW.created_at_jst := to_char(NEW.created_at AT TIME ZONE 'Asia/Tokyo', 'YYYY-MM-DD HH24:MI:SS');
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- トリガーの作成（INSERT時に実行）
CREATE TRIGGER trg_auth_test_update_created_at_jst
BEFORE INSERT OR UPDATE ON public.auth_test_user_records
FOR EACH ROW
EXECUTE FUNCTION auth_test_update_created_at_jst();
