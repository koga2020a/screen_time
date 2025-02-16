# Supabase の SQL / RPC 利用例
以下は、Supabase の SQL クエリや RPC（リモートプロシージャコール）を JavaScript と Python で利用する例をまとめた Markdown です。  
各例では、リクエストの送信方法やレスポンスの処理方法、環境変数やヘッダーの準備方法などについて説明しています。

# Supabase の SQL / RPC 利用例（JavaScript と Python）

Supabase では、データベースのテーブルに対する SQL クエリの実行や、サーバーサイドに定義したストアドプロシージャ（RPC）を呼び出すことで、複雑な処理やビジネスロジックを実装できます。  
ここでは、JavaScript と Python それぞれでの利用例を紹介します。

---

## 1. JavaScript での利用例

### A. RPC を利用したデータ取得例  
以下のコード例は、`sc_time_viewer_8.html` 内の一部抜粋です。  
ユーザー ID と対象日 (`target_date`) をリクエストボディに含め、Supabase の RPC エンドポイント `get_time_ranges_by_user` を呼び出して、タイムレンジのデータを取得しています。

```javascript:sc_time_viewer_8.html
async function renderDaySet(dateStr) {
  // 各日の日付・利用データ表示用のDOM要素生成
  const daySet = document.createElement('div');
  daySet.className = 'day-set';

  // (省略) 日付ラベル等のDOM操作…

  try {
    // RPC 呼び出し用のリクエストボディ
    const requestBody = {
      target_user_id: USER_ID,
      target_date: dateStr
    };

    // RPC: get_time_ranges_by_user の呼び出し
    const usageResponse = await fetch(
      `${SUPABASE_URL}/rest/v1/rpc/get_time_ranges_by_user`,
      {
        method: 'POST',
        headers: HEADERS,
        body: JSON.stringify(requestBody)
      }
    );

    if (!usageResponse.ok) {
      throw new Error(`Usage fetch error: ${usageResponse.status} ${usageResponse.statusText}`);
    }

    const usageData = await usageResponse.json();
    // 取得したタイムレンジのデータを元にタイムラインを描画
    // (例: timeRanges のマージ、パース処理などの関数呼び出し)
  } catch (error) {
    console.error('Error details:', error);
    // エラー用のDOM更新処理
  }
  return daySet;
}
```

#### 解説  
- **リクエスト**  
  - `fetch()` を用いて Supabase の REST API エンドポイント `/rpc/get_time_ranges_by_user` に POST リクエストを送信します。  
  - リクエストボディには、ユーザー ID と対象の日付を JSON で送っています。

- **レスポンス処理**  
  - レスポンスの JSON をパースし、各 PC の利用時間データ（タイムレンジ）として利用しています。  
  - 後続の処理では、取得した時間レンジを統合・マージしてタイムライン上に描画するなどの UI 操作を行います。

---

### B. 分析結果や利用状況の取得例（RPC と SQL の混在）  
`add_time.html` 内では、ユーザーの全体の視聴時間や追加された時間、差分の算出に RPC を組み合わせて利用しています。
例えば、`displayAnalysisSummary` 関数では以下のように RPC を呼び出しています。

```javascript:add_time.html
async function displayAnalysisSummary() {
  try {
    const today = getTodayJST();
    const requestBody = {
      target_user_id: USER_ID,
      target_date: today
    };

    // RPC: get_total_watch_time の呼び出し
    const totalResponse = await fetch(
      `${SUPABASE_URL}/rest/v1/rpc/get_total_watch_time`,
      {
        method: 'POST',
        headers: HEADERS,
        body: JSON.stringify(requestBody)
      }
    );
    // (レスポンスのチェックと JSON パース処理)

    // RPC: analyze_time_difference の呼び出し（利用時間と許容時間の差分を算出）
    const diffResponse = await fetch(
      `${SUPABASE_URL}/rest/v1/rpc/analyze_time_difference`,
      {
        method: 'POST',
        headers: HEADERS,
        body: JSON.stringify(requestBody)
      }
    );
    // (レスポンスのチェックと JSON パース処理)

    // 取得したデータを用いて DOM に結果を表示
  } catch (error) {
    console.error('分析サマリー取得エラー:', error);
  }
}
```

