import httpx
import asyncio
import json
import os
import logging
import csv
import re
from datetime import datetime

# ロギングの基本設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 環境変数から設定を読み込む。見つからない場合はデフォルト値を使用する。
CRAWL4AI_ENDPOINT = os.getenv("CRAWL4AI_ENDPOINT", "http://crawl4ai:11235/crawl")
TARGET_URLS = os.getenv("TARGET_URLS", "https://example.com").split(',')


def sanitize_url_for_filename(url: str) -> str:
    """URLを安全なディレクトリ名に変換する"""
    # プロトコル部分を削除 (e.g., "https://")
    url_path = re.sub(r'^https?:\/\/', '', url)
    # ファイル名として無効な文字をアンダースコアに置換
    sanitized = re.sub(r'[\\/*?:"<>|]', '_', url_path)
    # 長すぎる場合に切り詰める
    return sanitized[:100]


async def crawl(base_output_dir: str):
    """
    crawl4aiサービスにAPIリクエストを送信し、
    結果をURLごとのフォルダに分けて保存する非同期関数。
    """
    async with httpx.AsyncClient(timeout=300.0) as client:
        logging.info(f"--- Sending crawl request to crawl4ai service for URLs: {TARGET_URLS} ---")
        try:
            response = await client.post(
                CRAWL4AI_ENDPOINT,
                json={
                    "urls": TARGET_URLS,
                    "crawler_config": {
                        "type": "CrawlerRunConfig",
                        "params": {
                            "scraping_strategy": { "type": "WebScrapingStrategy", "params": {} },
                            "stream": True
                        }
                    }
                }
            )
            response.raise_for_status()
            logging.info(f"HTTP Request: POST {response.url} \"HTTP/{response.http_version} {response.status_code} {response.reason_phrase}\"")
        except httpx.RequestError as e:
            logging.error(f"An error occurred while requesting {e.request.url!r}.")
            return None
        except httpx.HTTPStatusError as e:
            logging.error(f"Error response {e.response.status_code} while requesting {e.request.url!r}.")
            return None

        all_results = []
        logging.info("--- Receiving stream response and saving to structured files ---")
        async for line in response.aiter_lines():
            if not line:
                continue
            try:
                data = json.loads(line)
                if 'results' in data and isinstance(data['results'], list):
                    for result_item in data['results']:
                        url = result_item.get('url')
                        if not url:
                            continue

                        # URLごとにユニークなディレクトリを作成
                        sanitized_url = sanitize_url_for_filename(url)
                        url_output_dir = os.path.join(base_output_dir, sanitized_url)
                        os.makedirs(url_output_dir, exist_ok=True)
                        logging.info(f"Saving results for {url} to {url_output_dir}/")

                        # 1. 本文コンテンツをMarkdownファイルに保存
                        content = result_item.get('markdown', {}).get('raw_markdown', '').strip()
                        with open(os.path.join(url_output_dir, 'content.md'), 'w', encoding='utf-8') as f:
                            f.write(content)

                        # 2. リンク一覧をCSVファイルに保存
                        links = result_item.get('links', {})
                        with open(os.path.join(url_output_dir, 'links.csv'), 'w', newline='', encoding='utf-8') as f:
                            writer = csv.writer(f)
                            writer.writerow(['type', 'href', 'text', 'base_domain'])
                            for link_type, link_list in links.items():
                                if isinstance(link_list, list):
                                    for link in link_list:
                                        writer.writerow([
                                            link_type,
                                            link.get('href', ''),
                                            link.get('text', ''),
                                            link.get('base_domain', '')
                                        ])
                        
                        # 3. メタデータをJSONファイルに保存
                        metadata = result_item.get('metadata', {})
                        metadata['crawled_at'] = datetime.now().isoformat()
                        metadata['original_url'] = url
                        with open(os.path.join(url_output_dir, 'metadata.json'), 'w', encoding='utf-8') as f:
                            json.dump(metadata, f, indent=2, ensure_ascii=False)
                
                all_results.append(data)

            except json.JSONDecodeError:
                logging.error(f"Could not decode a line from stream: {line}")
        
        return all_results

if __name__ == "__main__":
    # 今回の実行結果を保存する親ディレクトリを作成
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = f"crawl_output_{timestamp}"
    os.makedirs(output_dir, exist_ok=True)
    
    logging.info(f"Results will be saved to directory: {output_dir}")
    
    try:
        final_result = asyncio.run(crawl(output_dir))
        
        if final_result is not None:
            logging.info(f"\n--- Crawling Finished ---")
            logging.info(f"All data saved in directory: {output_dir}")
        else:
            logging.error("\n--- Crawling Failed ---")

    except IOError as e:
        logging.error(f"Failed to write to file: {e}")
