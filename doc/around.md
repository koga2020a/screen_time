# ファイル構造と概要

## 1. メインドキュメント
### `doc/around.md`
- 空のドキュメントファイル

### `doc/SQL_LIST.md`
- SQLシステムの構成一覧を記載
- テーブル構造、ストアドファンクション、トリガーなどの概要を説明

```1:52:doc/SQL_LIST.md
# SQLシステム構成一覧

## 1. テーブル構造

### 1.1 メインテーブル
- **pc_activity_2**: PC利用記録テーブル
  - PC識別子、ユーザー識別子、利用時間（分）を管理
  - JST対応のタイムスタンプカラムを保持

- **users_watch_time**: ユーザー視聴時間設定テーブル
  - デフォルト視聴時間（分）を管理
  - APIキー認証機能を追加

- **watch_time_log**: 視聴時間ログテーブル
  - 追加視聴時間の記録を管理
  - JST対応のタイムスタンプを保持

### 1.2 認証関連テーブル
- **auth_test_user_records**: ユーザー認証テストテーブル
  - ユーザーIDと最終ログイン時刻を管理
  - Row Level Security (RLS) 対応

## 2. ストアドファンクション

### 2.1 基本機能
- **minutes_to_time**: 分を時刻文字列（HHMM形式）に変換
- **append_pc_activity**: PC利用記録の追加
- **delete_pc_activity**: PC利用記録の削除
- **update_jst_timestamp**: JSTタイムスタンプの更新

### 2.2 分析機能
- **get_total_watch_time**: 総視聴時間の計算
- **get_daily_activity_count**: 日別活動カウント取得
- **analyze_time_difference**: 利用時間と設定時間の差分分析
- **get_time_ranges_by_pc**: PC別の利用時間帯取得
- **get_time_ranges_by_user**: ユーザー別の利用時間帯取得

### 2.3 API認証機能
- **validate_user_api_key_ext**: APIキーの検証
- **get_user_api_key**: ユーザーのAPIキー取得
- 各基本機能のAPIキー認証付きラッパー関数群

## 3. トリガー
- **set_minutes_time_jst**: pc_activity_2テーブルの分数自動計算
- **update_auth_test_user_records_updated_at**: 更新日時の自動設定
- **trg_auth_test_update_created_at_jst**: JST作成日時の自動設定

## 4. セキュリティ設定
- Row Level Security (RLS) ポリシー
- APIキーによる認証システム
- ユーザー権限の適切な設定

```


### `doc/SQL_text.md`
- SQLの詳細な実装コードと説明を含むドキュメント
- テーブル定義、関数定義、使用例などを記載

```1:15:doc/SQL_text.md

| 関数名                         | 引数                                                                                                                                       | 内部で利用しているテーブル                                                  |
| ------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------- |
| **minutes_to_time**            | `minutes INTEGER`                                                                                                                          | なし                                                                      |
| **append_pc_activity**         | `p_pc_id UUID, p_user_id UUID, p_minutes int[]`                                                                                            | なし<br>※内部では `unnest()` を用いて配列を展開しているだけ                    |
| **delete_pc_activity**         | `p_pc_id UUID, p_user_id UUID, p_minutes int[]`                                                                                            | `pc_activity_2`                                                           |
| **get_total_watch_time**       | `target_user_id UUID, target_date DATE`                                                                                                   | `watch_time_log`<br>`users_watch_time`                                      |
| **get_daily_activity_count**   | `target_user_id UUID, target_date DATE`                                                                                                   | `pc_activity_2`                                                           |
| **analyze_time_difference**    | `target_user_id UUID, target_date DATE`                                                                                                   | `pc_activity_2`<br>※また、内部で `get_total_watch_time` を利用しており、間接的に `watch_time_log` と `users_watch_time` も参照 |
| **get_time_ranges_by_pc**       | `target_user_id UUID, target_pc_id UUID, target_date DATE`                                                                                 | `pc_activity_2`                                                           |
| **get_time_ranges_by_user**     | `target_user_id UUID, target_date DATE`                                                                                                   | `pc_activity_2`                                                           |
| **insert_continuous_activity** | `target_user_id UUID, target_pc_id UUID, start_time TEXT, end_time TEXT, target_date DATE`                                                   | なし<br>※`generate_series` などの関数を利用しているが、データベーステーブルへの直接の SELECT は無し |
| **update_jst_timestamp**       | （引数なし・トリガー関数として呼び出される）                                                                                              | なし                                                                      |
| **get_pc_name**                | `p_pc_id UUID`                                                                                                                             | `user_pcs`                                                                |

```


### `doc/UseSample.md`
- APIの使用例とサンプルコードを提供
- 分析サマリー表示などの実装例を含む

## 2. フロントエンド
### `add_time.html`
- 視聴時間の追加・管理用のWebインターフェース
- PC別の利用時間表示や分析サマリーの表示機能を実装

