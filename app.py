import os
import sys
import time
import json
import threading
import subprocess
from flask import Flask

app = Flask(__name__)

# 👑 網頁偽裝模組化讀取接口
def get_mock_html():
    html_path = os.path.join(os.path.dirname(__file__), 'index.html')
    if os.path.exists(html_path):
        with open(html_path, 'r', encoding='utf-8') as f:
            return f.read()
    return "<h1>API Service Running</h1>"

@app.route('/')
def home():
    return get_mock_html(), 200

# 👑 Gost 微信專用防爆連接池守護
def run_gost_bridge():
    print("🛡️ [Gost] 高性能連接池就位，開始監聽 11111...", flush=True)
    gost_cmd = (
        "/app/gost "
        "-L=socks5://:11111?mwm=100&max_conns=300&keepalive=true&ttl=30s "
        "-F=socks5://127.0.0.1:11112"
    )
    subprocess.run(gost_cmd, shell=True)

# 👑 Tailscale 24小時不失眠哨兵控制中樞
def tailscale_sentinel():
    authkey = os.getenv("TAILSCALE_AUTHKEY", "")
    api_secret = os.getenv("TS_API_SECRET", "")
    
    if not authkey or not api_secret:
        print("❌ [哨兵] 錯誤: 缺少環境變量 TAILSCALE_AUTHKEY 或 TS_API_SECRET，監控終止！", flush=True)
        return

    # 👑【天王蓋地虎：物理清場】強制擊殺任何可能殘留的舊進程，防止 bad version 踩踏
    print("🧹 [🧹 清場] 正在強力清空後台殘留的僵屍進程...", flush=True)
    os.system("pkill -9 -f tailscaled")
    os.system("pkill -9 -f tailscale")
    os.system("pkill -9 -f gost")
    time.sleep(3) # 留出 3 秒讓作業系統徹底釋放端口

    # 👑 使用完全精確的靜態二進制路徑啟動核心
    print("🚀 [哨兵] 正在全新拉起純淨版 Tailscale 核心...", flush=True)
    ts_daemon_cmd = (
        "/usr/local/bin/tailscaled "
        "--tun=userspace-networking "
        "--socks5-server=127.0.0.1:11112 "
        "--socket=/app/ts_run/tailscaled.sock "
        "--state=/app/ts_var/tailscaled.state > /dev/null 2>&1 &"
    )
    os.system(ts_daemon_cmd)
    time.sleep(5)

    # 啟動代理中轉橋樑
    threading.Thread(target=run_gost_bridge, daemon=True).start()

    print("👁️ [哨兵] 24小時不間斷監控已完全上線...", flush=True)
    
    while True:
        try:
            # 檢查狀態
            result = subprocess.run(
                ["/usr/local/bin/tailscale", "--socket=/app/ts_run/tailscaled.sock", "status", "--json"],
                capture_output=True, text=True
            )
            
            # 如果核心沒響應，說明進程死鎖或崩潰，觸發自癒重啟
            if result.returncode != 0:
                print("🚨 [哨兵] 檢測到 Tailscale 核心無響應，正在自動重置進程...", flush=True)
                os.system("pkill -9 -f tailscaled")
                time.sleep(2)
                os.system(ts_daemon_cmd)
                time.sleep(5)
                continue

            status_data = json.loads(result.stdout)
            current_name = status_data.get("Self", {}).get("DNSName", "").split(".")[0]
            
            # 情況 A：名正言順，穩穩鎖定
            if current_name == "render-proxy":
                time.sleep(60) # 正常狀態下，每 60 秒巡邏一次
                continue
                
            # 情況 B：名稱不對（被搶名），執行強殺老節點奪名
            print(f"⚠️ [哨兵] 當前名稱為 [{current_name}]，開始執行強殺老節點奪名...", flush=True)
            
            api_cmd = f"curl -s -X DELETE -u \"{api_secret}:\" https://api.tailscale.com/api/v2/tailnet/-/devices"
            devices_res = subprocess.run(f"curl -s -u \"{api_secret}:\" https://api.tailscale.com/api/v2/tailnet/-/devices", shell=True, capture_output=True, text=True)
            
            if devices_res.returncode == 0:
                devices_data = json.loads(devices_res.stdout)
                for device in devices_data.get("devices", []):
                    if device.get("hostname") == "render-proxy" and device.get("id") != status_data.get("Self", {}).get("ID"):
                        old_id = device.get("id")
                        subprocess.run(f"{api_cmd}/{old_id}", shell=True, capture_output=True)
                        print(f"💥 [哨兵] 已成功擊殺殘留老節點 ID: {old_id}", flush=True)
            
            # 重新進網
            subprocess.run([
                "/usr/local/bin/tailscale", "--socket=/app/ts_run/tailscaled.sock", 
                "up", f"--authkey={authkey}", "--hostname=render-proxy", "--reset"
            ], capture_output=True)
            
        except Exception as e:
            print(f"🔴 [哨兵異常] 監控大循環出錯: {str(e)}，將在 15 秒後嘗試重置...", flush=True)
            time.sleep(15)

if __name__ == '__main__':
    threading.Thread(target=tailscale_sentinel, daemon=True).start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
