// common-header.js
(function() {
  // common-header.html を DOMParser でパースし、スクリプトも個別に実行する
  fetch('common-header.html')
    .then(response => response.text())
    .then(html => {
      const parser = new DOMParser();
      const doc = parser.parseFromString(html, 'text/html');

      const container = document.getElementById('commonHeader');
      if (!container) {
        console.error('共通ヘッダーを挿入する要素 (#commonHeader) が見つかりません');
        return;
      }
      container.innerHTML = ''; // 既存の内容をクリア

      const fragment = document.createDocumentFragment();
      // body 要素があればその子ノードを利用、なければ documentElement の子ノードを利用
      const childNodes = doc.body ? Array.from(doc.body.childNodes) : Array.from(doc.documentElement.childNodes);
      childNodes.forEach(node => {
        if (node.nodeName.toLowerCase() === 'script') {
          // スクリプトは個別に作成し、属性と内容をコピーして実行する
          const script = document.createElement('script');
          Array.from(node.attributes).forEach(attr => {
            script.setAttribute(attr.name, attr.value);
          });
          script.text = node.textContent;
          fragment.appendChild(script);
        } else {
          fragment.appendChild(document.importNode(node, true));
        }
      });
      container.appendChild(fragment);

      // メニューアイテムにアニメーションとアイコンを追加
      const menuItems = container.querySelectorAll('.menu-item');
      menuItems.forEach(item => {
        // アイコンの追加
        const icon = document.createElement('i');
        const text = item.textContent.trim();
        
        if (text.includes('PC使用状況タイムライン')) {
          icon.className = 'fas fa-chart-line';
        } else if (text.includes('PCアクティビティ登録')) {
          icon.className = 'fas fa-plus-circle';
        } else if (text.includes('PC視聴時間修正')) {
          icon.className = 'fas fa-edit';
        }
        
        // アイコンを先頭に挿入
        item.insertBefore(icon, item.firstChild);
        icon.style.marginRight = '8px';

        // ホバーアニメーションのためのスタイル追加
        item.style.cssText = `
          transition: all 0.3s ease;
          position: relative;
          cursor: pointer;
          display: inline-block;
          padding: 8px 16px;
          text-decoration: none;
          color: #333;
        `;
        
        // ホバー時のイベントリスナー
        item.addEventListener('mouseenter', () => {
          item.style.transform = 'translateX(10px)';
          item.style.color = '#007bff';
          icon.style.color = '#007bff';
        });
        
        item.addEventListener('mouseleave', () => {
          item.style.transform = 'translateX(0)';
          item.style.color = '#333';
          icon.style.color = '#333';
        });
      });

      // Supabaseライブラリ読み込み後にセッション情報を取得してメールアドレスを表示する関数
      function displaySessionEmail() {
        const SUPABASE_URL = 'https://xalrqqutkxzwzvahqpjg.supabase.co';
        const SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InhhbHJxcXV0a3h6d3p2YWhxcGpnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkyNDE2MDIsImV4cCI6MjA1NDgxNzYwMn0.OzfyNlLHmZJOiWnCgsUCnvA9npaDXzVeASr-HVOT1MA';
        const supabaseClient = supabase.createClient(SUPABASE_URL, SUPABASE_KEY);
        
        supabaseClient.auth.getSession().then(({ data: { session }, error }) => {
          const userDisplay = document.getElementById('user-display-name');
          if (error) {
            console.error('セッション取得エラー:', error.messagse);
            return;
          }
          if (session && session.user) {
            userDisplay.textContent = `ようこそ, ${session.user.email} さん`;
            console.log('ユーザー情報:', session.user);
          } else {
            console.log('セッションまたはユーザー情報がありません');
            userDisplay.textContent = 'ログインしていません';
          }
        }).catch(err => {
          console.error('予期せぬエラー:', err);
        });
      }
      
      // Supabaseライブラリの読み込み完了を待って displaySessionEmail() を実行
      // common-header.html 内の supabase ライブラリ用の script タグを探す
      const supabaseScript = container.querySelector('script[src*="supabase-js"]');
      if (supabaseScript) {
        if (supabaseScript.readyState) { // IE向けの処理
          supabaseScript.onreadystatechange = function() {
            if (supabaseScript.readyState === 'loaded' || supabaseScript.readyState === 'complete') {
              supabaseScript.onreadystatechange = null;
              displaySessionEmail();
            }
          };
        } else {
          supabaseScript.onload = displaySessionEmail;
        }
      } else {
        // supabaseライブラリが見つからなければ、すぐに試みる
        displaySessionEmail();
      }
    })
    .catch(error => console.error('共通ヘッダー読み込みエラー:', error));
})(); 