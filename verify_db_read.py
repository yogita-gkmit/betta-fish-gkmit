import sys
import os
import asyncio

# Setup path
sys.path.append(os.getcwd())

from InsightEngine.tools.search import MediaCrawlerDB

def main():
    print("--- [VERIFY] Init MediaCrawlerDB ---")
    try:
        db = MediaCrawlerDB()
        print("--- [VERIFY] DB Initialized ---")
    except Exception as e:
        print(f"--- [VERIFY] FAIL: DB Init Error: {e}")
        return

    keywords = ["Astral", "Cloudera"]
    
    for kw in keywords:
        print(f"\n--- [VERIFY] Searching for '{kw}' ---")
        try:
            # MediaCrawlerDB.search_topic_globally is synchronous wrapper
            res = db.search_topic_globally(kw, limit_per_table=5)
            print(f"--- [VERIFY] Results Count: {len(res.results)}")
            if res.results:
                print(f"--- [VERIFY] Top Result: {res.results[0].title_or_content[:50]}...")
            else:
                print(f"--- [VERIFY] No results found.")
        except Exception as e:
            print(f"--- [VERIFY] FAIL: Search Error for '{kw}': {e}")

if __name__ == "__main__":
    main()
