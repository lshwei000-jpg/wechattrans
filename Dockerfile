FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    curl python3 python3-pip wget gzip ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 👑 【核心改動】：直接下載 Tailscale 官方純靜態 Linux 二進制包（極其穩定）
RUN wget https://pkgs.tailscale.com/stable/tailscale_1.66.4_amd64.tgz \
    && tar -zxvf tailscale_1.66.4_amd64.tgz \
    && mv tailscale_1.66.4_amd64/tailscale /usr/local/bin/tailscale \
    && mv tailscale_1.66.4_amd64/tailscaled /usr/local/bin/tailscaled \
    && chmod +x /usr/local/bin/tailscale /usr/local/bin/tailscaled \
    && rm -rf tailscale_1.66.4_amd64*

# 2. 下載 Gost
RUN wget https://github.com/ginuerzh/gost/releases/download/v2.11.5/gost-linux-amd64-2.11.5.gz \
    && gzip -d gost-linux-amd64-2.11.5.gz \
    && mv gost-linux-amd64-2.11.5 gost \
    && chmod +x gost

RUN pip3 install --no-cache-dir flask

# 建立獨立的數據和運行目錄
RUN mkdir -p /app/ts_var /app/ts_run

COPY app.py /app/app.py
COPY index.html /app/index.html

CMD ["python3", "app.py"]
