# -*- coding: utf-8 -*-
# Disclaimer: This code is for educational and research purposes only. Users must adhere to the following principles:
# 1. Not for any commercial use.
# 2. Comply with the target platform's terms of service and robots.txt.
# 3. Do not perform large-scale scraping or disrupt platform operations.
# 4. Reasonably control request frequency to avoid unnecessary burden on the target platform.
# 5. Not for any illegal or improper purposes.
#
# For detailed license terms, please refer to the LICENSE file in the project root directory.
# Using this code indicates your agreement to the above principles and all terms in the LICENSE.

import hashlib
import base64
import json
from typing import Any

def _build_c(e: Any, a: Any) -> str:
    c = str(e)
    if isinstance(a, (dict, list)):
        c += json.dumps(a, separators=(",", ":"), ensure_ascii=False)
    elif isinstance(a, str):
        c += a
    # Other types not concatenated
    return c


# ---------------------------
# p.Pu = MD5(c) => hex 小写
# ---------------------------
def _md5_hex(s: str) -> str:
    return hashlib.md5(s.encode("utf-8")).hexdigest()



# ============================================================
# ============================================================
# Playwright Version (Async): Pass page (Page Object)
#    Internal use page.evaluate('window.mnsv2(...)')
# ============================================================
async def seccore_signv2_playwright(
    page,  # Playwright Page
    e: Any,
    a: Any,
) -> str:
    """
    Use Playwright's page.evaluate to call window.mnsv2(c, d) to generate signature.
    Ensure window.mnsv2 already exists in page context (e.g. target site script injected).

    Usage:
      s = await page.evaluate("(c, d) => window.mnsv2(c, d)", c, d)
    """
    c = _build_c(e, a)
    d = _md5_hex(c)

    # Call window.mnsv2 in browser context
    s = await page.evaluate("(c, d) => window.mnsv2(c, d)", [c, d])
    f = {
        "x0": "4.2.6",
        "x1": "xhs-pc-web",
        "x2": "Mac OS",
        "x3": s,
        "x4": a,
    }
    payload = json.dumps(f, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    token = "XYS_" + base64.b64encode(payload).decode("ascii")
    print(token)
    return token