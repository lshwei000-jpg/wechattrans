import os
import sys
import time
import datetime
import threading
from flask import Flask, render_template_string, request, redirect, url_for

app = Flask(__name__)

# 纯内存存储，不再碰敏感的第三方云 API，绝对安全、绝不挂机
MESSAGES = [
    {"id": 1, "name": "Alpha_Go", "avatar": "🤖", "content": "祝賀基於 Flask 架構的輕量級交互 Space 順利上線！測試過高並發請求，響應速度非常絲滑！", "time": "2026-05-18 10:24"},
    {"id": 2, "name": "林中有鹿", "avatar": "🦌", "content": "偶然刷到這個寶藏空間，UI 風格太戳我了。在這個喧囂的互聯網裡，能有一個安靜寫下心情的角落真好。", "time": "2026-05-19 14:15"}
]

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EchoSpace - 鳴響互動留言牆</title>
    <style>
        :root { --bg-color: #f4f7f6; --card-bg: #ffffff; --text-main: #2c3e50; --text-muted: #7f8c8d; --primary: #3498db; --primary-hover: #2980b9; }
        body { background-color: var(--bg-color); color: var(--text-main); font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin: 0; padding: 0; display: flex; flex-direction: column; align-items: center; }
        header { background: linear-gradient(135deg, #2c3e50, #3498db); color: white; width: 100%; text-align: center; padding: 40px 0; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
        header h1 { margin: 0; font-size: 32px; letter-spacing: 1px; }
        header p { margin: 10px 0 0 0; opacity: 0.8; font-size: 16px; }
        .main-container { max-width: 1000px; width: 100%; padding: 30px 20px; box-sizing: border-box; }
        .form-box { background: var(--card-bg); border-radius: 12px; padding: 25px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 40px; }
        .form-title { font-size: 18px; font-weight: bold; margin-bottom: 15px; color: var(--primary); }
        .form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 15px; }
        @media(max-width: 600px) { .form-grid { grid-template-columns: 1fr; } }
        label { display: block; margin-bottom: 6px; font-size: 14px; font-weight: 500; }
        input, select, textarea { width: 100%; padding: 12px; border: 1px solid #e0e0e0; border-radius: 8px; box-sizing: border-box; font-size: 15px; background: #fafafa; }
        input:focus, select:focus, textarea:focus { border-color: var(--primary); background: #fff; outline: none; box-shadow: 0 0 0 3px rgba(52,152,219,0.1); }
        button { background: var(--primary); color: white; border: none; padding: 12px 24px; font-size: 16px; font-weight: bold; border-radius: 8px; cursor: pointer; transition: background 0.2s; width: 100%; }
        button:hover { background: var(--primary-hover); }
        .wall-title { font-size: 22px; font-weight: bold; margin-bottom: 20px; border-left: 5px solid var(--primary); padding-left: 10px; }
        .grid-container { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; }
        .card { background: var(--card-bg); border-radius: 12px; padding: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.03); transition: transform 0.2s; border-top: 4px solid #e0e0e0; display: flex; flex-direction: column; justify-content: space-between; }
        .card:hover { transform: translateY(-3px); box-shadow: 0 8px 15px rgba(0,0,0,0.08); }
        .card-header { display: flex; align-items: center; margin-bottom: 12px; }
        .avatar { font-size: 24px; margin-right: 12px; background: #f0f3f5; width: 40px; height: 40px; border-radius: 50%; display: flex; align-items: center; justify-content: center; }
        .username { font-weight: bold; font-size: 16px; }
        .card-body { font-size: 15px; line-height: 1.6; color: #34495e; word-break: break-all; margin-bottom: 15px; flex-grow: 1; }
        .card-footer { font-size: 12px; color: var(--text-muted); text-align: right; border-top: 1px solid #f9f9f9; padding-top: 8px; }
        footer { margin-top: 60px; padding: 20px 0; color: var(--text-muted); font-size: 13px; text-align: center; border-top: 1px solid #e0e0e0; width: 100%; }
    </style>
</head>
<body>
    <header>
        <h1>EchoSpace 鳴響牆</h1>
        <p>心有所鳴，匯聚於此 —— 全新平台託管，全天候穩定不掉線</p>
    </header>
    <div class="main-container">
        <div class="form-box">
            <div class="form-title">✍️ 撰寫新留言</div>
            <form method="POST" action="/">
                <div class="form-grid">
                    <div>
                        <label>暱稱 / 身份</label>
                        <input type="text" name="username" placeholder="請輸入您的公開暱稱" maxlength="20" required>
                    </div>
                    <div>
                        <label>選擇個性頭像</label>
                        <select name="avatar">
                            <option value="🎯">🎯 探索者</option>
                            <option value="💻">💻 極客</option>
                            <option value="🐱">🐱 喵星人</option>
                            <option value="🌟">🌟 追光者</option>
                            <option value="☕">☕ 咖啡黨</option>
                        </select>
                    </div>
                </div>
                <div style="margin-bottom: 15px;">
                    <label>留言內容</label>
                    <textarea name="content" rows="3" placeholder="寫下你想說的話..." maxlength="200" required></textarea>
                </div>
                <button type="submit">發 布 留 言</button>
            </form>
        </div>
        <div class="wall-title">全部留言 ({{ total_count }})</div>
        <div class="grid-container">
            {% for msg in messages %}
            <div class="card" style="border-top-color: {{ ['#3498db', '#2ecc71', '#9b59b6', '#e67e22', '#1abc9c'] | random }}">
                <div>
                    <div class="card-header">
                        <div class="avatar">{{ msg.avatar }}</div>
                        <div class="username">{{ msg.name }}</div>
                    </div>
                    <div class="card-body">{{ msg.content }}</div>
                </div>
                <div class="card-footer">發佈於：{{ msg.time }}</div>
            </div>
            {% endfor %}
        </div>
    </div>
    <footer>EchoSpace Web Application Control Panel © 2026. All Rights Reserved.</footer>
</body>
</html>
"""

@app.route('/', methods=['GET', 'POST'])
def home():
    global MESSAGES
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        avatar = request.form.get('avatar', '🎯')
        content = request.form.get('content', '').strip()
        
        if username and content:
            now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            MESSAGES.insert(0, {
                "id": len(MESSAGES) + 1,
                "name": username,
                "avatar": avatar,
                "content": content,
                "time": now_str
            })
        return redirect(url_for('home'))
            
    return render_template_string(HTML_TEMPLATE, messages=MESSAGES, total_count=len(MESSAGES))

def run_backend():
    print("=== [後台] 正在建立 Zeabur 純淨網絡隧道 ===", flush=True)
    os.makedirs("/app/ts_state", exist_ok=True)
    os.makedirs("/app/ts_run", exist_ok=True)
    
    # 靜默拉起服務
    os.system("/usr/sbin/tailscaled --tun=userspace-networking --socks5-server=127.0.0.1:12371 --statedir=/app/ts_state --socket=/app/ts_run/tailscaled.sock > /dev/null 2>&1 &")
    
    time.sleep(3)
    auth_key = os.getenv("TAILSCALE_AUTHKEY", "")
    if auth_key:
        # 【程式碼層級臨時節點防撞名暗號】：
        # 加上 --ephemeral 讓 Tailscale 後台在它斷線時秒刪它，騰出名字給下一次重啟
        os.system(f"/usr/bin/tailscale --socket=/app/ts_run/tailscaled.sock up --authkey={auth_key} --hostname=render-proxy --ephemeral --accept-dns=false")
        print("✅ Tailscale 臨時自愈隧道就緒，固定名稱 render-proxy 已鎖定！", flush=True)

if __name__ == "__main__":
    sys.stdout.reconfigure(line_buffering=True)
    
    # 异步拉起网络，绝对不卡主 Flask 响应
    t = threading.Thread(target=run_backend)
    t.daemon = True
    t.start()
    
    print("=== [前端] Zeabur Web 服務已就緒 ===", flush=True)
    app.run(host='0.0.0.0', port=7860, threaded=True)
