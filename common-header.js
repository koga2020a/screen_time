// common-header.js
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
      <a href="set_use_time.html" style="color:white; margin-right:15px; text-decoration:none;">
        <i class="fas fa-keyboard"></i> PCアクティビティ登録
      </a>
      <a href="add_time.html" style="color:white; margin-right:15px; text-decoration:none;">
        <i class="fas fa-clock"></i> PC視聴時間修正
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
      transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
      display: inline-block;
      position: relative;
      padding: 5px 10px;
      border-radius: 4px;
    }
    
    #commonHeader nav a:hover {
      transform: translateY(-6px) scale(1.05);
      text-shadow: 0 0 8px rgba(255,255,255,0.5);
      box-shadow: 0 10px 20px rgba(255,255,255,0.1), 0 6px 6px rgba(0,0,0,0.08);
    }
    
    #commonHeader nav a:hover i {
      transform: scale(1.2);
      transition: transform 0.3s ease;
    }
    
    #commonHeader nav a::after {
      content: '';
      position: absolute;
      bottom: -2px;
      left: 0;
      width: 100%;
      height: 0;
      background: rgba(255,255,255,0.3);
      transition: height 0.3s ease;
      z-index: -1;
      border-radius: 4px;
      opacity: 0;
    }
    
    #commonHeader nav a:hover::after {
      height: 100%;
      opacity: 0.2;
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
    const script = document.createElement('script');
    script.src = 'https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2';
    script.onload = displaySessionEmail;
    document.head.appendChild(script);
  }
  
  // Supabase関連の処理を開始（ページロード完了後）
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      if (typeof supabase !== 'undefined') {
        displaySessionEmail();
      } else {
        loadSupabaseLibrary();
      }
    });
  } else {
    // DOMがすでに読み込まれている場合
    if (typeof supabase !== 'undefined') {
      displaySessionEmail();
    } else {
      loadSupabaseLibrary();
    }
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
      }, 500); // 0.5秒後に表示
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
})();