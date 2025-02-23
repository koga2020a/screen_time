auth_test_user_records
pc_activity
pc_activity_2
user_pcs
user_records
users_watch_time
watch_time_log

-- pc_activity_2 テーブルのRLS設定
ALTER TABLE public.pc_activity_2 ENABLE ROW LEVEL SECURITY;

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
参照：
