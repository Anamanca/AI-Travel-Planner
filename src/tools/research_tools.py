import os
from apify_client import ApifyClient
from tavily import TavilyClient
from typing import List, Dict

class ResearchTools:
    """Tập hợp các công cụ tìm kiếm cho các Agent."""
    def __init__(self):
        self.apify_client = ApifyClient(os.getenv("APIFY_TOKEN"))
        self.tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

    def search_tiktok(self, query: str, limit: int = 5) -> List[Dict]:
        """Tìm kiếm thông tin trên TikTok thông qua Apify."""
        try:
            # Chuyển query thành hashtag (loại bỏ dấu và khoảng trắng nếu cần)
            # Ở đây ta lấy từ khóa chính làm hashtag
            tag = query.replace(" ", "").replace("#", "")
            run_input = {
                "hashtags": [tag],
                "max_posts_per_query": limit,
            }
            run = self.apify_client.actor("clockworks/free-tiktok-scraper").call(run_input=run_input, timeout_secs=60)
            results = []
            for item in self.apify_client.dataset(run["defaultDatasetId"]).iterate_items():
                results.append({
                    "title": item.get("desc", ""),
                    "link": f"https://www.tiktok.com/@{item.get('authorMeta', {}).get('name', '')}/video/{item.get('id', '')}",
                    "source": "TikTok"
                })
            return results
        except Exception as e:
            print(f"Error scraping TikTok: {e}")
            return []

    def search_facebook(self, query: str, limit: int = 5) -> List[Dict]:
        """Tìm kiếm thông tin trên Facebook thông qua Apify."""
        try:
            run_input = {
                "queries": [query],
                "resultsLimit": limit,
            }
            run = self.apify_client.actor("apify/facebook-search-scraper").call(run_input=run_input, timeout_secs=60)
            results = []
            for item in self.apify_client.dataset(run["defaultDatasetId"]).iterate_items():
                results.append({
                    "title": item.get("text", "")[:200],
                    "link": item.get("url", ""),
                    "source": "Facebook"
                })
            return results
        except Exception as e:
            print(f"Error scraping Facebook: {e}")
            return []

    def search_web(self, query: str) -> str:
        """Tìm kiếm thông tin web chung qua Tavily."""
        response = self.tavily_client.search(query=query, search_depth="advanced")
        return response.get("results", [])
