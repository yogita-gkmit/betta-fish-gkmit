"""
Public opinion big data aggregation main table ORM model (automatically generated from the original tables.sql structure, corresponding to bulk search and content insertion for large tables).

Data model definition location:
- MindSpider/DeepSentimentCrawling/MediaCrawler/schema/tables.sql  # Source file for main table structure
- This module (automatically maps SQL tables, adapts to MySQL/PostgreSQL, manual completion of comments, unique/index additions recommended)
- MindSpider/schema/models_sa.py  # Base definition source

This module is based on MindSpider\DeepSentimentCrawling\MediaCrawler\database\models.py
"""

from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, String, BigInteger, Text, ForeignKey
from typing import Optional

# Use Base from models_sa to ensure all tables share the same metadata, allowing proper foreign key references.
from models_sa import Base

class BilibiliVideo(Base):
    __tablename__ = "bilibili_video"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    video_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True, unique=True)
    video_url: Mapped[str] = mapped_column(Text, nullable=False)
    user_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
    nickname: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    avatar: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    liked_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    add_ts: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    last_modify_ts: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    video_type: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    desc: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    create_time: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
    disliked_count: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    video_play_count: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    video_favorite_count: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    video_share_count: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    video_coin_count: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    video_danmaku: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    video_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    video_cover_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_keyword: Mapped[Optional[str]] = mapped_column(Text, default='', nullable=True)
    topic_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("daily_topics.topic_id", ondelete="SET NULL"), nullable=True)
    crawling_task_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("crawling_tasks.task_id", ondelete="SET NULL"), nullable=True)

class BilibiliVideoComment(Base):
    __tablename__ = "bilibili_video_comment"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    nickname: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sex: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sign: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    avatar: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    add_ts: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    last_modify_ts: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    comment_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
    video_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    create_time: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    sub_comment_count: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    parent_comment_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    like_count: Mapped[Optional[str]] = mapped_column(Text, default='0', nullable=True)


class BilibiliUpInfo(Base):
    __tablename__ = "bilibili_up_info"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
    nickname: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sex: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sign: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    avatar: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    add_ts: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    last_modify_ts: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    total_fans: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_liked: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    user_rank: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_official: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class BilibiliContactInfo(Base):
    __tablename__ = "bilibili_contact_info"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    up_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
    fan_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
    up_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    fan_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    up_sign: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    fan_sign: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    up_avatar: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    fan_avatar: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    add_ts: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    last_modify_ts: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)


class BilibiliUpDynamic(Base):
    __tablename__ = "bilibili_up_dynamic"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dynamic_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    user_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    type: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    pub_ts: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    total_comments: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_forwards: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_liked: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    add_ts: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    last_modify_ts: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)


class DouyinAweme(Base):
    __tablename__ = "douyin_aweme"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    sec_uid: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    short_user_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    user_unique_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    nickname: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    avatar: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    user_signature: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ip_location: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    add_ts: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    last_modify_ts: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    aweme_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
    aweme_type: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    desc: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    create_time: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
    liked_count: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    comment_count: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    share_count: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    collected_count: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    aweme_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cover_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    video_download_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    music_download_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    note_download_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_keyword: Mapped[Optional[str]] = mapped_column(Text, default='', nullable=True)
    topic_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("daily_topics.topic_id", ondelete="SET NULL"), nullable=True)
    crawling_task_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("crawling_tasks.task_id", ondelete="SET NULL"), nullable=True)

class DouyinAwemeComment(Base):
    __tablename__ = "douyin_aweme_comment"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    sec_uid: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    short_user_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    user_unique_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    nickname: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    avatar: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    user_signature: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ip_location: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    add_ts: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    last_modify_ts: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    comment_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
    aweme_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    create_time: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    sub_comment_count: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    parent_comment_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    like_count: Mapped[Optional[str]] = mapped_column(Text, default='0', nullable=True)
    pictures: Mapped[Optional[str]] = mapped_column(Text, default='', nullable=True)


class DyCreator(Base):
    __tablename__ = "dy_creator"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    nickname: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    avatar: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ip_location: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    add_ts: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    last_modify_ts: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    desc: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    gender: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    follows: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    fans: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    interaction: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    videos_count: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)


