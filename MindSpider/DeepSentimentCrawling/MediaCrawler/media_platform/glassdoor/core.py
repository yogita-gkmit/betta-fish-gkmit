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
        browser = None
        playwright = None
        
        try:
            playwright = await async_playwright().start()
            chromium = playwright.chromium
            self.browser_context = await self.launch_browser(
                chromium, None, self.user_agent, headless=config.HEADLESS
            )
            # Get the browser instance associated with the context to close it later
            browser = self.browser_context.browser
            
            # Resolve absolute path to stealth.min.js
            current_dir = os.path.dirname(os.path.abspath(__file__))
            root_dir = os.path.dirname(os.path.dirname(current_dir))
            stealth_path = os.path.join(root_dir, "libs", "stealth.min.js")
            
            if os.path.exists(stealth_path):
                await self.browser_context.add_init_script(path=stealth_path)
            
            self.context_page = await self.browser_context.new_page()
            
            # Warm up with timeout to prevent hang
            try:
                await self.context_page.goto(self.index_url, wait_until="domcontentloaded", timeout=15000)
            except Exception:
                pass
                
            results = await self.search_keywords(keywords)
            
        except Exception as e:
            utils.logger.error(f"[GlassdoorCrawler] run_search failed: {e}")
        finally:
            # Explicit cleanup to prevent zombie processes/hangs
            if self.browser_context:
                await self.browser_context.close()
            if browser:
                await browser.close()
            if playwright:
                await playwright.stop()
            utils.logger.info("[GlassdoorCrawler] Browser resources closed.")
            
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
        """Parse Glassdoor HTML results with robust fallbacks"""
        soup = BeautifulSoup(html, 'html.parser')
        items = []
        
        utils.logger.info(f"[GlassdoorCrawler] Parsing HTML length: {len(html)}")
        
        # 1. Companies - Try multiple container selectors
        company_cards = soup.select('div[data-test="company-card"]') or \
                        soup.select('.employer-card') # Fallback to partial class
        
        utils.logger.info(f"[GlassdoorCrawler] Found {len(company_cards)} potential company cards")

        for i, div in enumerate(company_cards):
            # Try to find name in common locations
            name_el = div.select_one('[data-test="employer-short-name"]') or \
                      div.select_one('h2') or \
                      div.select_one('h3') or \
                      div.select_one('a') # Last resort: first link
            
            name_text = name_el.get_text(strip=True) if name_el else div.get_text(strip=True).split('  ')[0]
            
            # Find link
            link = div.find('a', href=True)
            
            # Find rating
            rating_el = div.select_one('[data-test="rating"]') or \
                        div.select_one('span[class*="rating"]')
            
            rating = rating_el.get_text(strip=True) if rating_el else "N/A"

            if name_text:
                logger_msg = f"[Glassdoor] Found Company: {name_text} (Rating: {rating})"
                utils.logger.info(logger_msg)
                print(f"--- FRETCHED DATA: {logger_msg} ---")
                
                items.append({
                    "id": f"gd_comp_{keyword}_{i}",
                    "title": f"[Company] {name_text}",
                    "url": f"https://www.glassdoor.com{link['href']}" if link else "",
                    "source": "glassdoor_company",
                    "rank": i + 1,
                    "metadata": {"rating": rating},
                    "content": div.get_text(separator=' | ', strip=True) # Capture full card text as content
                })

        # 2. Jobs - Try multiple container selectors
        job_cards = soup.select('div[data-test="jobs-item"]') or \
                    soup.select('li[data-test="job-listing"]') or \
                    soup.select('.job-search-key') # Common reactive class prefix
        
        utils.logger.info(f"[GlassdoorCrawler] Found {len(job_cards)} potential job cards")

        for i, div in enumerate(job_cards):
            # Job Title
            title_el = div.select_one('[data-test="job-title"]') or \
                       div.select_one('a[data-test="job-link"]') or \
                       div.find('a', class_=lambda x: x and 'job' in x.lower())
            
            # Employer
            emp_el = div.select_one('[data-test="employer-name"]') or \
                     div.find(lambda tag: tag.name == "div" and tag.text and len(tag.text) < 50)
            
            title_text = title_el.get_text(strip=True) if title_el else "Unknown Job"
            emp_text = emp_el.get_text(strip=True) if emp_el else "Unknown Company"
            
            if title_el or "Job" in title_text:
                logger_msg = f"[Glassdoor] Found Job: {title_text} at {emp_text}"
                print(f"--- FETCHED DATA: {logger_msg} ---")
                
                items.append({
                    "id": f"gd_job_{keyword}_{i}",
                    "title": f"[Job] {title_text} at {emp_text}",
                    "url": f"https://www.glassdoor.com{title_el['href']}" if title_el and title_el.has_attr('href') else "",
                    "source": "glassdoor_job",
                    "rank": i + 1,
                    "metadata": {"company": emp_text},
                    "content": div.get_text(separator=' | ', strip=True)
                })
                
        # 3. Generic Fallback (If structured parsing failed completely)
        # 3. Force Capture / Generic Fallback
        if not items:
            utils.logger.warning("[GlassdoorCrawler] Structured parsing yielded 0 results. Executing Force Capture of text content.")
            # Capture visible text chunks to form a rough summary
            main_text = soup.get_text(separator='\n', strip=True)
            # Filter out too short lines to reduce noise
            clean_lines = [line for line in main_text.split('\n') if len(line) > 20] 
            content_dump = "\n".join(clean_lines)[:10000] # Limit to 10k chars
            
            if len(content_dump) > 100:
                items.append({
                    "id": f"gd_dump_{keyword}",
                    "title": f"[Glassdoor Raw Summary] {keyword}",
                    "url": config.GLASSDOOR_SEARCH_URL_TEMPLATE.format(keyword=keyword),
                    "source": "glassdoor_fallback",
                    "rank": 1,
                    "metadata": {"type": "page_dump"},
                    "content": f"Glassdoor Search Results for {keyword} (Raw Text Extraction):\n\n{content_dump}"
                })

        # Remove duplicates
        seen_ids = set()
        unique_items = []
        for item in items:
            if item['id'] not in seen_ids:
                unique_items.append(item)
                seen_ids.add(item['id'])
                
        return unique_items

    async def launch_browser(self, chromium: BrowserType, playwright_proxy: Optional[Dict], user_agent: Optional[str], headless: bool = True) -> BrowserContext:
        browser = await chromium.launch(headless=headless, proxy=playwright_proxy)
        browser_context = await browser.new_context(
            viewport={"width": 1920, "height": 1080}, user_agent=user_agent
        )
        return browser_context
