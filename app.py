import os
import sys
import time
import json
import threading
import subprocess
from flask import Flask, Response

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
    print("🛡️ [Gost] 正在拉起微信專用高性能連接池...", flush=True)
    # 鎖定最大300個長連接，開啟記憶體復用，加入30秒超時主動回收，物理閹割 TIME_WAIT 堆積
    gost_cmd = (
        "/app/gost "
        "-L=socks5://:11111?mwm=100&max_conns=300&keepalive=true&ttl=30s "
        "-F=socks5://127.0.0.1:11112"
    )
    subprocess.run(gost_cmd, shell=True)

# 👑 Tailscale 24小時不失眠哨兵（帶自癒重啟邏輯）
def tailscale_sentinel():
    authkey = os.getenv("TAILSCALE_AUTHKEY", "")
    api_secret = os.getenv("TS_API_SECRET", "")
    
    if not authkey or not api_secret:
        print("❌ [哨兵] 錯誤: 缺少環境變量 TAILSCALE_AUTHKEY 或 TS_API_SECRET，監控終止！", flush=True)
        return

    # 首次啟動用戶態內核
    print("🚀 [哨兵] 正在初始化 Tailscale 用戶態核心...", flush=True)
    os.system("/usr/bin/tailscaled --tun=userspace-networking --socks5-server=127.0.0.1:11112 --socket=/app/ts_run/tailscaled.sock > /dev/null 2>&1 &")
    time.sleep(5)

    # 啟動 Gost 橋樑對接
    threading.Thread(target=run_gost_bridge, daemon=True).start()

    # 進入 24 小時無限巡邏大循環
    print("👁️ [哨兵] 24小時不間斷網絡健康監控已上線...", flush=True)
    
    while True:
        try:
            # 檢查當前節點狀態
            result = subprocess.run(
                ["/usr/bin/tailscale", "--socket=/app/ts_run/tailscaled.sock", "status", "--json"],
                capture_output=True, text=True, check=True
            )
            status_data = json.loads(result.stdout)
            current_name = status_data.get("Self", {}).get("DNSName", "").split(".")[0]
            
            # 情況 A：名正言順，穩穩鎖定
            if current_name == "render-proxy":
                print("🟢 [哨兵巡邏] 網絡通道完美，正統標籤 [render-proxy] 鎖定中。", flush=True)
                time.sleep(60) # 正常狀態下，每 60 秒巡邏一次，極致節省 CPU
                continue
                
            # 情況 B：被搶名，降級為 render-proxy-1 等，觸發擊殺自癒
            print(f"⚠️ [哨兵巡邏] 檢測到名稱異常降級為 [{current_name}]，啟動雲端老節點清理...", flush=True)
            
            # 調用 API 強殺阻礙域名的老殘留
            api_cmd = f"curl -s -X DELETE -u \"{api_secret}:\" https://api.tailscale.com/api/v2/tailnet/-/devices"
            devices_res = subprocess.run(f"curl -s -u \"{api_secret}:\" https://api.tailscale.com/api/v2/tailnet/-/devices", shell=True, capture_output=True, text=True)
            
            if devices_res.returncode == 0:
                devices_data = json.loads(devices_res.stdout)
                for device in devices_data.get("devices", []):
                    if device.get("hostname") == "render-proxy" and device.get("id") != status_data.get("Self", {}).get("ID"):
                        old_id = device.get("id")
                        subprocess.run(f"{api_cmd}/{old_id}", shell=True, capture_output=True)
                        print(f"💥 [哨兵] 已成功擊殺殘留老節點 ID: {old_id}", flush=True)
            
            # 重新登入以奪回正統域名
            print("🔄 [哨兵] 正在重新登入以奪取正統域名...", flush=True)
            subprocess.run([
                "/usr/bin/tailscale", "--socket=/app/ts_run/tailscaled.sock", 
                "up", f"--authkey={authkey}", "--hostname=render-proxy", "--reset"
            ], capture_output=True)
            
        except Exception as e:
            print(f"🔴 [哨兵異常] 監控大循環出錯: {str(e)}，將在 15 秒後嘗試重置...", flush=True)
            time.sleep(15)

if __name__ == '__main__':
    # 啟動守護線程
    threading.Thread(target=tailscale_sentinel, daemon=True).start()
    
    # 兼容 Render / Railway 端口綁定機制
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
