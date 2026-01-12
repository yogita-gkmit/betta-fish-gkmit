import asyncio
import os
import random
import sys
from typing import Dict, List, Optional
from datetime import datetime

from playwright.async_api import BrowserContext, BrowserType, Page, Playwright, async_playwright
from bs4 import BeautifulSoup

from base.base_crawler import AbstractCrawler
from proxy.proxy_ip_pool import ProxyIpPool
from tools import utils
from var import crawler_type_var

# Robust Config Import to avoid shadowing by MindSpider/config.py
try:
    from MindSpider.DeepSentimentCrawling.MediaCrawler import config
    utils.logger.info("[GlassdoorCrawler] Loaded config from absolute path (MindSpider package)")
except ImportError:
    try:
        import config
        utils.logger.info("[GlassdoorCrawler] Loaded config from relative/local path")
    except ImportError:
        utils.logger.error("[GlassdoorCrawler] CRITICAL: Could not load ANY config.")
        config = None # prevent immediate crash, handle locally

class GlassdoorCrawler(AbstractCrawler):
    context_page: Page
    browser_context: BrowserContext

    def __init__(self) -> None:
        self.index_url = "https://www.glassdoor.com"
        # Use None to let the browser report its actual User-Agent (avoids Client Hints mismatch)
        self.user_agent = None
        self.browser_context = None # Initialize to avoid AttributeError in cleanup

    async def run_search(self, keywords: List[str]) -> List[Dict]:
        """Entry point for external scripts to run search"""
        self.browser_context = None # Ensure reset
        # Config loaded via top-level check

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
            root_dir = os.path.dirname(os.path.dirname(current_dir)) # Correct path calc (2 levels up)
            stealth_path = os.path.join(root_dir, "libs", "stealth.min.js")
            
            if os.path.exists(stealth_path):
                await self.browser_context.add_init_script(path=stealth_path)
            
            # Reuse existing page if available (Critical for CDP mode)
            if self.browser_context.pages:
                self.context_page = self.browser_context.pages[0]
                try:
                    title_log = await self.context_page.title()
                except Exception:
                    title_log = "Unknown (Context Unstable)"
                utils.logger.info(f"[GlassdoorCrawler] Attaching to existing tab: {title_log}")
            else:
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
            # In CDP mode, we might NOT want to close the context/browser if we want to reuse it,
            # but for this specific flow, keeping cleanup is safer to avoid leaks, 
            # UNLESS it closes the user's main window.
            # If CDP mode is active, closing browser might close user window.
            # We should only close if NOT in CDP mode or if we created it.
            if config.ENABLE_CDP_MODE:
                utils.logger.info("[GlassdoorCrawler] CDP Mode: Skipping browser close to keep session alive.")
            else:
                if self.browser_context:
                    await self.browser_context.close()
                if browser:
                    await browser.close()
            if playwright:
                await playwright.stop()
            utils.logger.info("[GlassdoorCrawler] Browser resources released.")
            
        return results

    async def start(self) -> None:
        print(f"[DEBUG] GlassdoorCrawler.start() called.")


        async with async_playwright() as playwright:
            chromium = playwright.chromium
            self.browser_context = await self.launch_browser(
                chromium, None, self.user_agent, headless=config.HEADLESS
            )
            
            current_dir = os.path.dirname(os.path.abspath(__file__))
            root_dir = os.path.dirname(os.path.dirname(current_dir))
            stealth_path = os.path.join(root_dir, "libs", "stealth.min.js")
            
            # Reuse existing page if available (Critical for CDP mode)
            if self.browser_context.pages:
                self.context_page = self.browser_context.pages[0]
                utils.logger.info(f"[GlassdoorCrawler] Attaching to existing tab: {await self.context_page.title()}")
            else:
                self.context_page = await self.browser_context.new_page()

            # Anti-Detection: Manually override webdriver property (Redundant safety net)
            # Only apply stealth/overrides if NOT in CDP mode (Real browsers don't need this and it can cause flags)
            try:
                if not config.ENABLE_CDP_MODE:
                    await self.browser_context.add_init_script(path=stealth_path)
                    await self.context_page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                    print(f"[DEBUG] Injected 'navigator.webdriver = undefined' override.")
            except Exception as e:
                print(f"[DEBUG] Failed to inject webdriver override: {e}")

            try:
                await self.context_page.goto(self.index_url, wait_until="domcontentloaded")
            except Exception as e:
                utils.logger.error(f"[GlassdoorCrawler] Failed to load index page: {e}")

            crawler_type_var.set(config.CRAWLER_TYPE)
            print(f"[DEBUG] GlassdoorCrawler: Checking CRAWLER_TYPE: '{config.CRAWLER_TYPE}'")
            
            results = []
            if config.CRAWLER_TYPE == "search":
                # Default behavior uses config keywords
                keywords_list = config.KEYWORDS.split(",")
                print(f"[DEBUG] GlassdoorCrawler: Split keywords: {keywords_list}")
                results = await self.search_keywords(keywords_list)
            else:
                pass
            
            if results:
                print(f"[DEBUG] Found {len(results)} items.")
            else:
                print("[DEBUG] No results found.")

            utils.logger.info("[GlassdoorCrawler.start] Crawler finished ...")



    async def search(self) -> None:
        """Default search implementation using config keywords"""
        await self.search_keywords(config.KEYWORDS.split(","))

    async def search_keywords(self, keywords: List[str]) -> List[Dict]:
        """Search for multiple keywords and return combined results with pagination"""
        all_results = []
        utils.logger.info("[GlassdoorCrawler.search] Begin search keywords")
        print(f"\n[DEBUG] GlassdoorCrawler: Received keywords: {keywords}")
        
        # Ensure login/captcha clearance first
        await self.login()

        for keyword in keywords:
            if not keyword.strip(): continue
            
            # Rate Limiting / Delay: Random sleep to avoid CF-429
            # Configurable via code for now, default 10-20s
            delay = random.uniform(10, 20)
            print(f"[DEBUG] GlassdoorCrawler: Waiting {delay:.2f}s before processing '{keyword}' to avoid rate limits...")
            await asyncio.sleep(delay)

            utils.logger.info(f"[GlassdoorCrawler.search] Current search keyword: {keyword}")
            search_url = config.GLASSDOOR_SEARCH_URL_TEMPLATE.format(keyword=keyword)
            print(f"[DEBUG] GlassdoorCrawler: Navigating to {search_url}")
            
            try:
                # Robust Navigation with Cloudflare Interception
                # Robust Navigation with Cloudflare Interception
                try:
                    await self.context_page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
                    print(f"[DEBUG] check: Navigation Success")
                except Exception as goto_err:
                    print(f"[DEBUG] Navigation aborted/failed: {goto_err}. Triggering Passive/Manual Mode...")
                    
                    # Passive Mode: Wait for USER to navigate to results
                    utils.logger.warning(f"[GlassdoorCrawler] Cloudflare Block Active. Please solve CAPTCHA and Navigate to Search Results for '{keyword}' manually.")
                    print(f"!!! ACTION REQUIRED !!!")
                    print(f"1. Switch to Chrome window.")
                    print(f"2. Solve the CAPTCHA.")
                    print(f"3. If the page stays on home/login, MANUALLY TYPE '{keyword}' in search and hit Enter.")
                    print(f"4. Wait for the Job/Company results to load.")
                    print(f"The script is watching and will auto-scrape once results appear.")
                    
                    # Wait loop until we see results
                    max_passive_wait = 300 # 5 minutes
                    start_wait = asyncio.get_event_loop().time()
                    while True:
                        if (asyncio.get_event_loop().time() - start_wait) > max_passive_wait:
                            print("[DEBUG] Passive wait timed out.")
                            break
                        
                        try:
                            t = await self.context_page.title()
                            u = self.context_page.url
                            
                            # Quick Check for results
                            # If unblocked and URL has keyword or title has relevant terms
                            if "Just a moment" not in t and "Access denied" not in t and "Help Us Protect" not in t:
                                if (keyword in u) or ("Job" in t) or ("Company" in t) or ("Overview" in t) or ("Reviews" in t):
                                        print(f"[DEBUG] Detected Results Page (Title: {t}). Proceeding to scrape...")
                                        break
                                        
                        except Exception as e:
                            pass
                        await asyncio.sleep(2)

                await asyncio.sleep(5)
                print(f"[DEBUG] Post-Sleep (Wait Time: 5s)")
                
                # CRITICAL: Check for immediate post-navigation CAPTCHA/Block
                current_title = await self.context_page.title()
                current_content = await self.context_page.content()
                
                if "Just a moment" in current_title or "Help Us Protect Glassdoor" in current_content or "CF-103" in current_content or "CF-429" in current_content or "Access denied" in current_title:
                     print(f"[DEBUG] CAPTCHA Block Detected post-navigation (Title: {current_title}). Pausing for user...")
                     utils.logger.warning("[GlassdoorCrawler] Cloudflare/CAPTCHA detected. Waiting for user clearance in browser...")
                     await self.wait_for_user_clearance()

                keyword_results = []
                seen_ids = set()
                page_count = 1
                
                max_notes = getattr(config, 'CRAWLER_MAX_NOTES_COUNT', 20)
                print(f"[DEBUG] Pre-Loop Check: Results={len(keyword_results)}, Max={max_notes}")
                
                while len(keyword_results) < max_notes:
                    try:
                        print(f"[DEBUG] Loop Start. Results so far: {len(keyword_results)}")
                        
                        # Check for blocking mid-crawl
                        if "Just a moment" in await self.context_page.title():
                            utils.logger.warning("[GlassdoorCrawler] Cloudflare challenge detected mid-crawl. Waiting for user...")
                            await self.wait_for_user_clearance()

                        # Wait for results to load explicitly
                        try:
                            print(f"[DEBUG] Waiting for results to render...")
                            # Relaxed selector to ensure we don't timeout if structure changes slightly
                            await self.context_page.wait_for_selector('div[id*="MainCol"], div[class*="MainCol"]', timeout=5000) # Wait for main column
                            await asyncio.sleep(5) # Force wait for React hydration
                        except Exception as e:
                            print(f"[DEBUG] Timeout waiting for page load: {e}")
                            await asyncio.sleep(2)

                        print(f"[DEBUG] Fetching page content...")
                        html_content = await self.context_page.content()
                        
                        print(f"[DEBUG] Parsing content...")
                        current_items = self._parse_search_results(html_content, keyword)
                        print(f"[DEBUG] Parser returned {len(current_items)} items.")
                        
                        if not current_items:
                            print(f"[DEBUG] CRITICAL: Parsed 0 items. Dumping HTML to glassdoor_zero_results.html")
                            try:
                                with open("glassdoor_zero_results.html", "w", encoding="utf-8") as f:
                                    f.write(html_content)
                            except Exception as dump_err:
                                print(f"[DEBUG] Failed to write dump file: {dump_err}")
                        
                        new_count = 0
                        for item in current_items:
                            if item['id'] not in seen_ids:
                                keyword_results.append(item)
                                seen_ids.add(item['id'])
                                new_count += 1
                                
                        utils.logger.info(f"[GlassdoorCrawler] Keyword '{keyword}': Page {page_count}, Parsed {len(current_items)} items, {new_count} new. Total: {len(keyword_results)}")
                        
                        if new_count == 0:
                            utils.logger.info(f"[GlassdoorCrawler] No new items found on page {page_count}. Stopping search for this keyword.")
                            break

                        if len(keyword_results) >= config.CRAWLER_MAX_NOTES_COUNT:
                            break
                            
                        # Pagination logic
                        try:
                            # Check for "Give-to-Get" Content Wall (Review/Salary Request)
                            # Glassdoor often blocks users forcing them to contribute.
                            content_wall_close = self.context_page.locator('button[className*="Close"], span[alt="Close"], [data-test="ContentWall_Close"], div[class*="ContentWall_closeIcon"]')
                            if await content_wall_close.count() > 0:
                                 # Iterate to find the visible one
                                 for i in range(await content_wall_close.count()):
                                     btn = content_wall_close.nth(i)
                                     if await btn.is_visible():
                                         utils.logger.info("[GlassdoorCrawler] Detected 'Give-to-Get' Wall. Attempting to dismiss...")
                                         try:
                                             await btn.click()
                                             utils.logger.info("[GlassdoorCrawler] Dismissed Content Wall.")
                                             await asyncio.sleep(1) # Wait for animation
                                         except Exception as e:
                                             utils.logger.warning(f"[GlassdoorCrawler] Failed to dismiss wall: {e}")
                                         break
    
                            # Check for blocking login modal before interaction
                            modal = self.context_page.locator('#LoginModal, .Modal').first
                            if await modal.is_visible():
                                utils.logger.warning("[GlassdoorCrawler] Login Modal detected blocking navigation. Waiting for user clearance...")
                                await self.wait_for_user_clearance()
    
                            # Common Glassdoor pagination selectors
                            next_btn = self.context_page.locator('[data-test="pagination-next"], button[aria-label="Next"], .next a')
                            
                            if await next_btn.count() > 0 and await next_btn.first.is_visible():
                                # Check if disabled
                                if await next_btn.first.get_attribute("disabled"):
                                    utils.logger.info("[GlassdoorCrawler] Next button is disabled. End of results.")
                                    break
                                    
                                utils.logger.info("[GlassdoorCrawler] Clicking Next Page...")
                                # Force click or rigorous visibility check to handle overlays
                                try:
                                    async with self.context_page.expect_navigation(timeout=15000, wait_until="domcontentloaded"):
                                        await next_btn.first.click(timeout=5000)
                                except Exception as click_err:
                                    # Handle "Execution context was destroyed" specifically
                                    if "Execution context was destroyed" in str(click_err):
                                        utils.logger.warning("[GlassdoorCrawler] Context destroyed during navigation. Attempting to re-stabilize...")
                                        # If context is destroyed, the navigation *might* have happened or we are in a bad state.
                                        # We will try to rely on the outer loop to check the new page state.
                                        pass
                                    # Double check for modal if click failed (interception)
                                    elif "intercepts pointer events" in str(click_err):
                                        utils.logger.warning("[GlassdoorCrawler] Click intercepted by modal. Waiting for user...")
                                        await self.wait_for_user_clearance()
                                        # Retry click once if still visible
                                        if await next_btn.first.is_visible():
                                            await next_btn.first.click()
                                    else:
                                        # For other timeouts (navigation didn't finish), assume failure and STOP to prevent infinite scraping of same page
                                        utils.logger.error(f"[GlassdoorCrawler] Navigation wait timed out or failed: {click_err}. Stopping pagination to prevent loops.")
                                        break

                                previous_count = len(current_items)
                                # Safety wait for dynamic content
                                await asyncio.sleep(2)
                                page_count += 1
                            else:
                                utils.logger.info("[GlassdoorCrawler] No Next button found. End of results.")
                                break
                        except Exception as e:
                            utils.logger.error(f"[GlassdoorCrawler] Pagination error: {e}")
                            break
    
                    except Exception as loop_error:
                         print(f"[DEBUG] CRITICAL ERROR IN SEARCH LOOP: {loop_error}")
                         import traceback
                         traceback.print_exc()
                         break

                # Enrich with reviews (Limit to top items to avoid huge delays/bans)
                items_to_enrich = [i for i in keyword_results if i.get('url')][:5]
                utils.logger.info(f"[GlassdoorCrawler] Enriching {len(items_to_enrich)} items with reviews...")
                
                for item in items_to_enrich:
                    try:
                        reviews = await self.get_company_reviews(item['url'])
                        if reviews:
                            item['content'] += f"\n\n=== REVIEWS ===\n{reviews}"
                            utils.logger.info(f"[GlassdoorCrawler] Added reviews to {item['title']}")
                    except Exception as e:
                         utils.logger.error(f"[GlassdoorCrawler] Enrichment failed for {item['title']}: {e}")

                all_results.extend(keyword_results)
                
            except Exception as e:
                utils.logger.error(f"[GlassdoorCrawler] Error during search for {keyword}: {e}")
                
        return all_results

    async def login(self):
        """Check for login/captcha and wait for user if needed"""
        print("[DEBUG] GlassdoorCrawler: Checking Login Status...")
        
        try:
            # Retry loop for volatile contexts (e.g. page navigation/reload)
            for attempt in range(3):
                try:
                    # Attempt to stabilize
                    try:
                        await self.context_page.wait_for_load_state("domcontentloaded", timeout=3000)
                    except:
                        pass

                    # 1. Check Title & Content (Quick check)
                    title = await self.context_page.title()
                    content = await self.context_page.content()
                    if "Just a moment" in title or "Access denied" in title or "Help Us Protect" in title or "CF-103" in content or "CF-429" in content:
                        print(f"[DEBUG] Blocked by Cloudflare (Title: {title}).")
                        await self.wait_for_user_clearance()
                        return

                    # 2. Check DOM for Sign In button (More robust)
                    sign_in_elements = self.context_page.locator('header a[href*="signin"], header button:has-text("Sign In"), [data-test="site-header-sign-in"]')
                    
                    if await sign_in_elements.count() > 0 and await sign_in_elements.first.is_visible():
                        print("[DEBUG] 'Sign In' button detected. User is NOT logged in.")
                        await self.wait_for_user_clearance()
                    else:
                        print("[DEBUG] No 'Sign In' button found. Assuming Logged In.")
                    
                    # If we successfully checked, return
                    return

                except Exception as e:
                    if "Execution context was destroyed" in str(e) or "Target closed" in str(e):
                        print(f"[DEBUG] Context destroyed during login check (Attempt {attempt+1}/3). waiting and retrying...")
                        await asyncio.sleep(2)
                        # Try to re-attach if pages exist
                        if self.browser_context and self.browser_context.pages:
                             self.context_page = self.browser_context.pages[0]
                        continue
                    else:
                        utils.logger.error(f"[GlassdoorCrawler] Login check failed: {e}")
                        return
            
            print("[DEBUG] Login check exhausted retries. Proceeding carefully.")
            
        except Exception as e:
            print(f"[DEBUG] CRITICAL: Login check crashed entirely: {e}. Proceeding to search anyway.")
        finally:
            print("[DEBUG] Login check routine finished.")

    async def wait_for_user_clearance(self):
        """Loop until page title indicates access granted"""
        print("\n" + "="*50)
        print("!!! GLASSDOOR CRAWLER PAUSED !!!")
        print("Reason: Cloudflare Block or Login Needed.")
        print("ACTION REQUIRED: Go to the Chrome window and solve the CAPTCHA or Log In.")
        print("The script will resume automatically when you are done.")
        print("="*50 + "\n")
        
        counter = 0
        while True:
            try:
                title = await self.context_page.title()
                content = await self.context_page.content()
                
                # conditions to stay paused
                # conditions to stay paused
                is_blocked = "Just a moment" in title or "Help Us Protect Glassdoor" in content or "Access denied" in title or "CF-103" in content or "CF-429" in content
                is_login_page = "Sign In" in title or "header a[href*='signin']" in content # rough check
                
                # Better check: If we see search results or standard header profile
                has_results = "Job Search" in title or "Glassdoor" in title
                
                # If NOT blocked and (Title looks normal), resume
                if not is_blocked and ("Glassdoor" in title or "Job" in title):
                     print(f"\n[DEBUG] Block cleared! Current title: {title}")
                     utils.logger.info(f"[GlassdoorCrawler] User cleared the block. Resuming...")
                     await asyncio.sleep(2) # stabilization
                     break
                
                if counter % 5 == 0:
                    print(f"Waiting for clearance... (Current Title: {title})")
                
                counter += 1
                await asyncio.sleep(2)
            except Exception as e:
                print(f"Waiting... (Error checking page: {e})")
                await asyncio.sleep(2)

    def _parse_search_results(self, html: str, keyword: str) -> List[Dict]:
        """Parse Glassdoor HTML results with robust fallbacks"""
        soup = BeautifulSoup(html, 'html.parser')
        items = []
        
        utils.logger.info(f"[GlassdoorCrawler] Parsing HTML length: {len(html)}")
        
        # DEBUG DUMP - UNCONDITIONAL
        try:
            dump_path = os.path.join(os.getcwd(), "glassdoor_debug_dump.html")
            with open(dump_path, "w", encoding="utf-8") as f:
                 f.write(html)
            print(f"[DEBUG] SAVED HTML DUMP to {dump_path}")
        except Exception as e:
            print(f"[DEBUG] Failed to save dump: {e}")
        
        # 1. Companies - Try multiple container selectors
        company_cards = soup.select('div[data-test="company-card"]') or \
                        soup.select('.employer-card') or \
                        soup.select('div[class*="EmployerProfile"]') # Alert: Added React fallback
        
        utils.logger.info(f"[GlassdoorCrawler] Found {len(company_cards)} potential company cards")

        # --- 1. COMPANIES ---
        for i, div in enumerate(company_cards):
            # Name
            name_el = div.select_one('span[class*="employerName"]') or \
                      div.select_one('[data-test="employer-short-name"]') or \
                      div.select_one('h2') or \
                      div.select_one('h3')
            
            # Link
            link = div.find('a', href=True)
            
            # Rating
            rating_el = div.select_one('span[class*="employerRating"]') or \
                        div.select_one('[data-test="rating"]') or \
                        div.select_one('span[class*="rating"]')
            
            name_text = "Unknown"
            if name_el:
                name_text = name_el.get_text(strip=True)
            elif link:
                logo_div = div.select_one('[aria-label*="logo"]')
                name_text = logo_div['aria-label'].replace(' logo', '').replace(' Logo', '') if logo_div else link.get_text(strip=True).split('3.')[0]

            rating = rating_el.get_text(strip=True).replace('★', '').strip() if rating_el else "N/A"

            if name_text and name_text != "Unknown":
                logger_msg = f"[Glassdoor] Found Company: {name_text} (Rating: {rating})"
                utils.logger.info(logger_msg)
                print(f"--- FETCHED DATA: {logger_msg} ---")
                
                items.append({
                    "id": f"gd_comp_{keyword}_{i}",
                    "model_type": "glassdoor",
                    "title": name_text,
                    "content": f"Rating: {rating}. Type: Company Profile.",
                    "url": f"https://www.glassdoor.com{link['href']}" if link else "",
                    "publish_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "author": "Glassdoor",
                    "avatar": ""
                })

        # --- 2. JOBS ---
        # Robust React + Legacy Selectors
        job_cards = soup.select('div[data-test="jobs-item"]') or \
                    soup.select('div[class*="JobCard"]') or \
                    soup.select('li[class*="react-job-listing"]')
                    
        utils.logger.info(f"[GlassdoorCrawler] Found {len(job_cards)} job cards")
        for i, div in enumerate(job_cards):
            # Title: Try generic regex on class name for "jobTitle"
            title_el = div.select_one('[data-test="job-title"]') or \
                       div.select_one('[class*="jobTitle"]') or \
                       div.select_one('[class*="JobTitle"]') or \
                       div.select_one('a[data-test="job-link"]')
            
            # Employer: Try generic regex for "employerName"
            emp_el = div.select_one('[data-test="employer-name"]') or \
                     div.select_one('[class*="employerName"]') or \
                     div.select_one('[class*="EmployerName"]')
            
            # Location: "location"
            loc_el = div.select_one('[data-test="emp-location"]') or \
                     div.select_one('[class*="location"]') or \
                     div.select_one('[class*="Location"]')
            
            # Salary: "salaryEstimate"
            sal_el = div.select_one('[data-test="detailSalary"]') or \
                     div.select_one('[class*="salaryEstimate"]') or \
                     div.select_one('[class*="SalaryEstimate"]')

            title = title_el.get_text(strip=True) if title_el else "Unknown Job"
            employer = emp_el.get_text(strip=True) if emp_el else "Unknown Employer"
            location = loc_el.get_text(strip=True) if loc_el else ""
            salary = sal_el.get_text(strip=True) if sal_el else ""
            
            # Link finding logic (Title often is the link, or contains it)
            link_url = ""
            if title_el and title_el.name == 'a' and title_el.has_attr('href'):
                link_url = title_el['href']
            elif div.find('a', href=True):
                 link_url = div.find('a', href=True)['href']

            if not link_url.startswith("http") and link_url:
                link_url = f"https://www.glassdoor.com{link_url}"

            # Only append if we actually found something meaningful
            if title != "Unknown Job":
                msg = f"Job: {title} at {employer} ({location}) {salary}"
                items.append({
                    "id": f"gd_job_{keyword}_{i}",
                    "model_type": "glassdoor",
                    "title": f"Job: {title}",
                    "content": msg,
                    "url": link_url,
                    "publish_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "author": employer,
                    "avatar": "https://www.glassdoor.com/favicon.ico"
                })

        # --- 3. SALARIES ---
        salary_cards = soup.select('a[data-test^="salary-sgoc-tile-link"]')
        if salary_cards:
            utils.logger.info(f"[GlassdoorCrawler] Found {len(salary_cards)} salary entries")
            for i, link in enumerate(salary_cards):
                dept_el = link.select_one('strong')
                count_el = link.select_one('div[class*="styledSubtext"]')
                
                dept = dept_el.get_text(strip=True) if dept_el else "Unknown Dept"
                count = count_el.get_text(strip=True) if count_el else ""
                
                items.append({
                    "id": f"gd_salary_{keyword}_{i}", # Temporary ID
                    "model_type": "glassdoor",
                    "title": f"Salaries: {dept}",
                    "content": f"Department: {dept}. Data points: {count}",
                    "url": f"https://www.glassdoor.com{link['href']}" if link.has_attr('href') else "",
                    "publish_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "author": "Glassdoor Salaries",
                    "avatar": ""
                })

        # --- 4. INTERVIEWS ---
        int_card = soup.select_one('a[data-test="interview-summary-card"]')
        if int_card:
            pos_el = int_card.select_one('span[class*="isPositive"]')
            diff_el = int_card.select_one('div[class*="InterviewSummaryCard_summary"] p:nth-of-type(2)')
            
            pos = pos_el.get_text(strip=True) if pos_el else "N/A"
            diff = diff_el.get_text(strip=True) if diff_el else "N/A"
            
            items.append({
                "id": f"gd_interview_{keyword}", # Temporary ID
                "model_type": "glassdoor",
                "title": "Interview Experience",
                "content": f"Positive Experience: {pos}. Difficulty: {diff}",
                "url": f"https://www.glassdoor.com{int_card['href']}" if int_card.has_attr('href') else "",
                "publish_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "author": "Glassdoor Interviews",
                "avatar": ""
            })
                
        # 3. Generic Fallback (If structured parsing failed completely)
        # 3. Force Capture / Generic Fallback
        if not items:
            # DEBUG DUMP - CRITICAL FOR DIAGNOSIS
            try:
                dump_path = os.path.join(os.getcwd(), "glassdoor_debug_dump.html")
                with open(dump_path, "w", encoding="utf-8") as f:
                     f.write(html)
                print(f"[DEBUG] SAVED HTML DUMP to {dump_path} (Parse failed)")
            except Exception as e:
                print(f"[DEBUG] Failed to save dump: {e}")

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
        import json
        
        # Priority 0: CDP (Connect to Existing Chrome) - BEST FOR ANTIDETECTION
        # This allows the crawler to "hijack" the user's main verified Chrome window
        if config.ENABLE_CDP_MODE:
            try:
                endpoint = f"http://localhost:{config.CDP_DEBUG_PORT}"
                utils.logger.info(f"[GlassdoorCrawler] Attempting CDP connection to {endpoint}...")
                print(f"[DEBUG] Attempting CDP connection to {endpoint}...")
                
                browser = await chromium.connect_over_cdp(endpoint)
                print(f"[DEBUG] CDP Connected! Browser has {len(browser.contexts)} contexts.")
                
                default_context = browser.contexts[0]
                print(f"[DEBUG] Context 0 has {len(default_context.pages)} pages.")
                
                if not default_context.pages:
                    print("[DEBUG] No pages found in context. Creating new page...")
                    await default_context.new_page()
                else:
                    print(f"[DEBUG] Found {len(default_context.pages)} existing pages. Will attach to first one.")

                utils.logger.info(f"[GlassdoorCrawler] Connected to existing Chrome via CDP! Using your verified session.")
                
                # CRITICAL: Inject stealth to hide automation property
                # SKIP stealth for CDP mode to avoid corrupting the real browser fingerprint
                # await default_context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                # print(f"[DEBUG] Injected navigator.webdriver stealth override.")
                
                return default_context
            except Exception as e:
                print(f"!!! CDP CONNECTION FAILED !!! Error: {e}")
                utils.logger.error(f"[GlassdoorCrawler] CDP Connection failed: {e}. ABORTING because ENABLE_CDP_MODE is True.")
                print("HINT: Ensure Chrome is running with: --remote-debugging-port=9222")
                raise e # CRITICAL: Do not fallback. Fail hard so we see the error.
                # utils.logger.warning(f"[GlassdoorCrawler] CDP Connection failed: {e}. Falling back to standard launch.")

        # Priority 1: Load from Environment Variable (Credential-style)
        # DISABLE ENV VAR LOADING: Force usage of local persistent context to match Setup Script environment exactly.
        # session_env = os.environ.get("GLASSDOOR_SESSION")
        # if session_env and headless: # Only use env session in headless/run mode, likely
        #     try:
        #         utils.logger.info("[GlassdoorCrawler] Loading session from GLASSDOOR_SESSION environment variable.")
        #         state = json.loads(session_env)
        #         
        #         # Use standard ephemeral browser with injected state
        #         browser = await chromium.launch(
        #             headless=headless, 
        #             proxy=playwright_proxy,
        #             channel="chrome",
        #             args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
        #             ignore_default_args=["--enable-automation"]
        #         )
        #         browser_context = await browser.new_context(
        #             storage_state=state,
        #             viewport={"width": 1920, "height": 1080},
        #             user_agent=user_agent
        #         )
        #         return browser_context
        #     except Exception as e:
        #         utils.logger.error(f"[GlassdoorCrawler] Failed to load session from env: {e}. Falling back to disk.")

        # Priority 2: Persistent Disk Storage (Used for Setup or Fallback)
        user_data_dir = os.path.join(os.path.expanduser("~"), ".gemini", "browser_data", "glassdoor")
        os.makedirs(user_data_dir, exist_ok=True)
        utils.logger.info(f"[GlassdoorCrawler] Launching persistent browser context in: {user_data_dir}")
        
        browser_context = await chromium.launch_persistent_context(
            user_data_dir,
            headless=headless,
            proxy=playwright_proxy,
            viewport=None, # Allow browser to determine natural viewport
            user_agent=user_agent,
            channel="chrome",
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--start-maximized"], # Added start-maximized
            ignore_default_args=["--enable-automation"]
        )
        return browser_context

    async def get_company_reviews(self, url: str) -> str:
        """Visit company page and extract top reviews"""
        if not url: return ""
        try:
            # Check if it's a reviews URL or Overview
            # Adjust to point to reviews if not already
            if "Reviews" not in url and ".htm" in url:
                # Naive attempt to switch to reviews url if possible, or just visit and look for tab
                pass
                
            utils.logger.info(f"[GlassdoorCrawler] Fetching reviews from: {url}")
            await self.context_page.goto(url, wait_until="domcontentloaded", timeout=20000)
            await asyncio.sleep(2)
            
            # Extract Pros/Cons or main review text
            # Selectors for reviews vary... looking for standard review cards
            reviews_text = []
            
            # Try 2024 selectors
            review_cards = await self.context_page.locator('li[class*="review"], div.review-element').all()
            if not review_cards:
                 # Fallback: Just grab the "Pros" and "Cons" sections if visible on overview
                 content = await self.context_page.content()
                 soup = BeautifulSoup(content, 'html.parser')
                 text = soup.get_text(separator='\n', strip=True)
                 return f"Snippet from Page:\n{text[:5000]}"
            
            for i, card in enumerate(review_cards[:5]): # Top 5 reviews
                 text = await card.inner_text()
                 reviews_text.append(f"--- Review {i+1} ---\n{text}\n")
                 
            return "\n".join(reviews_text)
            
        except Exception as e:
            utils.logger.error(f"[GlassdoorCrawler] Failed to fetch reviews for {url}: {e}")
            return f"Error fetching reviews: {e}"
