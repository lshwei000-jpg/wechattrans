import os
import sys
import time
import datetime
import threading
from flask import Flask, render_template_string, request, redirect, url_for
import subprocess
import json
import urllib.request
import base64

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
    
    # 1. 拉起服務底層
    os.system("/usr/sbin/tailscaled --tun=userspace-networking --socks5-server=127.0.0.1:12371 --statedir=/app/ts_state --socket=/app/ts_run/tailscaled.sock > /dev/null 2>&1 &")
    time.sleep(3)
    
    auth_key = os.getenv("TAILSCALE_AUTHKEY", "")
    api_secret = os.getenv("TS_API_SECRET", "") 
    if not auth_key:
        print("❌ 未檢測到 TAILSCALE_AUTHKEY，終止啟動。", flush=True)
        return

    # 2. 第一次登入嘗試（名字可能被降級為 -1, -2）
    print("🚀 發起初始網絡衝鋒...", flush=True)
    os.system(f"/usr/bin/tailscale --socket=/app/ts_run/tailscaled.sock up --authkey={auth_key} --hostname=render-proxy --accept-dns=false")
    
    print("🚀 [智能自愈] 啟動閉環重置監控...", flush=True)
    
    # 整體大循環最多嘗試 5 次
    for big_loop in range(1, 6):
        print(f"🔄 [大循環] 正在執行第 {big_loop} / 5 輪狀態確認...", flush=True)
        time.sleep(3)
        
        try:
            # 查戶口
            result = subprocess.run(
                ["/usr/bin/tailscale", "--socket=/app/ts_run/tailscaled.sock", "status", "--json"],
                capture_output=True, text=True, check=True
            )
            status_data = json.loads(result.stdout)
            full_status_name = status_data.get("Self", {}).get("DNSName", "").split(".")[0]
            
            # 【終極目標】名字完全歸位，大獲全勝，直接退出銷毀線程
            if full_status_name == "render-proxy":
                print(f"🎉🎉 🎉 【大獲全勝】本機名稱已完美鎖定為 [render-proxy]！", flush=True)
                break
                
            # 如果發現自身名字帶有髒後綴（例如 render-proxy-1）
            if "render-proxy-" in full_status_name:
                print(f"⚠️ 警報！本機當前叫: {full_status_name}。正統名字被霸佔，啟動奪名程序...", flush=True)
                
                peers = status_data.get("Peer", {})
                target_api_id = None
                for peer_id, peer_info in peers.items():
                    if peer_info.get("HostName", "") == "render-proxy":
                        target_api_id = peer_info.get("ID", "")
                        break
                
                # 步驟 A：如果發現了叫 render-proxy 的老節點，API 隔空擊殺它
                if target_api_id:
                    print(f"💥 找到老節點 ID: {target_api_id}，調用雲端 API 強制抹除...", flush=True)
                    url = f"https://api.tailscale.com/api/v2/device/{target_api_id}"
                    req = urllib.request.Request(url, method="DELETE")
                    auth_str = base64.b64encode(f":{api_secret}".encode()).decode()
                    req.add_header("Authorization", f"Basic {auth_str}")
                    
                    try:
                        with urllib.request.urlopen(req) as response:
                            if response.status in [200, 204]:
                                print("🗡️ API 擊殺成功，進入【回讀確認小循環】...", flush=True)
                    except Exception as api_err:
                        print(f"❌ API 擊殺請求異常: {str(api_err)}", flush=True)
                else:
                    print("ℹ️ 列表中目前沒看到叫 render-proxy 的老設備，可能已被雲端釋放。", flush=True)
                
                # 步驟 B：【回讀確認】等待老節點在雲端名單中徹底消失
                killed_successfully = False
                for verify_count in range(1, 7): # 每 5 秒確認一次，最多等 30 秒
                    time.sleep(5)
                    print(f"🔍 正在進行第 {verify_count} 次雲端名單回讀確認...", flush=True)
                    
                    v_result = subprocess.run(
                        ["/usr/bin/tailscale", "--socket=/app/ts_run/tailscaled.sock", "status", "--json"],
                        capture_output=True, text=True, check=True
                    )
                    v_status = json.loads(v_result.stdout)
                    v_peers = v_status.get("Peer", {})
                    
                    # 檢查叫 render-proxy 的老傢伙走了沒
                    still_exists = any(p.get("HostName", "") == "render-proxy" for p in v_peers.values())
                    
                    if not still_exists:
                        print("💡 [驗證成功]：雲端老節點已徹底蒸發，資料庫已純淨！", flush=True)
                        killed_successfully = True
                        break
                    else:
                        print("⏳ [繼續等待]：雲端資料庫尚未同步，老節點依然殘留...", flush=True)
                
                # 步驟 C：【本機自切重置】（核心修正！）
                # 不管 API 有沒有刪除成功，只要名額空出來了（或者超時了），本機必須「主動登出解綁」來刷新本地進程狀態
                print("♻️ 正在執行本機登出解綁 (tailscale logout)，清空髒名稱緩存...", flush=True)
                subprocess.run(["/usr/bin/tailscale", "--socket=/app/ts_run/tailscaled.sock", "logout"], capture_output=True)
                time.sleep(3)
                
                # 步驟 D：全新衝鋒，重新搶佔正統官名
                print("🚀 本地已純淨，正在發起全新 [render-proxy] 官名搶佔...", flush=True)
                os.system(f"/usr/bin/tailscale --socket=/app/ts_run/tailscaled.sock up --authkey={auth_key} --hostname=render-proxy --accept-dns=false")
                
        except Exception as e:
            print(f"❌ 自愈大循環執行異常: {str(e)}", flush=True)
            
    print("🏁 [限時自愈] 閉環驗證任務結束，監控線程已全自動銷毀。", flush=True)

if __name__ == "__main__":
    sys.stdout.reconfigure(line_buffering=True)
    
    # 异步拉起网络，绝对不卡主 Flask 响应
    t = threading.Thread(target=run_backend)
    t.daemon = True
    t.start()
    
    print("=== [前端] Zeabur Web 服務已就緒 ===", flush=True)
    app.run(host='0.0.0.0', port=7860, threaded=True)
