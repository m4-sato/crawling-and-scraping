"""
intra_crawler.py
社内イントラサイトの階層とファイル名一覧を CSV / text で保存するサンプル
Python 3.10 以上 / crawl4ai 0.7.* （Docker API モード）
"""
import asyncio
import csv
import os
from pathlib import Path
from urllib.parse import urlparse

from crawl4ai import (
    BrowserConfig,
    CrawlerRunConfig,
    CacheMode,
)
# The explicit scraping strategy import is removed to rely on the library's default browser-based strategy.
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy
from crawl4ai.deep_crawling.filters import FilterChain, ContentTypeFilter
from crawl4ai.docker_client import Crawl4aiDockerClient  # ★ サーバー呼び出し用

# ---------- 変更必須 ----------
ROOT_URL = os.getenv("ROOT_URL", "https://www.python.org/")
MAX_DEPTH = int(os.getenv("MAX_DEPTH", "3"))
MAX_PAGES = int(os.getenv("MAX_PAGES", "2000"))
CRAWL4AI_BASE = os.getenv("CRAWL4AI_BASE_URL", "http://crawl4ai:11235")
# --------------------------------

OUTPUT_DIR = Path("crawl_results")
OUTPUT_DIR.mkdir(exist_ok=True)

SITE_CSV = OUTPUT_DIR / "site_structure.csv"
FILES_CSV = OUTPUT_DIR / "file_links.csv"
TREE_TXT = OUTPUT_DIR / "site_tree.txt"

FILE_EXTS = {
    ".pdf", ".doc", ".docx", ".ppt", ".pptx",
    ".xls", ".xlsx", ".csv", ".zip", ".rar", ".7z", ".txt"
}

def strip_base(url: str, base_netloc: str) -> str:
    p = urlparse(url)
    return p.path or "/" if p.netloc == base_netloc else url

async def main() -> None:
    # ---- フィルタチェーン（HTML のみ） ----
    # filters = FilterChain([ContentTypeFilter(allowed_types=["text/html"])]) # DEBUG: Temporarily disabled

    # ---- Deep‑crawl 戦略 ----
    # DEBUG: Temporarily disabling deep crawl to isolate the 500 error.
    # This will test if a single-page scrape works.
    # deep_crawl = BFSDeepCrawlStrategy(
    #     max_depth=MAX_DEPTH,
    #     include_external=False,
    #     max_pages=MAX_PAGES,
    #     # filter_chain=filters,
    # )

    # The explicit scraping_strategy is removed. The default is a browser-based strategy (Playwright)
    # which is what we need, and this avoids the ImportError.
    crawl_cfg = CrawlerRunConfig(
        # deep_crawl_strategy=deep_crawl, # DEBUG: Temporarily disabled
        cache_mode=CacheMode.BYPASS,
        verbose=True,
    )

    async with Crawl4aiDockerClient(base_url=CRAWL4AI_BASE, verbose=True) as client:
        # BrowserConfig is still needed because the default strategy uses a browser.
        results = await client.crawl(
            [ROOT_URL],
            browser_config=BrowserConfig(headless=True),
            crawler_config=crawl_cfg,
        )

    base_netloc = urlparse(ROOT_URL).netloc
    site_rows, file_rows, tree = [], [], []

    for res in results:
        # The depth will not be present without deep crawling, so we default to 0.
        depth = res.metadata.get("depth", 0)
        path = strip_base(res.url, base_netloc)
        is_file = os.path.splitext(path)[1].lower() in FILE_EXTS

        site_rows.append({
            "url": res.url,
            "path": path,
            "depth": depth,
            "type": "file" if is_file else "page",
            "status_code": res.status_code,
            "success": res.success,
            "error": res.error_message or "",
        })
        tree.append((depth, path))

        for link in res.links.get("internal", []):
            href = link.get("href", "")
            if not href:
                continue
            fname = os.path.basename(urlparse(href).path)
            if os.path.splitext(fname)[1].lower() in FILE_EXTS:
                file_rows.append({
                    "page_url": res.url,
                    "file_name": fname,
                    "file_url": href,
                })

    # ---------- CSV 出力 ----------
    if site_rows:
        with SITE_CSV.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=site_rows[0].keys())
            w.writeheader(); w.writerows(site_rows)

    if file_rows:
        with FILES_CSV.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=file_rows[0].keys())
            w.writeheader(); w.writerows(file_rows)

    # ---------- ツリー ----------
    with TREE_TXT.open("w", encoding="utf-8") as f:
        for d, p in sorted(tree, key=lambda x: x[0]):
            f.write(f"{'    '*d}{os.path.basename(p) or '/'}\n")

    print(f"✓ サイト構造: {SITE_CSV}")
    if file_rows:
        print(f"✓ ファイル一覧: {FILES_CSV}")
    print(f"✓ ツリー表示: {TREE_TXT}")

if __name__ == "__main__":
    asyncio.run(main())
