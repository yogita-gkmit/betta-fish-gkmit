#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BroadTopicExtraction Module - News Acquisition and Collection
Integrates News API usage and database storage functionality
"""

import sys
import asyncio
import httpx
import json
from datetime import datetime, date
from pathlib import Path
from typing import List, Dict, Optional
from loguru import logger

# Add project root directory to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

try:
    from BroadTopicExtraction.database_manager import DatabaseManager
except ImportError as e:
    raise ImportError(f"Failed to import module: {e}")

# News API Base URL
BASE_URL = "https://newsnow.busiyi.world"

# News Source Chinese Name Mapping
SOURCE_NAMES = {
    "weibo": "Weibo Hot Search",
    "zhihu": "Zhihu Hot List",
    "bilibili-hot-search": "Bilibili Hot Search",
    "toutiao": "Toutiao",
    "douyin": "Douyin Hot List",
    "github-trending-today": "GitHub Trending",
    "coolapk": "Coolapk Hot List",
    "tieba": "Baidu Tieba",
    "wallstreetcn": "WallstreetCN",
    "thepaper": "The Paper",
    "cls-hot": "CLS Hot",
    "xueqiu": "Xueqiu Hot List"
}

class NewsCollector:
    """News Collector - Integrates API calls and database storage"""
    
    def __init__(self):
        """Initialize News Collector"""
        self.db_manager = DatabaseManager()
        self.supported_sources = list(SOURCE_NAMES.keys())
    
    def close(self):
        """Close Resources"""
        if self.db_manager:
            self.db_manager.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    # ==================== News API Calls ====================
    
    async def fetch_news(self, source: str) -> dict:
        """Fetch latest news from specified source"""
        url = f"{BASE_URL}/api/s?id={source}&latest"
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Referer": BASE_URL,
            "Connection": "keep-alive",
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                
                # Parse JSON response
                data = response.json()
                return {
                    "source": source,
                    "status": "success",
                    "data": data,
                    "timestamp": datetime.now().isoformat()
                }
        except httpx.TimeoutException:
            return {
                "source": source,
                "status": "timeout",
                "error": f"Request timeout: {source}({url})",
                "timestamp": datetime.now().isoformat()
            }
        except httpx.HTTPStatusError as e:
            return {
                "source": source,
                "status": "http_error",
                "error": f"HTTP Error: {source}({url}) - {e.response.status_code}",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "source": source,
                "status": "error",
                "error": f"Unknown Error: {source}({url}) - {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
    
    async def get_popular_news(self, sources: List[str] = None) -> List[dict]:
        """Get Popular News"""
        if sources is None:
            sources = list(SOURCE_NAMES.keys())
        
        logger.info(f"Fetching latest content from {len(sources)} news sources...")
        logger.info("=" * 80)
        
        results = []
        for source in sources:
            source_name = SOURCE_NAMES.get(source, source)
            logger.info(f"Fetching news from {source_name}...")
            result = await self.fetch_news(source)
            results.append(result)
            
            if result["status"] == "success":
                data = result["data"]
                if 'items' in data and isinstance(data['items'], list):
                    count = len(data['items'])
                    logger.info(f"✓ {source_name}: Successfully fetched, total {count} news")
                else:
                    logger.info(f"✓ {source_name}: Successfully fetched")
            else:
                logger.error(f"✗ {source_name}: {result.get('error', 'Fetch failed')}")
            
            # Avoid requesting too fast
            await asyncio.sleep(0.5)
        
        return results
    
    # ==================== Data Processing and Storage ====================
    
    async def collect_and_save_news(self, sources: Optional[List[str]] = None) -> Dict:
        """
        Collect and Save Daily Hot News
        
        Args:
            sources: List of specified news sources, None means use all supported sources
            
        Returns:
            Dictionary containing collection results
        """
        collection_summary_message = ""
        collection_summary_message += "\nStarting collection of daily hot news...\n"
        collection_summary_message += f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        
        # Select News Sources
        if sources is None:
            # Use all supported news sources
            sources = list(SOURCE_NAMES.keys())
        
        collection_summary_message += f"Will collect data from {len(sources)} news sources:\n"
        for source in sources:
            source_name = SOURCE_NAMES.get(source, source)
            collection_summary_message += f"  - {source_name}\n"
        
        logger.info(collection_summary_message)
        
        try:
            # Fetch News Data
            results = await self.get_popular_news(sources)
            
            # Process Results
            processed_data = self._process_news_results(results)
            
            # Save to Database (Overwrite Mode)
            if processed_data['news_list']:
                saved_count = self.db_manager.save_daily_news(
                    processed_data['news_list'], 
                    date.today()
                )
                processed_data['saved_count'] = saved_count
            
            # Print Summary Stats
            self._print_collection_summary(processed_data)
            
            return processed_data
            
        except Exception as e:
            logger.exception(f"Failed to collect news: {e}")
            return {
                'success': False,
                'error': str(e),
                'news_list': [],
                'total_news': 0
            }
    
    def _process_news_results(self, results: List[Dict]) -> Dict:
        """Process News Fetch Results"""
        news_list = []
        successful_sources = 0
        total_news = 0
        
        for result in results:
            source = result['source']
            status = result['status']
            
            if status == 'success':
                successful_sources += 1
                data = result['data']
                
                if 'items' in data and isinstance(data['items'], list):
                    source_news_count = len(data['items'])
                    total_news += source_news_count
                    
                    # Process news from this source
                    for i, item in enumerate(data['items'], 1):
                        processed_news = self._process_news_item(item, source, i)
                        if processed_news:
                            news_list.append(processed_news)
        
        return {
            'success': True,
            'news_list': news_list,
            'successful_sources': successful_sources,
            'total_sources': len(results),
            'total_news': total_news,
            'collection_time': datetime.now().isoformat()
        }
    
    def _process_news_item(self, item: Dict, source: str, rank: int) -> Optional[Dict]:
        """Process Single News Item"""
        try:
            if isinstance(item, dict):
                title = item.get('title', 'No Title').strip()
                url = item.get('url', '')
                
                # Generate News ID
                news_id = f"{source}_{item.get('id', f'rank_{rank}')}"
                
                return {
                    'id': news_id,
                    'title': title,
                    'url': url,
                    'source': source,
                    'rank': rank
                }
            else:
                # Process string type news
                title = str(item)[:100] if len(str(item)) > 100 else str(item)
                return {
                    'id': f"{source}_rank_{rank}",
                    'title': title,
                    'url': '',
                    'source': source,
                    'rank': rank
                }
                
        except Exception as e:
            logger.exception(f"Failed to process news item: {e}")
            return None
    
    def _print_collection_summary(self, data: Dict):
        """Print Collection Summary"""
        collection_summary_message = ""
        collection_summary_message += f"\nTotal News Sources: {data['total_sources']}\n"
        collection_summary_message += f"Successful Sources: {data['successful_sources']}\n"
        collection_summary_message += f"Total News Count: {data['total_news']}\n"
        if 'saved_count' in data:
            collection_summary_message += f"Saved Count: {data['saved_count']}\n"
        logger.info(collection_summary_message)
    
    def get_today_news(self) -> List[Dict]:
        """Get Today's News"""
        try:
            return self.db_manager.get_daily_news(date.today())
        except Exception as e:
            logger.exception(f"Failed to get today's news: {e}")
            return []

async def main():
    """Test News Collector"""
    logger.info("Testing News Collector...")
    
    async with NewsCollector() as collector:
        # Collect news
        result = await collector.collect_and_save_news(
            sources=["weibo", "zhihu"]  # Test use, only use two sources
        )
        
        if result['success']:
            logger.info(f"Collection successful! Fetched {result['total_news']} news items")
        else:
            logger.error(f"Collection failed: {result.get('error', 'Unknown Error')}")

if __name__ == "__main__":
    asyncio.run(main())
