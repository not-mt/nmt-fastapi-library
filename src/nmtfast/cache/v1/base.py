# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Base classes which can be used for app cache implementations."""

from typing import Any, Optional


class AppCacheBase:
    """Base class for cache implementations."""

    def store_app_cache(self, key: str, value: Any, ttl: int = -1) -> bool:
        """
        Store/replace cache data in backend storage.

        Args:
            key: The cache key.
            value: The value to cache.
            ttl: Time-to-live override (in seconds).

        Raises:
            NotImplementedError: Raised if subclass does not implement this method.

        Returns:
            bool: True if the operation was successful.
        """
        raise NotImplementedError

    def fetch_app_cache(self, key: str) -> Optional[Any]:
        """
        Fetch cache data from backend storage.

        Args:
            key: The cache key.

        Raises:
            NotImplementedError: Raised if subclass does not implement this method.

        Returns:
            Optional[Any]: The cached value, or None if not found.
        """
        raise NotImplementedError

    def clear_app_cache(self, key: str) -> bool:
        """
        Clear cached data from backend storage.

        Args:
            key: The cache key to clear.

        Raises:
            NotImplementedError: Raised if subclass does not implement this method.

        Returns:
            bool: True if the operation was successful.
        """
        raise NotImplementedError
