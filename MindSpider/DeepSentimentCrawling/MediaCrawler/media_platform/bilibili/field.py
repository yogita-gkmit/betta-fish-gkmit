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
# @Time    : 2023/12/3 16:20
# @Desc    :

from enum import Enum


class SearchOrderType(Enum):
    # Comprehensive sort
    DEFAULT = ""

    # Most clicks
    MOST_CLICK = "click"

    # Latest publish
    LAST_PUBLISH = "pubdate"

    # Most danmaku
    MOST_DANMU = "dm"

    # Most bookmarks
    MOST_MARK = "stow"


class CommentOrderType(Enum):
    # By popularity only
    DEFAULT = 0

    # By popularity + by time
    MIXED = 1

    # By time
    TIME = 2
