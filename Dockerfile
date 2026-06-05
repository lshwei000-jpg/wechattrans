FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive

# 安裝基礎依賴網路組件
RUN apt-get update && apt-get install -y \
    curl python3 python3-pip wget gzip iptables \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 1. 安裝 Tailscale 官方官方內核
RUN curl -fsSL https://tailscale.com/install.sh | sh

# 2. 下載並解壓 Gost 高性能代理
RUN wget https://github.com/ginuerzh/gost/releases/download/v2.11.5/gost-linux-amd64-2.11.5.gz \
    && gzip -d gost-linux-amd64-2.11.5.gz \
    && mv gost-linux-amd64-2.11.5 gost \
    && chmod +x gost

# 3. 安裝 Python 輕量 Web 依賴
RUN pip3 install --no-cache-dir flask

# 4. 建立 Tailscale 運行所需的套接字目錄
RUN mkdir -p /app/ts_run

# 5. 複製項目代碼與模組化 HTML
COPY app.py /app/app.py
COPY index.html /app/index.html

# 啟動控制中樞
CMD ["python3", "app.py"]
