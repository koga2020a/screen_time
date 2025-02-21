# Screen Time Management CLI ツール

このリポジトリは、PCのアクティビティログおよび視聴時間の管理を行うための CLI ツールと、Windows 環境での自動実行をサポートする AutoHotkey スクリプトを提供します。Python スクリプトで各種コマンドを実装しており、Supabase をバックエンドにしてデータの記録・照会を行います。

---

## 目次

- [概要](#概要)
- [特徴](#特徴)
- [前提条件](#前提条件)
- [セットアップ](#セットアップ)
  - [Python 環境および依存ライブラリ](#python-環境および依存ライブラリ)
  - [.env ファイルの設定](#env-ファイルの設定)
  - [Supabaseテーブルの設定](#supabasetableの設定)
  - [sclog.py の EXE 化](#sclogpy-の-exe-化)
- [コマンドの使い方](#コマンドの使い方)
  - [log-pc-activity](#log-pc-activity)
  - [check-watch-time](#check-watch-time)
  - [get-total-usage](#get-total-usage)
  - [get-pc-usage](#get-pc-usage)
  - [get-allowed-time](#get-allowed-time)
  - [check-usage](#check-usage)
  - [is-able-watch](#is-able-watch)
  - [insert-watch-log](#insert-watch-log)
- [AutoHotkey スクリプト (over_windows.ahk) について](#autohotkey-スクリプト-over_windowsahk-について)
- [変更点と注意事項](#変更点と注意事項)
- [トラブルシューティング](#トラブルシューティング)
- [追加したストアドプロシージャの説明](#追加したストアドプロシージャの説明)
- [ライセンス](#ライセンス)

---

## 概要

本ツールは、PC の利用時間管理や視聴可能時間の制御を目的としています。  
主に以下のデータ操作が可能です:

- ユーザごとの視聴時間の記録（PC アクティビティログ）
- 利用可能な視聴時間の計算（デフォルト時間＋追加分 － 使用済み分数）
- 各 PC ごとおよび全 PC の利用状況の照会
- 利用可能かどうかの判定（`T`：視聴可能 / `F`：視聴不可 / `E`：エラー）
- 視聴時間ログの挿入（増減の操作に対応）

Supabase の REST API を利用して、`users_watch_time`、`pc_activity`、`watch_time_log` の各テーブルに対して操作を行ないます。

---

## 特徴

- **UUID バリデーション:** ユーザIDおよび PC ID の正しさをチェックします。
- **リアルタイムモニタリング:** AutoHotkey スクリプトにより、PC の利用状況を定期的に記録・監視することが可能です。
- **柔軟な出力:** 結果は標準出力または指定したファイルへ出力可能です。  
- **エラーハンドリング:** API のレスポンスが空、またはエラーとなった場合のハンドリングがなされています。

---

## 前提条件

- **Python 3.6 以上**  
- **Supabase アカウント:**  
  Supabase の URL および API キーが必要です。  
- **AutoHotkey:**  
  Windows 環境での自動化のために [AutoHotkey](https://www.autohotkey.com/) をインストールしてください。

---

## セットアップ

### Python 環境および依存ライブラリ

1. Python がインストールされていることを確認してください。

2. プロジェクトの依存パッケージはすべて `requirements.txt` に記載されています。  
   以下のコマンドを実行することで、必要なライブラリが一括でインストールされます:

   ```bash
   pip install -r requirements.txt
   ```

### .env ファイルの設定

プロジェクトルートに `.env` ファイルを作成し、Supabase の URL と API キーを設定してください。例:

```env
SUPABASE_URL=https://your-supabase-project-url.supabase.co
SUPABASE_API_KEY=your-supabase-api-key
```

※ `.env` ファイルはセキュリティ上の理由から Git 管理から除外することを推奨します。

### AHK環境設定ファイルの生成

Webインターフェースから簡単にAHK環境設定ファイルを生成できます：

1. `make_ahk_env.html` にアクセス
2. PCを選択（既存のPCまたは新規PC ID）
3. 保存先ディレクトリを指定
4. 「env_ahk.txt生成」ボタンをクリック

### Supabaseテーブルの設定

1. 以下のSQLコマンドを実行して、必要なテーブルを作成します：

```sql
-- ユーザーの基本視聴時間を管理するテーブル
CREATE TABLE users_watch_time (
    user_id UUID PRIMARY KEY,
    user_name VARCHAR(255) NOT NULL,  -- ユーザー名を追加
    default_time INT NOT NULL DEFAULT 120  -- 初期視聴時間（分）
);

-- ユーザーが使用するPC情報を管理するテーブル
CREATE TABLE user_pcs (
    pc_id UUID PRIMARY KEY,
    pc_name VARCHAR(255) NOT NULL,  -- PCの名前
    user_id UUID NOT NULL,  -- users_watch_time テーブルとの関連付け
    FOREIGN KEY (user_id) REFERENCES users_watch_time(user_id) ON DELETE CASCADE
);

-- PCアクティビティを記録するテーブル
CREATE TABLE pc_activity (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    pc_id UUID NOT NULL,  -- PC識別ID
    activity_time INT NOT NULL,  -- その日の 0:00 からの分数
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    FOREIGN KEY (user_id) REFERENCES users_watch_time(user_id) ON DELETE CASCADE
);

-- 視聴時間の増減ログを記録するテーブル
CREATE TABLE watch_time_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    added_minutes INT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    FOREIGN KEY (user_id) REFERENCES users_watch_time(user_id) ON DELETE CASCADE
);
```

2. 以下のストアドプロシージャを作成します：

```sql
-- 1. 指定されたユーザIDに対応するユーザ名を取得するプロシージャ
CREATE OR REPLACE FUNCTION get_user_name(p_user_id UUID)
RETURNS VARCHAR(255) AS $$
DECLARE
    v_user_name VARCHAR(255);
BEGIN
    SELECT user_name INTO v_user_name
    FROM users_watch_time
    WHERE user_id = p_user_id;

    RETURN v_user_name;
END;
$$ LANGUAGE plpgsql;
```


```sql
-- 1. 指定した JST の日付と pc_id に基づいてレコードを取得するプロシージャ
CREATE OR REPLACE FUNCTION get_pc_activity_by_pc_id(
    p_pc_id UUID,      -- 検索対象のPC ID
    p_jst_date DATE    -- 検索対象の日付（JST）
)
RETURNS TABLE (
    id UUID,
    pc_id UUID,
    user_id UUID,
    activity_time TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT *
    FROM pc_activity
    WHERE pc_id = p_pc_id
      -- JSTからUTCに変換して検索（-9時間）
      AND created_at >= (p_jst_date - INTERVAL '9 hours')
      AND created_at < (p_jst_date + INTERVAL '1 day' - INTERVAL '9 hours');
END;
$$ LANGUAGE plpgsql;

-- 2. 指定した JST の日付と user_id に基づいて activity_time をユニークにしてレコードを取得するプロシージャ
CREATE OR REPLACE FUNCTION get_unique_pc_activity_by_user_id(
    p_user_id UUID,    -- 検索対象のユーザーID
    p_jst_date DATE    -- 検索対象の日付（JST）
)
RETURNS TABLE (
    id UUID,
    pc_id UUID,
    user_id UUID,
    activity_time INTEGER,  -- TIMESTAMP WITH TIME ZONE から INTEGER に変更
    created_at TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT DISTINCT ON (pa.activity_time) 
        pa.id,
        pa.pc_id,
        pa.user_id,
        pa.activity_time,
        pa.created_at
    FROM pc_activity pa
    WHERE pa.user_id = p_user_id
      -- JSTからUTCに変換して検索（-9時間）
      AND pa.created_at >= (p_jst_date - INTERVAL '9 hours')
      AND pa.created_at < (p_jst_date + INTERVAL '1 day' - INTERVAL '9 hours')
    ORDER BY pa.activity_time, pa.created_at;
END;
$$ LANGUAGE plpgsql;
```

3. ユーザーIDとPC IDの準備:
   - ユーザーIDとPC IDには、UUID形式の値を使用します
   - 複数のPCを監視する場合は、それぞれにユニークなUUIDを割り当てます
   - UUIDは[オンラインジェネレーター](https://www.uuidgenerator.net/)などで生成できます

4. 初期ユーザー設定の作成:
   ```sql
   -- ユーザーの基本設定を登録（必須）
   -- user_idは実際に使用するUUIDに置き換えてください
   INSERT INTO users_watch_time (user_id, user_name, default_time)
   VALUES ('your-user-uuid-here', 'ユーザー名', 120);

   -- PCの登録（必須）
   -- pc_idは実際に使用するUUIDに置き換えてください
   INSERT INTO user_pcs (pc_id, pc_name, user_id)
   VALUES ('your-pc-uuid-here', 'PC1', 'your-user-uuid-here');
   ```

### sclog.py の EXE 化

Windows 環境で `sclog.py` を実行可能な EXE ファイルに変換する手順を以下に示します。

1. `PyInstaller` をインストールします。

   ```bash
   pip install pyinstaller
   ```

2. `sclog.py` を EXE ファイルに変換します。

   ```bash
   pyinstaller --onefile sclog.py
   ```

   これにより、`dist` フォルダ内に `sclog.exe` が生成されます。

---

## コマンドの使い方

`sclog.py` は CLI で実行可能な多機能なスクリプトです。各サブコマンドについて説明します。

各コマンドは `--api-key` オプションでユーザー固有のAPIキーを指定できます：

```bash
python sclog.py <command> <params> --api-key your-api-key
```

### log-pc-activity

**機能:**  
PC アクティビティを記録します。ユーザID と PC ID の UUID を受け取り、現在の活動時刻（その日の経過分数）を Supabase に記録します。

**使用例:**

```bash
python sclog.py log-pc-activity <user_id> <pc_id>
```

**オプション:**  
`--output` または `-o` を用いて、結果をファイルへ出力できます。

---

### check-watch-time

**機能:**  
ユーザの残り視聴可能時間を算出します。  
計算式:  
`残り時間 = (default_time + watch_time_log の合計) - 使用済み分数(全PC)`

**使用例:**

```bash
python sclog.py check-watch-time <user_id>
```

---

### get-total-usage

**機能:**  
全 PC での利用済み分数と、利用時刻の一覧（HH:MM形式）を取得します。

**使用例:**

```bash
python sclog.py get-total-usage <user_id>
```

---

### get-pc-usage

**機能:**  
指定した PC の利用済み分数と利用時刻（HH:MM形式）の一覧を取得します。

**使用例:**

```bash
python sclog.py get-pc-usage <user_id> <pc_id>
```

---

### get-allowed-time

**機能:**  
その日の視聴可能時間（default_time + watch_time_log の合計）を取得します。

**使用例:**

```bash
python sclog.py get-allowed-time <user_id>
```

---

### check-usage

**機能:**  
全PCの利用済み分数と視聴可能時間を比較し、状態を返します。

**メッセージモード:**
- `normal`: 標準的な詳細メッセージ
- `hover`: AHKのマウスホバー表示用の簡潔なメッセージ
- `giant`: 警告表示用の大きなメッセージ
- `fileout`: 3種類のメッセージを別々のファイルに出力
- `fileout_only_message`: メッセージ部分のみを3ファイルに出力

**エンコーディング:**
`--encoding` オプションで出力エンコードを指定可能（cp932またはsjis）

**使用例:**
```bash
python sclog.py check-usage <user_id>
```

---

### is-able-watch

**機能:**  
全 PC の利用済み分数とその日の視聴可能時間を比較し、  
- 利用が許容内 → `T`  
- 利用が超過 → `F`  
- エラー → `E`  
を返します。

**使用例:**

```bash
python sclog.py is-able-watch <user_id>
```

---

### insert-watch-log

**機能:**  
`watch_time_log` テーブルに、指定した分数を追加または減算（マイナス値も可）します。

**使用例:**

```bash
python sclog.py insert-watch-log <user_id> <added_minutes>
```

---

## AutoHotkey スクリプト (over_windows.ahk) について

`over_windows.ahk` は、定期的に Python スクリプトを実行し、PC のアクティビティログを記録・監視するための AutoHotkey スクリプトです。

### 主な機能

- **定期実行:**  
  `SetTimer` を利用して 20 秒ごとに以下を実行:
  - `log-pc-activity`: 現在の PC 活動時刻を記録
  - `is-able-watch`: 利用可能時間の照会（結果は指定ファイルに出力）
  - `check-watch-time`: 視聴可能時間の再計算

- **GUI 表示:**  
  `is-able-watch` の結果が `T` の場合、常に最前面に GUI ウィンドウが表示され、監視結果や視聴時間がビューされます。  
  ※ 結果ファイル (`is_able_watch.txt` および `sc_result_time.txt`) を読み込むことで、ツールチップやウィンドウが更新されます。

### 設定内容

スクリプト冒頭部分では以下のグローバル変数を設定しています:

- `screenTimeDir`: Python スクリプトや結果ファイルがあるディレクトリ
- `user_id`: ユーザの UUID
- `pc_id`: PC の UUID
- `isAbleWatchFile`: `is-able-watch` の結果が出力されるファイルパス
- `scResultTimeFile`: `check-watch-time` の結果が出力されるファイルパス

これらの値は、自身の環境に合わせて適宜変更してください。

---

## 変更点と注意事項

今回の更新では、以下の修正点および仕様変更を実施しています。

- **ペイロード形式の変更:**  
  以前は、Supabase の RPC 呼び出し時に配列形式や異なる形式のペイロードを使用していました。  
  今回は、`sc_time_viewer_8.html` 内の `renderDaySet` 関数で、Supabase へのリクエストペイロードを次の JSON オブジェクト形式に統一しました:
  ```json
  {
    "target_user_id": "<ユーザID>",
    "target_date": "<YYYY-MM-DD>"
  }
  ```
  これにより、各 RPC 関数（`get_time_ranges_by_user`、`get_total_watch_time`、`analyze_time_difference`）へ正確なパラメータが渡されるようになりました。

- **エラーハンドリングの強化:**  
  API 呼び出し後のレスポンスにおいて、エラーが発生した場合は詳細なエラーメッセージをコンソールに出力するよう実装を強化しました。  
  これにより、Supabase 側のエラー内容を把握しやすくなっています。

- **仕様変更の背景:**  
  - ペイロード形式の統一により、バックエンド側でのパラメータ検証やエラー検知が容易になるとともに、デバッグ作業の効率向上を図りました。  
  - 今後、Supabase の API 仕様に変更があった場合は、同様の形式修正が必要になる可能性があります。

- **注意点:**  
  - Supabase 側で実装している SQL ファンクションの引数定義が、今回のペイロード形式と合致しているか確認してください。  
  - フロントエンド（`sc_time_viewer_8.html`）およびバックエンド両面での動作確認を十分に行ってください。

---

## トラブルシューティング

- **UUID のバリデーションエラー:**  
  ユーザIDや PC ID が正しい UUID 形式であるか確認してください。

- **Supabase からデータが取得できない:**  
  - `.env` ファイルに正しい SUPABASE_URL と SUPABASE_API_KEY が設定されているか確認してください。  
  - Supabase 上に必要なテーブル（`users_watch_time`、`pc_activity`、`watch_time_log`）が存在していることを確認してください。

- **AutoHotkey スクリプト関連:**  
  - `screenTimeDir` のパスが正しいか確認してください。  
  - Python スクリプトが正しく動作しているか、コマンドラインから手動で実行してテストしてください。

---

## 追加したストアドプロシージャの説明

### get_watch_time_total
このストアドプロシージャは、指定したユーザID（UUID）に対して、開始日から終了日までの期間における `watch_time_log` テーブル内の視聴時間増減分（`added_minutes`）の合計を計算します。  
- **パラメータ:**  
  - `p_uuid`: 対象のユーザID（UUID）  
  - `p_start_date`: 集計の開始日（`date`型）  
  - `p_end_date`: 集計の終了日（`date`型）  
- **処理内容:**  
  - 指定された期間内で、Asia/Tokyo タイムゾーンに合わせた日時範囲内のレコードから `added_minutes` の合計を算出します。  
  - 取得結果が NULL である場合は、0 を返します。

**ソースコード例:**
```sql
CREATE OR REPLACE FUNCTION public.get_watch_time_total(
    p_uuid uuid,
    p_start_date date,
    p_end_date date
)
RETURNS integer
LANGUAGE plpgsql
AS $$
DECLARE
    total integer;
BEGIN
    SELECT COALESCE(SUM(added_minutes), 0)
      INTO total
      FROM watch_time_log
     WHERE user_id = p_uuid
       AND created_at >= p_start_date::timestamp AT TIME ZONE 'Asia/Tokyo'
       AND created_at <  (p_end_date::timestamp + interval '1 day') AT TIME ZONE 'Asia/Tokyo';
       
    RETURN total;
END;
$$;
```

### get_default_time
このストアドプロシージャは、ユーザに対するデフォルトの視聴可能時間を返します。  
- **処理内容:**  
  - 現在は例として 30 分のデフォルト視聴時間を返す実装となっています。  
  - 将来的にユーザごとに異なる初期値の設定が可能となる場合、ここを変更する基盤となります。

**ソースコード例:**
```sql
CREATE OR REPLACE FUNCTION public.get_default_time()
RETURNS TABLE(default_time integer) AS $$
BEGIN
  RETURN QUERY SELECT 30;
END;
$$ LANGUAGE plpgsql STABLE;
```

---

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## Webインターフェースの共通機能

- **共通ヘッダー:** すべてのページで統一されたナビゲーションを提供
  - PC使用状況タイムライン
  - PCアクティビティ登録
  - PC視聴時間修正
  - メンテナンス（AHK環境構築等）
  - ログアウト機能

- **レスポンシブデザイン:** スマートフォンやタブレットでも適切に表示