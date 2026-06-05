import os
import sys
import time
import json
import threading
import subprocess
from datetime import datetime
from flask import Flask
import requests

app = Flask(__name__)

recovery_lock = threading.Lock()
CONTAINER_BOOT_TIME = time.time()

def get_mock_html():
    html_path = os.path.join(os.path.dirname(__file__), 'index.html')
    if os.path.exists(html_path):
        with open(html_path, 'r', encoding='utf-8') as f:
            return f.read()
    return "<h1>Proxy Service is running normally.</h1>"

@app.route('/')
def home():
    return get_mock_html(), 200

def physical_cleanup():
    print("🧹 [清場] 正在強力回收本地網絡進程與僵屍埠...", flush=True)
    os.system("pkill -9 -f tailscaled")
    os.system("pkill -9 -f tailscale")
    os.system("pkill -9 -f gost")
    time.sleep(3)

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
    time.sleep(5)

def launch_gost():
    # 👑 調整：將 max_conns 大幅提升至 1000，完美容納微信狂暴的短連接
    print("🛡️ [Gost] 正在注入高階長連接與埠回收參數 (容量擴展至 1000)...", flush=True)
    gost_cmd = [
        "/app/gost",
        "-L=socks5://0.0.0.0:11111?mwm=200&max_conns=1000&keepalive=true&ttl=15s",
        "-F=socks5://127.0.0.1:11112"
    ]
    subprocess.Popen(gost_cmd, shell=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def tailscale_api_grab_and_up():
    authkey = os.getenv("TAILSCALE_AUTHKEY", "")
    api_secret = os.getenv("TS_API_SECRET", "")
    
    if not authkey or not api_secret:
        print("❌ [API 奪名] 錯誤: 缺少環境變量，跳過搶名直接嘗試 up 登入...", flush=True)
    else:
        try:
            print("🎯 [API 奪名] 正在請求雲端設備清單...", flush=True)
            api_url = "https://api.tailscale.com/api/v2/tailnet/-/devices"
            res = requests.get(api_url, auth=(api_secret, ''))
            
            if res.status_code == 200:
                devices = res.json().get("devices", [])
                for device in devices:
                    hostname = device.get("hostname", "")
                    if hostname.startswith("render-proxy"):
                        created_str = device.get("created", "")
                        created_dt = datetime.strptime(created_str, "%Y-%m-%dT%H:%M:%SZ")
                        created_timestamp = created_dt.timestamp()
                        
                        if created_timestamp < CONTAINER_BOOT_TIME:
                            old_id = device.get("id")
                            print(f"💥 [API 奪名] 發現歷史殘留節點 [{hostname}]，執行精確獵殺...", flush=True)
                            requests.delete(f"{api_url}/{old_id}", auth=(api_secret, ''))
            else:
                print(f"⚠️ [API 奪名] 獲取設備清單失敗: {res.status_code}", flush=True)
        except Exception as e:
            print(f"🔴 [API 奪名] 執行異常: {str(e)}", flush=True)

    print("🚀 [Tailscale] 發起搶名衝鋒，正在將當前實例強行鎖定至 [render-proxy]...", flush=True)
    up_cmd = [
        "/usr/local/bin/tailscale", "--socket=/app/ts_run/tailscaled.sock", 
        "up", f"--authkey={authkey}", "--hostname=render-proxy", "--reset"
    ]
    subprocess.run(up_cmd, capture_output=True)
    print("✅ [Tailscale] 域名覆蓋認證已完成！", flush=True)

def master_orchestrator():
    with recovery_lock:
        physical_cleanup()
        launch_tailscaled()
        launch_gost()
        tailscale_api_grab_and_up()
    
    print("👁️ [哨兵系統] 雙軌自癒巡邏（Tailscale 狀態 + Gost 埠耗盡）已完全上線...", flush=True)
    
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
                    launch_tailscaled()
                    launch_gost()
                    tailscale_api_grab_and_up()
                ts_fail_count = 0
                continue
                
        except Exception as e:
            print(f"🔴 [Tailscale 哨兵] 異常: {str(e)}", flush=True)

        # ───【TRACK 2: GOST 真正活動連線死鎖監控】───
        try:
            # 👑 核心優化：增加 | grep ESTABLISHED，只統計當前真正活躍通訊的連線，精確排除 TIME_WAIT 噪點
            netstat_cmd = "netstat -an | grep :11111 | grep ESTABLISHED | wc -l"
            netstat_res = subprocess.run(netstat_cmd, shell=True, capture_output=True, text=True)
            active_conn = 0
            if netstat_res.returncode == 0:
                active_conn = int(netstat_res.stdout.strip())
            
            # 當真正活躍的併發連線逼近我們設定的 1000 臨界點時（例如超過 850），才觸發自癒
            if active_conn >= 850:
                print(f"🚨 [Gost 哨兵] 警告: 本地 11111 端口真實活動連線達 {active_conn}，遭遇狂暴微信死鎖！", flush=True)
                with recovery_lock:
                    os.system("pkill -9 -f gost")
                    time.sleep(5) # 留足時間給系統釋放緩衝
                    launch_gost()
                print("✅ [Gost 哨兵] 微信爆池已強制清空，Gost 已重拉並進入冷卻期。", flush=True)
                time.sleep(15) # 強制休眠 15 秒，躲過過渡期的 TIME_WAIT 噪點
                
        except Exception as e:
            print(f"🔴 [Gost 哨兵] 掃描異常: {str(e)}", flush=True)

if __name__ == '__main__':
    threading.Thread(target=master_orchestrator, daemon=True).start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