#### 解説  
- RPC 呼び出しにより、サーバー側で定義された関数（例：`get_total_watch_time` や `analyze_time_difference`）が実行され、ユーザーの許可時間や使用時間の計算結果を返します。  
- これにより、フロントエンド側の複雑な計算処理をサーバー側で実施でき、コードの分担が明確になります。

---

## 2. Python での利用例

`sclog.py` は、同様に Supabase の REST API を Python の `requests` ライブラリで呼び出し、SQL クエリや RPC を利用して処理を実施する例です。  
以下は、RPC を利用して「視聴可能時間」をチェックする関数 `is_able_watch` の抜粋です。

```python:sclog.py
def is_able_watch(user_id, return_result=False):
    """
    全PCの実際利用分数とその日の設定視聴可能総分数（default_time + watch_time_log の合算）の差分を取得し、視聴可能かどうかを判断します。
    新仕様では、Supabase の RPC analyze_time_difference を利用します。
    """
    try:
        # JST の当日の日付 (YYYY-MM-DD形式) を取得
        now_jst = datetime.now(JST)
        target_date = now_jst.strftime("%Y-%m-%d")

        # RPC の呼び出し URL
        url_rpc = f"{SUPABASE_URL}/rest/v1/rpc/analyze_time_difference"
        payload = {
            "target_user_id": user_id,
            "target_date": target_date
        }
        response = requests.post(url_rpc, headers=HEADERS, json=payload)
        data = response.json() if response.text.strip() else None

        # 呼び出し結果が存在し、time_difference の情報が含まれているかチェック
        if not data or "time_difference" not in data[0]:
            result = "E"
            return result if return_result else print(result)
        
        row = data[0]
        time_difference = row["time_difference"]

        # 利用時間が許容範囲内なら time_difference <= 0
        result = "T" if time_difference <= 0 else "F"
    except Exception:
        result = "E"
    return result if return_result else print(result)
```

#### 解説  
- **日付の取得と変換**  
  - 現在の JST 日付を取得し、`target_date` として RPC に渡します。
  
- **RPC 呼び出し**  
  - `requests.post()` を利用して、Supabase の `/rpc/analyze_time_difference` エンドポイントに対して JSON ペイロードを送信します。

- **レスポンスの処理**  
  - 取得した JSON データから `time_difference`（許容時間との差分）を確認し、結果として `'T'`（許容内）、`'F'`（超過している）、またはエラー発生時 `'E'` を返します。

---

### C. SQL テーブルの直接クエリ例  
また、Python では RPC 呼び出しだけでなく、通常の SQL テーブルへの GET リクエストも送信できます。  
以下は、ユーザーの PC 情報 (pc_id を取得する) を問い合わせる例です。

```python:sclog.py
def get_pc_id_from_user(user_id, pc_identifier):
    """
    pc_identifier が UUID 形式の場合はそのまま返し、
    そうでなければ pc_identifier (pc_name) を元に user_pcs テーブルから pc_id を取得します。
    """
    if is_valid_uuid(pc_identifier):
        return pc_identifier

    url = (
        f"{SUPABASE_URL}/rest/v1/user_pcs"
        f"?user_id=eq.{user_id}&pc_name=eq.{pc_identifier}&select=pc_id"
    )
    response = requests.get(url, headers=HEADERS)
    if not response.text.strip():
        return None

    data = response.json()
    if not data:
        return None

    return data[0]["pc_id"]
```

#### 解説  
- **URL の生成**  
  - クエリパラメータを利用して、`user_pcs` テーブルから指定した `user_id` と `pc_name` に該当するレコードの `pc_id` を取得します。
  
- **レスポンスの処理**  
  - 返された JSON データから `pc_id` を抽出し、処理に利用します。

---

## まとめ

- **JavaScript 側**  
  - `fetch()` を利用して Supabase の REST API（RPC および通常の SQL クエリ）にアクセス  
  - RPC 呼び出し時は、適切なリクエストボディを JSON 形式で送信し、レスポンスの JSON をパースして UI 表示に活用

- **Python 側**  
  - `requests` ライブラリを使用して同様のエンドポイントへアクセス  
  - RPC や直接 SQL クエリを行い、結果を JSON として受け取り解析・判定処理を実施

これらの例を応用することで、フロントエンドとバックエンド（Python スクリプト）間で一貫したデータ処理およびビジネスロジックの実装が可能になります。  
Supabase の各種機能を利用し、より効率的かつ保守性の高いアプリケーション開発に役立ててください。  

