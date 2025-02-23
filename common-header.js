(function() {
  // 元のデザインに基づいたHTMLを埋め込む
  const headerHTML = `
  <header style="background:#2563eb; padding:10px; color:white; display:flex; align-items:center; justify-content:space-between;">
    <div style="display:flex; align-items:center;">
      <h1 style="margin:0;">アクティビティ</h1>
      <!-- ログインユーザ名を表示するエリア -->
      <span id="user-display-name" style="margin-left:20px; font-size:0.9em;"></span>
    </div>
    <nav>
      <a href="sc_time_viewer_8.html" style="color:white; margin-right:15px; text-decoration:none;">
        <i class="fas fa-chart-line"></i> PC使用状況タイムライン
      </a>
      <a href="add_time.html" style="color:white; margin-right:15px; text-decoration:none;">
        <i class="fas fa-clock"></i> PC許可時間追加
      </a>
      <a href="set_use_time.html" style="color:white; margin-right:15px; text-decoration:none;">
        <i class="fas fa-keyboard"></i> PCアクティビティ登録
      </a>
      <div class="dropdown" style="display:inline-block; position:relative;">
        <a href="#" style="color:white; text-decoration:none;">
          <i class="fas fa-tools"></i> メンテナンス
        </a>
        <div class="dropdown-content" style="display:none; position:absolute; background:#2563eb; min-width:200px; box-shadow:0 8px 16px rgba(0,0,0,0.2); z-index:1; border-radius:4px; margin-top:5px;">
          <a href="make_ahk_env.html" style="color:white; text-decoration:none; display:block; padding:10px;">
            <i class="fas fa-wrench"></i> AHK環境構築
          </a>
        </div>
      </div>
      <button id="logout-btn" style="background:none; border:none; color:white; cursor:pointer; margin-left:15px;">
        <i class="fas fa-sign-out-alt"></i> ログアウト
      </button>
    </nav>
  </header>
  `;

  const container = document.getElementById('commonHeader');
  if (!container) {
    console.error('共通ヘッダーを挿入する要素 (#commonHeader) が見つかりません');
    return;
  }
  
  // コンテナにヘッダーHTMLを挿入
  container.innerHTML = headerHTML;
  
  // カスタムスタイルを追加
  const customStyle = document.createElement('style');
  customStyle.textContent = `
    #commonHeader nav a {
      transition: all 0.3s ease;
      display: inline-block;
      position: relative;
      padding: 5px 10px;
      border-radius: 4px;
    }
    
    #commonHeader nav a:hover {
      box-shadow: 0 0 0 2px rgba(255,255,255,0.3);
    }
    
    /* ドロップダウンメニューのスタイル */
    .dropdown-content {
      transition: visibility 0s, opacity 0.2s;
      visibility: hidden;
      opacity: 0;
    }
    
    .dropdown:hover .dropdown-content {
      visibility: visible;
      opacity: 1;
    }
    
    .dropdown.show .dropdown-content {
      visibility: visible;
      opacity: 1;
    }
    
    .dropdown-content a:hover {
      background: rgba(255,255,255,0.1);
    }

    /* 形式認識用の表示 */
    #timeFormatInfo {
      margin-top: 5px;
    }
    #timeFormatInfo span {
      padding: 4px 8px;
      border: 1px solid #ddd;
      margin-right: 4px;
      border-radius: 4px;
      background: #f0f0f0;
    }

    /* ダークモード対応 */
    body.dark-mode #timeFormatInfo span {
      background: #2d3748;
      border-color: #4a5568;
      color: #e2e8f0;
    }

    /* 通常モードのハイライト */
    #timeFormatInfo span.highlight {
      background: #d0f0d0;
      border-color: #90cfa0;
    }

    /* ダークモードのハイライト */
    body.dark-mode #timeFormatInfo span.highlight {
      background: #2f4f3f;
      border-color: #3d6b4f;
      color: #98fb98;
    }
  `;
  document.head.appendChild(customStyle);

  // Supabaseライブラリを使ってセッション情報とユーザー名を取得して表示する関数
  function displaySessionEmail() {
    try {
      const SUPABASE_URL = 'https://xalrqqutkxzwzvahqpjg.supabase.co';
      const SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InhhbHJxcXV0a3h6d3p2YWhxcGpnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkyNDE2MDIsImV4cCI6MjA1NDgxNzYwMn0.OzfyNlLHmZJOiWnCgsUCnvA9npaDXzVeASr-HVOT1MA';
      
      // すでにsupabaseがグローバルで利用可能かチェック
      if (typeof supabase !== 'undefined') {
        const supabaseClient = supabase.createClient(SUPABASE_URL, SUPABASE_KEY);
        
        supabaseClient.auth.getSession().then(async ({ data: { session }, error }) => {
          const userDisplay = document.getElementById('user-display-name');
          if (!userDisplay) return;
          
          if (error) {
            console.error('セッション取得エラー:', error.message);
            return;
          }
          
          if (session && session.user) {
            try {
              // get_user_name関数を呼び出す
              const { data: userName, error: funcError } = await supabaseClient.rpc(
                'get_user_name',
                { p_user_id: session.user.id }
              );
              
              if (funcError) {
                console.error('ユーザー名取得エラー:', funcError.message);
                userDisplay.textContent = `ようこそ, ${session.user.email} さん`;
              } else if (userName) {
                userDisplay.textContent = `ようこそ, ${userName} さん`;
              } else {
                // ユーザー名が見つからない場合はメールアドレスを表示
                userDisplay.textContent = `ようこそ, ${session.user.email} さん`;
              }
              console.log('ユーザー情報:', session.user);
              
            } catch (funcErr) {
              console.error('関数呼び出しエラー:', funcErr);
              userDisplay.textContent = `ようこそ, ${session.user.email} さん`;
            }
          } else {
            console.log('セッションまたはユーザー情報がありません');
            userDisplay.textContent = 'ログインしていません';
          }
        }).catch(err => {
          console.error('予期せぬエラー:', err);
        });
      } else {
        console.warn('Supabaseライブラリが読み込まれていません');
        // Supabaseが必要な場合はここでスクリプトを動的に読み込む
        loadSupabaseLibrary();
      }
    } catch (err) {
      console.error('セッション取得中にエラーが発生しました:', err);
    }
  }
  
  // Supabaseライブラリを動的に読み込む関数
  function loadSupabaseLibrary() {
    return new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = 'https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2';
      script.onload = () => {
        try {
          // Supabaseクライアントの初期化
          const SUPABASE_URL = 'https://xalrqqutkxzwzvahqpjg.supabase.co';
          const SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InhhbHJxcXV0a3h6d3p2YWhxcGpnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkyNDE2MDIsImV4cCI6MjA1NDgxNzYwMn0.OzfyNlLHmZJOiWnCgsUCnvA9npaDXzVeASr-HVOT1MA';
          window.supabaseClient = supabase.createClient(SUPABASE_URL, SUPABASE_KEY);
          resolve(window.supabaseClient);
        } catch (error) {
          reject(error);
        }
      };
      script.onerror = reject;
      document.head.appendChild(script);
    });
  }
  
  // ログアウトボタンの動作を設定
  function setupLogoutButton() {
    const logoutButton = document.getElementById('logout-btn');
    if (!logoutButton) return;

    logoutButton.addEventListener('click', async () => {
      try {
        console.log('ログアウト中...');
        if (!window.supabaseClient) {
          await loadSupabaseLibrary();
        }
        const { error } = await window.supabaseClient.auth.signOut();
        
        if (error) throw error;

        console.log('ログアウトしました。ログインページへ移動します...');
        setTimeout(() => {
          window.location.href = 'auth_test_login.html';
        }, 1500);
        
      } catch (err) {
        console.error('ログアウトエラー:', err);
      }
    });
  }

  // Supabase関連の処理を開始（ページロード完了後）
  async function initializeSupabase() {
    try {
      if (!window.supabaseClient) {
        await loadSupabaseLibrary();
      }
      displaySessionEmail();
      setupLogoutButton();
    } catch (error) {
      console.error('Supabase初期化エラー:', error);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeSupabase);
  } else {
    initializeSupabase();
  }

  // ドロップダウンの動作制御を追加
  document.addEventListener('DOMContentLoaded', () => {
    const dropdown = document.querySelector('.dropdown');
    const dropdownLink = dropdown.querySelector('a');
    const dropdownContent = dropdown.querySelector('.dropdown-content');
    let hoverTimeoutId;
    let leaveTimeoutId;

    // ホバーの処理
    dropdown.addEventListener('mouseenter', () => {
      if (leaveTimeoutId) {
        clearTimeout(leaveTimeoutId);
      }
      hoverTimeoutId = setTimeout(() => {
        dropdownContent.style.display = 'block';
      }, 300); // 0.3秒後に表示
    });

    dropdown.addEventListener('mouseleave', () => {
      if (hoverTimeoutId) {
        clearTimeout(hoverTimeoutId);
      }
      leaveTimeoutId = setTimeout(() => {
        dropdownContent.style.display = 'none';
      }, 500); // 0.5秒後に非表示
    });

    // クリックの処理
    dropdownLink.addEventListener('click', (e) => {
      e.preventDefault(); // デフォルトの動作をキャンセル
      if (dropdownContent.style.display === 'block') {
        dropdownContent.style.display = 'none';
      } else {
        dropdownContent.style.display = 'block';
      }
    });

    // ドロップダウン以外の場所をクリックした時の処理
    document.addEventListener('click', (e) => {
      if (!dropdown.contains(e.target)) {
        dropdownContent.style.display = 'none';
      }
    });
  });

  // ダークモード設定の取得と適用
  function initializeDarkMode() {
    const isDarkMode = localStorage.getItem('darkMode') === 'true';
    document.body.classList.toggle('dark-mode', isDarkMode);
  }

  // DOMContentLoadedイベントでダークモード初期化
  document.addEventListener('DOMContentLoaded', initializeDarkMode);
})();