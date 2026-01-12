# Declaration: This code is for learning and research purposes only. Users must adhere to the following principles:  
# 1. Do not use for any commercial purposes.  
# 2. Comply with the target platform's terms of use and robots.txt rules.  
# 3. Do not perform large-scale crawling or disrupt platform operations.  
# 4. Reasonably control request frequency to avoid unnecessary burden on the target platform.   
# 5. Do not use for any illegal or improper purposes.
#   
# For detailed license terms, please refer to the LICENSE file in the project root directory.  
# Using this code indicates your agreement to abide by the above principles and all terms in the LICENSE.  


# -*- coding: utf-8 -*-
# @Author  : relakkes@gmail.com
# @Name    : Programmer Ajiang - Relakkes
# @Time    : 2024/6/10 02:24
# @Desc    : Get a_bogus parameter, for learning and exchange use only, do not use for commercial purposes, contact author to delete if infringement occurs

import random
import re
from typing import Optional

import execjs
from playwright.async_api import Page

from model.m_douyin import VideoUrlInfo, CreatorUrlInfo
from tools.crawler_util import extract_url_params_to_dict

douyin_sign_obj = execjs.compile(open('libs/douyin.js', encoding='utf-8-sig').read())

def get_web_id():
    """
    Generate random webid
    Returns:

    """

    def e(t):
        if t is not None:
            return str(t ^ (int(16 * random.random()) >> (t // 4)))
        else:
            return ''.join(
                [str(int(1e7)), '-', str(int(1e3)), '-', str(int(4e3)), '-', str(int(8e3)), '-', str(int(1e11))]
            )

    web_id = ''.join(
        e(int(x)) if x in '018' else x for x in e(None)
    )
    return web_id.replace('-', '')[:19]



async def get_a_bogus(url: str, params: str, post_data: dict, user_agent: str, page: Page = None):
    """
    Get a_bogus parameter, currently does not support post request type signature
    """
    return get_a_bogus_from_js(url, params, user_agent)

def get_a_bogus_from_js(url: str, params: str, user_agent: str):
    """
    Get a_bogus parameter through js
    Args:
        url:
        params:
        user_agent:

    Returns:

    """
    sign_js_name = "sign_datail"
    if "/reply" in url:
        sign_js_name = "sign_reply"
    return douyin_sign_obj.call(sign_js_name, params, user_agent)



async def get_a_bogus_from_playright(params: str, post_data: dict, user_agent: str, page: Page):
    """
    Get a_bogus parameter through playwright
    Playwright version is deprecated/failed
    Returns:

    """
    if not post_data:
        post_data = ""
    a_bogus = await page.evaluate(
        "([params, post_data, ua]) => window.bdms.init._v[2].p[42].apply(null, [0, 1, 8, params, post_data, ua])",
        [params, post_data, user_agent])

    return a_bogus


def parse_video_info_from_url(url: str) -> VideoUrlInfo:
    """
    Parse video ID from Douyin video URL
    Supports the following formats:
    1. Normal video link: https://www.douyin.com/video/7525082444551310602
    2. Link with modal_id parameter:
       - https://www.douyin.com/user/MS4wLjABAAAATJPY7LAlaa5X-c8uNdWkvz0jUGgpw4eeXIwu_8BhvqE?modal_id=7525082444551310602
       - https://www.douyin.com/root/search/python?modal_id=7471165520058862848
    3. Short link: https://v.douyin.com/iF12345ABC/ (Needs client parsing)
    4. Pure ID: 7525082444551310602

    Args:
        url: Douyin video link or ID
    Returns:
        VideoUrlInfo: Object containing video ID
    """
    # If it is a pure numeric ID, return directly
    if url.isdigit():
        return VideoUrlInfo(aweme_id=url, url_type="normal")

    # Check if it is a short link (v.douyin.com)
    if "v.douyin.com" in url or url.startswith("http") and len(url) < 50 and "video" not in url:
        return VideoUrlInfo(aweme_id="", url_type="short")  # Needs parsing by client

    # Try to extract modal_id from URL parameters
    params = extract_url_params_to_dict(url)
    modal_id = params.get("modal_id")
    if modal_id:
        return VideoUrlInfo(aweme_id=modal_id, url_type="modal")

    # Extract ID from standard video URL: /video/digit
    video_pattern = r'/video/(\d+)'
    match = re.search(video_pattern, url)
    if match:
        aweme_id = match.group(1)
        return VideoUrlInfo(aweme_id=aweme_id, url_type="normal")

    raise ValueError(f"Unable to parse video ID from URL: {url}")


def parse_creator_info_from_url(url: str) -> CreatorUrlInfo:
    """
    Parse creator ID (sec_user_id) from Douyin creator homepage URL
    Supports the following formats:
    1. Creator homepage: https://www.douyin.com/user/MS4wLjABAAAATJPY7LAlaa5X-c8uNdWkvz0jUGgpw4eeXIwu_8BhvqE?from_tab_name=main
    2. Pure ID: MS4wLjABAAAATJPY7LAlaa5X-c8uNdWkvz0jUGgpw4eeXIwu_8BhvqE

    Args:
        url: Douyin creator homepage link or sec_user_id
    Returns:
        CreatorUrlInfo: Object containing creator ID
    """
    # If it is pure ID format (usually starts with MS4wLjABAAAA), return directly
    if url.startswith("MS4wLjABAAAA") or (not url.startswith("http") and "douyin.com" not in url):
        return CreatorUrlInfo(sec_user_id=url)

    # Extract sec_user_id from creator homepage URL: /user/xxx
    user_pattern = r'/user/([^/?]+)'
    match = re.search(user_pattern, url)
    if match:
        sec_user_id = match.group(1)
        return CreatorUrlInfo(sec_user_id=sec_user_id)

    raise ValueError(f"Unable to parse creator ID from URL: {url}")


if __name__ == '__main__':
    # Test video URL parsing
    print("=== Video URL Parsing Test ===")
    test_urls = [
        "https://www.douyin.com/video/7525082444551310602",
        "https://www.douyin.com/user/MS4wLjABAAAATJPY7LAlaa5X-c8uNdWkvz0jUGgpw4eeXIwu_8BhvqE?from_tab_name=main&modal_id=7525082444551310602",
        "https://www.douyin.com/root/search/python?aid=b733a3b0-4662-4639-9a72-c2318fba9f3f&modal_id=7471165520058862848&type=general",
        "7525082444551310602",
    ]
    for url in test_urls:
        try:
            result = parse_video_info_from_url(url)
            print(f"✓ URL: {url[:80]}...")
            print(f"  Result: {result}\n")
        except Exception as e:
            print(f"✗ URL: {url}")
            print(f"  Error: {e}\n")

    # Test creator URL parsing
    print("=== Creator URL Parsing Test ===")
    test_creator_urls = [
        "https://www.douyin.com/user/MS4wLjABAAAATJPY7LAlaa5X-c8uNdWkvz0jUGgpw4eeXIwu_8BhvqE?from_tab_name=main",
        "MS4wLjABAAAATJPY7LAlaa5X-c8uNdWkvz0jUGgpw4eeXIwu_8BhvqE",
    ]
    for url in test_creator_urls:
        try:
            result = parse_creator_info_from_url(url)
            print(f"✓ URL: {url[:80]}...")
            print(f"  Result: {result}\n")
        except Exception as e:
            print(f"✗ URL: {url}")
            print(f"  Error: {e}\n")

