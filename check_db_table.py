
import sys
import os
from sqlalchemy import create_engine, inspect, text

# Add project root to path
sys.path.append(os.getcwd())

try:
    import config
    from config import settings
except ImportError:
    print("Error: Could not import config")
    sys.exit(1)

def check_tables():
    try:
        if (settings.DB_DIALECT or "mysql").lower() in ("postgresql", "postgres"):
             url = f"postgresql+psycopg://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
        else:
             url = f"mysql+pymysql://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}?charset={settings.DB_CHARSET}"
        
        print(f"Connecting to: {url.split('@')[-1]}") # Hide password
        engine = create_engine(url)
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"Existing Tables: {tables}")
        
        if 'daily_news' in tables:
            print("SUCCESS: daily_news table FOUND.")
            # Check columns
            cols = [c['name'] for c in inspector.get_columns('daily_news')]
            print(f"Columns: {cols}")
        else:
            print("FAILURE: daily_news table NOT FOUND.")

    except Exception as e:
        print(f"Connection Failed: {e}")

if __name__ == "__main__":
    check_tables()
