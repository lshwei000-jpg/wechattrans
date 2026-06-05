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

# 👑 4. 5輪智能閉環自癒奪名引擎（極致防禦安全版）
def tailscale_smart_autofix_and_up():
    auth_key = os.getenv("TAILSCALE_AUTHKEY", "")
    api_secret = os.getenv("TS_API_SECRET", "") 
    if not auth_key:
        print("❌ [智能自愈] 未檢測到 TAILSCALE_AUTHKEY，終止啟動。", flush=True)
        return

    # 🚀 執行第一次登入嘗試（如果正統名字被佔用，此時本機名字會被降級為 -1 或 -2）
    print("🚀 [智能自愈] 發起初始網絡衝鋒...", flush=True)
    os.system(f"/usr/local/bin/tailscale --socket=/app/ts_run/tailscaled.sock up --authkey={auth_key} --hostname=render-proxy --accept-dns=false")
    
    print("🚀 [智能自愈] 啟動閉環重置監控...", flush=True)
    
    # 5輪死磕確認
    for big_loop in range(1, 6):
        print(f"🔄 [智能自愈] [大循環] ======= 正在執行第 {big_loop} / 5 輪狀態確認 =======", flush=True)
        time.sleep(4) 
        
        # 🔥 核心防禦：提前初始化安全變數，徹底杜絕 UnboundLocalError
        full_status_name = ""
        
        try:
            # 讀取本地狀態
            result = subprocess.run(
                ["/usr/local/bin/tailscale", "--socket=/app/ts_run/tailscaled.sock", "status", "--json"],
                capture_output=True, text=True, check=True
            )
            status_data = json.loads(result.stdout)
            
            self_info = status_data.get("Self", {})
            dns_name = self_info.get("DNSName", "")
            
            if dns_name:
                full_status_name = dns_name.split(".")[0]
            else:
                full_status_name = self_info.get("HostName", "")
                
            print(f"ℹ️ [智能自愈] 本機當前在網內被識別為名稱: [{full_status_name}]", flush=True)
            
            # 【情況 A】名字完全歸位，大獲全勝，直接退出自癒
            if full_status_name == "render-proxy":
                print(f"🎉🎉🎉 【大獲全勝】本機名稱已完美鎖定為 [render-proxy]！", flush=True)
                break
                
            # 【情況 B】發現自身名字帶有髒後綴（例如 render-proxy-1, render-proxy-2）
            elif "render-proxy" in full_status_name and full_status_name != "render-proxy":
                print(f"⚠️ [智能自愈] 警報！正統名字被老設備霸佔，啟動奪名程序...", flush=True)
                
                peers = status_data.get("Peer", {})
                target_api_id = None
                for peer_id, peer_info in peers.items():
                    if peer_info.get("HostName", "") == "render-proxy":
                        target_api_id = peer_info.get("ID", "")
                        break
                
                # 步驟 A：API 精確隔空擊殺老節點
                if target_api_id:
                    print(f"💥 [智能自愈] 找到老節點 ID: {target_api_id}，調用雲端 API 強制抹除...", flush=True)
                    url = f"https://api.tailscale.com/api/v2/device/{target_api_id}"
                    req = urllib.request.Request(url, method="DELETE")
                    
                    # 密鑰放在用戶名位置，格式為 api_secret:
                    auth_str = base64.b64encode(f"{api_secret}:".encode()).decode()
                    req.add_header("Authorization", f"Basic {auth_str}")
                    
                    try:
                        with urllib.request.urlopen(req) as response:
                            if response.status in [200, 204]:
                                print("🗡️ [智能自愈] API 擊殺成功，進入【回讀確認小循環】...", flush=True)
                    except Exception as api_err:
                        print(f"❌ [智能自愈] API 擊殺請求異常: {str(api_err)}", flush=True)
                else:
                    print("ℹ️ [智能自愈] 列表中目前沒看到叫 render-proxy 的老設備，可能已被雲端釋放。", flush=True)
                
                # 步驟 B：【回讀確認】等待老節點在雲端名單中徹底消失
                for verify_count in range(1, 7): 
                    time.sleep(5)
                    print(f"🔍 [智能自愈] 正在進行第 {verify_count} 次雲端名單回讀確認...", flush=True)
                    
                    v_result = subprocess.run(
                        ["/usr/local/bin/tailscale", "--socket=/app/ts_run/tailscaled.sock", "status", "--json"],
                        capture_output=True, text=True, check=True
                    )
                    v_status = json.loads(v_result.stdout)
                    v_peers = v_status.get("Peer", {})
                    
                    still_exists = any(p.get("HostName", "") == "render-proxy" for p in v_peers.values())
                    
                    if not still_exists:
                        print("💡 [智能自愈] [驗證成功]：雲端老節點已徹底蒸發，資料庫已純淨！", flush=True)
                        break
                    else:
                        print("⏳ [智能自愈] [繼續等待]：雲端資料庫尚未同步，老節點依然殘留...", flush=True)
                
                # 步驟 C：【本機自切重置】
                print("♻️ [智能自愈] 正在執行本機登出解綁 (tailscale logout)，清空髒名稱緩存...", flush=True)
                subprocess.run(["/usr/local/bin/tailscale", "--socket=/app/ts_run/tailscaled.sock", "logout"], capture_output=True)
                time.sleep(3)
                
                # 步驟 D：全新衝鋒，重新搶佔正統官名
                print("🚀 [智能自愈] 本地已純淨，正在發起全新 [render-proxy] 官名搶佔...", flush=True)
                os.system(f"/usr/local/bin/tailscale --socket=/app/ts_run/tailscaled.sock up --authkey={auth_key} --hostname=render-proxy --accept-dns=false")
            
            # 【情況 C】名稱為空或尚未初始化完畢，不崩潰，重新 Up 觸發握手
            else:
                print("⏳ [智能自愈] 網卡尚未完全初始化或名稱為空，嘗試重新發起 Up 握手刷新...", flush=True)
                os.system(f"/usr/local/bin/tailscale --socket=/app/ts_run/tailscaled.sock up --authkey={auth_key} --hostname=render-proxy --accept-dns=false")

        except Exception as e:
            print(f"❌ [智能自愈] 自愈大循環內部執行異常: {str(e)}", flush=True)
            
    print("🏁 [限時自愈] 閉環驗證任務結束。", flush=True)

# 👑 總調度哨兵
def master_orchestrator():
    # 🏃 黃金線性順序
    with recovery_lock:
        physical_cleanup()                  # Step 1: 物理清場
        launch_tailscaled()                 # Step 2: 本地點火
        tailscale_smart_autofix_and_up()   # Step 3: 進入 5 輪智能自癒奪名（內部包含了所有認證與清理）
        launch_gost()                      # Step 4: 後端完全就緒，拉起轉發橋樑
    
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
                    launch_tailscaled()
                    tailscale_smart_autofix_and_up()
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
