
import sys
import os
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text, MetaData, Table, Column, Integer, String, Text, Date, BigInteger, inspect
from loguru import logger

# Add project root directory to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(str(project_root))

try:
    import config
    from config import settings
except ImportError:
    print("Error: Could not import config")
    sys.exit(1)

async def init_db_async():
    try:
        # Connect using asyncpg which is confirmed to be installed
        dialect = (settings.DB_DIALECT or "mysql").lower()
        if dialect in ("postgresql", "postgres"):
             # Use asyncpg
             url = f"postgresql+asyncpg://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
             logger.info("Dialect: PostgreSQL (asyncpg)")
        else:
             # Assuming mysql+aiomysql or similar if needed, but likely strict postgres here based on errors
             url = f"mysql+pymysql://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}?charset={settings.DB_CHARSET}"
             logger.info("Dialect: MySQL")
        
        engine = create_async_engine(url)
        metadata = MetaData()

        # ------------------- Column Definitions -------------------

        # Common columns for media content (videos, notes, articles)
        def common_media_columns():
            return [
                Column('id', Integer, primary_key=True, autoincrement=True),
                Column('content', Text),
                Column('title', Text),
                Column('desc', Text),  # REQUIRED by search.py
                Column('url', Text),
                Column('video_url', Text), 
                Column('note_url', Text), 
                Column('content_url', Text), 
                Column('aweme_url', Text),
                # Author Info
                Column('nickname', Text),
                Column('user_nickname', Text),
                Column('user_name', Text),
                # Time
                Column('create_time', BigInteger),
                Column('created_time', BigInteger),
                Column('create_date_time', Text), 
                Column('publish_time', Text),
                Column('time', BigInteger), 
                # Engagement
                Column('liked_count', Integer),
                Column('like_count', Integer),
                Column('voteup_count', Integer),
                Column('comment_count', Integer),
                Column('comments_count', Integer),
                Column('share_count', Integer),
                Column('shared_count', Integer),
                Column('view_count', Integer),
                Column('viewd_count', Integer),
                Column('collected_count', Integer),
                Column('favorite_count', Integer),
                # Search metadata
                Column('source_keyword', Text),
                Column('tag_list', Text),
                Column('content_text', Text),
            ]

        # Common columns for comments
        def common_comment_columns():
            return [
                Column('id', Integer, primary_key=True, autoincrement=True),
                Column('content', Text),
                Column('nickname', Text),
                Column('user_nickname', Text),
                Column('create_time', BigInteger),
                Column('publish_time', BigInteger),
                Column('create_date_time', Text),
                Column('liked_count', Integer),
                Column('like_count', Integer),
                Column('comment_like_count', Integer),
                Column('source_keyword', Text),
            ]

        # ------------------- Table List -------------------
        
        tables_to_sync = []

        # 1. Media Content Tables
        content_tables = [
            'bilibili_video', 'douyin_aweme', 'kuaishou_video', 
            'weibo_note', 'xhs_note', 'zhihu_content', 'tieba_note'
        ]
        for t_name in content_tables:
            tables_to_sync.append((t_name, common_media_columns()))

        # 2. Comment Tables
        comment_tables = [
            'bilibili_video_comment', 'douyin_aweme_comment', 'kuaishou_video_comment',
            'weibo_note_comment', 'xhs_note_comment', 'zhihu_comment', 'tieba_comment'
        ]
        for t_name in comment_tables:
            tables_to_sync.append((t_name, common_comment_columns()))

        # 3. Special: Daily News
        daily_news_cols = [
            Column('id', Integer, primary_key=True, autoincrement=True),
            Column('news_id', String(255), unique=True),
            Column('source_platform', String(50)),
            Column('title', Text),
            Column('url', Text),
            Column('crawl_date', Date),
            Column('rank_position', Integer),
            Column('add_ts', BigInteger),
            Column('last_modify_ts', BigInteger),
            Column('summary', Text),
            Column('content', Text),
            Column('source_keyword', Text),
        ]
        tables_to_sync.append(('daily_news', daily_news_cols))
        
        # 4. Special: Daily Topics
        daily_topics_cols = [
            Column('id', Integer, primary_key=True, autoincrement=True),
            Column('topic_id', String(255), unique=True),
            Column('broad_topic', String(255)),
            Column('specific_topic', String(255)),
            Column('topic_date', Date),
            Column('rank_position', Integer),
            Column('hot_score', BigInteger),
            Column('add_ts', BigInteger),
            Column('summary', Text),
        ]
        tables_to_sync.append(('daily_topics', daily_topics_cols))

        # ------------------- Execution (Async) -------------------

        logger.info(f"Connected to database at {settings.DB_HOST}. Starting schema synchronization...")

        async with engine.begin() as conn:
            # Run blocking inspector code in run_sync
            await conn.run_sync(sync_schema_logic, tables_to_sync, metadata)

        logger.info("Database schema synchronization completed.")
        await engine.dispose()

    except Exception as e:
        logger.error(f"Initialization failed: {e}")
        import traceback
        traceback.print_exc()

def sync_schema_logic(conn, tables_to_sync, metadata):
    inspector = inspect(conn)
    
    for table_name, columns in tables_to_sync:
        # 1. Create table if not exists
        if not inspector.has_table(table_name):
            logger.info(f"--> Creating missing table: {table_name}")
            t = Table(table_name, metadata, *columns)
            t.create(conn)
        else:
            # 2. Check for missing columns in existing tables
            logger.info(f"Checking existing table: {table_name}")
            existing_cols = {c['name'] for c in inspector.get_columns(table_name)}
            
            for col in columns:
                if col.name not in existing_cols:
                    try:
                        logger.warning(f"  + Adding missing column '{col.name}' to '{table_name}'")
                        pg_type = "TEXT"
                        if isinstance(col.type, Integer): pg_type = "INTEGER"
                        elif isinstance(col.type, BigInteger): pg_type = "BIGINT"
                        elif isinstance(col.type, Date): pg_type = "DATE"
                        
                        conn.execute(text(f'ALTER TABLE "{table_name}" ADD COLUMN "{col.name}" {pg_type}'))
                    except Exception as alter_err:
                        logger.error(f"Failed to add column {col.name}: {alter_err}")

if __name__ == "__main__":
    asyncio.run(init_db_async())
