# Disclaimer: This code is for learning and research purposes only. Users must adhere to the following principles:
# 1. Do not use for any commercial purposes.
# 2. Comply with the target platform's terms of use and robots.txt rules.
# 3. Do not perform large-scale crawling or disrupt platform operations.
# 4. Reasonably control request frequency to avoid unnecessary burden on target platforms.
# 5. Do not use for any illegal or improper purposes.
#
# Please refer to the LICENSE file in the project root for detailed license terms.
# Using this code indicates your agreement to abide by the above principles and all terms in the LICENSE.  


from asyncio.tasks import Task
from contextvars import ContextVar
from typing import List

import aiomysql

request_keyword_var: ContextVar[str] = ContextVar("request_keyword", default="")
crawler_type_var: ContextVar[str] = ContextVar("crawler_type", default="")
comment_tasks_var: ContextVar[List[Task]] = ContextVar("comment_tasks", default=[])
db_conn_pool_var: ContextVar[aiomysql.Pool] = ContextVar("db_conn_pool_var")
source_keyword_var: ContextVar[str] = ContextVar("source_keyword", default="")