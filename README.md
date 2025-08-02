# crawling-and-scraping

## tutorial

- AsyncWebCrawler

## crawl4ai docker setup

[crawl4ai](https://github.com/unclecode/crawl4ai)

```bash
docker run -d \
 -p 11235:11235 \
 --name crawl4ai \
 --shm-size=3g \
 unclecode/crawl4ai:latest
```

```bash
DOCKER_BUILDKIT=1 docker build -t my-crawl-client .
```

```bash
docker network create crawl-net
```

```bash
docker run -d --network crawl-net --name crawl4ai -p 11235:11235 --shm-size=3g unclecode/crawl4ai:latest
```

```bash
docker run --network crawl-net my-crawl-client
```

docker compose down # 全コンテナ停止
docker compose pull crawl4ai # 新イメージ取得
docker compose up -d crawl4ai # サーバー先に起動
docker compose build crawler # クライアントは変更なしでも OK
docker compose up crawler # 再実行

### ドキュメント

- [orilly github](https://github.com/REMitchell/python-scraping)
- [domain URL 違い](https://www.pignus.co.jp/column/webmarketing/2056/)
