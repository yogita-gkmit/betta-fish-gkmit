# Disclaimer: This code is for learning and research purposes only. Users must adhere to the following principles:
# 1. Do not use for any commercial purposes.
# 2. Comply with the target platform's terms of use and robots.txt rules.
# 3. Do not perform large-scale crawling or disrupt platform operations.
# 4. Reasonably control request frequency to avoid unnecessary burden on target platforms.
# 5. Do not use for any illegal or improper purposes.
#
# Please refer to the LICENSE file in the project root for detailed license terms.
# Using this code indicates your agreement to abide by the above principles and all terms in the LICENSE.

from dotenv import load_dotenv
load_dotenv()

# Basic Configuration
PLATFORM = "toi"  # Platform，xhs | dy | ks | bili | wb | tieba | zhihu
KEYWORDS = "India,AI" 
LOGIN_TYPE = "qrcode"  # qrcode or phone or cookie
COOKIES = ""
CRAWLER_TYPE = "search"  # Crawler type, search(keyword search) | detail(post details)| creator(creator homepage data)

# Whether to enable IP proxy
ENABLE_IP_PROXY = False

# Number of proxy IPs in pool
IP_PROXY_POOL_COUNT = 2

# Proxy IP provider name
IP_PROXY_PROVIDER_NAME = "kuaidaili"  # kuaidaili | wandouhttp

# Set to True to not open browser (headless browser)
# Set to False to open a browser
# If Xiaohongshu login fails repeatedly with QR code, open browser to manually pass sliding captcha
# If Douyin login fails repeatedly, open browser to see if phone verification appeared after QR scan, pass it manually if so.
# If Douyin login fails repeatedly, open browser to see if phone verification appeared after QR scan, pass it manually if so.
HEADLESS = False

# Whether to save login state
SAVE_LOGIN_STATE = True

# ==================== CDP (Chrome DevTools Protocol) Config ====================
# Whether to enable CDP mode - Use user's existing Chrome/Edge browser for crawling, providing better anti-detection capability
# If enabled, will automatically detect and start user's Chrome/Edge browser, controlled via CDP protocol
# This method uses real browser environment, including user extensions, cookies and settings, greatly reducing detection risk
ENABLE_CDP_MODE = True

# CDP debug port, used for communicating with browser
# If port is occupied, system will automatically try next available port
CDP_DEBUG_PORT = 9222

# Custom browser path (optional)
# If empty, system will automatically detect Chrome/Edge installation path
# Windows example: "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
# macOS example: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
CUSTOM_BROWSER_PATH = ""

# Whether to enable headless mode in CDP mode
# Note: Even if set to True, some anti-detection features may not work well in headless mode
CDP_HEADLESS = False

# Browser launch timeout (seconds)
BROWSER_LAUNCH_TIMEOUT = 30

# Whether to automatically close browser when program ends
# Set to False to keep browser running for debugging
AUTO_CLOSE_BROWSER = True

# Data save option config, supports five types: csv, db, json, sqlite, postgresql. Best to save to DB for deduplication.
SAVE_DATA_OPTION = "postgresql"  # csv or db or json or sqlite or postgresql

# User browser cache file config
USER_DATA_DIR = "%s_user_data_dir"  # %s will be replaced by platform name

# Crawl start page, defaults to 1
START_PAGE = 1

# Crawl video/post quantity control
CRAWLER_MAX_NOTES_COUNT = 9999999

# Concurrent crawler quantity control
MAX_CONCURRENCY_NUM = 1

# Whether to enable media crawling mode (including images or video resources), default disabled
ENABLE_GET_MEIDAS = False

# Whether to enable comment crawling mode, default enabled
ENABLE_GET_COMMENTS = True

# Level 1 comment quantity control (single video/post)
CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES = 20

# Whether to enable level 2 comment crawling mode, default disabled
# Old version project used db, need to refer to schema/tables.sql line 287 to add table fields
ENABLE_GET_SUB_COMMENTS = False

# Wordcloud related
# Whether to enable generating comment wordcloud
ENABLE_GET_WORDCLOUD = False
# Custom words and their grouping
# Rule: xx:yy where xx is custom word, yy is group name for xx.
CUSTOM_WORDS = {
    "2000s": "Year",  # Identify "2000s" as a unit
    "HighFreqWord": "Term",  # Example custom word
}

# Stop (forbidden) words file path
STOP_WORDS_FILE = "./docs/hit_stopwords.txt"

# Chinese font file path
FONT_PATH = "./docs/STZHONGS.TTF"

# Crawl interval time
CRAWLER_MAX_SLEEP_SEC = 2

from .bilibili_config import *
from .xhs_config import *
from .dy_config import *
from .ks_config import *
from .weibo_config import *
from .tieba_config import *
from .zhihu_config import *
from .times_of_india_config import *
from .glassdoor_config import *
