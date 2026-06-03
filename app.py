import os
import time
import socket
import threading
import subprocess
import json
import urllib.request
import base64
from flask import Flask, render_template_string

app = Flask(__name__)

# 🎭 網頁偽裝
MOCK_HTML = "<html><body><h2>📋 System Dashboard</h2><ul><li>🟢 Network Status: Optimal</li></ul></body></html>"

@app.route('/')
def home(): return render_template_string(MOCK_HTML), 200

@app.route('/healthz')
def healthz(): return "ok", 200

# 👑 絕活一：Gost 高性能長連接橋樑（解決微信圖片傳輸慢、規避 TIME_WAIT 端口用盡）
def run_gost_bridge():
    print("🚀 [Gost] 正在拉起 Gost 高性能長連接代理橋梁...", flush=True)
    time.sleep(5)
    
    # 👑 【精準修正版】：使用陣列傳參，徹底絕育 Linux Shell 符號解析 Bug
    gost_args = [
        "/app/gost",
        "-L=socks5://:11111?mwm=100&max_conns=100&keepalive=true",
        "-F=socks5://127.0.0.1:11112"
    ]
    
    while True:
        try:
            # 使用 Popen 靜默啟動，將輸出導向黑洞，防止日誌刷屏
            with open(os.devnull, 'w') as devnull:
                process = subprocess.Popen(gost_args, stdout=devnull, stderr=devnull)
                print("🟢 [Gost] 核心長連接池已在後台穩健監聽 11111 端口！", flush=True)
                process.wait() # 讓線程在這裡等待 Gost 運行
        except Exception as e:
            print(f"⚠️ [Gost] 異常退出: {e}，5秒後重啟...", flush=True)
            time.sleep(5)
            

# 👑 絕活二：雲端奪名大循環（解決 Render 無狀態重啟導致域名變動的問題）
def run_tailscale_snatch(auth_key, api_secret):
    print("🚀 [智能自癒] 啟動 Render 專屬域名奪名監控...", flush=True)
    
    for big_loop in range(1, 6):
        time.sleep(4)
        try:
            # 獲取當前本機在 Tailscale 網絡中的狀態
            result = subprocess.run(
                ["/usr/bin/tailscale", "--socket=/app/ts_run/tailscaled.sock", "status", "--json"],
                capture_output=True, text=True, check=True
            )
            status_data = json.loads(result.stdout)
            full_status_name = status_data.get("Self", {}).get("DNSName", "").split(".")[0]
            
            # 如果成功拿到正統名字，大功告成，退出循環
            if full_status_name == "render-proxy":
                print("🎉 【奪名成功】本機已完美鎖定正統域名標識 [render-proxy]！", flush=True)
                break
                
            # 如果被降級為 render-proxy-1 等，觸發擊殺清理邏輯
            if "render-proxy-" in full_status_name:
                print(f"⚠️ 檢測到名稱被降級為 {full_status_name}，啟動雲端老節點清理...", flush=True)
                peers = status_data.get("Peer", {})
                target_api_id = None
                
                # 尋找是哪台「死去的舊殘留機器」霸佔了 render-proxy 這個名字
                for peer_id, peer_info in peers.items():
                    if peer_info.get("HostName", "") == "render-proxy":
                        target_api_id = peer_info.get("ID", "")
                        break
                
                # 調用 Tailscale API 強制抹除老節點
                if target_api_id and api_secret:
                    url = f"https://api.tailscale.com/api/v2/device/{target_api_id}"
                    req = urllib.request.Request(url, method="DELETE")
                    auth_str = base64.b64encode(f":{api_secret}".encode()).decode()
                    req.add_header("Authorization", f"Basic {auth_str}")
                    try:
                        with urllib.request.urlopen(req) as response:
                            if response.status in [200, 204]: 
                                print("🗡️ API 擊殺成功，已抹除阻礙域名的老節點殘留。", flush=True)
                    except Exception as api_err: 
                        print(f"❌ API 擊殺請求異常: {api_err}", flush=True)
                
                # 登出並重新衝鋒，強行頂替正統名字
                print("🔄 正在重新登入以奪取正統域名...", flush=True)
                subprocess.run(["/usr/bin/tailscale", "--socket=/app/ts_run/tailscaled.sock", "logout"], capture_output=True)
                time.sleep(2)
                os.system(f"/usr/bin/tailscale --socket=/app/ts_run/tailscaled.sock up --authkey={auth_key} --hostname=render-proxy --accept-dns=false")
                
        except Exception as e:
            print(f"❌ 自癒循環執行異常: {e}", flush=True)

def run_backend():
    print("=== [後台] 正在建立 Render 高性能自癒網絡隧道 ===", flush=True)
    os.makedirs("/app/ts_state", exist_ok=True)
    os.makedirs("/app/ts_run", exist_ok=True)
    
    # 1. 啟動 Tailscale 官方服務，縮回內部 11112 端口
    os.system("/usr/sbin/tailscaled --tun=userspace-networking --socks5-server=127.0.0.1:11112 --statedir=/app/ts_state --socket=/app/ts_run/tailscaled.sock > /dev/null 2>&1 &")
    time.sleep(3)
    
    # 2. 拉起 Gost 高性能長連接橋樑（接管前台 11111 端口）
    threading.Thread(target=run_gost_bridge, daemon=True).start()
    
    auth_key = os.getenv("TAILSCALE_AUTHKEY", "")
    api_secret = os.getenv("TS_API_SECRET", "") # 記得在 Render 後台配置此 API Access Token
    
    if not auth_key:
        print("❌ 未檢測到 TAILSCALE_AUTHKEY，終止啟動。", flush=True)
        return

    # 3. 發起初始連接
    print("🚀 發起初始網絡衝鋒 [目標名稱: render-proxy]...", flush=True)
    os.system(f"/usr/bin/tailscale --socket=/app/ts_run/tailscaled.sock up --authkey={auth_key} --hostname=render-proxy --accept-dns=false")
    
    # 4. 併發執行奪名守護線程，確保域名不變
    threading.Thread(target=run_tailscale_snatch, args=(auth_key, api_secret), daemon=True).start()

if __name__ == '__main__':
    threading.Thread(target=run_backend, daemon=True).start()
    app.run(host='0.0.0.0', port=10000) # Render 要求的 Web 端口
