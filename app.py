import os
import sys
import time
import subprocess
from flask import Flask
import threading

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

# Gost 轉發中轉站
def run_gost_bridge():
    print("🛡️ [Gost] 高性能連接池就位，強制監聽 IPv4 127.0.0.1:11111...", flush=True)
    # 👑 【回歸純淨】：將 Gost 綁定在本地 127.0.0.1，只對內網轉發，徹底阻斷外網混亂流量的 bad version
    gost_cmd = "/app/gost -L=socks5://127.0.0.1:11111?mwm=100&max_conns=300 -F=socks5://127.0.0.1:11112"
    subprocess.run(gost_cmd, shell=True)

# Tailscale 哨兵核心
def tailscale_sentinel():
    authkey = os.getenv("TAILSCALE_AUTHKEY", "")
    
    if not authkey:
        print("❌ [哨兵] 錯誤: 缺少環境變量 TAILSCALE_AUTHKEY，監控終止！", flush=True)
        return

    print("🧹 [清場] 正在清除本地殘留進程...", flush=True)
    os.system("pkill -9 -f tailscaled")
    os.system("pkill -9 -f tailscale")
    os.system("pkill -9 -f gost")
    time.sleep(2)

    print("🚀 [哨兵] 正在啟動 Tailscale 核心守護進程...", flush=True)
    ts_daemon_cmd = (
        "/usr/local/bin/tailscaled "
        "--tun=userspace-networking "
        "--socks5-server=127.0.0.1:11112 "
        "--socket=/app/ts_run/tailscaled.sock "
        "--state=/app/ts_var/tailscaled.state > /dev/null 2>&1 &"
    )
    os.system(ts_daemon_cmd)
    time.sleep(4)

    # 啟動代理橋樑
    threading.Thread(target=run_gost_bridge, daemon=True).start()

    # 👑 【核心改動】：不再調用集體 API，直接使用內置強權覆蓋，強行把 render-proxy 域名奪過來！
    print("🎯 [哨兵] 正在發起強制覆蓋認證，綁定 [render-proxy] 域名...", flush=True)
    up_cmd = [
        "/usr/local/bin/tailscale", "--socket=/app/ts_run/tailscaled.sock", 
        "up", 
        f"--authkey={authkey}", 
        "--hostname=render-proxy", 
        "--force-reauth",  # 👑 核心參數：強行把老節點的憑證撕下來，自己貼上
        "--reset"
    ]
    subprocess.run(up_cmd, capture_output=True)
    print("✅ [哨兵] 強制覆蓋認證已完成！進入平穩維護期...", flush=True)

    while True:
        try:
            # 每隔 60 秒做一次常規保活心跳即可，絕不折騰 API
            result = subprocess.run(
                ["/usr/local/bin/tailscale", "--socket=/app/ts_run/tailscaled.sock", "status", "--json"],
                capture_output=True, text=True
            )
            if result.returncode != 0:
                print("🚨 [哨兵] 內核失去響應，執行自癒重啟...", flush=True)
                os.system("pkill -9 -f tailscaled")
                time.sleep(2)
                os.system(ts_daemon_cmd)
                time.sleep(4)
                subprocess.run(up_cmd, capture_output=True)
            
            time.sleep(60)
        except Exception as e:
            time.sleep(15)

if __name__ == '__main__':
    threading.Thread(target=tailscale_sentinel, daemon=True).start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
