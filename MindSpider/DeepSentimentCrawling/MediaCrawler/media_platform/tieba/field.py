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


class SearchSortType(Enum):
    """search sort type"""
    # Descending by time
    TIME_DESC = "1"
    # Ascending by time
    TIME_ASC = "0"
    # Order by relevance
    RELEVANCE_ORDER = "2"


class SearchNoteType(Enum):
    # Only view main threads
    MAIN_THREAD = "1"
    # Mixed mode (posts + replies)
    FIXED_THREAD = "0"
