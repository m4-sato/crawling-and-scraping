# tutorial_basic_crawl.py
from typing import List
import asyncio,csv
from unittest import result
from crawl4ai import AsyncWebCrawler, CrawlResult, CrawlerRunConfig
from crawl4ai.content_filter_strategy import PruningContentFilter
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

from pathlib import Path
from datetime import datetime


TS = datetime.now().strftime("%Y%m%d_%H%M%S")

# ---------- csv 出力フォルダ ----------
OUTPUT_DIR = Path("/app/output") / f"{TS}_crawl_results"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
CSV_PATH = OUTPUT_DIR / f"{TS}_crawl_output.csv"


def write_csv_header(fieldnames):
    with CSV_PATH.open("w", newline="", encoding="utf-8") as f:
        csv.DictWriter(f, fieldnames=fieldnames).writeheader()

def append_row(row: dict):
    with CSV_PATH.open("a", newline="", encoding="utf-8") as f:
        csv.DictWriter(f, fieldnames=row.keys()).writerow(row)

def log_result(url: str, result: CrawlResult, *, use_fit=False):
    """CrawlResult を 1 行の dict にして CSV へ追記"""
    text = (
        result.markdown.fit_markdown if (use_fit and result.success)
        else result.markdown.raw_markdown
    )
    row = {
        "url": url,
        "success": result.success,
        "markdown_len": len(text) if result.success else 0,
        "preview100": text[:100] if result.success else "",
        "error": result.error_message or "",
    }
    append_row(row)

write_csv_header(["url", "success", "markdown_len", "preview100", "error"])


# ---------- クロールのメイン処理 ----------

async def basic_crawl() -> None:
    """1 URL をクロールして Markdown を 100 文字だけ表示"""
    async with AsyncWebCrawler() as crawler:
        results: List[CrawlResult] = await crawler.arun(
            url="https://news.ycombinator.com",
        )

    for i, result in enumerate(results):
        print(f"\nResult {i + 1}:")
        print(f"Success: {result.success}")
        if result.success:
            md = result.markdown.raw_markdown
            print(f"Markdown length: {len(md)} chars")
            print(f"First 100 chars:\n{md[:100]}")
        else:
            print(f"Failed → {result.error_message}")

        log_result("https://news.ycombinator.com", result)


async def parallel_crawl() -> None:
    urls = [
        "https://news.ycombinator.com",
        "https://www.python.org",
        "https://example.com",
    ]
    async with AsyncWebCrawler() as crawler:
        results: List[CrawlResult] = await crawler.arun_many(urls=urls)
    for url, result in zip(urls, results):
        print(f"\n{url}: {result.success}")
        log_result(url, result)

async def fit_markdown():

    prune_filter = PruningContentFilter(
    # Lower → more content retained, higher → more content pruned
    threshold=0.45,           
    # "fixed" or "dynamic"
    threshold_type="dynamic",  
    # Ignore nodes with <5 words
    min_word_threshold=5
    )

    # Step 2: Insert it into a Markdown Generator
    md_generator = DefaultMarkdownGenerator(content_filter=prune_filter)

    # Step 3: Pass it to CrawlerRunConfig
    config = CrawlerRunConfig(
        markdown_generator=md_generator
    )

    async with AsyncWebCrawler() as crawler:
        result: CrawlResult = await crawler.arun(
            url="https://news.ycombinator.com",
            config=config
            )

        if result.success:
            # 'fit_markdown' is your pruned content, focusing on "denser" text
            print("Raw Markdown length:", len(result.markdown.raw_markdown))
            print("Fit Markdown length:", len(result.markdown.fit_markdown))
        else:
            print("Error:", result.error_message)

            log_result("https://news.ycombinator.com", result, use_fit=True)

async def main() -> None:
    await basic_crawl()
    await parallel_crawl()
    await fit_markdown()


if __name__ == "__main__":
    asyncio.run(main())
