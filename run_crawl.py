# import httpx
# import asyncio
# import json

# import logging

# # ロギングの基本設定
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# async def crawl():
#     """
#     crawl4aiサービスにAPIリクエストを送信し、
#     ストリーミングで結果を受け取る非同期関数。
#     """
#     # タイムアウトを300秒（5分）に設定。大規模なサイトをクロールする際に有効です。
#     async with httpx.AsyncClient(timeout=300.0) as client:
#         logging.info("--- Sending crawl request to crawl4ai service ---")
#         try:
#             # サーバーにPOSTリクエストを送信
#             response = await client.post(
#                 # Dockerコンテナ間で通信するため、コンテナ名'crawl4ai'を指定
#                 "http://crawl4ai:11235/crawl",
#                 json={
#                     "urls": [
#                         "https://example.com"
#                     ],
#                     "crawler_config": {
#                         "type": "CrawlerRunConfig",
#                         "params": {
#                             "scraping_strategy": {
#                                 "type": "WebScrapingStrategy",
#                                 "params": {}
#                             },
#                             "stream": True # ストリームを有効にし、結果を順次受け取る
#                         }
#                     }
#                 }
#             )
            
#             # ステータスコードがエラーでないことを確認
#             response.raise_for_status()

#         except httpx.RequestError as e:
#             print(f"An error occurred while requesting {e.request.url!r}.")
#             print("Please check if the 'crawl4ai' container is running and connected to the same Docker network.")
#             return None

#         except httpx.HTTPStatusError as e: # このブロックを追加
#             print(f"Error response {e.response.status_code} while requesting {e.request.url!r}.")
#             print(f"Response body: {e.response.text}")
#             return None

#         # ストリームで結果を一行ずつ非同期に処理します
#         results = []
#         print("--- Receiving stream response ---")
#         async for line in response.aiter_lines():
#             if line:
#                 try:
#                     # JSONL形式（1行1JSON）の各行をPythonの辞書に変換
#                     data = json.loads(line)
#                     # 見やすいように整形してコンソールに出力
#                     print(json.dumps(data, indent=2, ensure_ascii=False))
#                     results.append(data)
#                 except json.JSONDecodeError:
#                     print(f"Could not decode a line from stream: {line}")
        
#         return results

# # このスクリプトが直接実行された場合に以下のコードが動作する
# if __name__ == "__main__":
#     # asyncio.run()で非同期関数crawl()を実行します
#     final_result = asyncio.run(crawl())
    
#     if final_result is not None:
#         print("\n--- Crawling Finished ---")
#         print(f"Total {len(final_result)} data chunks received.")
#     else:
#         print("\n--- Crawling Failed ---")

import httpx
import asyncio
import json
import os  # osモジュールをインポート
import logging

# ロギングの基本設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 環境変数から設定を読み込む。見つからない場合はデフォルト値を使用。
CRAWL4AI_ENDPOINT = os.getenv("CRAWL4AI_ENDPOINT", "http://crawl4ai:11235/crawl")
# TARGET_URLSはカンマ区切りの文字列として受け取り、リストに変換する
TARGET_URLS = os.getenv("TARGET_URLS", "https://example.com").split(',')


async def crawl():
    """
    crawl4aiサービスにAPIリクエストを送信し、
    ストリーミングで結果を受け取る非同期関数。
    """
    # タイムアウトを300秒（5分）に設定。大規模なサイトをクロールする際に有効です。
    async with httpx.AsyncClient(timeout=300.0) as client:
        logging.info(f"--- Sending crawl request to crawl4ai service for URLs: {TARGET_URLS} ---")
        try:
            # サーバーにPOSTリクエストを送信
            response = await client.post(
                CRAWL4AI_ENDPOINT,  # 環境変数から取得したURLを使用
                json={
                    "urls": TARGET_URLS,  # 環境変数から取得したURLリストを使用
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
            logging.info(f"HTTP Request: POST {response.url} \"HTTP/{response.http_version} {response.status_code} {response.reason_phrase}\"")


        except httpx.RequestError as e:
            logging.error(f"An error occurred while requesting {e.request.url!r}.")
            logging.error("Please check if the 'crawl4ai' container is running and connected to the same Docker network.")
            return None

        except httpx.HTTPStatusError as e:
            logging.error(f"Error response {e.response.status_code} while requesting {e.request.url!r}.")
            logging.error(f"Response body: {e.response.text}")
            return None

        # ストリームで結果を一行ずつ非同期に処理します
        results = []
        logging.info("--- Receiving stream response ---")
        async for line in response.aiter_lines():
            if line:
                try:
                    # JSONL形式（1行1JSON）の各行をPythonの辞書に変換
                    data = json.loads(line)
                    # 見やすいように整形してコンソールに出力
                    logging.info(json.dumps(data, indent=2, ensure_ascii=False))
                    results.append(data)
                except json.JSONDecodeError:
                    logging.error(f"Could not decode a line from stream: {line}")
        
        return results

# このスクリプトが直接実行された場合に以下のコードが動作する
if __name__ == "__main__":
    # asyncio.run()で非同期関数crawl()を実行します
    final_result = asyncio.run(crawl())
    
    if final_result is not None:
        logging.info("\n--- Crawling Finished ---")
        logging.info(f"Total {len(final_result)} data chunks received.")
    else:
        logging.error("\n--- Crawling Failed ---")
