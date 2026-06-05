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

# 全局鎖，防止 Tailscale 與 Gost 的自癒線程同時引發清場衝突
recovery_lock = threading.Lock()

# 容器本地啟動時間戳，用於 API 時間戳安全鎖
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

# 👑 物理強力清場函數
def physical_cleanup():
    print("🧹 [清場] 正在強力回收本地網絡進程與僵屍埠...", flush=True)
    os.system("pkill -9 -f tailscaled")
    os.system("pkill -9 -f tailscale")
    os.system("pkill -9 -f gost")
    time.sleep(3)

# 👑 模塊一：拉起 Tailscale 內核
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
    time.sleep(5) # 預留 5 秒給核心網絡棧建立

# 👑 模塊二：Gost 微信專用防爆長連接池（嚴格 List 傳參）
def launch_gost():
    print("🛡️ [Gost] 正在注入高階長連接與埠回收參數...", flush=True)
    # 鎖定最大 300 個併發，強制開啟長連接 keepalive，設置 30 秒 ttl 自動回收過期短連接
    gost_cmd = [
        "/app/gost",
        "-L=socks5://0.0.0.0:11111?mwm=100&max_conns=300&keepalive=true&ttl=30s",
        "-F=socks5://127.0.0.1:11112"
    ]
    # 使用 Popen 異步掛起，壓制內部日誌，避免刷屏
    subprocess.Popen(gost_cmd, shell=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# 👑 模塊三：API 時間戳安全鎖 ＆ 強制覆蓋域名登入
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
                    # 如果發現雲端有同名或降級的老節點
                    if hostname.startswith("render-proxy"):
                        created_str = device.get("created", "") # 格式: "2026-06-05T01:40:00Z"
                        # 將 ISO 時間解析為時間戳
                        created_dt = datetime.strptime(created_str, "%Y-%m-%dT%H:%M:%SZ")
                        created_timestamp = created_dt.timestamp()
                        
                        # 👑【核心安全鎖】：只有當雲端節點的創建時間，早於當前容器啟動時間，才判定為歷史殘留，執行精確獵殺
                        if created_timestamp < CONTAINER_BOOT_TIME:
                            old_id = device.get("id")
                            print(f"💥 [API 奪名] 發現歷史殘留節點 [{hostname}] (創建時間早於當前容器)，執行精確獵殺...", flush=True)
                            requests.delete(f"{api_url}/{old_id}", auth=(api_secret, ''))
            else:
                print(f"⚠️ [API 奪名] 獲取設備清單失敗，錯誤碼: {res.status_code}", flush=True)
        except Exception as e:
            print(f"🔴 [API 奪名] 執行異常: {str(e)}", flush=True)

    # 執行最終的搶名登入
    print("🚀 [Tailscale] 發起搶名衝鋒，正在將當前實例強行鎖定至 [render-proxy]...", flush=True)
    up_cmd = [
        "/usr/local/bin/tailscale", "--socket=/app/ts_run/tailscaled.sock", 
        "up", f"--authkey={authkey}", "--hostname=render-proxy", "--reset"
    ]
    subprocess.run(up_cmd, capture_output=True)
    print("✅ [Tailscale] 域名覆蓋認證已完成！", flush=True)

# 👑 總控制線程：生命周期編排
def master_orchestrator():
    with recovery_lock:
        physical_cleanup()
        launch_tailscaled()
        launch_gost()
        tailscale_api_grab_and_up()
    
    # 雙軌監控大循環上線
    print("👁️ [哨兵系統] 雙軌自癒巡邏（Tailscale 狀態 + Gost 埠耗盡）已完全上線...", flush=True)
    
    ts_fail_count = 0
    while True:
        time.sleep(30) # 每 30 秒高頻巡邏一次
        
        # ───【TRACK 1: TAILSCALE 連線與核心健康度雙檢測】───
        try:
            status_res = subprocess.run(
                ["/usr/local/bin/tailscale", "--socket=/app/ts_run/tailscaled.sock", "status", "--json"],
                capture_output=True, text=True
            )
            
            is_healthy = False
            if status_res.returncode == 0:
                status_data = json.loads(status_res.stdout)
                # 檢查 Online 狀態是否為 True
                if status_data.get("Self", {}).get("Online", False) is True:
                    is_healthy = True
            
            if is_healthy:
                ts_fail_count = 0 # 綠燈，重置失敗計數
            else:
                ts_fail_count += 1
                print(f"⚠️ [Tailscale 哨兵] 警告: 檢測到內核假死或處於 Offline 狀態 ({ts_fail_count}/2)...", flush=True)
                
            if ts_fail_count >= 2:
                print("🚨 [Tailscale 哨兵] 連續兩次連線雙檢失敗！立刻執行全面重啟自癒...", flush=True)
                with recovery_lock:
                    physical_cleanup()
                    launch_tailscaled()
                    launch_gost()
                    tailscale_api_grab_and_up()
                ts_fail_count = 0
                continue
                
        except Exception as e:
            print(f"🔴 [Tailscale 哨兵] 監控運行異常: {str(e)}", flush=True)

        # ───【TRACK 2: GOST 埠耗盡死鎖監控】───
        try:
            # 使用 netstat 掃描本地 11111 埠上的所有連接數
            netstat_res = subprocess.run("netstat -an | grep :11111 | wc -l", shell=True, capture_output=True, text=True)
            conn_count = 0
            if netstat_res.returncode == 0:
                conn_count = int(netstat_res.stdout.strip())
            
            # 如果發現埠堆積數已經超過了防爆池的極限（例如滿載300個或極度逼近）
            if conn_count >= 280:
                print(f"🚨 [Gost 哨兵] 警告: 檢測到本地 11111 埠連線數達 {conn_count}，處於耗盡死鎖邊緣！", flush=True)
                print("💥 [Gost 哨兵] 執行緊急物理重置，重啟 Gost 以強制關閉並釋放所有僵死埠...", flush=True)
                with recovery_lock:
                    os.system("pkill -9 -f gost")
                    time.sleep(2)
                    launch_gost()
                print("✅ [Gost 哨兵] Gost 連接池已被清空並成功重拉！", flush=True)
                
        except Exception as e:
            print(f"🔴 [Gost 哨兵] 埠掃描異常: {str(e)}", flush=True)

if __name__ == '__main__':
    # 啟動雙軌守護中樞
    threading.Thread(target=master_orchestrator, daemon=True).start()
    
    # 響應雲端 Web 伺服器健康檢查
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
