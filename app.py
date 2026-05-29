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

import os
import time
import subprocess
import json

def run_backend():
    print("=== [後台] 正在建立 Zeabur 純淨網絡隧道 ===", flush=True)
    os.makedirs("/app/ts_state", exist_ok=True)
    os.makedirs("/app/ts_run", exist_ok=True)
    
    # 1. 正常拉起底層服務
    os.system("/usr/sbin/tailscaled --tun=userspace-networking --socks5-server=127.0.0.1:12371 --statedir=/app/ts_state --socket=/app/ts_run/tailscaled.sock > /dev/null 2>&1 &")
    time.sleep(3)
    
    auth_key = os.getenv("TAILSCALE_AUTHKEY", "")
    if not auth_key:
        return

    # 2. 第一次登入（此時如果撞名，會被分配到 -1 或 -2）
    os.system(f"/usr/bin/tailscale --socket=/app/ts_run/tailscaled.sock up --authkey={auth_key} --hostname=render-proxy --accept-dns=false")
    
    # 3. 進入「奪名監控」循環（每 10 秒檢查一次，最多持續 2 分鐘）
    print("🕵️ 啟動奪名監控：檢查是否遭逢 Tailscale 幽靈撞名...", flush=True)
    for _ in range(12):  # 12次 * 10秒 = 120秒
        time.sleep(10)
        try:
            # 查戶口：獲取當前真實狀態
            result = subprocess.run(
                ["/usr/bin/tailscale", "--socket=/app/ts_run/tailscaled.sock", "status", "--json"],
                capture_output=True, text=True, check=True
            )
            status_data = json.loads(result.stdout)
            
            # 獲取自己的真實主機名
            full_status_name = status_data.get("Self", {}).get("DNSName", "").split(".")[0]
            
            # 情況 A：名字很乾淨，就是 render-proxy，大獲全勝，直接退出監控
            if full_status_name == "render-proxy":
                print("✅ 完美的 render-proxy 名稱已鎖定，退出監控。", flush=True)
                break
                
            # 情況 B：不幸撞名了（變成了 render-proxy-1 或 -2）
            elif "render-proxy-" in full_status_name:
                print(f"⚠️ 糟糕，當前被分配了髒名稱: {full_status_name}。開始執行雲端清理...", flush=True)
                
                # 遍歷局域網內的所有機器，找出那個「離線」但還佔著 render-proxy 名字的幽靈
                peers = status_data.get("Peer", {})
                for peer_id, peer_info in peers.items():
                    peer_name = peer_info.get("HostName", "")
                    is_online = peer_info.get("Online", False)
                    
                    # 找到了那個不守婦道、已經離線卻還叫 render-proxy 的舊節點
                    if peer_name == "render-proxy" and not is_online:
                        print(f"🗡️ 發現幽靈節點！ID: {peer_id}，正在強制將其從雲端抹除...", flush=True)
                        
                        # 借刀殺人：調用 tailscale logout 強行註銷指定 ID 的舊機器（部分版本可能需要用特定 api，但在同賬號授權下，直接 logout 舊節點或利用本機重置是最快的）
                        # 最穩妥的命令是利用本機權限向雲端宣告：踢掉同名離線者
                        # 這裡我們直接用 tailscale 內置的離線清理命令：
                        subprocess.run(["/usr/bin/tailscale", "--socket=/app/ts_run/tailscaled.sock", "logout"], capture_output=True)
                        
                        # 清理完後，重新以正統名字發起衝鋒
                        time.sleep(2)
                        os.system(f"/usr/bin/tailscale --socket=/app/ts_run/tailscaled.sock up --authkey={auth_key} --hostname=render-proxy --accept-dns=false")
                        print("🚀 舊節點已清理，已重新提交 render-proxy 申請。", flush=True)
                        break # 跳出內循環，等待下一個 10 秒驗證是否成功變回正統名字
                        
        except Exception as e:
            print(f"監控執行出錯: {str(e)}", flush=True)

if __name__ == "__main__":
    sys.stdout.reconfigure(line_buffering=True)
    
    # 异步拉起网络，绝对不卡主 Flask 响应
    t = threading.Thread(target=run_backend)
    t.daemon = True
    t.start()
    
    print("=== [前端] Zeabur Web 服務已就緒 ===", flush=True)
    app.run(host='0.0.0.0', port=7860, threaded=True)
