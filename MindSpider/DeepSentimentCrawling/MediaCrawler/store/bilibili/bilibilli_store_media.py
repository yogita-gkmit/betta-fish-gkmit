# Disclaimer: This code is for educational and research purposes only. Users must adhere to the following principles:
# 1. Not for any commercial use.
# 2. Comply with the target platform's terms of service and robots.txt.
# 3. Do not perform large-scale scraping or disrupt platform operations.
# 4. Reasonably control request frequency to avoid unnecessary burden on the target platform.
# 5. Not for any illegal or improper purposes.
#
# For detailed license terms, please refer to the LICENSE file in the project root directory.
# Using this code indicates your agreement to the above principles and all terms in the LICENSE.

# -*- coding: utf-8 -*-
# @Author  : helloteemo
# @Time    : 2024/7/12 20:01
# @Desc    : bilibili media storage
import pathlib
from typing import Dict

import aiofiles

from base.base_crawler import AbstractStoreImage, AbstractStoreVideo
from tools import utils


class BilibiliVideo(AbstractStoreVideo):
    video_store_path: str = "data/bili/videos"

    async def store_video(self, video_content_item: Dict):
        """
        store content
        
        Args:
            video_content_item:

        Returns:

        """
        await self.save_video(video_content_item.get("aid"), video_content_item.get("video_content"), video_content_item.get("extension_file_name"))

    def make_save_file_name(self, aid: str, extension_file_name: str) -> str:
        """
        make save file name by store type
        
        Args:
            aid: aid
            extension_file_name: video filename with extension
            
        Returns:

        """
        return f"{self.video_store_path}/{aid}/{extension_file_name}"

    async def save_video(self, aid: int, video_content: str, extension_file_name="mp4"):
        """
        save video to local
        
        Args:
            aid: aid
            video_content: video content
            extension_file_name: video filename with extension

        Returns:

        """
        pathlib.Path(self.video_store_path + "/" + str(aid)).mkdir(parents=True, exist_ok=True)
        save_file_name = self.make_save_file_name(str(aid), extension_file_name)
        async with aiofiles.open(save_file_name, 'wb') as f:
            await f.write(video_content)
            utils.logger.info(f"[BilibiliVideoImplement.save_video] save save_video {save_file_name} success ...")
