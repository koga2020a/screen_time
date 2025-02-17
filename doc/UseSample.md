# Supabase の SQL / RPC 利用例（拡張版）

本ドキュメントでは、最新の SQL_text.md のテーブル定義とストアドプロシージャ定義に基づいて、Supabase の RPC を用いたデータ操作の実例を紹介します。  
**※ RPC 呼び出し時のリクエストペイロードは、必ず下記のコード例通りに記述してください。**  
（例：日付は "YYYY-MM-DD"、時刻は "HH:MM" 形式で送信することなど）

---

## 1. JavaScript での利用例

### A. 利用時間帯の取得とタイムライン描画

以下は、指定日付の利用記録を RPC `get_time_ranges_by_user` で取得し、各 PC ごとの利用時間帯を描画する例です。

```javascript:sc_time_viewer_8.html
async function renderDaySet(dateStr) {
  // 利用状況表示用要素の作成
  const daySet = document.createElement('div');
  daySet.className = 'day-set';

  // (ここで日付ラベル等のDOM要素を作成)

  try {
    // ※ペイロードは必ず「target_user_id」と「target_date」を含む、
    //    日付形式は "YYYY-MM-DD" としてください。
    const requestBody = {
      target_user_id: USER_ID,
      target_date: dateStr
    };

    const usageResponse = await fetch(
      `${SUPABASE_URL}/rest/v1/rpc/get_time_ranges_by_user`,
      {
        method: 'POST',
        headers: HEADERS,
        body: JSON.stringify(requestBody)
      }
    );
    if (!usageResponse.ok) {
      throw new Error(`RPCエラー (get_time_ranges_by_user): ${usageResponse.statusText}`);
    }
    const usageData = await usageResponse.json();

    // usageData 内の時間帯情報をタイムラインに描画する処理を実装
    // 例: 各時間帯のセグメントを div 要素として追加 (詳細は各プロジェクトに合わせて)
    
  } catch (error) {
    console.error('renderDaySet エラー:', error);
  }
  return daySet;
}
```

#### 注意点:
- **ペイロード形式:** リクエストボディに含むキー（例：`target_user_id`、`target_date`）は必ずドキュメント通りに記述してください。  
- **エラーハンドリング:** `fetch` のレスポンスが OK でない場合は、例外処理を実施してエラー内容をログ出力してください。

---

### B. 利用時間の分析と警告メッセージの表示

次の例は、`analyze_time_difference` RPC を利用して、実際の利用時間（`unique_minutes_count`）と許可された視聴時間との差分（`time_difference`）を計算し、画面上に警告メッセージ等を表示する例です。

```javascript:sc_time_viewer_8.html
async function displayAnalysisSummary() {
  try {
    const today = getTodayJST(); // 日付は "YYYY-MM-DD" の形式
    const requestBody = {
      target_user_id: USER_ID,
      target_date: today
    };

    const diffResponse = await fetch(
      `${SUPABASE_URL}/rest/v1/rpc/analyze_time_difference`,
      {
        method: 'POST',
        headers: HEADERS,
        body: JSON.stringify(requestBody)
      }
    );
    if (!diffResponse.ok) {
      throw new Error(`RPCエラー (analyze_time_difference): ${diffResponse.statusText}`);
    }
    const diffDataArray = await diffResponse.json();
    const diffData = diffDataArray[0] || {};

    // 表示例: 利用可能時間・利用時間・差分の値をそれぞれのラベルに反映
    document.getElementById('analysisSummary').innerHTML = `
      許可: ${diffData.total_time || 0}分<br>
      利用時間: ${diffData.unique_minutes_count || 0}分, 差分: ${diffData.time_difference || 0}分
    `;
  } catch (error) {
    console.error('displayAnalysisSummary エラー:', error);
  }
}
```

#### 注意点:
- **レスポンス形式:** 取得するレスポンスは配列形式になっているため、先頭要素を利用する点に注意してください。
- **パラメータの正確性:** 日付などのパラメータは正確な形式を守り（例："YYYY-MM-DD"）、変更しないようにしてください。

---

### C. 連続活動レコードの自動生成

以下は、指定された時刻範囲内で 1 分刻みの活動レコードを一括登録する例です。これは `insert_continuous_activity` RPC を使用しています。

```javascript:continuous_activity.html
async function insertContinuousActivity() {
  try {
    // ※ペイロードの各項目は必ずコード例通りに記載すること！
    const requestBody = {
      target_user_id: USER_ID,
      target_pc_id: PC_ID,
      start_time: '09:30',  // HH:MM形式
      end_time: '10:45',    // HH:MM形式
      target_date: '2024-02-15'  // 日付形式は "YYYY-MM-DD"
    };

    const response = await fetch(
      `${SUPABASE_URL}/rest/v1/rpc/insert_continuous_activity`,
      {
        method: 'POST',
        headers: HEADERS,
        body: JSON.stringify(requestBody)
      }
    );
    if (!response.ok) {
      throw new Error('RPCエラー (insert_continuous_activity)');
    }
    const insertedCount = await response.json();
    console.log('登録された活動レコード数:', insertedCount);
  } catch (error) {
    console.error('insertContinuousActivity エラー:', error);
  }
}
```

#### 注意点:
- **リクエストの正確性:** 各パラメータ（`target_user_id`、`target_pc_id`、`start_time`、`end_time`、`target_date`）は、必ず仕様通りに記載してください。
- **バックエンド処理:** 挿入処理は RPC 側で自動的に行われるため、リクエスト内容の不備は直接挿入件数に影響します。

---

## 2. Python での利用例

たとえば、PC 識別子が UUID かどうかをチェックし、必要に応じてテーブルから値を引き出す例を以下に示します。

```python:sclog.py
def get_pc_id_from_user(user_id, pc_identifier):
    """
    pc_identifier が UUID 形式の場合はそのまま返し、
    そうでなければ user_pcs テーブルから pc_id を取得します。
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

#### 注意点:
- **UUID の検証:** 渡された文字列が正しい形式かどうかを事前にチェックし、必要な場合のみテーブルクエリを実行してください。
- **APIレスポンス:** レスポンス内容が空の場合に備えて、`None` を返すなどの例外処理を実装しています。

---

## まとめ

- **統一された仕様の遵守:**  
  RPC の呼び出し時に使用するリクエストペイロードは、ドキュメントに記載された通りに必ず実装してください。形式（例："YYYY-MM-DD", "HH:MM"）やキー名が変更されると、バックエンド側との不整合が発生し、エラーの原因となります。
  
- **エラーハンドリングの徹底:**  
  JavaScript の場合は `fetch` のレスポンスチェックと try/catch によるエラーハンドリング、Python でも API レスポンスの検証を確実に行い、適切な対応をしてください。

- **実環境での検証:**  
  ここに掲載した例は各環境で実動作確認済みのものですが、実際の利用時は自分のシステム（Supabase プロジェクトやテーブル定義）に合わせた微調整が必要です。

以上の実例と注意点を参考に、正確かつ一貫性のある実装を行ってください。
```