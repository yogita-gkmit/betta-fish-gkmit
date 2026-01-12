"""
Local Public Opinion Database Query Toolset Designed for AI Agent (MediaCrawlerDB)

Version: 3.0
Last Update: 2025-08-23

This script encapsulates complex local MySQL database query functions into a series of independent tools with clear goals and parameters,
designed for AI Agent calls. The Agent only needs to choose the appropriate tool according to the task intent (such as searching for hot topics, searching topics globally,
analyzing by time range, getting comments), without writing complex SQL statements.

V3.0 Core Updates:
- Intelligent Hotness Calculation: `search_hot_content` no longer needs `sort_by` parameter, instead uses unified weighted hotness algorithm internally,
  calculating hotness score based on likes, comments, shares, views, etc., making results more intelligent and consistent with comprehensive hotness.
- New Platform Precise Search Tool: Added `search_topic_on_platform` tool, as a special case,
  allowing Agent to precisely search for a topic on a specific platform (Glassdoor, Times of India, etc.), and supports time filtering.
- Structure Optimization: Adjusted data structures and function documentation to adapt to new features.

Main Tools:
- search_hot_content: Find content with highest comprehensive hotness within specified time range.
- search_topic_globally: Globally search all content and comments related to specific topic in the entire database.
- search_topic_by_date: Search content related to specific topic within specified historical date range.
- get_comments_for_topic: Specifically extract public comment data for a specific topic.
- search_topic_on_platform: Search specific topic on specified single social media platform.
"""

import os
import json
from loguru import logger
import asyncio
from typing import List, Dict, Any, Optional, Literal
from dataclasses import dataclass, field
from ..utils.db import fetch_all
from datetime import datetime, timedelta, date

# --- 1. Data Structure Definitions ---

@dataclass
class QueryResult:
    """Unified database query result data class"""
    platform: str
    content_type: str
    title_or_content: str
    author_nickname: Optional[str] = None
    url: Optional[str] = None
    publish_time: Optional[datetime] = None
    engagement: Dict[str, int] = field(default_factory=dict)
    source_keyword: Optional[str] = None
    hotness_score: float = 0.0
    source_table: str = ""

@dataclass
class DBResponse:
    """Encapsulate complete return result of tool"""
    tool_name: str
    parameters: Dict[str, Any]
    results: List[QueryResult] = field(default_factory=list)
    results_count: int = 0
    error_message: Optional[str] = None

# --- 2. Core Client and Specialized Toolset ---

