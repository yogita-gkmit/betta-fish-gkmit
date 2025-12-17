# Disclaimer: This code is for learning and research purposes only. Users must adhere to the following principles:
# 1. Do not use for any commercial purposes.
# 2. Comply with the target platform's terms of use and robots.txt rules.
# 3. Do not perform large-scale crawling or disrupt platform operations.
# 4. Reasonably control request frequency to avoid unnecessary burden on target platforms.
# 5. Do not use for any illegal or improper purposes.
#
# Please refer to the LICENSE file in the project root for detailed license terms.
# Using this code indicates your agreement to abide by the above principles and all terms in the LICENSE.  


import os
from dotenv import load_dotenv

load_dotenv()

# mysql config - Use env vars
MYSQL_DB_PWD = os.getenv("MYSQL_DB_PWD", "12345678")
MYSQL_DB_USER = os.getenv("MYSQL_DB_USER", "pgsql")
MYSQL_DB_HOST = os.getenv("MYSQL_DB_HOST", "localhost")
MYSQL_DB_PORT = os.getenv("MYSQL_DB_PORT", 5432)
MYSQL_DB_NAME = os.getenv("MYSQL_DB_NAME", "betta_fish_local")

mysql_db_config = {
    "user": MYSQL_DB_USER,
    "password": MYSQL_DB_PWD,
    "host": MYSQL_DB_HOST,
    "port": MYSQL_DB_PORT,
    "db_name": MYSQL_DB_NAME,
}


# redis config
REDIS_DB_HOST = "127.0.0.1"  # your redis host
REDIS_DB_PWD = os.getenv("REDIS_DB_PWD", "123456")  # your redis password
REDIS_DB_PORT = os.getenv("REDIS_DB_PORT", 6379)  # your redis port
REDIS_DB_NUM = os.getenv("REDIS_DB_NUM", 0)  # your redis db num

# cache type
CACHE_TYPE_REDIS = "redis"
CACHE_TYPE_MEMORY = "memory"

# sqlite config
SQLITE_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "database", "sqlite_tables.db")

sqlite_db_config = {
    "db_path": SQLITE_DB_PATH
}

# postgresql config - Use MindSpider's database configuration (if DB_DIALECT is postgresql) or env vars
POSTGRESQL_DB_PWD = os.getenv("POSTGRESQL_DB_PWD", "12345678")
POSTGRESQL_DB_USER = os.getenv("POSTGRESQL_DB_USER", "pgsql")
POSTGRESQL_DB_HOST = os.getenv("POSTGRESQL_DB_HOST", "localhost")
POSTGRESQL_DB_PORT = os.getenv("POSTGRESQL_DB_PORT", "5432")
POSTGRESQL_DB_NAME = os.getenv("POSTGRESQL_DB_NAME", "betta_fish_local")

postgresql_db_config = {
    "user": POSTGRESQL_DB_USER,
    "password": POSTGRESQL_DB_PWD,
    "host": POSTGRESQL_DB_HOST,
    "port": POSTGRESQL_DB_PORT,
    "db_name": POSTGRESQL_DB_NAME,
}

