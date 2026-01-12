
import asyncio
import sys
from pathlib import Path
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from loguru import logger

# Setup path
current_dir = Path(__file__).parent
project_root = current_dir.parent
sys.path.append(str(project_root))
sys.path.append(str(current_dir)) # Add MindSpider dir
sys.path.append(str(current_dir / "schema")) # Add schema dir to path to allow "import models_sa" inside models_bigdata

try:
    try:
        from schema.models_sa import Base
        import schema.models_bigdata
    except ImportError:
        from MindSpider.schema.models_sa import Base
        import MindSpider.schema.models_bigdata
        
    from config import settings
except ImportError as e:
    print(f"Import Error: {e}")
    sys.exit(1)

def _build_url():
    dialect = (settings.DB_DIALECT or "mysql").lower()
    host = settings.DB_HOST or "localhost"
    port = str(settings.DB_PORT or ("3306" if dialect == "mysql" else "5432"))
    user = settings.DB_USER or "root"
    password = settings.DB_PASSWORD or ""
    db_name = settings.DB_NAME or "mindspider"

    if dialect in ("postgresql", "postgres"):
        return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db_name}"
    return f"mysql+aiomysql://{user}:{password}@{host}:{port}/{db_name}"

async def reset_db():
    url = _build_url()
    print(f"Connecting to: {url.split('@')[-1]}")
    
    engine = create_async_engine(url, echo=True)
    
    async with engine.begin() as conn:
        print("Dropping old tables...")
        # Drop strict dependencies first if needed, or use cascade
        await conn.run_sync(Base.metadata.drop_all)
        print("Creating new tables...")
        await conn.run_sync(Base.metadata.create_all)
        
    print("Database Reset Complete.")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(reset_db())
