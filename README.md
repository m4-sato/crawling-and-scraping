# crawling-and-scraping

## crawl4ai
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
