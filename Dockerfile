FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    curl python3 python3-pip iptables wget gzip \
    && curl -fsSL https://tailscale.com/install.sh | sh \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 👑 【穩健修正版】：下載、解壓並確保更名為 gost
RUN wget https://github.com/ginuerzh/gost/releases/download/v2.11.5/gost-linux-amd64-2.11.5.gz \
    && gzip -d gost-linux-amd64-2.11.5.gz \
    && mv gost-linux-amd64-2.11.5 gost \
    && chmod +x gost

RUN pip3 install --no-cache-dir flask

COPY app.py /app/app.py
EXPOSE 10000
CMD ["python3", "app.py"]
