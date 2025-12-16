# Disclaimer: This code is for educational and research purposes only. Users must adhere to the following principles:
# 1. Not for any commercial use.
# 2. Comply with the target platform's terms of service and robots.txt.
# 3. Do not perform large-scale scraping or disrupt platform operations.
# 4. Reasonably control request frequency to avoid unnecessary burden on the target platform.
# 5. Not for any illegal or improper purposes.
#
# For detailed license terms, please refer to the LICENSE file in the project root directory.
# Using this code indicates your agreement to the above principles and all terms in the LICENSE.  


from enum import Enum
from typing import NamedTuple

from constant import zhihu as zhihu_constant


class SearchTime(Enum):
    """
    Search time range
    """
    DEFAULT = ""  # Unlimited time
    ONE_DAY = "a_day"  # Within a day
    ONE_WEEK = "a_week"  # Within a week
    ONE_MONTH = "a_month"  # Within a month
    THREE_MONTH = "three_months"  # Within three months
    HALF_YEAR = "half_a_year"  # Within half a year
    ONE_YEAR = "a_year"  # Within a year


class SearchType(Enum):
    """
    Search result type
    """
    DEFAULT = ""  # Unlimited type
    ANSWER = zhihu_constant.ANSWER_NAME  # Only answers
    ARTICLE = zhihu_constant.ARTICLE_NAME  # Only articles
    VIDEO = zhihu_constant.VIDEO_NAME  # Only videos


class SearchSort(Enum):
    """
    Search result sorting
    """
    DEFAULT = ""  # Comprehensive sorting
    UPVOTED_COUNT = "upvoted_count"  # Most upvoted
    CREATE_TIME = "created_time"  # Newest published
