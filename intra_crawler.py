"""
intra_crawler.py
社内イントラサイトの階層とファイル名一覧を CSV / text で保存するサンプル
Python 3.10 以上 / crawl4ai 0.7.* / playwright
"""
import asyncio
import csv
import os
from pathlib import Path
from urllib.parse import urlparse

from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.content_scraping_strategy import LXMLWebScrapingStrategy
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy
from crawl4ai.deep_crawling.filters import FilterChain, ContentTypeFilter

# ---------- 変更必須 ----------
ROOT_URL = "https://intra.example.local"   # クロール開始 URL
MAX_DEPTH = 3                              # 必要に応じて調整
MAX_PAGES = 2000                           # 無制限は避ける
# --------------------------------

OUTPUT_DIR = Path("crawl_results")
OUTPUT_DIR.mkdir(exist_ok=True)

SITE_CSV = OUTPUT_DIR / "site_structure.csv"
FILES_CSV = OUTPUT_DIR / "file_links.csv"
TREE_TXT = OUTPUT_DIR / "site_tree.txt"

# 拡張子で「ファイル」とみなす簡易判定
FILE_EXTS = {".pdf", ".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx",
             ".csv", ".zip", ".rar", ".7z", ".txt"}

def path_from_url(url: str, base_netloc: str) -> str:
    """ベースドメイン部分を除いたパスを返す"""
    parsed = urlparse(url)
    # 別ドメインの場合はフル URL を返す（念のため）
    if parsed.netloc != base_netloc:
        return url
    return parsed.path or "/"            # 例: '' -> '/' にする

async def crawl():
    config = CrawlerRunConfig(
        deep_crawl_strategy=BFSDeepCrawlStrategy(
            max_depth=MAX_DEPTH,
            include_external=False,
            max_pages=MAX_PAGES
        ),
        scraping_strategy=LXMLWebScrapingStrategy(),
        filter_chain=FilterChain([
            ContentTypeFilter(allowed_types=["text/html"])
        ]),
        verbose=True              # ログを標準出力
    )

    site_rows = []   # URL / path 階層情報
    file_rows = []   # ファイル名
    tree_paths = []  # テキスト用

    async with AsyncWebCrawler() as crawler:
        results = await crawler.arun(ROOT_URL, config=config)

    base_netloc = urlparse(ROOT_URL).netloc

    for res in results:
        depth = res.metadata.get("depth", 0)
        path = path_from_url(res.url, base_netloc)
        is_file = os.path.splitext(path)[1].lower() in FILE_EXTS
        site_rows.append({
            "url": res.url,
            "path": path,
            "depth": depth,
            "type": "file" if is_file else "page",
            "status_code": res.status_code,
            "success": res.success,
            "error": res.error_message or ""
        })
        tree_paths.append((depth, path))

        # ページ内リンクからファイル名を抽出
        links = res.links.get("internal", [])
        for link in links:
            href = link.get("href", "")
            if not href:
                continue
            fname = os.path.basename(urlparse(href).path)
            if os.path.splitext(fname)[1].lower() in FILE_EXTS:
                file_rows.append({
                    "page_url": res.url,
                    "file_name": fname,
                    "file_url": href
                })

    # ---------- CSV 出力 ----------
    with SITE_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=site_rows[0].keys())
        writer.writeheader()
        writer.writerows(site_rows)

    if file_rows:
        with FILES_CSV.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=file_rows[0].keys())
            writer.writeheader()
            writer.writerows(file_rows)

    # ---------- ツリー (簡易) ----------
    with TREE_TXT.open("w", encoding="utf-8") as f:
        for depth, path in sorted(tree_paths, key=lambda x: x[0]):
            indent = "    " * depth
            f.write(f"{indent}{os.path.basename(path) or '/'}\n")

    print(f"✓ サイト構造: {SITE_CSV}")
    if file_rows:
        print(f"✓ ファイル一覧: {FILES_CSV}")
    print(f"✓ ツリー表示: {TREE_TXT}")

if __name__ == "__main__":
    asyncio.run(crawl())
