# Screen Time Management CLI ツール

このリポジトリは、PCのアクティビティログおよび視聴時間の管理を行うための CLI ツールと、Windows 環境での自動実行をサポートする AutoHotkey スクリプトを提供します。Python スクリプトで各種コマンドを実装しており、Supabase をバックエンドにしてデータの記録・照会を行います。

---

## 目次

- [概要](#概要)
- [特徴](#特徴)
- [前提条件](#前提条件)
- [セットアップ](#セットアップ)
  - [Python 環境および依存ライブラリ](#Python-環境および依存ライブラリ)
  - [.env ファイルの設定](#env-ファイルの設定)
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
- [トラブルシューティング](#トラブルシューティング)
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
- 必要な Python ライブラリ:
  - `requests`
  - `python-dotenv`
- **Supabase アカウント:**  
  Supabase の URL および API キーが必要です。  
- **AutoHotkey:**  
  Windows 環境での自動化のために [AutoHotkey](https://www.autohotkey.com/) をインストールしてください。

---

## セットアップ

### Python 環境および依存ライブラリ

1. Python がインストールされていることを確認してください。  
2. 必要なライブラリを pip でインストールします:

   ```bash
   pip install requests python-dotenv
   ```

### .env ファイルの設定

プロジェクトルートに `.env` ファイルを作成し、Supabase の URL と API キーを設定してください。例:

```env
SUPABASE_URL=https://your-supabase-project-url.supabase.co
SUPABASE_API_KEY=your-supabase-api-key
```

※ `.env` ファイルはセキュリティ上の理由から Git 管理から除外することを推奨します。

---

## コマンドの使い方

`sclog.py` は CLI で実行可能な多機能なスクリプトです。各サブコマンドについて説明します。

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
全 PC の利用済み分数と視聴可能時間を比較し、「within allowed（許容範囲内）」または「exceeded allowed（超過）」の状態を返します。

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

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。

---

この README が環境設定およびツールの利用開始に役立つことを願っています。ご不明点や改善の提案があれば、お気軽にお問い合わせください。
```
