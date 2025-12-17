import asyncio
import os
from typing import Dict, List, Optional
from playwright.async_api import BrowserContext, BrowserType, Page, Playwright, async_playwright
from bs4 import BeautifulSoup
import config
from base.base_crawler import AbstractCrawler
from tools import utils
from var import crawler_type_var

class GlassdoorCrawler(AbstractCrawler):
    context_page: Page
    browser_context: BrowserContext

    def __init__(self) -> None:
        self.index_url = "https://www.glassdoor.com"
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
            # glassdoor(or toi)/core.py -> glassdoor -> media_platform -> MediaCrawler -> libs
            root_dir = os.path.dirname(os.path.dirname(current_dir))
            stealth_path = os.path.join(root_dir, "libs", "stealth.min.js")
            
            await self.browser_context.add_init_script(path=stealth_path)
            self.context_page = await self.browser_context.new_page()
            
            # Warm up
            try:
                await self.context_page.goto(self.index_url, wait_until="domcontentloaded")
            except:
                pass
                
            results = await self.search_keywords(keywords)
            
        return results

    async def start(self) -> None:
        async with async_playwright() as playwright:
            chromium = playwright.chromium
            self.browser_context = await self.launch_browser(
                chromium, None, self.user_agent, headless=config.HEADLESS
            )
            
            current_dir = os.path.dirname(os.path.abspath(__file__))
            root_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
            stealth_path = os.path.join(root_dir, "libs", "stealth.min.js")
            
            await self.browser_context.add_init_script(path=stealth_path)
            self.context_page = await self.browser_context.new_page()
            
            try:
                await self.context_page.goto(self.index_url, wait_until="domcontentloaded")
            except Exception as e:
                utils.logger.error(f"[GlassdoorCrawler] Failed to load index page: {e}")

            crawler_type_var.set(config.CRAWLER_TYPE)
            if config.CRAWLER_TYPE == "search":
                # Default behavior uses config keywords
                await self.search_keywords(config.KEYWORDS.split(","))
            else:
                pass
            utils.logger.info("[GlassdoorCrawler.start] Crawler finished ...")

    async def search(self) -> None:
        """Default search implementation using config keywords"""
        await self.search_keywords(config.KEYWORDS.split(","))

    async def search_keywords(self, keywords: List[str]) -> List[Dict]:
        """Search for multiple keywords and return combined results"""
        all_results = []
        utils.logger.info("[GlassdoorCrawler.search] Begin search keywords")
        
        for keyword in keywords:
            if not keyword.strip(): continue
            utils.logger.info(f"[GlassdoorCrawler.search] Current search keyword: {keyword}")
            search_url = config.GLASSDOOR_SEARCH_URL_TEMPLATE.format(keyword=keyword)
            
            try:
                await self.context_page.goto(search_url, wait_until="domcontentloaded")
                await asyncio.sleep(config.GLASSDOOR_PAGE_WAIT_TIME)
                
                if "Sign In" in await self.context_page.title():
                    utils.logger.warning("[GlassdoorCrawler] Login wall detected. Results might be limited.")

                html_content = await self.context_page.content()
                items = self._parse_search_results(html_content, keyword)
                
                utils.logger.info(f"[GlassdoorCrawler.search] Found {len(items)} results for {keyword}")
                all_results.extend(items)
                
            except Exception as e:
                utils.logger.error(f"[GlassdoorCrawler] Error during search for {keyword}: {e}")
                
        return all_results

    def _parse_search_results(self, html: str, keyword: str) -> List[Dict]:
        """Parse Glassdoor HTML results"""
        soup = BeautifulSoup(html, 'html.parser')
        items = []
        
        # 1. Companies
        for i, div in enumerate(soup.select('div[data-test="company-card"]')):
            name = div.select_one('.employer-card_employerName__kSwU7')
            link = div.select_one('a.employer-card_employerCardContainer__Y7DA5')
            rating = div.select_one('.employer-card_employerRatingContainer__w93y9')
            
            if name:
                items.append({
                    "id": f"gd_comp_{keyword}_{i}",
                    "title": f"[Company] {name.get_text(strip=True)}",
                    "url": f"https://www.glassdoor.com{link['href']}" if link and link.get('href') else "",
                    "source": "glassdoor_company",
                    "rank": i + 1,
                    "metadata": {"rating": rating.get_text(strip=True) if rating else "N/A"}
                })

        # 2. Jobs
        for i, div in enumerate(soup.select('div[data-test="jobs-item"]')):
            title = div.select_one('div[data-test="job-title"]')
            emp = div.select_one('.EmployerProfile_compactEmployerName__9MGcV')
            loc = div.select_one('div[data-test="emp-location"]')
            
            if title:
                items.append({
                    "id": f"gd_job_{keyword}_{i}",
                    "title": f"[Job] {title.get_text(strip=True)} at {emp.get_text(strip=True) if emp else 'Unknown'}",
                    "url": "", # Job links often complex in this view
                    "source": "glassdoor_job",
                    "rank": i + 1,
                    "metadata": {"location": loc.get_text(strip=True) if loc else ""}
                })
                
        # 3. Conversations (Optional)
        for i, div in enumerate(soup.select('div[data-test="conversations-item"]')):
            body = div.select_one('p[data-test="PostPreviewCard-body"]')
            if body:
                items.append({
                    "id": f"gd_conv_{keyword}_{i}",
                    "title": f"[Discussion] {body.get_text(strip=True)[:100]}...",
                    "url": "",
                    "source": "glassdoor_conversation",
                    "rank": i + 1
                })
                
        return items

    async def launch_browser(self, chromium: BrowserType, playwright_proxy: Optional[Dict], user_agent: Optional[str], headless: bool = True) -> BrowserContext:
        browser = await chromium.launch(headless=headless, proxy=playwright_proxy)
        browser_context = await browser.new_context(
            viewport={"width": 1920, "height": 1080}, user_agent=user_agent
        )
        return browser_context