```237:378:add_time.html
    // PC名を取得する関数
    async function getPcName(pcId) {
      const requestBody = { p_pc_id: pcId };
      try {
        const response = await fetch(
          `${SUPABASE_URL}/rest/v1/rpc/get_pc_name`,
          {
            method: 'POST',
            headers: HEADERS,
            body: JSON.stringify(requestBody)
          }
        );
        if (!response.ok) {
          throw new Error(`PC name fetch error: ${response.status}`);
        }
        const pcName = await response.json();
        return pcName || pcId;
      } catch (error) {
        console.error('Error fetching PC name:', error);
        return pcId;
      }
    }

    // 分析サマリー表示用の関数
    async function displayAnalysisSummary() {
      try {
        const today = getTodayJST();
        const requestBody = {
          target_user_id: USER_ID,
          target_date: today
        };

        // 許可時間情報の取得（RPC: get_total_watch_time）
        const totalResponse = await fetch(
          `${SUPABASE_URL}/rest/v1/rpc/get_total_watch_time`,
          {
            method: 'POST',
            headers: HEADERS,
            body: JSON.stringify(requestBody)
          }
        );
        if (!totalResponse.ok) {
          throw new Error('合計視聴時間の取得に失敗しました');
        }
        const totalDataArray = await totalResponse.json();
        const totalData = totalDataArray[0] || {};

        // 利用時間差分情報の取得（RPC: analyze_time_difference）
        const diffResponse = await fetch(
          `${SUPABASE_URL}/rest/v1/rpc/analyze_time_difference`,
          {
            method: 'POST',
            headers: HEADERS,
            body: JSON.stringify(requestBody)
          }
        );
        if (!diffResponse.ok) {
          throw new Error('利用時間差分の取得に失敗しました');
        }
        const diffDataArray = await diffResponse.json();
        const diffData = diffDataArray[0] || {};

        // 差分の値に応じた注釈を付与（正の場合：超過、負の場合：許容）
        const timeDifference = diffData.time_difference || 0;
        let diffAnnotation = "";
        if (timeDifference > 0) {
          diffAnnotation = "（超過してる）";
        } else if (timeDifference < 0) {
          diffAnnotation = "（許容）";
        }

        // 分析サマリー表示用の要素を取得または作成
        let summaryElement = document.getElementById('analysisSummary');
        if (!summaryElement) {
          summaryElement = document.createElement('div');
          summaryElement.id = 'analysisSummary';
          summaryElement.style.margin = '20px 0';
          summaryElement.style.fontSize = '1em';
          summaryElement.style.fontWeight = 'bold';
          document.querySelector('.card').insertBefore(summaryElement, document.querySelector('.time-adjust'));
        }

        // 許可時間と利用時間の両方を表示
        summaryElement.innerHTML = `
          許可: ${totalData.total_time || 0}分 (追加: ${totalData.total_added_minutes || 0}分, ベース: ${totalData.default_time || 0}分)
          <br>
          利用時間: ${diffData.unique_minutes_count || 0}分, 差分: ${timeDifference}分${diffAnnotation}
        `;
} catch (error) {
        console.error('分析サマリー取得エラー:', error);
      }
    }

    // PCごとの情報を表示する関数
    async function displayPCInfo() {
      try {
        const today = getTodayJST();
        const response = await fetch(
          `${SUPABASE_URL}/rest/v1/rpc/get_time_ranges_by_user`,
          {
            method: 'POST',
            headers: HEADERS,
            body: JSON.stringify({
              target_user_id: USER_ID,
              target_date: today
            })
          }
        );
        if (!response.ok) throw new Error('データの取得に失敗しました');
        
        const data = await response.json();
        const pcListElement = document.getElementById('pcList');
        pcListElement.innerHTML = '';

        // PCごとの情報を表示
        for (const row of data) {
          let timeRanges = row.time_ranges;
          if (typeof timeRanges === 'string') {
            timeRanges = JSON.parse(timeRanges);
          }
          const mergedRanges = mergeTimeRanges(timeRanges);
          let usedMinutes = 0;
          mergedRanges.forEach(rangeStr => {
            const { start, end } = parseTimeRange(rangeStr);
            usedMinutes += (end - start);
          });
          const pcName = await getPcName(row.pc_id);
          const pcElement = document.createElement('div');
          pcElement.className = 'pc-item';
          pcElement.innerHTML = `
            <div class="pc-name">${pcName}</div>
            <div class="time-info">
              <div>視聴時間: ${usedMinutes}分</div>
              <div>利用回数: ${row.activity_count}回</div>
            </div>
          `;
          pcListElement.appendChild(pcElement);
        }

        // 分析サマリーを表示
        displayAnalysisSummary();

```


### `sc_time_viewer_8.html`
- PC利用時間のタイムライン表示用インターフェース
- 日付別・PC別の利用時間を視覚的に表示

