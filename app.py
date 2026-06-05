import os
import sys
import time
import json
import threading
import subprocess
from flask import Flask

app = Flask(__name__)

def get_mock_html():
    html_path = os.path.join(os.path.dirname(__file__), 'index.html')
    if os.path.exists(html_path):
        with open(html_path, 'r', encoding='utf-8') as f:
            return f.read()
    return "<h1>API Service Running</h1>"

@app.route('/')
def home():
    return get_mock_html(), 200

# Gost 守護
def run_gost_bridge():
    print("🛡️ [Gost] 高性能連接池就位，開始監聽 11111...", flush=True)
    gost_cmd = (
        "/app/gost "
        "-L=socks5://:11111?mwm=100&max_conns=300&keepalive=true&ttl=30s "
        "-F=socks5://127.0.0.1:11112"
    )
    subprocess.run(gost_cmd, shell=True)

# Tailscale 哨兵控制中樞
def tailscale_sentinel():
    authkey = os.getenv("TAILSCALE_AUTHKEY", "")
    api_secret = os.getenv("TS_API_SECRET", "")
    
    if not authkey or not api_secret:
        print("❌ [哨兵] 錯誤: 缺少必要的環境變量！", flush=True)
        return

    # 👑 【必勝改動】：加入 --state 和完整的用戶態運行路徑，物理隔離運行環境
    print("🚀 [哨兵] 正在手動拉起純淨版 Tailscale 核心...", flush=True)
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
            
            # 如果核心沒響應，說明進程死了，觸發自癒重啟
            if result.returncode != 0:
                print("🚨 [哨兵] 檢測到 Tailscale 核心無響應，正在嘗試修復進程...", flush=True)
                os.system("pkill -f tailscaled")
                time.sleep(2)
                os.system(ts_daemon_cmd)
                time.sleep(5)
                continue

            status_data = json.loads(result.stdout)
            current_name = status_data.get("Self", {}).get("DNSName", "").split(".")[0]
            
            # 情況 A：標籤正常
            if current_name == "render-proxy":
                time.sleep(60)
                continue
                
            # 情況 B：名稱不對，執行搶名
            print(f"⚠️ [哨兵] 當前名稱為 [{current_name}]，開始執行強殺老節點奪名...", flush=True)
            
            api_cmd = f"curl -s -X DELETE -u \"{api_secret}:\" https://api.tailscale.com/api/v2/tailnet/-/devices"
            devices_res = subprocess.run(f"curl -s -u \"{api_secret}:\" https://api.tailscale.com/api/v2/tailnet/-/devices", shell=True, capture_output=True, text=True)
            
            if devices_res.returncode == 0:
                devices_data = json.loads(devices_res.stdout)
                for device in devices_data.get("devices", []):
                    if device.get("hostname") == "render-proxy" and device.get("id") != status_data.get("Self", {}).get("ID"):
                        old_id = device.get("id")
                        subprocess.run(f"{api_cmd}/{old_id}", shell=True, capture_output=True)
                        print(f"💥 [哨兵] 已擊殺老節點 ID: {old_id}", flush=True)
            
            # 重新進網
            subprocess.run([
                "/usr/local/bin/tailscale", "--socket=/app/ts_run/tailscaled.sock", 
                "up", f"--authkey={authkey}", "--hostname=render-proxy", "--reset"
            ], capture_output=True)
            
        except Exception as e:
            print(f"🔴 [哨兵] 循環出錯: {str(e)}", flush=True)
            time.sleep(15)

if __name__ == '__main__':
    threading.Thread(target=tailscale_sentinel, daemon=True).start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
