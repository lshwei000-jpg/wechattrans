#!/bin/bash

# --- 配置参数 ---
NODE_NAME="render-proxy"
TS_API_URL="https://api.tailscale.com/api/v2"

# 检查必要变量
if [ -z "$TAILSCALE_AUTHKEY" ] || [ -z "$TS_API_SECRET" ] || [ -z "$TS_ORGANIZATION" ]; then
    echo "[ERROR] 缺少必要环境变量：TAILSCALE_AUTHKEY, TS_API_SECRET 或 TS_ORGANIZATION"
    exit 1
fi

# --- 1. 清理 Tailscale 残留节点 ---
echo "[Init] 正在检查并清理残留的 Tailscale 节点..."

# 获取当前组织下的所有机器列表 (使用 TS_API_SECRET 作为 Bearer Token)
# 注：Render 环境一般没有预装 jq，这里用 grep/awk 简单提取，或确保 Dockerfile 中安装了 jq
TS_DEVICES=$(curl -s -u "$TS_API_SECRET:" "$TS_API_URL/tailnet/$TS_ORGANIZATION/devices")

# 提取匹配 NODE_NAME 的设备 ID 并循环删除
echo "$TS_DEVICES" | grep -o '"id":"[^"]*"' | sed 's/"id":"//;s/"//' | while read -r device_id; do
    # 获取该 ID 对应的设备名是否匹配 render-proxy
    is_target=$(curl -s -u "$TS_API_SECRET:" "$TS_API_URL/devices/$device_id" | grep -q "\"name\":\"$NODE_NAME" && echo "yes" || echo "no")
    if [ "$is_target" = "yes" ]; then
        echo "[Init] 发现残留节点 ID: $device_id，正在执行删除..."
        curl -s -X DELETE -u "$TS_API_SECRET:" "$TS_API_URL/devices/$device_id"
        sleep 2
    fi
done

# --- 2. 启动 Tailscale 核心服务 ---
echo "[Init] 启动 Tailscaled 守护进程..."
mkdir -p /var/run/tailscale /var/lib/tailscale
tailscaled --state=/var/lib/tailscale/tailscaled.state --socket=/var/run/tailscale/tailscaled.sock &

# 等待 tailscaled 启动完成
sleep 3

echo "[Init] 正在将节点注册上色 (名称: $NODE_NAME)..."
tailscale up --authkey="$TAILSCALE_AUTHKEY" --hostname="$NODE_NAME" --accept-routes=true &

# --- 3. 启动 Gost 转发 ---
# 请根据你的微信转发需求修改此处的 gost 启动参数（例如将本地 8080 转发到目标）
START_GOST() {
    echo "[Gost] 正在启动 Gost 转发服务..."
    # 示例：监听 8080 端口，你可以修改为你的具体转发逻辑
    gost -L=:8080 &
    GOST_PID=$!
}
START_GOST

# --- 4. 守护监控死循环 (每 30 秒检查一次) ---
echo "[Monitor] 进入状态监控循环..."

while true; do
    sleep 30

    # ==================== Tailscale 监控与自愈 ====================
    # 检查 tailscaled 进程是否存在，以及通过 tailscale status 验证状态
    TS_PID=$(pgrep tailscaled)
    TS_STATUS=$(tailscale status 2>&1)
    
    if [ -z "$TS_PID" ] || echo "$TS_STATUS" | grep -q "failed" || echo "$TS_STATUS" | grep -q "Stopped"; then
        echo "[WARNING] Tailscale 状态异常或卡死，尝试重新拉起..."
        pkill -9 tailscaled
        pkill -9 tailscale
        sleep 2
        tailscaled --state=/var/lib/tailscale/tailscaled.state --socket=/var/run/tailscale/tailscaled.sock &
        sleep 3
        tailscale up --authkey="$TAILSCALE_AUTHKEY" --hostname="$NODE_NAME" --accept-routes=true &
        echo "[Monitor] Tailscale 重启指令已发送。"
    fi

    # ==================== Gost 端口与卡死监控 ====================
    # 1. 进程检查
    if ! ps -p $GOST_PID > /dev/null; then
        echo "[WARNING] Gost 进程意外退出，正在重新拉起..."
        START_GOST
        continue
    fi

    # 2. 端口用尽 / TIME_WAIT 过高监控
    # 微信高频转发极易导致端口卡在 TIME_WAIT 状态导致端口耗尽。
    # 如果系统并发连接数（或特定状态连接）超过安全阈值（例如 20000），则判定异常
    CONN_COUNT=$(ss -an | wc -l)
    # 你也可以专门监控 TIME_WAIT 数量： CONN_COUNT=$(ss -an | grep TIME-WAIT | wc -l)
    
    if [ "$CONN_COUNT" -gt 25000 ]; then
        echo "[WARNING] 检测到系统连接数过高 ($CONN_COUNT)，可能触发端口耗尽。正在强制重启 Gost..."
        kill -9 $GOST_PID
        sleep 2
        START_GOST
    fi

    # 3. Gost 响应卡死检查 (可用 curl 测活，假设 gost 开启了某个 http 代理或监控端口)
    # 如果你配置了 http 转发，可以用下面这段代码测活（可选）：
    # curl -I -s --connect-timeout 5 http://127.0.0.1:8080 > /dev/null
    # if [ $? -ne 0 ]; then 重启 GOST... fi

done
