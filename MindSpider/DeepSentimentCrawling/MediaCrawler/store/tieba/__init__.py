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
from typing import List

from model.m_baidu_tieba import TiebaComment, TiebaCreator, TiebaNote
from var import source_keyword_var

from ._store_impl import *


class TieBaStoreFactory:
    STORES = {
        "csv": TieBaCsvStoreImplement,
        "db": TieBaDbStoreImplement,
        "json": TieBaJsonStoreImplement,
        "sqlite": TieBaSqliteStoreImplement,
        "postgresql": TieBaDbStoreImplement,
    }

    @staticmethod
    def create_store() -> AbstractStore:
        store_class = TieBaStoreFactory.STORES.get(config.SAVE_DATA_OPTION)
        if not store_class:
            raise ValueError(
                "[TieBaStoreFactory.create_store] Invalid save option only supported csv or db or json or sqlite or postgresql ...")
        return store_class()


async def batch_update_tieba_notes(note_list: List[TiebaNote]):
    """
    Batch update tieba notes
    Args:
        note_list:

    Returns:

    """
    if not note_list:
        return
    for note_item in note_list:
        await update_tieba_note(note_item)


async def update_tieba_note(note_item: TiebaNote):
    """
    Add or Update tieba note
    Args:
        note_item:

    Returns:

    """
    note_item.source_keyword = source_keyword_var.get()
    save_note_item = note_item.model_dump()
    save_note_item.update({"last_modify_ts": utils.get_current_timestamp()})
    utils.logger.info(f"[store.tieba.update_tieba_note] tieba note: {save_note_item}")

    await TieBaStoreFactory.create_store().store_content(save_note_item)


async def batch_update_tieba_note_comments(note_id: str, comments: List[TiebaComment]):
    """
    Batch update tieba note comments
    Args:
        note_id:
        comments:

    Returns:

    """
    if not comments:
        return
    for comment_item in comments:
        await update_tieba_note_comment(note_id, comment_item)


async def update_tieba_note_comment(note_id: str, comment_item: TiebaComment):
    """
    Update tieba note comment
    Args:
        note_id:
        comment_item:

    Returns:

    """
    save_comment_item = comment_item.model_dump()
    save_comment_item.update({"last_modify_ts": utils.get_current_timestamp()})
    utils.logger.info(f"[store.tieba.update_tieba_note_comment] tieba note id: {note_id} comment:{save_comment_item}")
    await TieBaStoreFactory.create_store().store_comment(save_comment_item)


async def save_creator(user_info: TiebaCreator):
    """
    Save creator information to local
    Args:
        user_info:

    Returns:

    """
    local_db_item = user_info.model_dump()
    local_db_item["last_modify_ts"] = utils.get_current_timestamp()
    utils.logger.info(f"[store.tieba.save_creator] creator:{local_db_item}")
    await TieBaStoreFactory.create_store().store_creator(local_db_item)