class MediaCrawlerDB:
    """Client containing multiple specialized public opinion database query tools"""
    # Weight definitions
    W_LIKE = 1.0
    W_COMMENT = 5.0
    W_SHARE = 10.0  # High value interactions like share/forward/favorite/coin
    W_VIEW = 0.1
    W_DANMAKU = 0.5

    def __init__(self):
        """
        Initialize client.
        """
        pass
        
    def _execute_query(self, query: str, params: tuple = None) -> List[Dict[str, Any]]:
        """
        Execute query in a thread-safe manner, compatible with running event loops.
        Uses a separate thread to run the async DB operation to avoid nested loop issues.
        """
        import concurrent.futures
        
        def run_in_new_loop(q, p):
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            try:
                return new_loop.run_until_complete(fetch_all(q, p))
            finally:
                new_loop.close()

        try:
            # Check if there's a running loop to decide detailed strategy, 
            # but using a thread is the safest "sync-over-async" bridge regardless.
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(run_in_new_loop, query, params)
                return future.result()
        
        except Exception as e:
            logger.exception(f"Error occurred during database query: {e}")
            return []

    @staticmethod
    def _to_datetime(ts: Any) -> Optional[datetime]:
        if not ts: return None
        try:
            if isinstance(ts, datetime): return ts
            if isinstance(ts, date): return datetime.combine(ts, datetime.min.time())
            if isinstance(ts, (int, float)) or str(ts).isdigit():
                val = float(ts)
                return datetime.fromtimestamp(val / 1000 if val > 1_000_000_000_000 else val)
            if isinstance(ts, str):
                return datetime.fromisoformat(ts.split('+')[0].strip())
        except (ValueError, TypeError): return None

    _table_columns_cache = {}
    def _get_table_columns(self, table_name: str) -> List[str]:
        if table_name in self._table_columns_cache: return self._table_columns_cache[table_name]
        results = self._execute_query(f"SHOW COLUMNS FROM `{table_name}`")
        columns = [row['Field'] for row in results] if results else []
        self._table_columns_cache[table_name] = columns
        return columns

    def _extract_engagement(self, row: Dict[str, Any]) -> Dict[str, int]:
        """Extract and unify engagement metrics from data row"""
        engagement = {}
        mapping = { 'likes': ['liked_count', 'like_count', 'voteup_count', 'comment_like_count'], 'comments': ['video_comment', 'comments_count', 'comment_count', 'total_replay_num', 'sub_comment_count'], 'shares': ['video_share_count', 'shared_count', 'share_count', 'total_forwards'], 'views': ['video_play_count', 'viewd_count'], 'favorites': ['video_favorite_count', 'collected_count'], 'coins': ['video_coin_count'], 'danmaku': ['video_danmaku'], }
        for key, potential_cols in mapping.items():
            for col in potential_cols:
                if col in row and row[col] is not None:
                    try: engagement[key] = int(row[col])
                    except (ValueError, TypeError): engagement[key] = 0
                    break
        return engagement

    def search_hot_content(
        self,
        time_period: Literal['24h', 'week', 'year'] = 'week',
        limit: int = 50
    ) -> DBResponse:
        """
        [Tool] Search Hot Content: Get content with highest comprehensive popularity in recent period.

        Args:
            time_period (Literal['24h', 'week', 'year']): Time period, default is 'week'.
            limit (int): Maximum number of results to return, default is 50.

        Returns:
            DBResponse: List of content sorted by comprehensive hotness.
        """
        params_for_log = {'time_period': time_period, 'limit': limit}
        logger.info(f"--- TOOL: Search Hot Content (params: {params_for_log}) ---")
        
        now = datetime.now()
        start_time = now - timedelta(days={'24h': 1, 'week': 7}.get(time_period, 365))

        # Define hotness calculation SQL fragments for each platform
        hotness_formulas = {
            'bilibili_video': f"(COALESCE(CAST(liked_count AS UNSIGNED), 0) * {self.W_LIKE} + COALESCE(CAST(video_comment AS UNSIGNED), 0) * {self.W_COMMENT} + COALESCE(CAST(video_share_count AS UNSIGNED), 0) * {self.W_SHARE} + COALESCE(CAST(video_favorite_count AS UNSIGNED), 0) * {self.W_SHARE} + COALESCE(CAST(video_coin_count AS UNSIGNED), 0) * {self.W_SHARE} + COALESCE(CAST(video_danmaku AS UNSIGNED), 0) * {self.W_DANMAKU} + COALESCE(CAST(video_play_count AS DECIMAL(20,2)), 0) * {self.W_VIEW})",
            'douyin_aweme':   f"(COALESCE(CAST(liked_count AS UNSIGNED), 0) * {self.W_LIKE} + COALESCE(CAST(comment_count AS UNSIGNED), 0) * {self.W_COMMENT} + COALESCE(CAST(share_count AS UNSIGNED), 0) * {self.W_SHARE} + COALESCE(CAST(collected_count AS UNSIGNED), 0) * {self.W_SHARE})",
            'weibo_note':     f"(COALESCE(CAST(liked_count AS UNSIGNED), 0) * {self.W_LIKE} + COALESCE(CAST(comments_count AS UNSIGNED), 0) * {self.W_COMMENT} + COALESCE(CAST(shared_count AS UNSIGNED), 0) * {self.W_SHARE})",
            'xhs_note':       f"(COALESCE(CAST(liked_count AS UNSIGNED), 0) * {self.W_LIKE} + COALESCE(CAST(comment_count AS UNSIGNED), 0) * {self.W_COMMENT} + COALESCE(CAST(share_count AS UNSIGNED), 0) * {self.W_SHARE} + COALESCE(CAST(collected_count AS UNSIGNED), 0) * {self.W_SHARE})",
            'kuaishou_video': f"(COALESCE(CAST(liked_count AS UNSIGNED), 0) * {self.W_LIKE} + COALESCE(CAST(viewd_count AS DECIMAL(20,2)), 0) * {self.W_VIEW})",
            'zhihu_content':  f"(COALESCE(CAST(voteup_count AS UNSIGNED), 0) * {self.W_LIKE} + COALESCE(CAST(comment_count AS UNSIGNED), 0) * {self.W_COMMENT})",
        }

        all_queries, params = [], []
        for table, formula in hotness_formulas.items():
            time_filter_sql, time_filter_param = "", None
            if table == 'weibo_note': time_filter_sql, time_filter_param = "`create_date_time` >= %s", start_time.strftime('%Y-%m-%d %H:%M:%S')
            elif table in ['kuaishou_video', 'xhs_note', 'douyin_aweme']: time_col = 'time' if table == 'xhs_note' else 'create_time'; time_filter_sql, time_filter_param = f"`{time_col}` >= %s", str(int(start_time.timestamp() * 1000))
            elif table == 'zhihu_content': time_filter_sql, time_filter_param = "CAST(`created_time` AS UNSIGNED) >= %s", str(int(start_time.timestamp()))
            else: time_filter_sql, time_filter_param = "`create_time` >= %s", str(int(start_time.timestamp()))

            content_type = 'note' if table in ['weibo_note', 'xhs_note'] else 'content' if table == 'zhihu_content' else 'video'
            query_template = "SELECT '{platform}' as p, '{type}' as t, {title} as title, {author} as author, {url} as url, {ts} as ts, {formula} as hotness_score, source_keyword, '{tbl}' as tbl FROM `{tbl}` WHERE {time_filter}"
            
            field_subs = {'platform': table.split('_')[0], 'type': content_type, 'title': 'title', 'author': 'nickname', 'url': 'video_url', 'ts': 'create_time', 'formula': formula, 'tbl': table, 'time_filter': time_filter_sql}
            if table == 'weibo_note': field_subs.update({'title': 'content', 'url': 'note_url', 'ts': 'create_date_time'})
            elif table == 'xhs_note': field_subs.update({'ts': 'time', 'url': 'note_url'})
            elif table == 'zhihu_content': field_subs.update({'author': 'user_nickname', 'url': 'content_url', 'ts': 'created_time'})
            elif table == 'douyin_aweme': field_subs.update({'url': 'aweme_url'})

            all_queries.append(query_template.format(**field_subs))
            params.append(time_filter_param)
        
        final_query = f"({' ) UNION ALL ( '.join(all_queries)}) ORDER BY hotness_score DESC LIMIT %s"
        raw_results = self._execute_query(final_query, tuple(params) + (limit,))

        formatted_results = [QueryResult(platform=r['p'], content_type=r['t'], title_or_content=r['title'], author_nickname=r.get('author'), url=r['url'], publish_time=self._to_datetime(r['ts']), engagement=self._extract_engagement(r), hotness_score=r.get('hotness_score', 0.0), source_keyword=r.get('source_keyword'), source_table=r['tbl']) for r in raw_results]
        return DBResponse("search_hot_content", params_for_log, results=formatted_results, results_count=len(formatted_results))    

    def search_topic_globally(self, topic: str, limit_per_table: int = 100) -> DBResponse:
        """
        [Tool] Global Topic Search: Comprehensively search for specified topic in database (content, comments, tags, source keywords).

        Args:
            topic (str): Topic keyword to search.
            limit_per_table (int): Maximum number of records to return from each related table, default is 100.

        Returns:
            DBResponse: Aggregated list of all matching results.
        """
        params_for_log = {'topic': topic, 'limit_per_table': limit_per_table}
        logger.info(f"--- TOOL: Global Topic Search (params: {params_for_log}) ---")
        
        search_term, all_results = f"%{topic}%", []
        search_configs = { 'bilibili_video': {'fields': ['title', 'desc', 'source_keyword'], 'type': 'video'}, 'bilibili_video_comment': {'fields': ['content'], 'type': 'comment'}, 'douyin_aweme': {'fields': ['title', 'desc', 'source_keyword'], 'type': 'video'}, 'douyin_aweme_comment': {'fields': ['content'], 'type': 'comment'}, 'kuaishou_video': {'fields': ['title', 'desc', 'source_keyword'], 'type': 'video'}, 'kuaishou_video_comment': {'fields': ['content'], 'type': 'comment'}, 'weibo_note': {'fields': ['content', 'source_keyword'], 'type': 'note'}, 'weibo_note_comment': {'fields': ['content'], 'type': 'comment'}, 'xhs_note': {'fields': ['title', 'desc', 'tag_list', 'source_keyword'], 'type': 'note'}, 'xhs_note_comment': {'fields': ['content'], 'type': 'comment'}, 'zhihu_content': {'fields': ['title', 'desc', 'content_text', 'source_keyword'], 'type': 'content'}, 'zhihu_comment': {'fields': ['content'], 'type': 'comment'}, 'tieba_note': {'fields': ['title', 'desc', 'source_keyword'], 'type': 'note'}, 'tieba_comment': {'fields': ['content'], 'type': 'comment'}, 'daily_news': {'fields': ['title', 'content', 'summary'], 'type': 'news'}, }
        
        for table, config in search_configs.items():
            param_dict = {}
            where_clauses = []
            for idx, field in enumerate(config['fields']):
                pname = f"term_{idx}"
                where_clauses.append(f'"{field}" ILIKE :{pname}')
                param_dict[pname] = search_term
            param_dict['limit'] = limit_per_table
            where_clause = " OR ".join(where_clauses)
            query = f"SELECT * FROM {table} WHERE {where_clause} ORDER BY id DESC LIMIT :limit"
            raw_results = self._execute_query(query, param_dict)
            for row in raw_results:
                content = (row.get('title') or row.get('content') or row.get('desc') or row.get('content_text', ''))
                time_key = row.get('create_time') or row.get('time') or row.get('created_time') or row.get('publish_time') or row.get('crawl_date')
                all_results.append(QueryResult(
                    platform=table.split('_')[0], content_type=config['type'],
                    title_or_content=content if content else '',
                    author_nickname=row.get('nickname') or row.get('user_nickname') or row.get('user_name'),
                    url=row.get('video_url') or row.get('note_url') or row.get('content_url') or row.get('url') or row.get('aweme_url'),
                    publish_time=self._to_datetime(time_key),
                    engagement=self._extract_engagement(row),
                    source_keyword=row.get('source_keyword'),
                    source_table=table
                ))
        return DBResponse("search_topic_globally", params_for_log, results=all_results, results_count=len(all_results))

    def search_topic_by_date(self, topic: str, start_date: str, end_date: str, limit_per_table: int = 100) -> DBResponse:
        """
        [Tool] Search Topic by Date: Search content related to specific topic in clear historical time period.

        Args:
            topic (str): Topic keyword to search.
            start_date (str): Start date, format 'YYYY-MM-DD'.
            end_date (str): End date, format 'YYYY-MM-DD'.
            limit_per_table (int): Maximum number of records to return from each related table, default is 100.

        Returns:
            DBResponse: Aggregated list of results found in specified date range.
        """
        params_for_log = {'topic': topic, 'start_date': start_date, 'end_date': end_date, 'limit_per_table': limit_per_table}
        logger.info(f"--- TOOL: Search Topic by Date (params: {params_for_log}) ---")
        
        try:
            start_dt, end_dt = datetime.strptime(start_date, '%Y-%m-%d'), datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
        except ValueError:
            return DBResponse("search_topic_by_date", params_for_log, error_message="Date format error, please use 'YYYY-MM-DD' format.")
        
        search_term, all_results = f"%{topic}%", []
        search_configs = {
            'bilibili_video': {'fields': ['title', 'desc', 'source_keyword'], 'type': 'video', 'time_col': 'create_time', 'time_type': 'sec'}, 'douyin_aweme': {'fields': ['title', 'desc', 'source_keyword'], 'type': 'video', 'time_col': 'create_time', 'time_type': 'ms'},
            'kuaishou_video': {'fields': ['title', 'desc', 'source_keyword'], 'type': 'video', 'time_col': 'create_time', 'time_type': 'ms'}, 'weibo_note': {'fields': ['content', 'source_keyword'], 'type': 'note', 'time_col': 'create_date_time', 'time_type': 'str'},
            'xhs_note': {'fields': ['title', 'desc', 'tag_list', 'source_keyword'], 'type': 'note', 'time_col': 'time', 'time_type': 'ms'}, 'zhihu_content': {'fields': ['title', 'desc', 'content_text', 'source_keyword'], 'type': 'content', 'time_col': 'created_time', 'time_type': 'sec_str'},
            'tieba_note': {'fields': ['title', 'desc', 'source_keyword'], 'type': 'note', 'time_col': 'publish_time', 'time_type': 'str'}, 'daily_news': {'fields': ['title'], 'type': 'news', 'time_col': 'crawl_date', 'time_type': 'date_str'},
        }

        for table, config in search_configs.items():
            param_dict = {}
            where_clauses = []
            for idx, field in enumerate(config['fields']):
                pname = f"term_{idx}"
                where_clauses.append(f'"{field}" LIKE :{pname}')
                param_dict[pname] = search_term
            param_dict['limit'] = limit_per_table
            where_clause = ' OR '.join(where_clauses)
            query = f"SELECT * FROM {table} WHERE {where_clause} ORDER BY id DESC LIMIT :limit"
            raw_results = self._execute_query(query, param_dict)
            for row in raw_results:
                content = (row.get('title') or row.get('content') or row.get('desc') or row.get('content_text', ''))
                time_key = row.get('create_time') or row.get('time') or row.get('created_time') or row.get('publish_time') or row.get('crawl_date')
                all_results.append(QueryResult(
                    platform=table.split('_')[0], content_type=config['type'],
                    title_or_content=content if content else '',
                    author_nickname=row.get('nickname') or row.get('user_nickname') or row.get('user_name'),
                    url=row.get('video_url') or row.get('note_url') or row.get('content_url') or row.get('url') or row.get('aweme_url'),
                    publish_time=self._to_datetime(time_key),
                    engagement=self._extract_engagement(row),
                    source_keyword=row.get('source_keyword'),
                    source_table=table
                ))
        return DBResponse("search_topic_by_date", params_for_log, results=all_results, results_count=len(all_results))
        
    def get_comments_for_topic(self, topic: str, limit: int = 500) -> DBResponse:
        """
        [Tool] Get Topic Comments: Specifically search and return public comment data related to specific topic from all platforms.

        Args:
            topic (str): Topic keyword to search.
            limit (int): Maximum number of comments to return, default is 500.

        Returns:
            DBResponse: List of matching comments.
        """
        params_for_log = {'topic': topic, 'limit': limit}
        logger.info(f"--- TOOL: Get Topic Comments (params: {params_for_log}) ---")
        
        search_term = f"%{topic}%"
        comment_tables = ['bilibili_video_comment', 'douyin_aweme_comment', 'kuaishou_video_comment', 'weibo_note_comment', 'xhs_note_comment', 'zhihu_comment', 'tieba_comment']
        
        all_queries = []
        for table in comment_tables:
            cols = self._get_table_columns(table)
            author_col = 'user_nickname' if 'user_nickname' in cols else 'nickname'
            like_col = 'comment_like_count' if 'comment_like_count' in cols else 'like_count' if 'like_count' in cols else None
            time_col = 'publish_time' if 'publish_time' in cols else 'create_date_time' if 'create_date_time' in cols else 'create_time'
            like_select = f"`{like_col}` as likes" if like_col else "'0' as likes"
            
            query = (f"SELECT '{table.split('_')[0]}' as platform, `content`, `{author_col}` as author, "
                     f"`{time_col}` as ts, {like_select}, '{table}' as source_table "
                     f"FROM `{table}` WHERE `content` LIKE %s")
            all_queries.append(query)

        final_query = f"({' ) UNION ALL ( '.join(all_queries)}) ORDER BY ts DESC LIMIT %s"
        params = (search_term,) * len(comment_tables) + (limit,)
        raw_results = self._execute_query(final_query, params)
        
        formatted = [QueryResult(platform=r['platform'], content_type='comment', title_or_content=r['content'], author_nickname=r['author'], publish_time=self._to_datetime(r['ts']), engagement={'likes': int(r['likes']) if str(r['likes']).isdigit() else 0}, source_table=r['source_table']) for r in raw_results]
        return DBResponse("get_comments_for_topic", params_for_log, results=formatted, results_count=len(formatted))

    def search_topic_on_platform(
        self,
        platform: Literal['glassdoor', 'times_of_india', 'professional_network', 'general_news', 'bilibili', 'weibo', 'douyin', 'kuaishou', 'xhs', 'zhihu', 'tieba'],
        topic: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 20
    ) -> DBResponse:
        """
        [Tool] Platform Directed Search: (New) Search specific topic on specified single social media platform.

        Args:
            platform (Literal['glassdoor', ...]): Platform to search, must be one of the supported platforms.
            topic (str): Topic keyword to search.
            start_date (Optional[str]): Start date, format 'YYYY-MM-DD'. Default is None.
            end_date (Optional[str]): End date, format 'YYYY-MM-DD'. Default is None.
            limit (int): Maximum number of results to return, default is 20.

        Returns:
            DBResponse: List of results found on that platform.
        """
        params_for_log = {'platform': platform, 'topic': topic, 'start_date': start_date, 'end_date': end_date, 'limit': limit}
        logger.info(f"--- TOOL: Platform Directed Search (params: {params_for_log}) ---")

        all_configs = { 
            'glassdoor': [{'table': 'daily_news', 'fields': ['title', 'content', 'summary'], 'type': 'news', 'time_col': 'crawl_date', 'time_type': 'date_str', 'source_filter': 'glassdoor'}],
            'times_of_india': [{'table': 'daily_news', 'fields': ['title', 'content', 'summary'], 'type': 'news', 'time_col': 'crawl_date', 'time_type': 'date_str', 'source_filter': 'toi'}],
            'professional_network': [{'table': 'daily_news', 'fields': ['title', 'content', 'summary'], 'type': 'news', 'time_col': 'crawl_date', 'time_type': 'date_str'}], # Generic search on daily_news
            'general_news': [{'table': 'daily_news', 'fields': ['title', 'content', 'summary'], 'type': 'news', 'time_col': 'crawl_date', 'time_type': 'date_str'}],
            'bilibili': [{'table': 'bilibili_video', 'fields': ['title', 'desc', 'source_keyword'], 'type': 'video', 'time_col': 'create_time', 'time_type': 'sec'}, {'table': 'bilibili_video_comment', 'fields': ['content'], 'type': 'comment'}], 
            'douyin': [{'table': 'douyin_aweme', 'fields': ['title', 'desc', 'source_keyword'], 'type': 'video', 'time_col': 'create_time', 'time_type': 'ms'}, {'table': 'douyin_aweme_comment', 'fields': ['content'], 'type': 'comment'}], 
            'kuaishou': [{'table': 'kuaishou_video', 'fields': ['title', 'desc', 'source_keyword'], 'type': 'video', 'time_col': 'create_time', 'time_type': 'ms'}, {'table': 'kuaishou_video_comment', 'fields': ['content'], 'type': 'comment'}], 
            'weibo': [{'table': 'weibo_note', 'fields': ['content', 'source_keyword'], 'type': 'note', 'time_col': 'create_date_time', 'time_type': 'str'}, {'table': 'weibo_note_comment', 'fields': ['content'], 'type': 'comment'}], 
            'xhs': [{'table': 'xhs_note', 'fields': ['title', 'desc', 'tag_list', 'source_keyword'], 'type': 'note', 'time_col': 'time', 'time_type': 'ms'}, {'table': 'xhs_note_comment', 'fields': ['content'], 'type': 'comment'}], 
            'zhihu': [{'table': 'zhihu_content', 'fields': ['title', 'desc', 'content_text', 'source_keyword'], 'type': 'content', 'time_col': 'created_time', 'time_type': 'sec_str'}, {'table': 'zhihu_comment', 'fields': ['content'], 'type': 'comment'}], 
            'tieba': [{'table': 'tieba_note', 'fields': ['title', 'desc', 'source_keyword'], 'type': 'note', 'time_col': 'publish_time', 'time_type': 'str'}, {'table': 'tieba_comment', 'fields': ['content'], 'type': 'comment'}] 
        }
        
        if platform not in all_configs:
            return DBResponse("search_topic_on_platform", params_for_log, error_message=f"Unsupported platform: {platform}")

        search_term, all_results = f"%{topic}%", []
        platform_configs = all_configs[platform]

        time_clause, time_params_tuple = "", ()
        if start_date and end_date:
            try:
                start_dt, end_dt = datetime.strptime(start_date, '%Y-%m-%d'), datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
            except ValueError:
                return DBResponse("search_topic_on_platform", params_for_log, error_message="Date format error, please use 'YYYY-MM-DD' format.")
        else:
            start_dt, end_dt = None, None

        for config in platform_configs:
            table = config['table']
            topic_clause = " OR ".join([f"{field} LIKE %s" for field in config['fields']])
            query = f"SELECT * FROM {table} WHERE ({topic_clause})"
            params = [search_term] * len(config['fields'])

            if 'source_filter' in config:
                # Add source_platform filter for shared tables like daily_news
                query += " AND source_platform = %s"
                params.append(config['source_filter'])

            if start_dt and end_dt and 'time_col' in config:
                time_col, time_type = config['time_col'], config['time_type']
                if time_type == 'sec': t_params = (int(start_dt.timestamp()), int(end_dt.timestamp()))
                elif time_type == 'ms': t_params = (int(start_dt.timestamp() * 1000), int(end_dt.timestamp() * 1000))
                elif time_type in ['str', 'date_str']: t_params = (start_dt.strftime('%Y-%m-%d'), end_dt.strftime('%Y-%m-%d'))
                else: t_params = (str(int(start_dt.timestamp())), str(int(end_dt.timestamp())))
                
                t_clause = f"{time_col} >= %s AND {time_col} < %s"
                if table == 'zhihu_content': t_clause = f"CAST({time_col} AS UNSIGNED) >= %s AND CAST({time_col} AS UNSIGNED) < %s"
                
                query += f" AND ({t_clause})"
                params.extend(t_params)

            query += f" ORDER BY id DESC LIMIT %s"
            params.append(limit)

            raw_results = self._execute_query(query, tuple(params))
            for row in raw_results:
                content = (row.get('title') or row.get('content') or row.get('desc') or row.get('content_text', ''))
                time_key = config.get('time_col') and row.get(config.get('time_col'))
                all_results.append(QueryResult(platform=platform, content_type=config['type'], title_or_content=content if content else '', author_nickname=row.get('nickname') or row.get('user_nickname'), url=row.get('video_url') or row.get('note_url') or row.get('content_url') or row.get('url') or row.get('aweme_url'), publish_time=self._to_datetime(time_key), engagement=self._extract_engagement(row), source_keyword=row.get('source_keyword'), source_table=table))
        
        return DBResponse("search_topic_on_platform", params_for_log, results=all_results, results_count=len(all_results))

