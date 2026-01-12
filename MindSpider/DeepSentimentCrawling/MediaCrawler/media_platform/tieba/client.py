# Declaration: This code is for learning and research purposes only. Users must adhere to the following principles:
# 1. Do not use for any commercial purposes.
# 2. Comply with the target platform's terms of use and robots.txt rules.
# 3. Do not perform large-scale crawling or disrupt platform operations.
# 4. Reasonably control request frequency to avoid unnecessary burden on the target platform.
# 5. Do not use for any illegal or improper purposes.
#
# For detailed license terms, please refer to the LICENSE file in the project root directory.
# Using this code indicates your agreement to abide by the above principles and all terms in the LICENSE.

import asyncio
import json
from typing import Any, Callable, Dict, List, Optional, Union
from urllib.parse import urlencode, quote

import requests
from playwright.async_api import BrowserContext, Page
from tenacity import RetryError, retry, stop_after_attempt, wait_fixed

import config
from base.base_crawler import AbstractApiClient
from model.m_baidu_tieba import TiebaComment, TiebaCreator, TiebaNote
from proxy.proxy_ip_pool import ProxyIpPool
from tools import utils

from .field import SearchNoteType, SearchSortType
from .help import TieBaExtractor


class BaiduTieBaClient(AbstractApiClient):

    def __init__(
        self,
        timeout=10,
        ip_pool=None,
        default_ip_proxy=None,
        headers: Dict[str, str] = None,
        playwright_page: Optional[Page] = None,
    ):
        self.ip_pool: Optional[ProxyIpPool] = ip_pool
        self.timeout = timeout
        # Use the passed headers (including real browser UA) or default headers
        self.headers = headers or {
            "User-Agent": utils.get_user_agent(),
            "Cookie": "",
        }
        self._host = "https://tieba.baidu.com"
        self._page_extractor = TieBaExtractor()
        self.default_ip_proxy = default_ip_proxy
        self.playwright_page = playwright_page  # Playwright page object

    def _sync_request(self, method, url, proxy=None, **kwargs):
        """
        Synchronous requests request method
        Args:
            method: request method
            url: request URL
            proxy: proxy IP
            **kwargs: other request parameters

        Returns:
            response object
        """
        # Construct proxy dictionary
        proxies = None
        if proxy:
            proxies = {
                "http": proxy,
                "https": proxy,
            }

        # Send request
        response = requests.request(
            method=method,
            url=url,
            headers=self.headers,
            proxies=proxies,
            timeout=self.timeout,
            **kwargs
        )
        return response

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def request(self, method, url, return_ori_content=False, proxy=None, **kwargs) -> Union[str, Any]:
        """
        Encapsulate common requests request method, process request response
        Args:
            method: request method
            url: request URL
            return_ori_content: whether to return original content
            proxy: proxy IP
            **kwargs: other request parameters, e.g. headers, body etc.

        Returns:

        """
        actual_proxy = proxy if proxy else self.default_ip_proxy

        # Execute synchronous requests request in thread pool
        response = await asyncio.to_thread(
            self._sync_request,
            method,
            url,
            actual_proxy,
            **kwargs
        )

        if response.status_code != 200:
            utils.logger.error(f"Request failed, method: {method}, url: {url}, status code: {response.status_code}")
            utils.logger.error(f"Request failed, response: {response.text}")
            raise Exception(f"Request failed, method: {method}, url: {url}, status code: {response.status_code}")

        if response.text == "" or response.text == "blocked":
            utils.logger.error(f"request params incorrect, response.text: {response.text}")
            raise Exception("account blocked")

        if return_ori_content:
            return response.text

        return response.json()

    async def get(self, uri: str, params=None, return_ori_content=False, **kwargs) -> Any:
        """
        GET request, sign request headers
        Args:
            uri: request route
            params: request parameters
            return_ori_content: whether to return original content

        Returns:

        """
        final_uri = uri
        if isinstance(params, dict):
            final_uri = (f"{uri}?"
                         f"{urlencode(params)}")
        try:
            res = await self.request(method="GET", url=f"{self._host}{final_uri}", return_ori_content=return_ori_content, **kwargs)
            return res
        except RetryError as e:
            if self.ip_pool:
                proxie_model = await self.ip_pool.get_proxy()
                _, proxy = utils.format_proxy_info(proxie_model)
                res = await self.request(method="GET", url=f"{self._host}{final_uri}", return_ori_content=return_ori_content, proxy=proxy, **kwargs)
                self.default_ip_proxy = proxy
                return res

            utils.logger.error(f"[BaiduTieBaClient.get] Reached max retries, IP blocked, please try changing IP proxy: {e}")
            raise Exception(f"[BaiduTieBaClient.get] Reached max retries, IP blocked, please try changing IP proxy: {e}")

    async def post(self, uri: str, data: dict, **kwargs) -> Dict:
        """
        POST request, sign request headers
        Args:
            uri: request route
            data: request body parameters

        Returns:

        """
        json_str = json.dumps(data, separators=(',', ':'), ensure_ascii=False)
        return await self.request(method="POST", url=f"{self._host}{uri}", data=json_str, **kwargs)

    async def pong(self, browser_context: BrowserContext = None) -> bool:
        """
        Check if login state is invalid
        Use Cookie check instead of API call to avoid detection
        Args:
            browser_context: browser context object

        Returns:
            bool: True means logged in, False means not logged in
        """
        utils.logger.info("[BaiduTieBaClient.pong] Begin to check tieba login state by cookies...")

        if not browser_context:
            utils.logger.warning("[BaiduTieBaClient.pong] browser_context is None, assume not logged in")
            return False

        try:
            # Get cookies from browser and check key login cookies
            _, cookie_dict = utils.convert_cookies(await browser_context.cookies())

            # Baidu Tieba login identifier: STOKEN or PTOKEN
            stoken = cookie_dict.get("STOKEN")
            ptoken = cookie_dict.get("PTOKEN")
            bduss = cookie_dict.get("BDUSS")  # Baidu universal login cookie

            if stoken or ptoken or bduss:
                utils.logger.info(f"[BaiduTieBaClient.pong] Login state verified by cookies (STOKEN: {bool(stoken)}, PTOKEN: {bool(ptoken)}, BDUSS: {bool(bduss)})")
                return True
            else:
                utils.logger.info("[BaiduTieBaClient.pong] No valid login cookies found, need to login")
                return False

        except Exception as e:
            utils.logger.error(f"[BaiduTieBaClient.pong] Check login state failed: {e}, assume not logged in")
            return False

    async def update_cookies(self, browser_context: BrowserContext):
        """
        Update cookies method provided by API client, usually called after successful login
        Args:
            browser_context: browser context object

        Returns:

        """
        cookie_str, cookie_dict = utils.convert_cookies(await browser_context.cookies())
        self.headers["Cookie"] = cookie_str
        utils.logger.info("[BaiduTieBaClient.update_cookies] Cookie has been updated")

    async def get_notes_by_keyword(
        self,
        keyword: str,
        page: int = 1,
        page_size: int = 10,
        sort: SearchSortType = SearchSortType.TIME_DESC,
        note_type: SearchNoteType = SearchNoteType.FIXED_THREAD,
    ) -> List[TiebaNote]:
        """
        Search Tieba posts by keyword (Use Playwright to visit page, avoid API detection)
        Args:
            keyword: keyword
            page: page number
            page_size: page size
            sort: result sorting
            note_type: post type (main thread | mixed mode of main + reply)
        Returns:

        """
        if not self.playwright_page:
            utils.logger.error("[BaiduTieBaClient.get_notes_by_keyword] playwright_page is None, cannot use browser mode")
            raise Exception("playwright_page is required for browser-based search")

        # Construct search URL
        # Example: https://tieba.baidu.com/f/search/res?ie=utf-8&qw=programming
        search_url = f"{self._host}/f/search/res"
        params = {
            "ie": "utf-8",
            "qw": keyword,
            "rn": page_size,
            "pn": page,
            "sm": sort.value,
            "only_thread": note_type.value,
        }

        # Concatenate complete URL
        full_url = f"{search_url}?{urlencode(params)}"
        utils.logger.info(f"[BaiduTieBaClient.get_notes_by_keyword] Visiting search page: {full_url}")

        try:
            # Use Playwright to visit search page
            await self.playwright_page.goto(full_url, wait_until="domcontentloaded")

            # Wait for page load, use delay setting in config
            await asyncio.sleep(config.CRAWLER_MAX_SLEEP_SEC)

            # Get page HTML content
            page_content = await self.playwright_page.content()
            utils.logger.info(f"[BaiduTieBaClient.get_notes_by_keyword] Successfully got search page HTML, length: {len(page_content)}")

            # Extract search results
            notes = self._page_extractor.extract_search_note_list(page_content)
            utils.logger.info(f"[BaiduTieBaClient.get_notes_by_keyword] Extracted {len(notes)} posts")
            return notes

        except Exception as e:
            utils.logger.error(f"[BaiduTieBaClient.get_notes_by_keyword] Search failed: {e}")
            raise

    async def get_note_by_id(self, note_id: str) -> TiebaNote:
        """
        Get post details by post ID (Use Playwright to visit page, avoid API detection)
        Args:
            note_id: post ID

        Returns:
            TiebaNote: post detail object
        """
        if not self.playwright_page:
            utils.logger.error("[BaiduTieBaClient.get_note_by_id] playwright_page is None, cannot use browser mode")
            raise Exception("playwright_page is required for browser-based note detail fetching")

        # Construct post detail URL
        note_url = f"{self._host}/p/{note_id}"
        utils.logger.info(f"[BaiduTieBaClient.get_note_by_id] Visiting post detail page: {note_url}")

        try:
            # Use Playwright to visit post detail page
            await self.playwright_page.goto(note_url, wait_until="domcontentloaded")

            # Wait for page load, use delay setting in config
            await asyncio.sleep(config.CRAWLER_MAX_SLEEP_SEC)

            # Get page HTML content
            page_content = await self.playwright_page.content()
            utils.logger.info(f"[BaiduTieBaClient.get_note_by_id] Successfully got post detail HTML, length: {len(page_content)}")

            # Extract post details
            note_detail = self._page_extractor.extract_note_detail(page_content)
            return note_detail

        except Exception as e:
            utils.logger.error(f"[BaiduTieBaClient.get_note_by_id] Failed to get post detail: {e}")
            raise

    async def get_note_all_comments(
        self,
        note_detail: TiebaNote,
        crawl_interval: float = 1.0,
        callback: Optional[Callable] = None,
        max_count: int = 10,
    ) -> List[TiebaComment]:
        """
        Get all level 1 comments under the specified post (Use Playwright to visit page, avoid API detection)
        Args:
            note_detail: post detail object
            crawl_interval: sleep interval (seconds)
            callback: callback function after one post crawl ends
            max_count: maximum number of comments crawled for a single post
        Returns:
            List[TiebaComment]: comment list
        """
        if not self.playwright_page:
            utils.logger.error("[BaiduTieBaClient.get_note_all_comments] playwright_page is None, cannot use browser mode")
            raise Exception("playwright_page is required for browser-based comment fetching")

        result: List[TiebaComment] = []
        current_page = 1

        while note_detail.total_replay_page >= current_page and len(result) < max_count:
            # Construct comment page URL
            comment_url = f"{self._host}/p/{note_detail.note_id}?pn={current_page}"
            utils.logger.info(f"[BaiduTieBaClient.get_note_all_comments] Visiting comment page: {comment_url}")

            try:
                # Use Playwright to visit comment page
                await self.playwright_page.goto(comment_url, wait_until="domcontentloaded")

                # Wait for page load, use delay setting in config
                await asyncio.sleep(config.CRAWLER_MAX_SLEEP_SEC)

                # Get page HTML content
                page_content = await self.playwright_page.content()

                # Extract comments
                comments = self._page_extractor.extract_tieba_note_parment_comments(
                    page_content, note_id=note_detail.note_id
                )

                if not comments:
                    utils.logger.info(f"[BaiduTieBaClient.get_note_all_comments] No comments on page {current_page}, stop crawling")
                    break

                # Limit number of comments
                if len(result) + len(comments) > max_count:
                    comments = comments[:max_count - len(result)]

                if callback:
                    await callback(note_detail.note_id, comments)

                result.extend(comments)

                # Get all sub comments
                await self.get_comments_all_sub_comments(
                    comments, crawl_interval=crawl_interval, callback=callback
                )

                await asyncio.sleep(crawl_interval)
                current_page += 1

            except Exception as e:
                utils.logger.error(f"[BaiduTieBaClient.get_note_all_comments] Failed to get comments on page {current_page}: {e}")
                break

        utils.logger.info(f"[BaiduTieBaClient.get_note_all_comments] Total extracted {len(result)} level 1 comments")
        return result

    async def get_comments_all_sub_comments(
        self,
        comments: List[TiebaComment],
        crawl_interval: float = 1.0,
        callback: Optional[Callable] = None,
    ) -> List[TiebaComment]:
        """
        Get all sub comments under the specified comment (Use Playwright to visit page, avoid API detection)
        Args:
            comments: comment list
            crawl_interval: crawling interval unit (seconds)
            callback: callback function after one post crawl ends

        Returns:
            List[TiebaComment]: sub comment list
        """
        if not config.ENABLE_GET_SUB_COMMENTS:
            return []

        if not self.playwright_page:
            utils.logger.error("[BaiduTieBaClient.get_comments_all_sub_comments] playwright_page is None, cannot use browser mode")
            raise Exception("playwright_page is required for browser-based sub-comment fetching")

        all_sub_comments: List[TiebaComment] = []

        for parment_comment in comments:
            if parment_comment.sub_comment_count == 0:
                continue

            current_page = 1
            max_sub_page_num = parment_comment.sub_comment_count // 10 + 1

            while max_sub_page_num >= current_page:
                # Construct sub comment URL
                sub_comment_url = (
                    f"{self._host}/p/comment?"
                    f"tid={parment_comment.note_id}&"
                    f"pid={parment_comment.comment_id}&"
                    f"fid={parment_comment.tieba_id}&"
                    f"pn={current_page}"
                )
                utils.logger.info(f"[BaiduTieBaClient.get_comments_all_sub_comments] Visiting sub comment page: {sub_comment_url}")

                try:
                    # Use Playwright to visit sub comment page
                    await self.playwright_page.goto(sub_comment_url, wait_until="domcontentloaded")

                    # Wait for page load, use delay setting in config
                    await asyncio.sleep(config.CRAWLER_MAX_SLEEP_SEC)

                    # Get page HTML content
                    page_content = await self.playwright_page.content()

                    # Extract sub comments
                    sub_comments = self._page_extractor.extract_tieba_note_sub_comments(
                        page_content, parent_comment=parment_comment
                    )

                    if not sub_comments:
                        utils.logger.info(
                            f"[BaiduTieBaClient.get_comments_all_sub_comments] "
                            f"No sub comments on page {current_page} for comment {parment_comment.comment_id}, stop crawling"
                        )
                        break

                    if callback:
                        await callback(parment_comment.note_id, sub_comments)

                    all_sub_comments.extend(sub_comments)
                    await asyncio.sleep(crawl_interval)
                    current_page += 1

                except Exception as e:
                    utils.logger.error(
                        f"[BaiduTieBaClient.get_comments_all_sub_comments] "
                        f"Failed to get page {current_page} sub comments for comment {parment_comment.comment_id}: {e}"
                    )
                    break

        utils.logger.info(f"[BaiduTieBaClient.get_comments_all_sub_comments] Total extracted {len(all_sub_comments)} sub comments")
        return all_sub_comments

    async def get_notes_by_tieba_name(self, tieba_name: str, page_num: int) -> List[TiebaNote]:
        """
        Get post list by tieba name (Use Playwright to visit page, avoid API detection)
        Args:
            tieba_name: tieba name
            page_num: page number

        Returns:
            List[TiebaNote]: post list
        """
        if not self.playwright_page:
            utils.logger.error("[BaiduTieBaClient.get_notes_by_tieba_name] playwright_page is None, cannot use browser mode")
            raise Exception("playwright_page is required for browser-based tieba note fetching")

        # Construct tieba post list URL
        tieba_url = f"{self._host}/f?kw={quote(tieba_name)}&pn={page_num}"
        utils.logger.info(f"[BaiduTieBaClient.get_notes_by_tieba_name] Visiting tieba page: {tieba_url}")

        try:
            # Use Playwright to visit tieba page
            await self.playwright_page.goto(tieba_url, wait_until="domcontentloaded")

            # Wait for page load, use delay setting in config
            await asyncio.sleep(config.CRAWLER_MAX_SLEEP_SEC)

            # Get page HTML content
            page_content = await self.playwright_page.content()
            utils.logger.info(f"[BaiduTieBaClient.get_notes_by_tieba_name] Successfully got tieba page HTML, length: {len(page_content)}")

            # Extract post list
            notes = self._page_extractor.extract_tieba_note_list(page_content)
            utils.logger.info(f"[BaiduTieBaClient.get_notes_by_tieba_name] Extracted {len(notes)} posts")
            return notes

        except Exception as e:
            utils.logger.error(f"[BaiduTieBaClient.get_notes_by_tieba_name] Failed to get tieba post list: {e}")
            raise

    async def get_creator_info_by_url(self, creator_url: str) -> str:
        """
        Get creator info by creator URL (Use Playwright to visit page, avoid API detection)
        Args:
            creator_url: creator homepage URL

        Returns:
            str: page HTML content
        """
        if not self.playwright_page:
            utils.logger.error("[BaiduTieBaClient.get_creator_info_by_url] playwright_page is None, cannot use browser mode")
            raise Exception("playwright_page is required for browser-based creator info fetching")

        utils.logger.info(f"[BaiduTieBaClient.get_creator_info_by_url] Visiting creator homepage: {creator_url}")

        try:
            # Use Playwright to visit creator homepage
            await self.playwright_page.goto(creator_url, wait_until="domcontentloaded")

            # Wait for page load, use delay setting in config
            await asyncio.sleep(config.CRAWLER_MAX_SLEEP_SEC)

            # Get page HTML content
            page_content = await self.playwright_page.content()
            utils.logger.info(f"[BaiduTieBaClient.get_creator_info_by_url] Successfully got creator homepage HTML, length: {len(page_content)}")

            return page_content

        except Exception as e:
            utils.logger.error(f"[BaiduTieBaClient.get_creator_info_by_url] Failed to get creator homepage: {e}")
            raise

    async def get_notes_by_creator(self, user_name: str, page_number: int) -> Dict:
        """
        Get creator's posts by creator (Use Playwright to visit page, avoid API detection)
        Args:
            user_name: creator username
            page_number: page number

        Returns:
            Dict: dictionary containing post data
        """
        if not self.playwright_page:
            utils.logger.error("[BaiduTieBaClient.get_notes_by_creator] playwright_page is None, cannot use browser mode")
            raise Exception("playwright_page is required for browser-based creator notes fetching")

        # Construct creator post list URL
        creator_url = f"{self._host}/home/get/getthread?un={quote(user_name)}&pn={page_number}&id=utf-8&_={utils.get_current_timestamp()}"
        utils.logger.info(f"[BaiduTieBaClient.get_notes_by_creator] Visiting creator post list: {creator_url}")

        try:
            # Use Playwright to visit creator post list page
            await self.playwright_page.goto(creator_url, wait_until="domcontentloaded")

            # Wait for page load, use delay setting in config
            await asyncio.sleep(config.CRAWLER_MAX_SLEEP_SEC)

            # Get page content (this API returns JSON)
            page_content = await self.playwright_page.content()

            # Extract JSON data (page may contain <pre> tag or be direct JSON)
            try:
                # Attempt to extract JSON from page
                json_text = await self.playwright_page.evaluate("() => document.body.innerText")
                result = json.loads(json_text)
                utils.logger.info(f"[BaiduTieBaClient.get_notes_by_creator] Successfully got creator post data")
                return result
            except json.JSONDecodeError as e:
                utils.logger.error(f"[BaiduTieBaClient.get_notes_by_creator] JSON parsing failed: {e}")
                utils.logger.error(f"[BaiduTieBaClient.get_notes_by_creator] Page content: {page_content[:500]}")
                raise Exception(f"Failed to parse JSON from creator notes page: {e}")

        except Exception as e:
            utils.logger.error(f"[BaiduTieBaClient.get_notes_by_creator] Failed to get creator post list: {e}")
            raise

    async def get_all_notes_by_creator_user_name(
        self,
        user_name: str,
        crawl_interval: float = 1.0,
        callback: Optional[Callable] = None,
        max_note_count: int = 0,
        creator_page_html_content: str = None,
    ) -> List[TiebaNote]:
        """
        Get all posts by creator username
        Args:
            user_name: creator username
            crawl_interval: sleep interval (seconds)
            callback: callback function after one post crawl ends, is an awaitable function
            max_note_count: maximum number of posts, if 0 then get all
            creator_page_html_content: creator homepage HTML content

        Returns:

        """
        # Baidu Tieba is a bit special, the first 10 posts are displayed directly on the homepage, need to be handled separately, cannot be obtained via API
        result: List[TiebaNote] = []
        if creator_page_html_content:
            thread_id_list = (self._page_extractor.extract_tieba_thread_id_list_from_creator_page(creator_page_html_content))
            utils.logger.info(f"[BaiduTieBaClient.get_all_notes_by_creator] got user_name:{user_name} thread_id_list len : {len(thread_id_list)}")
            note_detail_task = [self.get_note_by_id(thread_id) for thread_id in thread_id_list]
            notes = await asyncio.gather(*note_detail_task)
            if callback:
                await callback(notes)
            result.extend(notes)

        notes_has_more = 1
        page_number = 1
        page_per_count = 20
        total_get_count = 0
        while notes_has_more == 1 and (max_note_count == 0 or total_get_count < max_note_count):
            notes_res = await self.get_notes_by_creator(user_name, page_number)
            if not notes_res or notes_res.get("no") != 0:
                utils.logger.error(f"[WeiboClient.get_notes_by_creator] got user_name:{user_name} notes failed, notes_res: {notes_res}")
                break
            notes_data = notes_res.get("data")
            notes_has_more = notes_data.get("has_more")
            notes = notes_data["thread_list"]
            utils.logger.info(f"[WeiboClient.get_all_notes_by_creator] got user_name:{user_name} notes len : {len(notes)}")

            note_detail_task = [self.get_note_by_id(note['thread_id']) for note in notes]
            notes = await asyncio.gather(*note_detail_task)
            if callback:
                await callback(notes)
            await asyncio.sleep(crawl_interval)
            result.extend(notes)
            page_number += 1
            total_get_count += page_per_count
        return result
