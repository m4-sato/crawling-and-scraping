"""
intra_crawler.py
ローカル Playwright + crawl4ai 0.7.* でイントラサイトをクロールして
- site_structure.csv       … URL,深さ,HTTP ステータス,成功/失敗 等
- file_links.csv           … ページ→添付ファイル名
- site_tree.txt            … インデント付きツリー（深さ順ソート）
- site_tree_fancy.txt      … └──/│ 付きの木構造   ★ NEW
- site_summary.csv         … パス別ページ／ファイル／エラー数   ★ NEW
"""

import asyncio, csv, os
from pathlib import Path
from urllib.parse import urlparse
from collections import Counter                 # ★ NEW

from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode
from crawl4ai.content_scraping_strategy import LXMLWebScrapingStrategy
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy
from crawl4ai.deep_crawling.filters import FilterChain, ContentTypeFilter

# 木構造表示用
try:
    from anytree import Node, RenderTree        # ★ NEW
except ImportError:
    Node = RenderTree = None    # anytree が未インストールでも動くように

# ----------- 必要に応じて書き換え -----------
ROOT_URL  = os.getenv("ROOT_URL",  "https://www.python.org/")
MAX_DEPTH = int(os.getenv("MAX_DEPTH", 8))
MAX_PAGES = int(os.getenv("MAX_PAGES", 50))
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "crawl_results"))
# -------------------------------------------

OUTPUT_DIR.mkdir(exist_ok=True)
SITE_CSV, FILES_CSV, TREE_TXT = (
    OUTPUT_DIR / "site_structure.csv",
    OUTPUT_DIR / "file_links.csv",
    OUTPUT_DIR / "site_tree.txt",
)
TREE_FANCY_TXT = OUTPUT_DIR / "site_tree_fancy.txt"   # ★ NEW
SUMMARY_CSV    = OUTPUT_DIR / "site_summary.csv"      # ★ NEW

FILE_EXTS = {
    ".pdf", ".doc", ".docx", ".ppt", ".pptx",
    ".xls", ".xlsx", ".csv", ".zip", ".rar", ".7z", ".txt"
}

def strip_base(url: str, netloc: str) -> str:
    p = urlparse(url)
    return p.path or "/" if p.netloc == netloc else url

async def crawl() -> None:
    filters = FilterChain([ContentTypeFilter(allowed_types=["text/html"])])

    deep_crawl = BFSDeepCrawlStrategy(
        max_depth=MAX_DEPTH,
        include_external=False,
        max_pages=MAX_PAGES,
        filter_chain=filters,
    )

    run_cfg = CrawlerRunConfig(
        deep_crawl_strategy=deep_crawl,
        scraping_strategy=LXMLWebScrapingStrategy(),
        cache_mode=CacheMode.BYPASS,
        verbose=True,
    )

    async with AsyncWebCrawler() as crawler:
        results = await crawler.arun(ROOT_URL, config=run_cfg)

    base = urlparse(ROOT_URL).netloc
    site_rows, file_rows, tree_paths = [], [], []

    for res in results:
        depth = res.metadata.get("depth", 0)
        path  = strip_base(res.url, base)
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
        tree_paths.append((depth, path))

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

    # ---------- ツリー (深さ順インデント) ----------
    with TREE_TXT.open("w", encoding="utf-8") as f:
        for d, p in sorted(tree_paths, key=lambda x: x[0]):
            f.write(f"{'    '*d}{os.path.basename(p) or '/'}\n")

    # ---------- 木構造 (anytree) ---------- ★ NEW
    if Node:
        root_node = Node("/")
        node_map = {"/": root_node}

        for _depth, p in tree_paths:
            parts = [seg for seg in p.split("/") if seg]
            cur = root_node
            acc = ""
            for seg in parts:
                acc += f"/{seg}"
                if acc not in node_map:
                    node_map[acc] = Node(seg, parent=cur)
                cur = node_map[acc]

        with TREE_FANCY_TXT.open("w", encoding="utf-8") as f:
            for pre, _, node in RenderTree(root_node):
                f.write(f"{pre}{node.name}\n")
    else:
        print("※ anytree が未インストールのため site_tree_fancy.txt は生成されません")

    # ---------- パス別サマリー ---------- ★ NEW
    seg_counter, file_counter, err_counter = Counter(), Counter(), Counter()
    for r in site_rows:
        # 第一階層（/about/ → about）
        seg = (r["path"].split("/", 2)[1] if "/" in r["path"][1:] else r["path"].lstrip("/")) or "/"
        seg_counter[seg] += 1
        if r["type"] == "file":
            file_counter[seg] += 1
        if not r["success"]:
            err_counter[seg] += 1

    if seg_counter:
        with SUMMARY_CSV.open("w", newline="", encoding="utf-8") as f:
            fieldnames = ["segment", "pages", "files", "errors"]
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            for seg in sorted(seg_counter):
                w.writerow({
                    "segment": seg,
                    "pages": seg_counter[seg],
                    "files": file_counter[seg],
                    "errors": err_counter[seg],
                })

    # ---------- 完了ログ ----------
    print(f"✓ site_structure.csv    → {SITE_CSV}")
    print(f"✓ file_links.csv        → {FILES_CSV}" if file_rows else "（添付ファイル無し）")
    print(f"✓ site_tree.txt         → {TREE_TXT}")
    if Node:
        print(f"✓ site_tree_fancy.txt   → {TREE_FANCY_TXT}")
    print(f"✓ site_summary.csv      → {SUMMARY_CSV}")

if __name__ == "__main__":
    asyncio.run(crawl())