```1:664:sc_time_viewer_8.html
<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <title>PC Usage Timeline</title>
  <link rel="icon" href="data:,">
  <link rel="icon" type="image/svg+xml" href="favicon.svg">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css">
  <style>
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      margin: 20px;
      background-color: #f5f5f5;
    }
    .card {
      background: white;
      border-radius: 8px;
      box-shadow: 0 2px 4px rgba(0,0,0,0.1);
      padding: 20px;
      max-width: 1500px;
      margin: 0 auto;
    }
    /* 上部：日付選択＋矢印ボタン */
    .date-controls-wrapper {
      text-align: center;
      margin-bottom: 10px;
    }
    .date-controls {
      display: inline-flex;
      align-items: center;
      gap: 5px;
    }
    .date-picker {
      padding: 8px;
      border: 1px solid #ddd;
      border-radius: 4px;
      font-size: 1em;
    }
    .arrow-button {
      padding: 8px;
      border: 1px solid #ddd;
      border-radius: 4px;
      background: white;
      cursor: pointer;
      font-size: 1em;
    }
    /* タイトル */
    .main-title {
      text-align: center;
      margin-bottom: 20px;
    }
    /* 各日のセット（左から：2日前、1日前、今日） */
    .sets-container {
      display: flex;
      justify-content: flex-start;
      gap: 20px;
      overflow-x: auto;
    }
    .day-set {
      flex: 0 0 auto;
      width: 33%;
      min-width: 300px;
      border: 1px solid #eee;
      border-radius: 8px;
      padding: 10px;
      background: #fafafa;
    }
    .day-label {
      text-align: center;
      font-weight: bold;
      margin-bottom: 10px;
    }
    /* 各日セット内の延長時間／視聴時間表示 */
    .total-view-label,
    .total-extension-label {
      text-align: center;
      font-size: 0.9em;
      color: #666;
      margin-bottom: 6px;
    }
    /* セット内：左側タイムマーカー、右側グラフ群 */
    .day-content {
      display: flex;
      gap: 10px;
      height: 600px; /* 固定高さを設定 */
      position: relative;
    }
    .time-markers {
      width: 50px;
      position: relative;
      border-right: 1px solid #ddd;
      height: 100%;
      flex-shrink: 0;
    }
    .time-marker {
      position: absolute;
      width: 100%;
      text-align: right;
      font-size: 0.8em;
      color: #666;
      padding-right: 5px;
      height: 20px;
      margin-top: -10px; /* 高さの半分を負のマージンで設定 */
      line-height: 20px;
      z-index: 1;
    }
    /* マーカーに対応する水平線 */
    .time-marker::after {
      content: '';
      position: absolute;
      left: 100%; /* マーカーの右端から */
      top: 50%;
      width: 100vw; /* 十分な長さ */
      height: 1px;
      background-color: rgba(0,0,0,0.05);
      z-index: -1;
    }
    .graphs-container {
      display: flex;
      flex: 1;
      flex-direction: row;
      gap: 10px;
      overflow-x: auto;
      height: 100%;
      justify-content: center;
      position: relative;
    }

    /* 各タイムライン（1PCまたは総視聴）のラッパー */
    .timeline-wrapper {
      display: inline-block;
    }
    .pc-info {
      text-align: center;
      margin-bottom: 12px;
      height: 40px;
      display: flex;
      flex-direction: column;
      justify-content: center;
    }
    .pc-title {
      font-size: 0.9em;
      margin: 0;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      max-width: 100px;
    }
    .total-minutes {
      font-size: 0.8em;
      color: #666;
      margin-top: 4px;
    }
    .timeline {
      position: relative;
      background: #f8f8f8;
      padding: 4px;
      border-radius: 4px;
      height: 100%; /* 変更前: 500px → 変更後: 100%（親要素 day-content の高さ 600px に合わせる） */
      width: 90px;
    }
    .loading, .error {
      text-align: center;
      padding: 20px;
      color: #666;
    }
    .error {
      color: #dc2626;
    }
    .analysis-summary {
      border-top: 1px solid #ddd;
      padding-top: 10px;
      margin-top: 10px;
      font-size: 0.9em;
      color: #444;
    }
    /* 時間帯セグメント */
    .time-segment {
      position: absolute;
      left: 0;
      right: 0;
      border-radius: 2px;
      transition: opacity 0.2s;
    }
    .time-segment:hover {
      opacity: 0.8;
    }
    /* モーダルウィンドウのスタイル */
    .modal {
      display: none;
      position: fixed;
      z-index: 10;
      left: 0;
      top: 0;
      width: 100%;
      height: 100%;
      overflow: auto;
      background-color: rgba(0,0,0,0.4);
    }
    .modal-content {
      background-color: #fefefe;
      margin: 15% auto;
      padding: 20px;
      border: 1px solid #888;
      width: 300px;
    }
  </style>
  <script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>
</head>
<body>
  <!-- 共通ヘッダーの読み込み -->
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css">
  <div id="commonHeader"></div>
  <script src="common-header.js"></script>
  <div class="card">
    <!-- 上部：日付選択＋設定ボタン -->
    <div class="date-controls-wrapper">
      <div class="date-controls">
        <button id="prevDate" class="arrow-button">&#8592;</button>
        <input type="date" id="datePicker" class="date-picker">
        <button id="nextDate" class="arrow-button">&#8594;</button>
        <button id="openSettings" class="arrow-button">設定</button>
      </div>
    </div>
    <!-- 各日のセット（左から：2日前、1日前、今日） -->
    <div id="setsContainer" class="sets-container">
      <!-- 各日セットはJSで生成 -->
    </div>
  </div>

  <!-- モーダル（設定画面） -->
  <div id="settingsModal" class="modal">
    <div class="modal-content">
      <h3>グラフ表示設定</h3>
      <label>
        開始時刻: <input type="number" id="displayStartHour" min="0" max="23">:00
      </label>
      <br>
      <label>
        終了時刻: <input type="number" id="displayEndHour" min="1" max="24">:00
      </label>
      <br><br>
      <button id="saveSettings">保存</button>
      <button id="cancelSettings">キャンセル</button>
    </div>
  </div>

  <script>
    // URLのGETパラメータで"project_id"が指定されていればそれを使用
    const urlParams = new URLSearchParams(window.location.search);
    const SUPABASE_PROJECT_ID = urlParams.get('project_id') || 'xalrqqutkxzwzvahqpjg';
    const SUPABASE_URL = `https://${SUPABASE_PROJECT_ID}.supabase.co`;
    const SUPABASE_KEY = urlParams.get('supabase_key') || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InhhbHJxcXV0a3h6d3p2YWhxcGpnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkyNDE2MDIsImV4cCI6MjA1NDgxNzYwMn0.OzfyNlLHmZJOiWnCgsUCnvA9npaDXzVeASr-HVOT1MA';

    // Supabaseクライアントの初期化
    const supabaseClient = supabase.createClient(SUPABASE_URL, SUPABASE_KEY, {
      auth: {
        autoRefreshToken: true,
        persistSession: true,
        detectSessionInUrl: true
      }
    });

    let USER_ID = null;

    // セッションチェックと初期化
    async function initializeWithSession() {
      try {
        const { data: { session }, error: sessionError } = await supabaseClient.auth.getSession();
        
        if (sessionError) throw sessionError;
        if (!session) {
          window.location.href = 'auth_test_login.html';
          return;
        }

        USER_ID = session.user.id;
        // 日付の初期化とデータ取得を開始
        const now = new Date();
        const jstDate = new Date(now.getTime() + (9 * 60 * 60 * 1000));
        document.getElementById('datePicker').value = formatDate(jstDate);
        
        // 前後の日付移動ボタンのイベントを設定
        document.getElementById('prevDate').addEventListener('click', () => {
          const currentDate = new Date(document.getElementById('datePicker').value);
          currentDate.setDate(currentDate.getDate() - 1);
          document.getElementById('datePicker').value = formatDate(currentDate);
          fetchAndRenderAllDays();
        });
        
        document.getElementById('nextDate').addEventListener('click', () => {
          const currentDate = new Date(document.getElementById('datePicker').value);
          currentDate.setDate(currentDate.getDate() + 1);
          document.getElementById('datePicker').value = formatDate(currentDate);
          fetchAndRenderAllDays();
        });
        
        // 日付選択時のイベントを設定
        document.getElementById('datePicker').addEventListener('change', fetchAndRenderAllDays);
        
        await fetchAndRenderAllDays();
      } catch (error) {
        console.error('セッション初期化エラー:', error);
        window.location.href = 'auth_test_login.html';
      }
    }

    // ヘルパー関数：分を HH:MM 形式に
    function getTimeString(minutes) {
      const hours = Math.floor(minutes / 60);
      const mins = minutes % 60;
      return `${hours.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}`;
    }
    
    function getMinutesFromTime(hours, minutes) {
      return hours * 60 + minutes;
    }
    
    // 時刻文字列（例："16:50-16:50"）をパースして開始・終了分を取得
    function parseTimeRange(rangeStr) {
      const [startStr, endStr] = rangeStr.split('-');
      const [startHour, startMin] = startStr.split(':').map(n => parseInt(n, 10));
      const [endHour, endMin] = endStr.split(':').map(n => parseInt(n, 10));
      return {
        start: startHour * 60 + startMin,
        end: endHour * 60 + endMin
      };
    }
    
    // 時間帯をマージする補助関数
    function mergeTimeRanges(ranges) {
      // 重複を除去
      ranges = [...new Set(ranges)];
      
      // 文字列を数値に変換してソート
      const parsed = ranges.map(range => parseTimeRange(range))
        .sort((a, b) => a.start - b.start);
      
      // 連続する時間帯をマージ
      const merged = [];
      let current = null;
      
      for (const range of parsed) {
        if (!current) {
          current = {...range};
          continue;
        }
        
        if (range.start <= current.end) {
          current.end = Math.max(current.end, range.end);
        } else {
          merged.push(`${getTimeString(current.start)}-${getTimeString(current.end)}`);
          current = {...range};
        }
      }
      
      if (current) {
        merged.push(`${getTimeString(current.start)}-${getTimeString(current.end)}`);
      }
      
      return merged;
    }
    
    // グラフ表示時間設定をLocalStorageから取得（デフォルトは5:00～23:00）
    function getDisplayHours() {
      const stored = localStorage.getItem('graphDisplayHours');
      if (stored) {
        try {
          const data = JSON.parse(stored);
          if (typeof data.startHour === 'number' && typeof data.endHour === 'number') {
            return data;
          }
        } catch(e) {}
      }
      return { startHour: 5, endHour: 23 };
    }
    
    // タイムマーカー生成（localStorage の設定に基づく）
    function createTimeMarkers() {
      const { startHour, endHour } = getDisplayHours();
      const container = document.createElement('div');
      container.className = 'time-markers';
      const startMinutes = startHour * 60;
      const endMinutes = endHour * 60;
      const totalMinutes = endMinutes - startMinutes;
      for (let hour = startHour; hour <= endHour; hour++) {
        const marker = document.createElement('div');
        marker.className = 'time-marker';
        const topPercent = (((hour * 60) - startMinutes) / totalMinutes) * 100;
        marker.style.top = `${topPercent}%`;
        marker.textContent = `${hour.toString().padStart(2, '0')}:00`;
        container.appendChild(marker);
      }
      return container;
    }
    
    // タイムライン描画（localStorage の設定に基づく）
    function createTimelineFromRanges(pcName, timeRanges, activityCount, isTotal = false) {
      const wrapper = document.createElement('div');
      wrapper.className = 'timeline-wrapper';
      wrapper.style.position = 'relative';

      // グラフ表示に影響しないよう、PC情報は絶対配置（class1構成）
      const pcInfo = document.createElement('div');
      pcInfo.className = 'pc-info class1';
      pcInfo.style.position = 'absolute';
      pcInfo.style.top = '0';
      pcInfo.style.left = '0';
      pcInfo.style.width = '100%';
      pcInfo.style.height = '40px';
      pcInfo.style.pointerEvents = 'none';
      pcInfo.style.zIndex = '1';

      const title = document.createElement('h2');
      title.className = 'pc-title';
      title.textContent = isTotal ? '総視聴時間' : pcName;
      title.title = title.textContent;

      const totalMins = document.createElement('div');
      totalMins.className = 'total-minutes';
      totalMins.textContent = `${activityCount}分`;

      pcInfo.appendChild(title);
      pcInfo.appendChild(totalMins);
      wrapper.appendChild(pcInfo);

      const timeline = document.createElement('div');
      timeline.className = `timeline ${isTotal ? 'total-usage' : ''}`;
      timeline.style.position = 'relative';

      const { startHour, endHour } = getDisplayHours();
      const startMinutes = startHour * 60;
      const endMinutes = endHour * 60;
      const totalMinutes = endMinutes - startMinutes;

      timeRanges.forEach(rangeStr => {
        const { start, end } = parseTimeRange(rangeStr);
        if (end <= startMinutes || start >= endMinutes) return;
        const adjustedStart = Math.max(start, startMinutes);
        const adjustedEnd = Math.min(end, endMinutes);

        const segDiv = document.createElement('div');
        segDiv.className = 'time-segment';
        const topPercent = ((adjustedStart - startMinutes) / totalMinutes) * 100;
        const heightPercent = ((adjustedEnd - adjustedStart) / totalMinutes) * 100;
        segDiv.style.top = `${topPercent}%`;
        segDiv.style.height = `${heightPercent}%`;
        segDiv.style.left = '4px';
        segDiv.style.right = '4px';
        segDiv.style.backgroundColor = isTotal ? '#22c55e' : '#2563eb';
        segDiv.title = `${getTimeString(start)} - ${getTimeString(end)}`;
        timeline.appendChild(segDiv);
      });

      wrapper.appendChild(timeline);
      return wrapper;
    }
    
    // 日付を YYYY-MM-DD 形式に
    function formatDate(date) {
      return date.toISOString().split('T')[0];
    }
    
    // APIリクエスト用の共通ヘッダー
    const HEADERS = {
      'apikey': SUPABASE_KEY,
      'Authorization': `Bearer ${SUPABASE_KEY}`,
      'Content-Type': 'application/json'
    };
    
    // １日のセット生成：RPC経由で新SQL関数からデータを取得してタイムライン描画
    async function renderDaySet(dateStr) {
      const daySet = document.createElement('div');
      daySet.className = 'day-set';
      
      const dayLabel = document.createElement('div');
      dayLabel.className = 'day-label';
      dayLabel.textContent = dateStr;
      
      // 視聴時間の表示を追加
      const totalViewLabel = document.createElement('div');
      totalViewLabel.className = 'total-view-label';
      const totalExtensionLabel = document.createElement('div');
      totalExtensionLabel.className = 'total-extension-label';
      
      daySet.appendChild(dayLabel);
      daySet.appendChild(totalViewLabel);
      daySet.appendChild(totalExtensionLabel);
      
      const dayContent = document.createElement('div');
      dayContent.className = 'day-content';
      
      const markersContainer = createTimeMarkers();
      dayContent.appendChild(markersContainer);
      
      const graphsContainer = document.createElement('div');
      graphsContainer.className = 'graphs-container';
      graphsContainer.innerHTML = '<div class="loading">データを読み込んでいます...</div>';
      dayContent.appendChild(graphsContainer);
      
      daySet.appendChild(dayContent);
      
      try {
        // リクエストペイロード形式
        const requestBody = {
          target_user_id: USER_ID,
          target_date: dateStr
        };

        console.log('Request to get_time_ranges_by_user:', {
          url: `${SUPABASE_URL}/rest/v1/rpc/get_time_ranges_by_user`,
          headers: HEADERS,
          body: requestBody
        });

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
        console.log('Parsed usage data:', usageData);

        graphsContainer.innerHTML = '';

        if (!Array.isArray(usageData) || usageData.length === 0) {
          graphsContainer.innerHTML = '<div class="loading">この日のデータはありません</div>';
        } else {
          // 各PCのタイムライン描画
          for (const row of usageData) {
            let timeRanges = row.time_ranges;
            if (typeof timeRanges === 'string') {
              timeRanges = JSON.parse(timeRanges);
            }
            timeRanges = mergeTimeRanges(timeRanges);
            const pcName = await getPcName(row.pc_id);
            const timeline = createTimelineFromRanges(pcName, timeRanges, row.activity_count);
            graphsContainer.appendChild(timeline);
          }
        }

        console.log('Request to get_total_watch_time:', {
          url: `${SUPABASE_URL}/rest/v1/rpc/get_total_watch_time`,
          headers: HEADERS,
          body: requestBody
        });

        const totalResponse = await fetch(
          `${SUPABASE_URL}/rest/v1/rpc/get_total_watch_time`,
          {
            method: 'POST',
            headers: HEADERS,
            body: JSON.stringify(requestBody)
          }
        );

        if (!totalResponse.ok) {
          throw new Error(`Total time fetch error: ${totalResponse.status} ${totalResponse.statusText}`);
        }

        const totalDataArray = await totalResponse.json();
        const totalData = totalDataArray[0] || {};
        
        console.log('Request to analyze_time_difference:', {
          url: `${SUPABASE_URL}/rest/v1/rpc/analyze_time_difference`,
          headers: HEADERS,
          body: requestBody
        });

        const diffResponse = await fetch(
          `${SUPABASE_URL}/rest/v1/rpc/analyze_time_difference`,
          {
            method: 'POST',
            headers: HEADERS,
            body: JSON.stringify(requestBody)
          }
        );

        if (!diffResponse.ok) {
          throw new Error(`Time difference fetch error: ${diffResponse.status} ${diffResponse.statusText}`);
        }

        const diffDataArray = await diffResponse.json();
        const diffData = diffDataArray[0] || {};
        
        // 分析サマリーを表示
        totalViewLabel.textContent = `許可: ${totalData.total_time}分 (追加: ${totalData.total_added_minutes}分, ベース: ${totalData.default_time}分)`;

        // 差分が正の場合：「超過してる」、負の場合：「許容」、0の場合はそのまま表示
        let diffLabel = "";
        if (diffData.time_difference > 0) {
          diffLabel = `${diffData.time_difference}分（超過してる）`;
        } else if (diffData.time_difference < 0) {
          diffLabel = `${Math.abs(diffData.time_difference)}分（許容）`;
        } else {
          diffLabel = `${diffData.time_difference}分`;
        }
        totalExtensionLabel.textContent = `利用時間: ${diffData.unique_minutes_count}分, 差分: ${diffLabel}`;
        
      } catch (error) {
        console.error('Error details:', error);
        graphsContainer.innerHTML = '<div class="error">データの取得に失敗しました</div>';
      }
      return daySet;
    
    
    // 選択日とその前日2日分のセットを生成
    async function fetchAndRenderAllDays() {
      const setsContainer = document.getElementById('setsContainer');
      setsContainer.innerHTML = '<div class="loading">データを読み込んでいます...</div>';
      
      const selectedDateStr = document.getElementById('datePicker').value;
      const selectedDate = new Date(selectedDateStr);
      const dates = [
        formatDate(new Date(selectedDate.getFullYear(), selectedDate.getMonth(), selectedDate.getDate() - 1)),
        formatDate(new Date(selectedDate.getFullYear(), selectedDate.getMonth(), selectedDate.getDate() - 0)),
        formatDate(selectedDate)
      ];
      
      try {
        const daySetPromises = dates.map(dateStr => renderDaySet(dateStr));
        const daySets = await Promise.all(daySetPromises);
        setsContainer.innerHTML = '';
        daySets.forEach(daySet => setsContainer.appendChild(daySet));
      } catch (error) {
        console.error('Error fetching data:', error);
        setsContainer.innerHTML = '<div class="error">データの取得に失敗しました</div>';
      }
    }
    
    // PC名を取得する関数
    async function getPcName(pcId) {
      const requestBody = {
        p_pc_id: pcId
      };

      try {
        const response = await fetch(
          `${SUPABASE_URL}/rest/v1/rpc/get_pc_name`,
          {
            method: 'POST',
            headers: HEADERS,
            body: JSON.stringify(requestBody)
          }
        );

        if (!response.ok) {
          throw new Error(`PC name fetch error: ${response.status}`);
        }

        const pcName = await response.json();
        return pcName || pcId; // PCの名前が取得できない場合はIDを返す
      } catch (error) {
        console.error('Error fetching PC name:', error);
        return pcId; // エラーの場合はIDを返す
      
```


### `make_ahk_env.html`
- AutoHotkey環境設定ファイル生成用のインターフェース
- PC IDの選択と設定ファイルの生成機能を提供

## 3. バックエンド
### `sclog.py`
- コマンドラインインターフェース（CLI）ツール
- PC活動ログの記録や視聴時間の管理機能を実装

```485:701:sclog.py
def main():
    # .envファイルから設定値を読み込む
    default_user_id = os.getenv("user_id")
    default_pc_id = os.getenv("pc_id")
    default_api_key = os.getenv("user_id_ApiKey")
    
    # グローバルオプションとしてapi-key, user-id, pc-idを設定するための親パーサーを作成
    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument(
        "--api-key",
        help="ユーザーのAPI key（省略時は環境変数 USER_API_KEY または user_id_ApiKey を使用）"
    )
    parent_parser.add_argument(
        "--user-id",
        help="ユーザID (UUID)（省略時は環境変数 user_id を使用）"
    )
    parent_parser.add_argument(
        "--pc-id",
        help="PC ID (UUID)（省略時は環境変数 pc_id を使用）"
    )

    parser = argparse.ArgumentParser(
        description=(
            "Screen Time Management CLI\n\n"
            "このスクリプトは、PCのアクティビティログ、視聴時間ログの管理および利用状況の照会機能を提供します。\n"
            "各コマンドは必須パラメータとして user_id（および pc_id/pc_name や added_minutes 等）を受け取り、\n"
            "オプションで --output (-o) を指定すると、結果を指定されたファイルに出力します。\n"
            "エラー発生時は 'E'、視聴可能なら 'T'、超過していれば 'F' などの結果を返します。"
        ),
        formatter_class=argparse.RawTextHelpFormatter,
        parents=[parent_parser]  # 親パーサーを継承
    )

    subparsers = parser.add_subparsers(title="コマンド", dest="command", required=True)

    # 各サブパーサーに親パーサーを継承させる
    parser_log_pc = subparsers.add_parser(
        "log-pc-activity",
        help="指定したユーザとPC (UUIDまたはpc_name) を用いて、現在時刻を記録します。",
        parents=[parent_parser]
    )
    parser_log_pc.add_argument(
        "user_id",
        nargs="?",
        default=None,
        help="ユーザID (UUID)（省略時は --user-id オプションまたは環境変数 user_id を使用）"
    )
    parser_log_pc.add_argument(
        "pc_identifier",
        nargs="?",
        default=None,
        help="PC ID (UUID) もしくは user_pcs の pc_name（省略時は --pc-id オプションまたは環境変数 pc_id を使用）"
    )
    parser_log_pc.add_argument("--output", "-o", help="結果出力先ファイル (省略時は標準出力)")

    parser_check_watch = subparsers.add_parser(
        "check-watch-time",
        help="ユーザの残り視聴可能時間を取得します。\n(ユーザの default_time + watch_time_log の合計 - 全PCの利用済み分数)",
        parents=[parent_parser]
    )
    parser_check_watch.add_argument("user_id", help="ユーザID (UUID)")
    parser_check_watch.add_argument("--output", "-o", help="結果出力先ファイル (省略時は標準出力)")

    parser_total_usage = subparsers.add_parser(
        "get-total-usage",
        help="当日の全PCでの利用済み分数（重複は1分として）と利用時刻 (HH:MM形式) を取得します。",
        parents=[parent_parser]
    )
    parser_total_usage.add_argument("user_id", help="ユーザID (UUID)")
    parser_total_usage.add_argument("--output", "-o", help="結果出力先ファイル (省略時は標準出力)")

    parser_pc_usage = subparsers.add_parser(
        "get-pc-usage",
        help="指定したPC (UUIDまたはpc_name) の利用済み分数（重複は1分として）と利用時刻 (HH:MM形式) を取得します。",
        parents=[parent_parser]
    )
    parser_pc_usage.add_argument("user_id", help="ユーザID (UUID)")

    parser_pc_usage.add_argument("--output", "-o", help="結果出力先ファイル (省略時は標準出力)")

    parser_allowed_time = subparsers.add_parser(
        "get-allowed-time",
        help="その日の視聴可能時間 (default_time + watch_time_log の合計) を取得します。",
        parents=[parent_parser]
    )
    parser_allowed_time.add_argument("user_id", help="ユーザID (UUID)")
    parser_allowed_time.add_argument("--output", "-o", help="結果出力先ファイル (省略時は標準出力)")

    parser_check_usage = subparsers.add_parser(
        "check-usage",
        help="全PCの利用済み分数と視聴可能時間を比較し、範囲内か超過かを返します。",
        parents=[parent_parser]
    )
    parser_check_usage.add_argument("user_id", help="ユーザID (UUID)")
    parser_check_usage.add_argument(
        "--message-mode",
        choices=["normal", "hover", "giant", "fileout", "fileout_only_message"],
        default="normal",
        help=(
            "日本語メッセージの出力形式を指定します。\n"
            " normal: 従来どおり\n"
            " hover:  AHK用のマウスホバー表示に最適化された短いメッセージ\n"
            " giant:  超過時に大きな警告を出す想定のメッセージ\n"
            " fileout: 3ファイル出力 (_hover, _giant, _normal)\n"
            " fileout_only_message: 3ファイル出力（ただし message_jp のみを書き込み）\n"
            "  -o が無い場合は CSV 形式で3種をまとめて出力"
        )
    )
    parser_check_usage.add_argument(
        "--encoding",
        choices=["cp932", "sjis"],
        default=None,
        help="出力時のエンコードを指定します（cp932 または sjis）。省略時は utf-8。"
    )
    parser_check_usage.add_argument("--output", "-o", help="結果出力先ファイル (省略時は標準出力)")

    parser_is_able = subparsers.add_parser(
        "is-able-watch",
        help=(
            "全PCの実際利用分数とその日の設定視聴可能総分数（default_time + watch_time_logの合算）との差分を取得し、\n"
            "視聴可能なら 'T'（実利用が設定内）、超過なら 'F'、エラー発生時は 'E' を返します。"
        ),
        parents=[parent_parser]
    )
    parser_is_able.add_argument(
        "user_id",
        nargs="?",
        default=None,
        help="ユーザID (UUID)（省略時は --user-id オプションまたは環境変数 user_id を使用）"
    )
    parser_is_able.add_argument("--output", "-o", help="結果出力先ファイル (省略時は標準出力)")

    parser_insert_watch = subparsers.add_parser(
        "insert-watch-log",
        help="watch_time_log テーブルに added_minutes の値を挿入します。（正・負どちらも可能）",
        parents=[parent_parser]
    )
    parser_insert_watch.add_argument("user_id", help="ユーザID (UUID)")
    parser_insert_watch.add_argument("added_minutes", type=int, help="追加する分数（マイナス値も可）")
    parser_insert_watch.add_argument("--output", "-o", help="結果出力先ファイル (省略時は標準出力)")

    args = parser.parse_args()
    
    # API keyの設定（コマンドライン引数 > 環境変数）
    global api_key
    api_key = args.api_key or USER_API_KEY or default_api_key
    if not api_key:
        print("エラー: API keyが指定されていません。--api-key オプションまたは環境変数 USER_API_KEY/user_id_ApiKey を設定してください。")


    # user_idの設定（位置引数 > --user-id オプション > 環境変数）
    if args.command == "log-pc-activity":
        user_id = args.user_id or args.user_id or default_user_id
        pc_identifier = args.pc_identifier or args.pc_id or default_pc_id
        if not user_id:
            print("エラー: user_idが指定されていません。コマンドライン引数、--user-id オプション、または環境変数 user_id を設定してください。")
            sys.exit(1)
        if not pc_identifier:
            print("エラー: PC IDが指定されていません。コマンドライン引数、--pc-id オプション、または環境変数 pc_id を設定してください。")
            sys.exit(1)
        result = log_pc_activity(user_id, pc_identifier, return_result=True)
        output_result(result, args.output)

    elif args.command == "check-watch-time":
        result = get_allowed_time(args.user_id, return_result=True)
        output_result(result, args.output)

    elif args.command == "get-total-usage":
        start, end = get_today_range_utc()
        result = str(get_total_usage_minutes(args.user_id, start, end, return_result=True))
        output_result(result, args.output)

    elif args.command == "get-pc-usage":
        result = get_pc_usage(args.user_id, args.pc_identifier, return_result=True)
        output_result(result, args.output)

    elif args.command == "get-allowed-time":
        result = get_allowed_time(args.user_id, return_result=True)


    elif args.command == "check-usage":
        msg_mode = args.message_mode
        user_id = args.user_id
        out_enc = args.encoding or "utf-8"

        if msg_mode == "fileout":
            if args.output:
                for mode in ["hover", "giant", "normal"]:
                    res = check_usage(user_id, message_mode=mode, return_result=True)
                    out_filename = f"{args.output}_{mode}"
                    try:
                        with open(out_filename, "w", encoding=out_enc) as f:
                            f.write(res)
                        print(f"Output to {out_filename}:")
                        print(res)
                        print("-----")
                    except Exception:
                        print("E")
            else:
                header = "mode,success,total_usage_minutes,allowed_watch_time_minutes,status,message_jp"
                print(header)
                for mode in ["hover", "giant", "normal"]:
                    res = check_usage(user_id, message_mode=mode, return_result=True)
                    try:
                        data = json.loads(res)
                        success = data.get("success", "")
                        total_usage_minutes = data.get("total_usage_minutes", "")
                        allowed_watch_time_minutes = data.get("allowed_watch_time_minutes", "")
                        status = data.get("status", "")
                        message_jp = data.get("message_jp", "")
                        line = (
                            f"{mode},{success},{total_usage_minutes},"
                            f"{allowed_watch_time_minutes},{status},{message_jp}"
                        )
                    except Exception:
                        line = f"{mode},E,,,,"
                    print(line)
```


## 4. システムドキュメント
### `complete-system-docs.md`
- システム全体の詳細なドキュメント
- テーブル構造、機能、セットアップ手順などを包括的に説明

````1:526:complete-system-docs.md
# PC Activity and Watch Time Tracking System

## 概要
PCの利用時間を記録・分析し、ユーザーごとの視聴時間設定と実際の利用時間を比較分析するためのシステムです。

## テーブル構造

### 1. pc_activity_2
PCの利用時間を分単位で記録するテーブル

| カラム名 | 型 | 説明 |
|----------|-----|------|
| pc_id | UUID | PC識別子 |
| user_id | UUID | ユーザー識別子 |
| minutes_time_jst | INTEGER | JST 00:00からの経過分数（自動計算） |
| created_at | TIMESTAMP WITH TIME ZONE | レコード作成時刻（UTC） |
| created_at_jst | TIMESTAMP WITH TIME ZONE | レコード作成時刻（JST） |

### 2. users_watch_time
ユーザーごとのデフォルト視聴時間設定テーブル

| カラム名 | 型 | 説明 |
|----------|-----|------|
| user_id | UUID | ユーザー識別子 |
| default_time | INTEGER | デフォルトの視聴時間（分） |
| created_at | TIMESTAMP WITH TIME ZONE | レコード作成時刻（UTC） |
| created_at_jst | TIMESTAMP WITH TIME ZONE | レコード作成時刻（JST） |

### 3. watch_time_log
視聴時間の追加記録テーブル

| カラム名 | 型 | 説明 |
|----------|-----|------|
| user_id | UUID | ユーザー識別子 |
| added_minutes | INTEGER | 追加された視聴時間（分） |
| created_at | TIMESTAMP WITH TIME ZONE | レコード作成時刻（UTC） |
| created_at_jst | TIMESTAMP WITH TIME ZONE | レコード作成時刻（JST） |

## セットアップ手順

### 1. テーブル作成
```sql
-- pc_activity_2テーブルの作成
CREATE TABLE pc_activity_2 (
    pc_id UUID NOT NULL,
    user_id UUID NOT NULL,
    minutes_time_jst INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at_jst TIMESTAMP WITH TIME ZONE DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'JST'),
    CONSTRAINT pc_activity_2_unique_combination 
    UNIQUE (pc_id, user_id, minutes_time_jst)
);

-- users_watch_timeテーブルの作成
CREATE TABLE users_watch_time (
    user_id UUID NOT NULL,
    default_time INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at_jst TIMESTAMP WITH TIME ZONE DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'JST')
);

-- watch_time_logテーブルの作成
CREATE TABLE watch_time_log (
    user_id UUID NOT NULL,
    added_minutes INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at_jst TIMESTAMP WITH TIME ZONE DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'JST')
);
```

### 2. 関数とトリガーの作成
```sql
-- minutes_time_jst自動計算用のトリガー関数
CREATE OR REPLACE FUNCTION calculate_minutes_time_jst() ...;

