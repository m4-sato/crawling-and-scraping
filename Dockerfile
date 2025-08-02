FROM mcr.microsoft.com/playwright/python:v1.54.0-jammy

ARG DEBIAN_FRONTEND=noninteractive
WORKDIR /app

# ---- 1️⃣ ビルド用ツールと開発ヘッダ ----
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential python3-dev libffi-dev zlib1g-dev libxml2-dev libxslt1-dev \
 && rm -rf /var/lib/apt/lists/*

# ---- 2️⃣ Python ライブラリ ----
COPY requirements.txt .
RUN pip install --upgrade pip \
 && pip install --no-cache-dir --prefer-binary -r requirements.txt

# ---- 3️⃣ アプリコード ----
COPY tutorial_basic_crawl.py .

CMD ["python", "tutorial_basic_crawl.py"]
