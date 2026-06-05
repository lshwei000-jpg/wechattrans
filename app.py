import os
import sys
import time
import json
import threading
import subprocess
import urllib.request
import base64
from flask import Flask

app = Flask(__name__)

# 全局鎖，防止自癒線程與常規監控線程引發衝突
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

# 👑 2. 啟動 Tailscale 內核
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
    time.sleep(4) # 留足時間建立本地網絡棧

# 👑 3. 拉起 Gost 防爆池
def launch_gost():
    print("🛡️ [Gost] 正在注入高性能連接池參數 (容量: 1000)...", flush=True)
    gost_raw_cmd = "/app/gost -L=socks5://0.0.0.0:11111?mwm=200&max_conns=1000&keepalive=true&ttl=15s -F=socks5://127.0.0.1:11112 > /dev/null 2>&1 &"
    os.system(gost_raw_cmd)
    time.sleep(1)

# 👑 4. 融合《參考代碼》：5輪智能閉環自癒奪名引擎
def tailscale_smart_autofix_and_up():
    auth_key = os.getenv("TAILSCALE_AUTHKEY", "")
    api_secret = os.getenv("TS_API_SECRET", "")
    
    if not auth_key:
        print("❌ [智能自愈] 未檢測到 TAILSCALE_AUTHKEY，終止網絡建立！", flush=True)
        return

    # 🚀 執行第一次登入嘗試（如果正統名字被佔用，此時名字會被降級為 render-proxy-1 或 -2）
    print("🚀 [智能自愈] 發起初始網絡衝鋒...", flush=True)
    os.system(f"/usr/local/bin/tailscale --socket=/app/ts_run/tailscaled.sock up --authkey={auth_key} --hostname=render-proxy --accept-dns=false")
    
    print("🚀 [智能自愈] 啟動閉環重置監控...", flush=True)
    
    # 融合：整體大循環最多嘗試 5 次 [cite: 58]
    for big_loop in range(1, 6):
        print(f"🔄 [智能自愈] [大循環] 正在執行第 {big_loop} / 5 輪狀態確認...", flush=True)
        time.sleep(3)
        
        try:
            # 查戶口：讀取本地節點狀態 [cite: 59]
            result = subprocess.run(
                ["/usr/local/bin/tailscale", "--socket=/app/ts_run/tailscaled.sock", "status", "--json"],
                capture_output=True, text=True, check=True
            )
            status_data = json.loads(result.stdout)
            full_status_name = status_data.get("Self", {}).get("DNSName", "").split(".")[0] [cite: 59]
            
            # 【終極目標】名字完全歸位為正統的 render-proxy，大獲全勝，直接退出奪名程序 [cite: 60]
            if full_status_name == "render-proxy":
                print(f"🎉🎉🎉 【大獲全勝】本機名稱已完美鎖定為 [render-proxy]！", flush=True)
                break
                
            # 如果發現自身名字帶有髒後綴（例如 render-proxy-1, render-proxy-2） [cite: 61]
            if "render-proxy-" in full_status_name:
                print(f"⚠️ [智能自愈] 警報！本機當前叫: {full_status_name}。正統名字被霸佔，啟動奪名程序...", flush=True)
                
                peers = status_data.get("Peer", {}) [cite: 61]
                target_api_id = None
                
                # 在 Peer 列表中精確搜尋那個霸占了 render-proxy 正統名字的老節點 ID [cite: 61, 62]
                for peer_id, peer_info in peers.items():
                    if peer_info.get("HostName", "") == "render-proxy":
                        target_api_id = peer_info.get("ID", "") [cite: 62]
                        break
                
                # 步驟 A：如果發現了叫 render-proxy 的老節點，精確調用 API 強制抹除 [cite: 63]
                if target_api_id:
                    print(f"💥 [智能自愈] 找到老節點 ID: {target_api_id}，調用雲端 API 強制抹除...", flush=True)
                    # 修正為正確的官方註銷 API URL 格式 [cite: 63]
                    url = f"https://api.tailscale.com/api/v2/device/{target_api_id}" [cite: 63]
                    
                    req = urllib.request.Request(url, method="DELETE") [cite: 64]
                    auth_str = base64.b64encode(f":{api_secret}".encode()).decode() [cite: 64]
                    req.add_header("Authorization", f"Basic {auth_str}") [cite: 64]
                    
                    try:
                        with urllib.request.urlopen(req) as response: [cite: 65]
                            if response.status in [200, 204]: [cite: 65]
                                print("🗡️ [智能自愈] API 擊殺成功，進入【回讀確認小循環】...", flush=True) [cite: 65]
                    except Exception as api_err:
                        print(f"❌ [智能自愈] API 擊殺請求異常: {str(api_err)}", flush=True) [cite: 66]
                else:
                    print("ℹ️ [智能自愈] 列表中目前沒看到叫 render-proxy 的老設備，可能已被雲端釋放。", flush=True) [cite: 66]
                
                # 步驟 B：【回讀確認】等待老節點在本地名單中徹底消失 [cite: 67]
                killed_successfully = False [cite: 67]
                for verify_count in range(1, 7): # 每 5 秒確認一次，最多等 30 秒 [cite: 67]
                    time.sleep(5)
                    print(f"🔍 [智能自愈] 正在進行第 {verify_count} 次雲端名單回讀確認...", flush=True) [cite: 67]
                    
                    v_result = subprocess.run(
                        ["/usr/local/bin/tailscale", "--socket=/app/ts_run/tailscaled.sock", "status", "--json"],
                        capture_output=True, text=True, check=True [cite: 68]
                    )
                    v_status = json.loads(v_result.stdout)
                    v_peers = v_status.get("Peer", {}) [cite: 69]
                    
                    # 檢查叫 render-proxy 的老傢伙走了沒 [cite: 70]
                    still_exists = any(p.get("HostName", "") == "render-proxy" for p in v_peers.values()) [cite: 70]
                    
                    if not still_exists:
                        print("💡 [智能自愈] [驗證成功]：雲端老節點已徹底蒸發，資料庫已純淨！", flush=True) [cite: 70]
                        killed_successfully = True [cite: 71]
                        break
                    else:
                        print("⏳ [智能自愈] [繼續等待]：雲端資料庫尚未同步，老節點依然殘留...", flush=True) [cite: 71]
                
                # 步驟 C：【本機自切重置】（核心修正：登出解綁以重置髒名稱快取） 
                print("♻️ [智能自愈] 正在執行本機登出解綁 (tailscale logout)，清空髒名稱緩存...", flush=True) [cite: 72]
                subprocess.run(["/usr/local/bin/tailscale", "--socket=/app/ts_run/tailscaled.sock", "logout"], capture_output=True) [cite: 72]
                time.sleep(3) [cite: 73]
                
                # 步驟 D：全新衝鋒，重新搶佔正統官名 
                print("🚀 [智能自愈] 本地已純淨，正在發起全新 [render-proxy] 官名搶佔...", flush=True) [cite: 73]
                os.system(f"/usr/local/bin/tailscale --socket=/app/ts_run/tailscaled.sock up --authkey={auth_key} --hostname=render-proxy --accept-dns=false") [cite: 73]
                
        except Exception as e:
            print(f"❌ [智能自愈] 自愈大循環執行異常: {str(e)}", flush=True) [cite: 74]
            
    print("🏁 [智能自愈] 限時自愈任務編排結束。", flush=True) [cite: 74]

