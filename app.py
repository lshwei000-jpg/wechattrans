import os
import sys
import time
import json
import uuid
import threading
import subprocess
from flask import Flask

app = Flask(__name__)

# 生成當前容器實例的唯一標識與啟動時間戳，防止大水沖了龍王廟
MY_INSTANCE_ID = str(uuid.uuid4())[:8]
BOOT_TIME = time.time()
print(f"🌟 [系統初始化] 當前節點特徵碼: {MY_INSTANCE_ID}, 啟動時間戳: {BOOT_TIME}", flush=True)

def get_mock_html():
    html_path = os.path.join(os.path.dirname(__file__), 'index.html')
    if os.path.exists(html_path):
        with open(html_path, 'r', encoding='utf-8') as f:
            return f.read()
    return "<h1>API Service Running</h1>"

@app.route('/')
def home():
    return get_mock_html(), 200

# Gost 微信專用防爆連接池守護（精確修正命令格式）
def run_gost_bridge():
    print("🛡️ [Gost] 高性能連接池就位，強制監聽 IPv4 0.0.0.0:11111...", flush=True)
    # 👑 【修正】：取消所有換行，寫成一條純粹的單行指令，防止出現 not found 錯誤
    gost_cmd = "/app/gost -L=socks5://0.0.0.0:11111?mwm=100&max_conns=300&keepalive=true&ttl=30s -F=socks5://127.0.0.1:11112"
    subprocess.run(gost_cmd, shell=True)

# Tailscale 24小時不失眠哨兵控制中樞
def tailscale_sentinel():
    authkey = os.getenv("TAILSCALE_AUTHKEY", "")
    api_secret = os.getenv("TS_API_SECRET", "")
    
    if not authkey or not api_secret:
        print("❌ [哨兵] 錯誤: 缺少環境變量，監控終止！", flush=True)
        return

    print("扫地 [清場] 正在強力清空後台殘留進程...", flush=True)
    os.system("pkill -9 -f tailscaled")
    os.system("pkill -9 -f tailscale")
    os.system("pkill -9 -f gost")
    time.sleep(3)

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
            # 檢查本地狀態
            result = subprocess.run(
                ["/usr/local/bin/tailscale", "--socket=/app/ts_run/tailscaled.sock", "status", "--json"],
                capture_output=True, text=True
            )
            
            if result.returncode != 0:
                print("🚨 [哨兵] 檢測到 Tailscale 核心無響應，正在自動重置進程...", flush=True)
                os.system("pkill -9 -f tailscaled")
                time.sleep(2)
                os.system(ts_daemon_cmd)
                time.sleep(5)
                continue

            status_data = json.loads(result.stdout)
            current_name = status_data.get("Self", {}).get("DNSName", "").split(".")[0]
            
            # 👑 【核心邏輯修正】：不再盲目擊殺！只有當節點名稱不對（被搶名）才觸發清理
            if current_name == "render-proxy":
                time.sleep(60) # 如果名字拿到了，安穩巡邏即可，絕對不觸發 API 清理
                continue
                
            print(f"⚠️ [哨兵] 當前名稱為 [{current_name}]，開始對雲端老舊殘留節點進行精確獵殺...", flush=True)
            
            api_url_base = "https://api.tailscale.com/api/v2/tailnet/-/devices"
            devices_res = subprocess.run(f"curl -s -u \"{api_secret}:\" {api_url_base}", shell=True, capture_output=True, text=True)
            
            if devices_res.returncode == 0:
                devices_data = json.loads(devices_res.stdout)
                for device in devices_data.get("devices", []):
                    hostname = device.get("hostname", "")
                    
                    # 👑 【安全識別鎖】：只獵殺名字叫 render-proxy 且「不是今天新註冊」或者「已經離線」的節點
                    if hostname.startswith("render-proxy"):
                        # 解析雲端節點的創建時間
                        # Tailscale API 返回格式如: "2026-06-05T01:40:00Z"
                        created_str = device.get("created", "")
                        is_online = device.get("connected", False)
                        old_id = device.get("id")
                        
                        # 如果該節點已經不線上，或者它是更早之前殘留的，直接擊殺
                        if not is_online:
                            print(f"💥 [哨兵] 發現離線老殘留節點 [{hostname}] (ID: {old_id})，執行擊殺...", flush=True)
                            subprocess.run(f"curl -s -X DELETE -u \"{api_secret}:\" {api_url_base}/{old_id}", shell=True, capture_output=True)
            
            # 確保清理完殘留後，自己再執行一次強力的註冊
            print(f"🚀 [哨兵] 發起搶名衝鋒，正在將當前實例綁定至 [render-proxy]...", flush=True)
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
