# Declaration: This code is for learning and research purposes only. Users must adhere to the following principles:
# 1. Must not be used for any commercial purposes.
# 2. When using, comply with the target platform's terms of service and robots.txt rules.
# 3. Do not perform large-scale crawling or cause operational disruption to the platform.
# 4. Reasonably control request frequency to avoid unnecessary load on the target platform.
# 5. Must not be used for any illegal or improper purposes.
#   
# For detailed license terms, see the LICENSE file in the project root.
# Using this code indicates your agreement to comply with the above principles and all terms in the LICENSE.


# -*- coding: utf-8 -*-
from typing import List

import config
from base.base_crawler import AbstractStore
from model.m_zhihu import ZhihuComment, ZhihuContent, ZhihuCreator
from ._store_impl import (ZhihuCsvStoreImplement,
                                          ZhihuDbStoreImplement,
                                          ZhihuJsonStoreImplement,
                                          ZhihuSqliteStoreImplement)
from tools import utils
from var import source_keyword_var


class ZhihuStoreFactory:
    STORES = {
        "csv": ZhihuCsvStoreImplement,
        "db": ZhihuDbStoreImplement,
        "json": ZhihuJsonStoreImplement,
        "sqlite": ZhihuSqliteStoreImplement,
        "postgresql": ZhihuDbStoreImplement,
    }

    @staticmethod
    def create_store() -> AbstractStore:
        store_class = ZhihuStoreFactory.STORES.get(config.SAVE_DATA_OPTION)
        if not store_class:
            raise ValueError("[ZhihuStoreFactory.create_store] Invalid save option only supported csv or db or json or sqlite or postgresql ...")
        return store_class()

async def batch_update_zhihu_contents(contents: List[ZhihuContent]):
    """
Batch update Zhihu contents.

Args:
    contents (List[ZhihuContent]): List of ZhihuContent objects to update.

Returns:
    None
"""
    if not contents:
        return

    for content_item in contents:
        await update_zhihu_content(content_item)

async def update_zhihu_content(content_item: ZhihuContent):
    """
    Update a Zhihu content.
    Args:
        content_item:

    Returns:

    """
    content_item.source_keyword = source_keyword_var.get()
    local_db_item = content_item.model_dump()
    local_db_item.update({"last_modify_ts": utils.get_current_timestamp()})
    utils.logger.info(f"[store.zhihu.update_zhihu_content] zhihu content: {local_db_item}")
    await ZhihuStoreFactory.create_store().store_content(local_db_item)



async def batch_update_zhihu_note_comments(comments: List[ZhihuComment]):
    """
Batch update Zhihu content comments.

Args:
    comments (List[ZhihuComment]): List of ZhihuComment objects to update.

Returns:
    None
"""
    if not comments:
        return
    
    for comment_item in comments:
        await update_zhihu_content_comment(comment_item)


async def update_zhihu_content_comment(comment_item: ZhihuComment):
    """
Update a Zhihu content comment.

Args:
    comment_item (ZhihuComment): The comment object to update.

Returns:
    None
"""
    local_db_item = comment_item.model_dump()
    local_db_item.update({"last_modify_ts": utils.get_current_timestamp()})
    utils.logger.info(f"[store.zhihu.update_zhihu_note_comment] zhihu content comment:{local_db_item}")
    await ZhihuStoreFactory.create_store().store_comment(local_db_item)


async def save_creator(creator: ZhihuCreator):
    """
Save Zhihu creator information.

Args:
    creator (ZhihuCreator): The creator object to save.

Returns:
    None
"""
    if not creator:
        return
    local_db_item = creator.model_dump()
    local_db_item.update({"last_modify_ts": utils.get_current_timestamp()})
    await ZhihuStoreFactory.create_store().store_creator(local_db_item)