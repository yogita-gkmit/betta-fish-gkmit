import config
from sqlalchemy import create_engine, text

config.settings.DB_DIALECT='postgresql'
url = f"postgresql+psycopg://{config.settings.DB_USER}:{config.settings.DB_PASSWORD}@{config.settings.DB_HOST}:{config.settings.DB_PORT}/{config.settings.DB_NAME}"
engine = create_engine(url)

with engine.connect() as conn:
    astral_count = conn.execute(text("SELECT count(*) FROM daily_news WHERE title ILIKE '%Astral%'")).scalar()
    cloudera_count = conn.execute(text("SELECT count(*) FROM daily_news WHERE title ILIKE '%Cloudera%'")).scalar()
    print(f"Astral: {astral_count}")
    print(f"Cloudera: {cloudera_count}")