-- その他の分析関数
CREATE OR REPLACE FUNCTION get_time_ranges_by_pc() ...;
CREATE OR REPLACE FUNCTION get_time_ranges_by_user() ...;
CREATE OR REPLACE FUNCTION get_total_watch_time() ...;
CREATE OR REPLACE FUNCTION analyze_time_difference() ...;
```

## 基本的な使用例

### 1. PC利用時間の記録
```sql
-- 現在時刻での利用記録
INSERT INTO pc_activity_2 (
    pc_id,
    user_id
) VALUES (
    '123e4567-e89b-12d3-a456-426614174000'::uuid,
    'user-123e4567-e89b-12d3-a456-111111111111'::uuid
);

-- 特定時刻での利用記録
INSERT INTO pc_activity_2 (
    pc_id,
    user_id,
    created_at_jst
) VALUES (
    '123e4567-e89b-12d3-a456-426614174000'::uuid,
    'user-123e4567-e89b-12d3-a456-111111111111'::uuid,
    '2024-02-15 09:30:00 JST'
);
```

### 2. 視聴時間の設定と追加
```sql
-- デフォルト視聴時間の設定
INSERT INTO users_watch_time (
    user_id,
    default_time
) VALUES (
    'user-123e4567-e89b-12d3-a456-111111111111'::uuid,
    480  -- 8時間
);

