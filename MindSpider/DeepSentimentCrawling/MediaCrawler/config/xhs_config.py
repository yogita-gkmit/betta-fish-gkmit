# -*- coding: utf-8 -*-
# Declaration: This code is for learning and research purposes only. Users must adhere to the following principles:
# 1. Do not use for any commercial purposes.
# 2. Comply with the target platform's terms of use and robots.txt rules.
# 3. Do not perform large-scale crawling or disrupt platform operations.
# 4. Reasonably control request frequency to avoid unnecessary burden on the target platform.
# 5. Do not use for any illegal or improper purposes.
#
# For detailed license terms, please refer to the LICENSE file in the project root directory.
# Using this code indicates your agreement to abide by the above principles and all terms in the LICENSE.


# Xiaohongshu platform configuration

# Sort type, specific enum values in media_platform/xhs/field.py
SORT_TYPE = "popularity_descending"

# Specify note URL list, must carry xsec_token parameter
XHS_SPECIFIED_NOTE_URL_LIST = [
    "https://www.xiaohongshu.com/explore/68f99f6d0000000007033fcf?xsec_token=ABZEzjuN2fPjKF9EcMsCCxfbt3IBRsFZldGFoCJbdDmXI=&xsec_source=pc_feed"
    # ........................
]

# Specify creator URL list (supports full URL or pure ID)
# Supported formats:
# 1. Full creator profile URL (with xsec_token and xsec_source parameters): "https://www.xiaohongshu.com/user/profile/5eb8e1d400000000010075ae?xsec_token=AB1nWBKCo1vE2HEkfoJUOi5B6BE5n7wVrbdpHoWIj5xHw=&xsec_source=pc_feed"
# 2. Pure user_id: "63e36c9a000000002703502b"
XHS_CREATOR_ID_LIST = [
    "https://www.xiaohongshu.com/user/profile/5eb8e1d400000000010075ae?xsec_token=AB1nWBKCo1vE2HEkfoJUOi5B6BE5n7wVrbdpHoWIj5xHw=&xsec_source=pc_feed",
    "63e36c9a000000002703502b",    
    # ........................
]
