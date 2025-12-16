# Declaration: This code is for learning and research purposes only. Users must adhere to the following principles:  
# 1. Do not use for any commercial purposes.  
# 2. Comply with the target platform's terms of use and robots.txt rules.  
# 3. Do not perform large-scale crawling or disrupt platform operations.  
# 4. Reasonably control request frequency to avoid unnecessary burden on the target platform.   
# 5. Do not use for any illegal or improper purposes.
#   
# For detailed license terms, please refer to the LICENSE file in the project root directory.  
# Using this code indicates your agreement to abide by the above principles and all terms in the LICENSE.  


from enum import Enum


class SearchChannelType(Enum):
    """search channel type"""
    GENERAL = "aweme_general"  # General
    VIDEO = "aweme_video_web"  # Video
    USER = "aweme_user_web"  # User
    LIVE = "aweme_live"  # Live


class SearchSortType(Enum):
    """search sort type"""
    GENERAL = 0  # General Sort
    MOST_LIKE = 1  # Most Likes
    LATEST = 2  # Latest Publish

class PublishTimeType(Enum):
    """publish time type"""
    UNLIMITED = 0  # Unlimited
    ONE_DAY = 1  # One Day
    ONE_WEEK = 7  # One Week
    SIX_MONTH = 180  # Six Months