-- 追加視聴時間の記録
INSERT INTO watch_time_log (
    user_id,
    added_minutes
) VALUES (
    'user-123e4567-e89b-12d3-a456-111111111111'::uuid,
    60   -- 1時間追加
);
```

## 分析機能の使用例

### 1. PC別の利用時間帯取得
```sql
-- 特定PCの利用時間帯
SELECT * FROM get_time_ranges_by_pc(
    'user-123e4567-e89b-12d3-a456-111111111111'::uuid,  -- user_id
    '123e4567-e89b-12d3-a456-426614174000'::uuid,       -- pc_id
    '2024-02-15'::date                                   -- date
);

-- 結果例：
-- time_range
-- --------------
-- 0922-1030
-- 1042-1352
-- 2355-2359
```

### 2. ユーザー別の利用サマリー
```sql
-- ユーザーの全PC利用サマリー
SELECT * FROM get_time_ranges_by_user(
    'user-123e4567-e89b-12d3-a456-111111111111'::uuid,
    '2024-02-15'::date
);

-- 結果例：
-- pc_id                    | activity_count | time_ranges
---------------------------|----------------|---------------------------
-- PC1                     | 25            | {0922-1030,1042-1352}
-- PC2                     | 15            | {1015-1245,1330-1455}
```

### 3. 視聴時間分析
```sql
-- 合計視聴時間の取得
SELECT * FROM get_total_watch_time(
    'user-123e4567-e89b-12d3-a456-111111111111'::uuid,
    '2024-02-15'::date
);