# --- 3. Test and Usage Examples ---
def print_response_summary(response: DBResponse):
    """Simplified print function for displaying test results"""
    if response.error_message:
        logger.info(f"Tool '{response.tool_name}' execution error: {response.error_message}")
        return

    params_str = ", ".join(f"{k}='{v}'" for k, v in response.parameters.items())
    logger.info(f"Query: Tool='{response.tool_name}', Params=[{params_str}]")
    logger.info(f"Found {response.results_count} related records.")
    
    # Unify into one message output
    output_lines = []
    output_lines.append("==== Query Result Preview (Max first 5) ====")
    if response.results and len(response.results) > 0:
        for idx, res in enumerate(response.results[:5], 1):
            content_preview = (res.title_or_content.replace('\n', ' ')[:70] + '...') if res.title_or_content and len(res.title_or_content) > 70 else (res.title_or_content or '')
            author_str = res.author_nickname or "N/A"
            publish_time_str = res.publish_time.strftime('%Y-%m-%d %H:%M') if res.publish_time else "N/A"
            hotness_str = f", hotness: {res.hotness_score:.2f}" if getattr(res, "hotness_score", 0) > 0 else ""
            engagement_dict = getattr(res, "engagement", {}) or {}
            engagement_str = ", ".join(f"{k}: {v}" for k, v in engagement_dict.items() if v)
            output_lines.append(
                f"{idx}. [{res.platform.upper()}/{res.content_type}] {content_preview}\n"
                f"   Author: {author_str} | Time: {publish_time_str}"
                f"{hotness_str} | Source Keyword: '{res.source_keyword or 'N/A'}'\n"
                f"   Link: {res.url or 'N/A'}\n"
                f"   Engagement: {{{engagement_str}}}"
            )
    else:
        output_lines.append("No related content.")
    output_lines.append("=" * 60)
    logger.info('\n'.join(output_lines))

