FROM alpine:latest

# 安装基础依赖：Tailscale 官方包、curl (API调用)、iproute2 (使用 ss 命令监控端口)
RUN apk update && apk add --no-cache \
    tailscale \
    curl \
    iproute2 \
    ca-certificates \
    bash \
    iptables

# 下载并安装 Gost (以 v2 为例，如需 v3 请更换下载链接)
RUN curl -L https://github.com/ginuerzh/gost/releases/download/v2.11.5/gost-linux-amd64-2.11.5.gz | gunzip > /usr/local/bin/gost \
    && chmod +x /usr/local/bin/gost

# 复制启动脚本
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# 暴露你的 Gost 转发端口（根据你在 entrypoint.sh 里的配置修改）
EXPOSE 8080

ENTRYPOINT ["/bin/bash", "/entrypoint.sh"]
