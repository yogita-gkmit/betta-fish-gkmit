
import sys
import os
from sqlalchemy import create_engine, text
from pathlib import Path

# Add project root to path
sys.path.append(os.getcwd())

try:
    import config
    from config import settings
except ImportError:
    print("Error: Could not import config")
    sys.exit(1)

def check_data():
    try:
        if (settings.DB_DIALECT or "mysql").lower() in ("postgresql", "postgres"):
             url = f"postgresql+psycopg://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
             print("Dialect: PostgreSQL")
        else:
             url = f"mysql+pymysql://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}?charset={settings.DB_CHARSET}"
             print("Dialect: MySQL")
        
        print(f"Connecting to: {url.split('@')[-1]}")
        engine = create_engine(url)
        
        with engine.connect() as conn:
            # Check count
            count = conn.execute(text("SELECT COUNT(*) FROM daily_news")).scalar()
            print(f"Total Rows in daily_news: {count}")
            
            # Check recent 5
            print("\nRecent 5 Rows:")
            rows = conn.execute(text("SELECT id, title, source_platform, crawl_date FROM daily_news ORDER BY id DESC LIMIT 5")).all()
            for r in rows:
                print(r)

            # Check for Sysdig
            print("\nSearching for 'Sysdig':")
            sysdig = conn.execute(text("SELECT id, title FROM daily_news WHERE title ILIKE '%Sysdig%' LIMIT 5")).all()
            for r in sysdig:
                print(r)

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_data()