if __name__ == "__main__":
    
    try:
        db_agent_tools = MediaCrawlerDB()
        logger.info("Database tools initialized successfully, starting test scenarios...\n")
        
        # Scenario 1: (New) Find content with highest comprehensive hotness in past week (no longer need sort_by)
        response1 = db_agent_tools.search_hot_content(time_period='week', limit=5)
        print_response_summary(response1)

        # Scenario 2: Find content with highest comprehensive hotness in past 24 hours
        response2 = db_agent_tools.search_hot_content(time_period='24h', limit=5)
        print_response_summary(response2)

        # Scenario 3: Global search "Luo Yonghao"
        response3 = db_agent_tools.search_topic_globally(topic="罗永浩", limit_per_table=2)
        print_response_summary(response3)

        # Scenario 4: (New) Precise search "benefits" on Glassdoor
        response4 = db_agent_tools.search_topic_on_platform(platform='glassdoor', topic="benefits", limit=5)
        print_response_summary(response4)

        # Scenario 5: (New) Precise search "tax" on Times of India within a specific day
        response5 = db_agent_tools.search_topic_on_platform(platform='times_of_india', topic="tax", start_date='2025-08-22', end_date='2025-08-22', limit=5)
        print_response_summary(response5)

    except ValueError as e:
        logger.exception(f"Initialization failed: {e}")
        logger.exception("Please ensure relevant database environment variables are set correctly, or provide connection info directly in code.")
    except Exception as e:
        logger.exception(f"Unknown error occurred during test: {e}")