class KuaishouVideo(Base):
    __tablename__ = "kuaishou_video"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    nickname: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    avatar: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    add_ts: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    last_modify_ts: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    video_id: Mapped[Optional[str]] = mapped_column(String(255), index=True, nullable=True)
    video_type: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    desc: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    create_time: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
    liked_count: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    viewd_count: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    video_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    video_cover_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    video_play_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_keyword: Mapped[Optional[str]] = mapped_column(Text, default='', nullable=True)
    topic_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("daily_topics.topic_id", ondelete="SET NULL"), nullable=True)
    crawling_task_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("crawling_tasks.task_id", ondelete="SET NULL"), nullable=True)

class KuaishouVideoComment(Base):
    __tablename__ = "kuaishou_video_comment"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    nickname: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    avatar: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    add_ts: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    last_modify_ts: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    comment_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
    video_id: Mapped[Optional[str]] = mapped_column(String(255), index=True, nullable=True)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    create_time: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    sub_comment_count: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

class WeiboNote(Base):
    __tablename__ = "weibo_note"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    nickname: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    avatar: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    gender: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    profile_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ip_location: Mapped[Optional[str]] = mapped_column(Text, default='', nullable=True)
    add_ts: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    last_modify_ts: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    note_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    create_time: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
    create_date_time: Mapped[Optional[str]] = mapped_column(String(255), index=True, nullable=True)
    liked_count: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    comments_count: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    shared_count: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    note_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_keyword: Mapped[Optional[str]] = mapped_column(Text, default='', nullable=True)
    topic_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("daily_topics.topic_id", ondelete="SET NULL"), nullable=True)
    crawling_task_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("crawling_tasks.task_id", ondelete="SET NULL"), nullable=True)

class WeiboNoteComment(Base):
    __tablename__ = "weibo_note_comment"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    nickname: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    avatar: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    gender: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    profile_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ip_location: Mapped[Optional[str]] = mapped_column(Text, default='', nullable=True)
    add_ts: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    last_modify_ts: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    comment_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
    note_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    create_time: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    create_date_time: Mapped[Optional[str]] = mapped_column(String(255), index=True, nullable=True)
    comment_like_count: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sub_comment_count: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    parent_comment_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)


class WeiboCreator(Base):
    __tablename__ = "weibo_creator"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    nickname: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    avatar: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ip_location: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    add_ts: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    last_modify_ts: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    desc: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    gender: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    follows: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    fans: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tag_list: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class XhsCreator(Base):
    __tablename__ = "xhs_creator"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    nickname: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    avatar: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ip_location: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    add_ts: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    last_modify_ts: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    desc: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    gender: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    follows: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    fans: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    interaction: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tag_list: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class XhsNote(Base):
    __tablename__ = "xhs_note"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    nickname: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    avatar: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ip_location: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    add_ts: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    last_modify_ts: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    note_id: Mapped[Optional[str]] = mapped_column(String(255), index=True, nullable=True)
    type: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    desc: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    video_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    time: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
    last_update_time: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    liked_count: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    collected_count: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    comment_count: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    share_count: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    image_list: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tag_list: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    note_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_keyword: Mapped[Optional[str]] = mapped_column(Text, default='', nullable=True)
    xsec_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    topic_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("daily_topics.topic_id", ondelete="SET NULL"), nullable=True)
    crawling_task_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("crawling_tasks.task_id", ondelete="SET NULL"), nullable=True)


class XhsNoteComment(Base):
    __tablename__ = "xhs_note_comment"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    nickname: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    avatar: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ip_location: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    add_ts: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    last_modify_ts: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    comment_id: Mapped[Optional[str]] = mapped_column(String(255), index=True, nullable=True)
    create_time: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
    note_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sub_comment_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    pictures: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    parent_comment_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    like_count: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

class TiebaNote(Base):
    __tablename__ = "tieba_note"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    note_id: Mapped[Optional[str]] = mapped_column(String(644), index=True, nullable=True)
    title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    desc: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    note_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    publish_time: Mapped[Optional[str]] = mapped_column(String(255), index=True, nullable=True)
    user_link: Mapped[Optional[str]] = mapped_column(Text, default='', nullable=True)
    user_nickname: Mapped[Optional[str]] = mapped_column(Text, default='', nullable=True)
    user_avatar: Mapped[Optional[str]] = mapped_column(Text, default='', nullable=True)
    tieba_id: Mapped[Optional[str]] = mapped_column(String(255), default='', nullable=True)
    tieba_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tieba_link: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    total_replay_num: Mapped[Optional[int]] = mapped_column(Integer, default=0, nullable=True)
    total_replay_page: Mapped[Optional[int]] = mapped_column(Integer, default=0, nullable=True)
    ip_location: Mapped[Optional[str]] = mapped_column(Text, default='', nullable=True)
    add_ts: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    last_modify_ts: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    source_keyword: Mapped[Optional[str]] = mapped_column(Text, default='', nullable=True)
    topic_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("daily_topics.topic_id", ondelete="SET NULL"), nullable=True)
    crawling_task_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("crawling_tasks.task_id", ondelete="SET NULL"), nullable=True)