-- 結果例：
-- total_added_minutes | default_time | total_time
-- -------------------|--------------|------------
-- 120                | 480          | 600

-- 実際の利用時間との差分分析
SELECT * FROM analyze_time_difference(
    'user-123e4567-e89b-12d3-a456-111111111111'::uuid,
    '2024-02-15'::date
);

-- 結果例：
-- unique_minutes_count | total_watch_time | time_difference
-- --------------------|------------------|----------------
-- 650                 | 600              | 50
```

## 主な機能一覧

### PC利用時間記録機能
1. **自動時間計算**
   - 関数: `calculate_minutes_time_jst()`
   - 用途: JST時刻から経過分数を自動計算

2. **時間帯分析**
   - 関数: `get_time_ranges_by_pc()`, `get_time_ranges_by_user()`
   - 用途: 連続する利用時間帯の把握

### 視聴時間管理機能
1. **視聴時間集計**
   - 関数: `get_total_watch_time()`
   - 用途: デフォルト時間と追加時間の合計算出

2. **差分分析**
   - 関数: `analyze_time_difference()`
   - 用途: 実際の利用時間と設定時間の比較

## 注意事項
- 時刻はすべてJST（日本標準時）で処理
- minutes_time_jstは0〜1439の範囲（24時間×60分）
- 連続する時間帯は自動的に結合
- PCとユーザーの組み合わせでの重複は排除
- デフォルト時間は最新の設定値が使用される

## バックアップとメンテナンス
1. 定期的なバックアップの推奨
2. インデックスの最適化
3. 古いログデータの保持期間設定

## トラブルシューティング
1. 時刻のずれが発生した場合
   - タイムゾーン設定の確認
   - created_at_jstの再計算

2. パフォーマンスの低下
   - インデックスの再構築
   - 不要なデータの削除
````


### `README.md`
- プロジェクトの概要、セットアップ手順、使用方法を説明
- CLIコマンドの詳細な使用例を含む

```1:31:README.md
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

```


このシステムは、PCの利用時間を追跡・管理し、ユーザーごとの視聴時間制限を設定・監視するための総合的なソリューションを提供しています。
