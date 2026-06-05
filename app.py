import os
import sys
import time
import json
import threading
import subprocess
from flask import Flask
import requests

app = Flask(__name__)

recovery_lock = threading.Lock()

def get_mock_html():
    html_path = os.path.join(os.path.dirname(__file__), 'index.html')
    if os.path.exists(html_path):
        with open(html_path, 'r', encoding='utf-8') as f:
            return f.read()
    return "<h1>Proxy Service is running normally.</h1>"

@app.route('/')
def home():
    return get_mock_html(), 200

# 👑 1. 物理清場
def physical_cleanup():
    print("🧹 [清場] 正在強力回收本地網絡進程與僵屍埠...", flush=True)
    os.system("pkill -9 -f tailscaled")
    os.system("pkill -9 -f tailscale")
    os.system("pkill -9 -f gost")
    time.sleep(2)

# 👑 2. 雲端清除衝突節點（確保 100% 拿到固定域名）
def tailscale_api_kill_blocking_nodes():
    api_secret = os.getenv("TS_API_SECRET", "")
    if not api_secret:
        print("❌ [API 獵殺] 錯誤: 缺少 TS_API_SECRET 環境變量，無法執行雲端清理！", flush=True)
        return

    try:
        print("🎯 [API 獵殺] 正在請求雲端設備清單，準備為新域名清空障礙...", flush=True)
        api_url = "https://api.tailscale.com/api/v2/tailnet/-/devices"
        res = requests.get(api_url, auth=(api_secret, ''))
        
        if res.status_code == 200:
            devices = res.json().get("devices", [])
            for device in devices:
                hostname = device.get("hostname", "")
                # 🔥 只要名字包含 render-proxy（不管是完全同名，還是之前被降級的 render-proxy-1），全部連根拔起
                if hostname.startswith("render-proxy"):
                    node_id = device.get("id")
                    print(f"💥 [API 獵殺] 發現衝突節點 [{hostname}] (ID: {node_id})，執行強制抹殺...", flush=True)
                    del_res = requests.delete(f"{api_url}/{node_id}", auth=(api_secret, ''))
                    if del_res.status_code == 200:
                        print(f"✅ [API 獵殺] 節點 [{hostname}] 已成功從雲端註銷。", flush=True)
            # 給雲端拓撲同步留出 2 秒刷新時間
            time.sleep(2)
        else:
            print(f"⚠️ [API 獵殺] 獲取設備清單失敗，錯誤碼: {res.status_code}", flush=True)
    except Exception as e:
        print(f"🔴 [API 獵殺] 執行異常: {str(e)}", flush=True)

# 👑 3. 啟動 Tailscale 內核
def launch_tailscaled():
    print("🚀 [Tailscale] 正在拉起用戶態核心守護進程...", flush=True)
    ts_daemon_cmd = (
        "/usr/local/bin/tailscaled "
        "--tun=userspace-networking "
        "--socks5-server=127.0.0.1:11112 "
        "--socket=/app/ts_run/tailscaled.sock "
        "--state=/app/ts_var/tailscaled.state > /dev/null 2>&1 &"
    )
    os.system(ts_daemon_cmd)
    time.sleep(5) # 留足 5 秒建立本地網路棧

# 👑 4. 註冊登入固定域名
def tailscale_up():
    authkey = os.getenv("TAILSCALE_AUTHKEY", "")
    print("🎯 [Tailscale] 雲端已乾淨，正式發起註冊，鎖定唯一的 [render-proxy] 域名...", flush=True)
    up_cmd = [
        "/usr/local/bin/tailscale", "--socket=/app/ts_run/tailscaled.sock", 
        "up", f"--authkey={authkey}", "--hostname=render-proxy", "--reset"
    ]
    subprocess.run(up_cmd, capture_output=True)
    print("✅ [Tailscale] 核心認證登入成功！", flush=True)

# 👑 5. 拉起 Gost 防爆池
def launch_gost():
    print("🛡️ [Gost] 正在注入高性能連接池參數 (容量: 1000)...", flush=True)
    gost_cmd = [
        "/app/gost",
        "-L=socks5://0.0.0.0:11111?mwm=200&max_conns=1000&keepalive=true&ttl=15s",
        "-F=socks5://127.0.0.1:11112"
    ]
    subprocess.Popen(gost_cmd, shell=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# 👑 總調度哨兵
def master_orchestrator():
    # 🏃 啟動時的黃金線性順序
    with recovery_lock:
        physical_cleanup()
        tailscale_api_kill_blocking_nodes() # Step 1: 先在雲端殺人
        launch_tailscaled()                 # Step 2: 本地點火
        tailscale_up()                      # Step 3: 登入註冊拿到乾淨名字
        launch_gost()                       # Step 4: 後端就緒後，拉起轉發橋樑
    
    print("👁️ [哨兵系統] 雙軌自癒巡邏已完全上線...", flush=True)
    
    ts_fail_count = 0
    while True:
        time.sleep(30)
        
        # ───【TRACK 1: TAILSCALE 健康度雙檢測】───
        try:
            status_res = subprocess.run(
                ["/usr/local/bin/tailscale", "--socket=/app/ts_run/tailscaled.sock", "status", "--json"],
                capture_output=True, text=True
            )
            is_healthy = False
            if status_res.returncode == 0:
                status_data = json.loads(status_res.stdout)
                if status_data.get("Self", {}).get("Online", False) is True:
                    is_healthy = True
            
            if is_healthy:
                ts_fail_count = 0
            else:
                ts_fail_count += 1
                print(f"⚠️ [Tailscale 哨兵] 警告: 檢測到內核 Offline ({ts_fail_count}/2)...", flush=True)
                
            if ts_fail_count >= 2:
                print("🚨 [Tailscale 哨兵] 連續連線雙檢失敗！執行全面重啟自癒...", flush=True)
                with recovery_lock:
                    physical_cleanup()
                    tailscale_api_kill_blocking_nodes()
                    launch_tailscaled()
                    tailscale_up()
                    launch_gost()
                ts_fail_count = 0
                continue
                
        except Exception as e:
            print(f"🔴 [Tailscale 哨兵] 異常: {str(e)}", flush=True)

        # ───【TRACK 2: GOST 真正活動連線死鎖監控】───
        try:
            netstat_cmd = "netstat -an | grep :11111 | grep ESTABLISHED | wc -l"
            netstat_res = subprocess.run(netstat_cmd, shell=True, capture_output=True, text=True)
            active_conn = 0
            if netstat_res.returncode == 0:
                active_conn = int(netstat_res.stdout.strip())
            
            if active_conn >= 850:
                print(f"🚨 [Gost 哨兵] 警告: 本地 11111 端口真實活動連線達 {active_conn}，遭遇死鎖邊緣！", flush=True)
                with recovery_lock:
                    os.system("pkill -9 -f gost")
                    time.sleep(5) 
                    launch_gost()
                print("✅ [Gost 哨兵] 微信爆池已強制清空并完成重拉。", flush=True)
                time.sleep(15) 
                
        except Exception as e:
            print(f"🔴 [Gost 哨兵] 掃描異常: {str(e)}", flush=True)

if __name__ == '__main__':
    threading.Thread(target=master_orchestrator, daemon=True).start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
