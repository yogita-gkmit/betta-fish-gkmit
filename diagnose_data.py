
import asyncio
import sys
from datetime import date
from loguru import logger
import json

# Setup paths
import os
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)
sys.path.append(os.path.join(project_root, "MindSpider"))

try:
    from MindSpider.BroadTopicExtraction.database_manager import DatabaseManager
except ImportError as e:
    print(f"Import failed: {e}")
    sys.exit(1)

async def check_data():
    print("--- DIAGNOSTIC START ---")
    try:
        db = DatabaseManager()
        print("Connected to DB.")
        
        # 1. Count
        # We need to use internal session to count, or just fetch
        # DatabaseManager is sync wrapper around async? No, it's mixed.
        # Let's just use its get_daily_news method
        
        today_news = db.get_daily_news(date.today())
        print(f"Total News for Today ({date.today()}): {len(today_news)}")
        
        if not today_news:
            print("WARNING: No news found for today. Check if Crawler actually ran and saved.")
        else:
            print("\nPreview of First 3 Items:")
            for item in today_news[:3]:
                print(f"ID: {item.get('id')}")
                print(f"Title: {item.get('title')}")
                print(f"Source: {item.get('source')}")
                content = item.get('content', '')
                print(f"Content Length: {len(content)}")
                print(f"Content Preview: {content[:100]}...")
                print("-" * 30)

    except Exception as e:
        print(f"DB Error: {e}")

    print("--- DIAGNOSTIC END ---")

if __name__ == "__main__":
    asyncio.run(check_data())
