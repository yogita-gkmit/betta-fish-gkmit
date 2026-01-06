#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BroadTopicExtraction Module - News Acquisition and Collection
Integrates News API usage and database storage functionality
"""

import sys
import asyncio
import json
from datetime import datetime, date
from pathlib import Path
from typing import List, Dict, Optional
from loguru import logger

# Import DatabaseManager
try:
    from database_manager import DatabaseManager
except ImportError:
    try:
        from MindSpider.BroadTopicExtraction.database_manager import DatabaseManager
    except ImportError:
        logger.error("Could not import DatabaseManager. Database saving will fail.")
        DatabaseManager = None


# Add project root and MediaCrawler to path for imports
project_root = Path(__file__).parent.parent
# CRITICAL: Insert MediaCrawler path FIRST to ensure its 'config' package is loaded 
# instead of the shadowing 'config.py' in MindSpider root.
media_crawler_path = str(project_root / "DeepSentimentCrawling" / "MediaCrawler")
if media_crawler_path not in sys.path:
    sys.path.insert(0, media_crawler_path) 
sys.path.append(str(project_root))

# Monkey patch config to satisfy MediaCrawler dependencies if needed
try:
    import config
    # Ensure we have the right config
    if "MediaCrawler" not in getattr(config, "__file__", "") and not hasattr(config, "ENABLE_CDP_MODE"):
         logger.warning(f"Loaded wrong config from {getattr(config, '__file__', 'unknown')}. forcing reload from MediaCrawler...")
         import importlib
         importlib.reload(config)

    # FORCE HEADLESS = False conditionally check is weak, FORCE IT.
    # FORCE HEADLESS = False conditionally check is weak, FORCE IT.
    config.HEADLESS = False 
    
    if not hasattr(config, "PLATFORM"):
        config.PLATFORM = "toi"
    if not hasattr(config, "CRAWLER_TYPE"):
        config.CRAWLER_TYPE = "search"
    if not hasattr(config, "KEYWORDS"):
        config.KEYWORDS = ""
    # Add other potentially missing configs used by crawlers
    if not hasattr(config, "LOGIN_TYPE"):
        config.LOGIN_TYPE = "qrcode"
    if not hasattr(config, "COOKIES"):
        config.COOKIES = ""

    # Platform specific configs
    if not hasattr(config, "TOI_SEARCH_URL_TEMPLATE"):
        config.TOI_SEARCH_URL_TEMPLATE = "https://timesofindia.indiatimes.com/topic/{keyword}"
    if not hasattr(config, "TOI_PAGE_WAIT_TIME"):
        config.TOI_PAGE_WAIT_TIME = 5
    if not hasattr(config, "GLASSDOOR_SEARCH_URL_TEMPLATE"):
        config.GLASSDOOR_SEARCH_URL_TEMPLATE = "https://www.glassdoor.com/Search/results.htm?keyword={keyword}"
    if not hasattr(config, "GLASSDOOR_PAGE_WAIT_TIME"):
        config.GLASSDOOR_PAGE_WAIT_TIME = 5
except ImportError:
    pass

try:
    from BroadTopicExtraction.database_manager import DatabaseManager
except ImportError as e:
    pass

try:
    from deep_sentiment_crawling.media_platform.glassdoor.core import GlassdoorCrawler
    from deep_sentiment_crawling.media_platform.times_of_india.core import TimesOfIndiaCrawler
except ImportError:
    # Try alternate import path if modules are structured differently
    try:
        from media_platform.glassdoor.core import GlassdoorCrawler
        from media_platform.times_of_india.core import TimesOfIndiaCrawler
    except ImportError as e:
        # Fallback for direct execution where checking paths is tricky
        try:
           sys.path.append(str(project_root / "DeepSentimentCrawling" / "MediaCrawler"))
           from media_platform.glassdoor.core import GlassdoorCrawler
           from media_platform.times_of_india.core import TimesOfIndiaCrawler
        except Exception as e2:
           logger.error(f"Failed to import Crawlers: {e2}")
           raise e

# News Source Mapping
SOURCE_NAMES = {
    "toi": "Times of India",
    "glassdoor": "Glassdoor"
}

class NewsCollector:
    """News Collector - Integrates API calls and database storage"""
    
    def __init__(self):
        """Initialize News Collector"""
        try:
            self.db_manager = DatabaseManager()
        except Exception as e:
            logger.warning(f"DatabaseManager init failed: {e}. Running in NO-DB mode.")
            self.db_manager = None
            
        self.supported_sources = list(SOURCE_NAMES.keys())
    
    def close(self):
        """Close Resources"""
        if self.db_manager:
             try:
                 self.db_manager.close()
             except:
                 pass
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    # ==================== Search & Fetch Logic ====================
    
    async def search_news(self, keyword: str) -> List[dict]:
        """Search news/data from all sources by keyword"""
        results = []
        logger.info(f"Starting unified search for keyword: {keyword}")
        
        # Run crawlers in parallel
        # Note: Playwright might have issues with parallel context creation in same loop if not handled carefully,
        # but separate instances typically work fine.
        gd_task = self._run_glassdoor(keyword)
        toi_task = self._run_toi(keyword)
        
        all_results = await asyncio.gather(gd_task, toi_task, return_exceptions=True)
        
        for res in all_results:
            if isinstance(res, Exception):
                logger.error(f"Search task failed: {res}")
            else:
                results.append(res)
        
        return results

    async def _run_glassdoor(self, keyword: str) -> dict:
        """Run Glassdoor Crawler"""
        try:
            logger.info("Initializing Glassdoor Crawler...")
            crawler = GlassdoorCrawler()
            items = await crawler.run_search([keyword])
            return {
                "source": "glassdoor",
                "status": "success",
                "data": {"items": items},
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Glassdoor Crawler failed: {e}")
            return {"source": "glassdoor", "status": "error", "error": str(e)}

    async def _run_toi(self, keyword: str) -> dict:
        """Run TOI Crawler"""
        try:
            logger.info("Initializing Times of India Crawler...")
            crawler = TimesOfIndiaCrawler()
            items = await crawler.run_search([keyword])
            return {
                "source": "toi",
                "status": "success",
                "data": {"items": items},
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"TOI Crawler failed: {e}")
            return {"source": "toi", "status": "error", "error": str(e)}
    
    # ==================== Data Processing and Storage ====================
    
    async def collect_and_save_search_results(self, keyword: str) -> Dict:
        """
        Collect and Save Search Results
        """
        logger.info(f"Starting collection for keyword: {keyword}")
        
        try:
            # Fetch Data
            results = await self.search_news(keyword)
            
            # Process Results
            processed_data = self._process_news_results(results)
            
            # Save to Database (Always call to ensure old data is cleared if new search is empty)
            if self.db_manager:
                try:
                    # save_daily_news will clear existing data for the date before inserting
                    saved_count = self.db_manager.save_daily_news(
                        processed_data['news_list'], 
                        date.today()
                    )
                    processed_data['saved_count'] = saved_count
                    if not processed_data['news_list']:
                        logger.info("News list is empty. Cleared existing data for today.")
                except Exception as e:
                    logger.error(f"Failed to save to DB: {e}")
            else:
                processed_data['saved_count'] = 0
                logger.info("Skipped DB save (DB manager not active)")
            
            self._print_collection_summary(processed_data)
            return processed_data
            
        except Exception as e:
            logger.exception(f"Failed to collect news: {e}")
            return {'success': False, 'error': str(e), 'news_list': []}
    
    def _process_news_results(self, results: List[Dict]) -> Dict:
        """Process News Fetch Results"""
        news_list = []
        successful_sources = 0
        total_news = 0
        
        for result in results:
            source = result.get('source', 'unknown')
            status = result.get('status', 'error')
            
            if status == 'success':
                successful_sources += 1
                data = result.get('data', {})
                
                if 'items' in data and isinstance(data['items'], list):
                    source_news_count = len(data['items'])
                    total_news += source_news_count
                    
                    for i, item in enumerate(data['items'], 1):
                        # Use specific source type if provided
                        source_type = item.get('source', source)
                        
                        processed_news = {
                            'id': item.get('id', f"{source}_{i}"), 
                            'title': item.get('title', 'No Title'),
                            'url': item.get('url', ''),
                            'source': source_type, 
                            'rank': item.get('rank', i),
                            'metadata': item.get('metadata', {}),
                            'content': item.get('content', '')
                        }
                        news_list.append(processed_news)
        
        return {
            'success': True,
            'news_list': news_list,
            'successful_sources': successful_sources,
            'total_sources': len(results),
            'total_news': total_news,
            'collection_time': datetime.now().isoformat()
        }
    
    def _print_collection_summary(self, data: Dict):
        """Print Collection Summary"""
        if data.get('success'):
            logger.info(f"Total News Count: {data['total_news']}")
            logger.info(f"Saved Count: {data.get('saved_count', 0)}")
    
    def get_today_news(self) -> List[Dict]:
        """Get Today's News (from DB)"""
        if not self.db_manager:
             return []
        try:
            return self.db_manager.get_daily_news(date.today())
        except Exception as e:
            logger.exception(f"Failed to get today's news: {e}")
            return []

async def main():
    """Test News Collector via Search"""
    keyword = "TCS" 
    if len(sys.argv) > 1:
        # Join all arguments to handle multi-word keywords (e.g. "Tata Motors")
        keyword = " ".join(sys.argv[1:])
        
    logger.info(f"Testing News Search for: {keyword}")
    
    async with NewsCollector() as collector:
        result = await collector.collect_and_save_search_results(keyword)
        
        if result['success']:
            logger.info(f"Search successful! Found {result.get('total_news')} items.")
            # Verify segregation
            sources = set(item['source'] for item in result['news_list'])
            logger.info(f"Data sources found: {sources}")
        else:
            logger.error(f"Search failed: {result.get('error')}")

if __name__ == "__main__":
    asyncio.run(main())