class TiebaComment(Base):
    __tablename__ = "tieba_comment"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    comment_id: Mapped[Optional[str]] = mapped_column(String(255), index=True, nullable=True)
    parent_comment_id: Mapped[Optional[str]] = mapped_column(String(255), default='', nullable=True)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    user_link: Mapped[Optional[str]] = mapped_column(Text, default='', nullable=True)
    user_nickname: Mapped[Optional[str]] = mapped_column(Text, default='', nullable=True)
    user_avatar: Mapped[Optional[str]] = mapped_column(Text, default='', nullable=True)
    tieba_id: Mapped[Optional[str]] = mapped_column(String(255), default='', nullable=True)
    tieba_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tieba_link: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    publish_time: Mapped[Optional[str]] = mapped_column(String(255), index=True, nullable=True)
    ip_location: Mapped[Optional[str]] = mapped_column(Text, default='', nullable=True)
    sub_comment_count: Mapped[Optional[int]] = mapped_column(Integer, default=0, nullable=True)
    note_id: Mapped[Optional[str]] = mapped_column(String(255), index=True, nullable=True)
    note_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    add_ts: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    last_modify_ts: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)


class TiebaCreator(Base):
    __tablename__ = "tieba_creator"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    user_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    nickname: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    avatar: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ip_location: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    add_ts: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    last_modify_ts: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    gender: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    follows: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    fans: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    registration_duration: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class ZhihuContent(Base):
    __tablename__ = "zhihu_content"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    content_id: Mapped[Optional[str]] = mapped_column(String(64), index=True, nullable=True)
    content_type: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    question_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    desc: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_time: Mapped[Optional[str]] = mapped_column(String(32), index=True, nullable=True)
    updated_time: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    voteup_count: Mapped[Optional[int]] = mapped_column(Integer, default=0, nullable=True)
    comment_count: Mapped[Optional[int]] = mapped_column(Integer, default=0, nullable=True)
    source_keyword: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    user_link: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    user_nickname: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    user_avatar: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    user_url_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    add_ts: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    last_modify_ts: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    topic_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("daily_topics.topic_id", ondelete="SET NULL"), nullable=True)
    crawling_task_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("crawling_tasks.task_id", ondelete="SET NULL"), nullable=True)

class ZhihuComment(Base):
    __tablename__ = "zhihu_comment"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    comment_id: Mapped[Optional[str]] = mapped_column(String(64), index=True, nullable=True)
    parent_comment_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    publish_time: Mapped[Optional[str]] = mapped_column(String(32), index=True, nullable=True)
    ip_location: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sub_comment_count: Mapped[Optional[int]] = mapped_column(Integer, default=0, nullable=True)
    like_count: Mapped[Optional[int]] = mapped_column(Integer, default=0, nullable=True)
    dislike_count: Mapped[Optional[int]] = mapped_column(Integer, default=0, nullable=True)
    content_id: Mapped[Optional[str]] = mapped_column(String(64), index=True, nullable=True)
    content_type: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    user_link: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    user_nickname: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    user_avatar: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    add_ts: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    last_modify_ts: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)


class ZhihuCreator(Base):
    __tablename__ = "zhihu_creator"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(64), unique=True, index=True, nullable=True)
    user_link: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    user_nickname: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    user_avatar: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    url_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    gender: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ip_location: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    follows: Mapped[Optional[int]] = mapped_column(Integer, default=0, nullable=True)
    fans: Mapped[Optional[int]] = mapped_column(Integer, default=0, nullable=True)
    anwser_count: Mapped[Optional[int]] = mapped_column(Integer, default=0, nullable=True)
    video_count: Mapped[Optional[int]] = mapped_column(Integer, default=0, nullable=True)
    question_count: Mapped[Optional[int]] = mapped_column(Integer, default=0, nullable=True)
    article_count: Mapped[Optional[int]] = mapped_column(Integer, default=0, nullable=True)
    column_count: Mapped[Optional[int]] = mapped_column(Integer, default=0, nullable=True)
    get_voteup_count: Mapped[Optional[int]] = mapped_column(Integer, default=0, nullable=True)
    add_ts: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    last_modify_ts: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
