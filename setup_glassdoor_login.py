
import asyncio
import sys
from pathlib import Path
from loguru import logger

# Add project root to path
project_root = Path(__file__).resolve().parent
sys.path.append(str(project_root))
sys.path.append(str(project_root / "MindSpider" / "DeepSentimentCrawling" / "MediaCrawler"))

try:
    from MindSpider.DeepSentimentCrawling.MediaCrawler.media_platform.glassdoor.core import GlassdoorCrawler
    import config
    # FLIP HEADLESS TO FALSE FOR INTERACTIVE LOGIN
    config.HEADLESS = False
    config.CRAWLER_MAX_NOTES_COUNT = 40 # Fetch 2 pages
    
    # Patch config if needed
    if not hasattr(config, "GLASSDOOR_SEARCH_URL_TEMPLATE"):
        config.GLASSDOOR_SEARCH_URL_TEMPLATE = "https://www.glassdoor.com/Search/results.htm?keyword={keyword}"
    if not hasattr(config, "GLASSDOOR_PAGE_WAIT_TIME"):
        config.GLASSDOOR_PAGE_WAIT_TIME = 3
except ImportError as e:
    logger.error(f"Import failed: {e}")
    sys.exit(1)

async def main():
    crawler = GlassdoorCrawler()
    
    # Manually setup browser context
    from playwright.async_api import async_playwright
    async with async_playwright() as playwright:
        chromium = playwright.chromium
        
        # Try CDP Connection First (User's Existing Chrome)
        try:
            logger.info("Attempting to connect to existing Chrome on port 9222...")
            logger.info("Ensure you started Chrome with: /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome --remote-debugging-port=9222")
            
            browser = await chromium.connect_over_cdp("http://localhost:9222")
            crawler.browser_context = browser.contexts[0]
            if not crawler.browser_context.pages:
                crawler.context_page = await crawler.browser_context.new_page()
            else:
                crawler.context_page = crawler.browser_context.pages[0]
            
            logger.success("Connected to existing Chrome via CDP! Using your logged-in session.")
            
        except Exception as cdp_error:
            logger.warning(f"CDP Connection failed ({cdp_error}). Falling back to launching new browser...")
            
            # Legacy Fallback: Force headless=False for this test
            crawler.browser_context = await crawler.launch_browser(
                chromium, None, crawler.user_agent, headless=False
            )
            crawler.context_page = await crawler.browser_context.new_page()
        
        # Inject Stealth Script (Crucial for Cloudflare)
        import os
        stealth_path = Path(project_root) / "MindSpider" / "DeepSentimentCrawling" / "MediaCrawler" / "libs" / "stealth.min.js"
        if stealth_path.exists():
            logger.info(f"Injecting stealth script from {stealth_path}")
            await crawler.browser_context.add_init_script(path=str(stealth_path))
        else:
             logger.warning(f"Stealth script not found at {stealth_path}")

        crawler.context_page = await crawler.browser_context.new_page()
        
        keyword = "Google"
        logger.info(f"Verifying Glassdoor Login & Pagination. Keyword: {keyword}")
        
        results = await crawler.search_keywords([keyword])
        
        logger.info(f"Total results fetched: {len(results)}")
        
        if len(results) >= 30:
            logger.info("SUCCESS: Pagination likely worked (fetched > 30 items)")
        elif len(results) > 0:
            logger.warning("PARTIAL SUCCESS: Fetched items but maybe not paginated fully.")
        else:
            logger.error("FAILURE: Fetched 0 items.")

        # Export Session for Env Var (Unconditional)
        import json
        try:
            state = await crawler.browser_context.storage_state()
            json_str = json.dumps(state)
            print("\n" + "="*80)
            print("SESSION CAPTURE SUCCESSFUL")
            print("To save this session as a credential in your .env file, copy the following JSON string:")
            print("-" * 80)
            print(f"GLASSDOOR_SESSION='{json_str}'")
            print("-" * 80)
            print("Instructions: Open your .env file and paste the line above.")
            print("="*80 + "\n")
        except Exception as e:
            logger.error(f"Failed to export session state: {e}")

        await crawler.browser_context.close()

if __name__ == "__main__":
    asyncio.run(main())
