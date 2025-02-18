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

-- インデックスの作成
CREATE INDEX idx_auth_test_user_records_user_id ON public.auth_test_user_records(user_id);

-- 更新日時を自動的に更新する関数
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 更新日時トリガーの設定
CREATE TRIGGER update_auth_test_user_records_updated_at
    BEFORE UPDATE ON public.auth_test_user_records
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- RLSの有効化
ALTER TABLE public.auth_test_user_records ENABLE ROW LEVEL SECURITY;

-- RLSポリシーの設定
CREATE POLICY "ユーザーは自分のレコードのみ参照可能" ON public.auth_test_user_records
    FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "ユーザーは自分のレコードのみ更新可能" ON public.auth_test_user_records
    FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "ユーザーは自分のレコードのみ削除可能" ON public.auth_test_user_records
    FOR DELETE
    USING (auth.uid() = user_id);

CREATE POLICY "ユーザーは自分のレコードのみ作成可能" ON public.auth_test_user_records
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- ユーザーレコード登録用RPC関数
CREATE OR REPLACE FUNCTION public.auth_test_register_user_record(_user_id UUID)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    _result JSONB;
BEGIN
    INSERT INTO public.auth_test_user_records (user_id)
    VALUES (_user_id)
    ON CONFLICT (user_id)
    DO UPDATE SET last_login = CURRENT_TIMESTAMP
    RETURNING jsonb_build_object(
        'user_id', user_id,
        'last_login', last_login,
        'created_at', created_at,
        'updated_at', updated_at
    ) INTO _result;
    
    RETURN _result;
END;
$$;

-- 権限の付与
GRANT ALL ON public.auth_test_user_records TO authenticated;
GRANT USAGE, SELECT ON SEQUENCE public.auth_test_user_records_id_seq TO authenticated;
GRANT EXECUTE ON FUNCTION public.auth_test_register_user_record(UUID) TO authenticated;