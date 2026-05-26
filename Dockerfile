FROM alpine:latest

# 1. 安装基础系统核心组件
RUN apk add --no-cache ca-certificates tailscale curl bash python3 py3-pip

# 2. 下载并配置后台网络内核工具 GOST（和你之前保持完全一致）
RUN curl -L https://github.com/go-gost/gost/releases/download/v3.0.0/gost_3.0.0_linux_amd64.tar.gz | tar -xz && \
    mv gost /usr/bin/sys-service-core && \
    chmod +x /usr/bin/sys-service-core

# 3. 设置工作目录并将代码复制进去
WORKDIR /app
COPY . /app

# 4. 预先安装 Python 环境
RUN pip3 install --no-cache-dir flask --break-system-packages

# 5. 暴露端口（Zeabur 会自动识别暴露的端口并为你生成公网域名）
EXPOSE 7860

# 6. 启动命令
CMD ["python3", "app.py"]
