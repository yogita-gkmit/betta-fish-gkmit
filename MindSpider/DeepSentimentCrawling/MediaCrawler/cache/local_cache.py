# Declaration: This code is for learning and research purposes only. Users must adhere to the following principles:  
# 1. Do not use for any commercial purposes.  
# 2. Comply with the target platform's terms of use and robots.txt rules.  
# 3. Do not perform large-scale crawling or disrupt platform operations.  
# 4. Reasonably control request frequency to avoid unnecessary burden on the target platform.   
# 5. Do not use for any illegal or improper purposes.
#   
# For detailed license terms, please refer to the LICENSE file in the project root directory.  
# Using this code indicates your agreement to abide by the above principles and all terms in the LICENSE.  


# -*- coding: utf-8 -*-
# @Author  : relakkes@gmail.com
# @Name    : Programmer Ajiang-Relakkes
# @Time    : 2024/6/2 11:05
# @Desc    : Local cache

import asyncio
import time
from typing import Any, Dict, List, Optional, Tuple

from cache.abs_cache import AbstractCache


class ExpiringLocalCache(AbstractCache):

    def __init__(self, cron_interval: int = 10):
        """
        Initialize local cache
        :param cron_interval: Interval for clearing cache
        :return:
        """
        self._cron_interval = cron_interval
        self._cache_container: Dict[str, Tuple[Any, float]] = {}
        self._cron_task: Optional[asyncio.Task] = None
        # Start scheduled cleanup task
        self._schedule_clear()

    def __del__(self):
        """
        Destructor, clear scheduled task
        :return:
        """
        if self._cron_task is not None:
            self._cron_task.cancel()

    def get(self, key: str) -> Optional[Any]:
        """
        Get value of key from cache
        :param key:
        :return:
        """
        value, expire_time = self._cache_container.get(key, (None, 0))
        if value is None:
            return None

        # If key has expired, delete key and return None
        if expire_time < time.time():
            del self._cache_container[key]
            return None

        return value

    def set(self, key: str, value: Any, expire_time: int) -> None:
        """
        Set value of key into cache
        :param key:
        :param value:
        :param expire_time:
        :return:
        """
        self._cache_container[key] = (value, time.time() + expire_time)

    def keys(self, pattern: str) -> List[str]:
        """
        Get all keys matching pattern
        :param pattern: Matching pattern
        :return:
        """
        if pattern == '*':
            return list(self._cache_container.keys())

        # Local cache wildcard temporarily replaces * with empty
        if '*' in pattern:
            pattern = pattern.replace('*', '')

        return [key for key in self._cache_container.keys() if pattern in key]

    def _schedule_clear(self):
        """
        Start scheduled cleanup task
        :return:
        """

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        self._cron_task = loop.create_task(self._start_clear_cron())

    def _clear(self):
        """
        Clear cache based on expiration time
        :return:
        """
        for key, (value, expire_time) in self._cache_container.items():
            if expire_time < time.time():
                del self._cache_container[key]

    async def _start_clear_cron(self):
        """
        Start scheduled cleanup task
        :return:
        """
        while True:
            self._clear()
            await asyncio.sleep(self._cron_interval)


if __name__ == '__main__':
    cache = ExpiringLocalCache(cron_interval=2)
    cache.set('name', 'Programmer Ajiang-Relakkes', 3)
    print(cache.get('key'))
    print(cache.keys("*"))
    time.sleep(4)
    print(cache.get('key'))
    del cache
    time.sleep(1)
    print("done")
