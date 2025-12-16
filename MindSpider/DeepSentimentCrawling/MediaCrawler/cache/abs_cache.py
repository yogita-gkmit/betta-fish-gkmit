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
# @Time    : 2024/6/2 11:06
# @Desc    : Abstract class

from abc import ABC, abstractmethod
from typing import Any, List, Optional


class AbstractCache(ABC):

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """
        Get value of key from cache.
        This is an abstract method. Subclasses must implement this method.
        :param key: Key
        :return:
        """
        raise NotImplementedError

    @abstractmethod
    def set(self, key: str, value: Any, expire_time: int) -> None:
        """
        Set value of key into cache.
        This is an abstract method. Subclasses must implement this method.
        :param key: Key
        :param value: Value
        :param expire_time: Expire time
        :return:
        """
        raise NotImplementedError

    @abstractmethod
    def keys(self, pattern: str) -> List[str]:
        """
        Get all keys matching pattern
        :param pattern: Matching pattern
        :return:
        """
        raise NotImplementedError
