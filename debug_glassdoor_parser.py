
import asyncio
import sys
from loguru import logger
import os

# Setup paths
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)
sys.path.append(os.path.join(project_root, "MindSpider", "DeepSentimentCrawling", "MediaCrawler"))

try:
    # Use the parsing logic from core.py
    from MindSpider.DeepSentimentCrawling.MediaCrawler.media_platform.glassdoor.core import GlassdoorCrawler
    import config
    # FORCE visible for debugging
    config.HEADLESS = False
    config.GLASSDOOR_PAGE_WAIT_TIME = 60
    config.GLASSDOOR_SEARCH_URL_TEMPLATE = "https://www.glassdoor.com/Search/results.htm?keyword={keyword}"
    
    print(f"DEBUG: Config source: {config.__file__}")
    print(f"DEBUG: Config dir: {dir(config)}")
except ImportError as e:
    print(f"Import failed: {e}")
    sys.exit(1)

async def test_crawler():
    print("--- CRAWLER DEBUG START ---")
    crawler = GlassdoorCrawler()
    
    keyword = "Cloudera"
    print(f"Searching for: {keyword}")
    
    try:
        results = await crawler.run_search([keyword])
        print(f"Crawler finished. Items found: {len(results)}")
        
        if results:
            print("First item preview:")
            print(results[0])
        else:
            print("FAILURE: No items found.")
            
    except Exception as e:
        print(f"Crawler Error: {e}")

    print("--- CRAWLER DEBUG END ---")

if __name__ == "__main__":
    asyncio.run(test_crawler())
