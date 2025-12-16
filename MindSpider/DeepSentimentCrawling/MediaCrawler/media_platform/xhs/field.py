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


class FeedType(Enum):
    # Recommend
    RECOMMEND = "homefeed_recommend"
    # Fashion
    FASION = "homefeed.fashion_v3"
    # Food
    FOOD = "homefeed.food_v3"
    # Cosmetics
    COSMETICS = "homefeed.cosmetics_v3"
    # Movie
    MOVIE = "homefeed.movie_and_tv_v3"
    # Career
    CAREER = "homefeed.career_v3"
    # Emotion
    EMOTION = "homefeed.love_v3"
    # House
    HOURSE = "homefeed.household_product_v3"
    # Game
    GAME = "homefeed.gaming_v3"
    # Travel
    TRAVEL = "homefeed.travel_v3"
    # Fitness
    FITNESS = "homefeed.fitness_v3"


class NoteType(Enum):
    NORMAL = "normal"
    VIDEO = "video"


class SearchSortType(Enum):
    """search sort type"""
    # default
    GENERAL = "general"
    # most popular
    MOST_POPULAR = "popularity_descending"
    # Latest
    LATEST = "time_descending"


class SearchNoteType(Enum):
    """search note type
    """
    # default
    ALL = 0
    # only video
    VIDEO = 1
    # only image
    IMAGE = 2


class Note(NamedTuple):
    """note tuple"""
    note_id: str
    title: str
    desc: str
    type: str
    user: dict
    img_urls: list
    video_url: str
    tag_list: list
    at_user_list: list
    collected_count: str
    comment_count: str
    liked_count: str
    share_count: str
    time: int
    last_update_time: int
