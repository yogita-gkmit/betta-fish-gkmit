import asyncio
import os
from typing import Dict, List, Optional
from playwright.async_api import BrowserContext, BrowserType, Page, Playwright, async_playwright
from bs4 import BeautifulSoup
import config
from base.base_crawler import AbstractCrawler
from tools import utils
from var import crawler_type_var

class TimesOfIndiaCrawler(AbstractCrawler):
    context_page: Page
    browser_context: BrowserContext

    def __init__(self) -> None:
        self.index_url = "https://timesofindia.indiatimes.com"
        self.user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"

    async def run_search(self, keywords: List[str]) -> List[Dict]:
        """Entry point for external scripts to run search"""
        results = []
        async with async_playwright() as playwright:
            chromium = playwright.chromium
            self.browser_context = await self.launch_browser(
                chromium, None, self.user_agent, headless=config.HEADLESS
            )
            
            # Resolve absolute path to stealth.min.js
            current_dir = os.path.dirname(os.path.abspath(__file__))
            root_dir = os.path.dirname(os.path.dirname(current_dir))
            stealth_path = os.path.join(root_dir, "libs", "stealth.min.js")
            
            await self.browser_context.add_init_script(path=stealth_path)
            self.context_page = await self.browser_context.new_page()
            
            results = await self.search_keywords(keywords)
            
        return results

    async def start(self) -> None:
        async with async_playwright() as playwright:
            chromium = playwright.chromium
            self.browser_context = await self.launch_browser(
                chromium, None, self.user_agent, headless=config.HEADLESS
            )
            
            current_dir = os.path.dirname(os.path.abspath(__file__))
            root_dir = os.path.dirname(os.path.dirname(current_dir))
            stealth_path = os.path.join(root_dir, "libs", "stealth.min.js")
            
            await self.browser_context.add_init_script(path=stealth_path)
            self.context_page = await self.browser_context.new_page()
            await self.context_page.goto(self.index_url, wait_until="domcontentloaded")
            
            crawler_type_var.set(config.CRAWLER_TYPE)
            if config.CRAWLER_TYPE == "search":
                await self.search_keywords(config.KEYWORDS.split(","))
            else:
                pass
            utils.logger.info("[TimesOfIndiaCrawler.start] Crawler finished ...")

    async def search(self) -> None:
        """Default search implementation using config keywords"""
        await self.search_keywords(config.KEYWORDS.split(","))

    async def search_keywords(self, keywords: List[str]) -> List[Dict]:
        """Search for multiple keywords and return combined results"""
        all_results = []
        utils.logger.info("[TimesOfIndiaCrawler.search] Begin search keywords")
        
        for keyword in keywords:
            if not keyword.strip(): continue
            utils.logger.info(f"[TimesOfIndiaCrawler.search] Current search keyword: {keyword}")
            search_url = config.TOI_SEARCH_URL_TEMPLATE.format(keyword=keyword)
            
            try:
                await self.context_page.goto(search_url, wait_until="domcontentloaded")
                await asyncio.sleep(config.TOI_PAGE_WAIT_TIME)
                
                html_content = await self.context_page.content()
                items = self._parse_search_results(html_content, keyword)
                
                utils.logger.info(f"[TimesOfIndiaCrawler.search] Found {len(items)} results for {keyword}")
                all_results.extend(items)
                
            except Exception as e:
                utils.logger.error(f"[TimesOfIndiaCrawler] Error during search for {keyword}: {e}")
        
        return all_results

    def _parse_search_results(self, html: str, keyword: str) -> List[Dict]:
        """Parse TOI HTML results"""
        soup = BeautifulSoup(html, 'html.parser')
        items = []
        seen_urls = set()
        
        # 1. Try Specific Classes (from legacy logic)
        for i, el in enumerate(soup.select('.uwU81')):
             title_el = el.select_one('.fHv_i')
             link_el = el.select_one('a')
             summary_el = el.select_one('.oxXSK')
             
             if title_el and link_el:
                 url = link_el['href']
                 if url not in seen_urls:
                     seen_urls.add(url)
                     items.append({
                        "id": f"toi_{keyword}_{i}",
                        "title": title_el.get_text(strip=True),
                        "url": url,
                        "source": "toi_news",
                        "rank": i + 1,
                        "metadata": {"summary": summary_el.get_text(strip=True) if summary_el else ""}
                     })

        if items:
            return items

        # 2. Fallback: Generic Link Search for '/articleshow/'
        articles = soup.find_all('a', href=True)
        for a in articles:
            href = a['href']
            if '/articleshow/' in href and a.get_text(strip=True):
                # Normalize URL
                if href.startswith('/'):
                    full_url = f"https://timesofindia.indiatimes.com{href}"
                else:
                    full_url = href
                    
                if full_url in seen_urls:
                    continue
                seen_urls.add(full_url)
                
                items.append({
                    "id": f"toi_{keyword}_{len(items)}",
                    "title": a.get_text(strip=True),
                    "url": full_url,
                    "source": "toi_news",
                    "rank": len(items) + 1,
                    "metadata": {}
                })
                
                if len(items) >= 20: # Limit result count
                    break
                    
        return items

    async def launch_browser(self, chromium: BrowserType, playwright_proxy: Optional[Dict], user_agent: Optional[str], headless: bool = True) -> BrowserContext:
        browser = await chromium.launch(headless=headless, proxy=playwright_proxy)
        browser_context = await browser.new_context(
            viewport={"width": 1920, "height": 1080}, user_agent=user_agent
        )
        return browser_context
