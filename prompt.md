# 役割
　優秀なバックエンドエンジニア(Python/Docker)

# 指示
　特定のサイトに対し、クローリング&スクレイピングをするためのプログラムを作成しております。以下のファイルの問題点を指摘してください。

# 条件

## 開発環境
- Azure VM (Basion)
- VSCode Remote-SSH

## ソースコード
```Dockerfile
# Use a Python image with uv pre-installed
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Install the project into `/app`
WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy

# Install the project's dependencies using the lockfile and settings
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev

# Then, add the rest of the project source code and install it
# Installing separately from its dependencies allows optimal layer caching
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"

# Reset the entrypoint, don't invoke `uv`
ENTRYPOINT []

# Run the FastAPI application by default
# Uses `fastapi dev` to enable hot-reloading when the `watch` sync occurs
# Uses `--host 0.0.0.0` to allow access from outside the container
CMD ["python", "run_crawl.py"]
```

```pyproject.toml
[project]
name = "uv-docker-example"
version = "0.1.0"
description = "Add your description here"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "fastapi[standard]>=0.112.2",
    "httpx",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project.scripts]
hello = "uv_docker_example:hello"

[tool.uv]
dev-dependencies = [
    "ruff>=0.6.2",
    "fastapi-cli>=0.0.5",
]
```

```python:run_crawl.py
import httpx
import asyncio
import json

async def crawl():
    """
    crawl4aiサービスにAPIリクエストを送信し、
    ストリーミングで結果を受け取る非同期関数。
    """
    # タイムアウトを300秒（5分）に設定。大規模なサイトをクロールする際に有効です。
    async with httpx.AsyncClient(timeout=300.0) as client:
        print("--- Sending crawl request to crawl4ai service ---")
        try:
            # サーバーにPOSTリクエストを送信
            response = await client.post(
                # Dockerコンテナ間で通信するため、コンテナ名'crawl4ai'を指定
                "http://crawl4ai:11235/crawl",
                json={
                    "urls": [
                        "https://example.com"
                    ],
                    "crawler_config": {
                        "type": "CrawlerRunConfig",
                        "params": {
                            "scraping_strategy": {
                                "type": "WebScrapingStrategy",
                                "params": {}
                            },
                            "stream": True # ストリームを有効にし、結果を順次受け取る
                        }
                    }
                }
            )
            
            # ステータスコードがエラーでないことを確認
            response.raise_for_status()

        except httpx.RequestError as e:
            print(f"An error occurred while requesting {e.request.url!r}.")
            print("Please check if the 'crawl4ai' container is running and connected to the same Docker network.")
            return None

        # ストリームで結果を一行ずつ非同期に処理します
        results = []
        print("--- Receiving stream response ---")
        async for line in response.aiter_lines():
            if line:
                try:
                    # JSONL形式（1行1JSON）の各行をPythonの辞書に変換
                    data = json.loads(line)
                    # 見やすいように整形してコンソールに出力
                    print(json.dumps(data, indent=2, ensure_ascii=False))
                    results.append(data)
                except json.JSONDecodeError:
                    print(f"Could not decode a line from stream: {line}")
        
        return results

# このスクリプトが直接実行された場合に以下のコードが動作する
if __name__ == "__main__":
    # asyncio.run()で非同期関数crawl()を実行します
    final_result = asyncio.run(crawl())
    
    if final_result is not None:
        print("\n--- Crawling Finished ---")
        print(f"Total {len(final_result)} data chunks received.")
    else:
        print("\n--- Crawling Failed ---")
```

## 参考にしているソースコード

- [crawl4ai](https://github.com/unclecode/crawl4ai)

# 目標
  特定のサイト領域をクローリングしてスクレイピングにより情報を取得する。