# 👑 5. 總控制中樞
def master_orchestrator():
    with recovery_lock:
        physical_cleanup()                 # 1. 物理清場 [cite: 45]
        launch_tailscaled()                # 2. 本地點火 [cite: 45]
        tailscale_smart_autofix_and_up()   # 3. 5輪自癒奪名（融合《參考代碼》核心）
        launch_gost()                      # 4. 後端就緒，拉起轉發橋樑 [cite: 45, 46]
    
    print("👁️ [哨兵系統] 雙軌自癒巡邏（Tailscale 狀態 + Gost 端口監控）已完全上線...", flush=True) [cite: 46]
    
    ts_fail_count = 0
    while True:
        time.sleep(30)
        
        # ───【TRACK 1: TAILSCALE 健康度巡檢】───
        try:
            status_res = subprocess.run( [cite: 46]
                ["/usr/local/bin/tailscale", "--socket=/app/ts_run/tailscaled.sock", "status", "--json"],
                capture_output=True, text=True [cite: 47]
            )
            is_healthy = False
            if status_res.returncode == 0:
                status_data = json.loads(status_res.stdout) [cite: 47]
                if status_data.get("Self", {}).get("Online", False) is True: [cite: 48]
                    is_healthy = True
            
            if is_healthy:
                ts_fail_count = 0
            else:
                ts_fail_count += 1 [cite: 49]
                print(f"⚠️ [Tailscale 哨兵] 警告: 檢測到內核 Offline ({ts_fail_count}/2)...", flush=True) [cite: 49]
                
            if ts_fail_count >= 2:
                print("🚨 [Tailscale 哨兵] 連續連線雙檢失敗！執行全面重啟與奪名自癒...", flush=True) [cite: 49]
                with recovery_lock:
                    physical_cleanup() [cite: 50]
                    launch_tailscaled() [cite: 50]
                    tailscale_smart_autofix_and_up()
                    launch_gost() [cite: 50]
                ts_fail_count = 0 [cite: 51]
                continue
                
        except Exception as e:
            print(f"🔴 [Tailscale 哨兵] 異常: {str(e)}", flush=True) [cite: 51]

        # ───【TRACK 2: GOST 真正活動連線死鎖監控】───
        try:
            netstat_cmd = "netstat -an | grep :11111 | grep ESTABLISHED | wc -l" [cite: 52, 53]
            netstat_res = subprocess.run(netstat_cmd, shell=True, capture_output=True, text=True) [cite: 53]
            active_conn = 0
            if netstat_res.returncode == 0:
                active_conn = int(netstat_res.stdout.strip()) [cite: 53]
            
            if active_conn >= 850: [cite: 53]
                print(f"🚨 [Gost 哨兵] 警告: 本地 11111 端口真實活動連線達 {active_conn}，遭遇死鎖邊緣！", flush=True) [cite: 54]
                with recovery_lock:
                    os.system("pkill -9 -f gost") [cite: 54]
                    time.sleep(5)  [cite: 54]
                    launch_gost() [cite: 54]
                print("✅ [Gost 哨兵] 微信爆池已強制清空并完成重拉。", flush=True) [cite: 55]
                time.sleep(15)  [cite: 55]
                
        except Exception as e:
            print(f"🔴 [Gost 哨兵] 掃描異常: {str(e)}", flush=True) [cite: 55]

if __name__ == '__main__':
    threading.Thread(target=master_orchestrator, daemon=True).start() [cite: 56]
    port = int(os.environ.get("PORT", 10000)) [cite: 56]
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False) [cite: 56]
