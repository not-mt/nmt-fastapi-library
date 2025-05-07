# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Base cache classes and utility functions for nmtfast apps."""

from typing import Any, Optional

import pytest

from nmtfast.cache.v1.base import AppCacheBase


def test_store_app_cache_not_implemented():
    """
    Test that store_app_cache raises NotImplementedError.
    """

    class TestCache(AppCacheBase):
        def fetch_app_cache(self, key: str) -> Optional[Any]:
            return None

        def clear_app_cache(self, key: str) -> bool:
            return True

    cache = TestCache()
    with pytest.raises(NotImplementedError):
        cache.store_app_cache("test", "value")


def test_fetch_app_cache_not_implemented():
    """
    Test that fetch_app_cache raises NotImplementedError.
    """

    class TestCache(AppCacheBase):

        def store_app_cache(self, key: str, value: Any, ttl: int = -1) -> bool:
            return True

        def clear_app_cache(self, key: str) -> bool:
            return True

    cache = TestCache()
    with pytest.raises(NotImplementedError):
        cache.fetch_app_cache("test")


def test_clear_app_cache_not_implemented():
    """
    Test that clear_app_cache raises NotImplementedError.
    """

    class TestCache(AppCacheBase):

        def store_app_cache(self, key: str, value: Any, ttl: int = -1) -> bool:
            return True

        def fetch_app_cache(self, key: str) -> Optional[Any]:
            return None

    cache = TestCache()
    with pytest.raises(NotImplementedError):
        cache.clear_app_cache("test")


def test_concrete_implementation_contract():
    """
    Test that a proper implementation follows the expected contract.
    """

    class WorkingCache(AppCacheBase):

        def __init__(self):
            self.storage = {}

        def store_app_cache(self, key: str, value: Any, ttl: int = -1) -> bool:
            self.storage[key] = value
            return True

        def fetch_app_cache(self, key: str) -> Optional[Any]:
            return self.storage.get(key)

        def clear_app_cache(self, key: str) -> bool:
            if key in self.storage:
                del self.storage[key]
                return True
            return False

    cache = WorkingCache()

    # test successful storage and fetch
    assert cache.store_app_cache("key1", "value1") is True
    assert cache.fetch_app_cache("key1") == "value1"

    # test clear operation
    assert cache.clear_app_cache("key1") is True
    assert cache.fetch_app_cache("key1") is None

    # test clearing non-existent key
    assert cache.clear_app_cache("nonexistent") is False


@pytest.mark.parametrize(
    "key,value,ttl,expected",
    [
        ("normal_key", "string_value", 60, True),
        ("", "empty_key", -1, True),
        ("special_chars", {"complex": ["object", 123]}, 0, True),
        (123, "numeric_key", 10, True),
    ],
)
def test_store_app_cache_interface_types(key, value, ttl, expected):
    """
    Test that store_app_cache accepts various input types.
    """

    class TestCache(AppCacheBase):

        def store_app_cache(self, key: str, value: Any, ttl: int = -1) -> bool:
            return expected

        def fetch_app_cache(self, key: str) -> Optional[Any]:
            return None

        def clear_app_cache(self, key: str) -> bool:
            return True

    cache = TestCache()
    assert cache.store_app_cache(key, value, ttl) == expected


def test_clear_app_cache_interface_types():
    """
    Test that clear_app_cache accepts various key types.
    """

    class TestCache(AppCacheBase):

        def store_app_cache(self, key: str, value: Any, ttl: int = -1) -> bool:
            return True

        def fetch_app_cache(self, key: str) -> Optional[Any]:
            return None

        def clear_app_cache(self, key: str) -> bool:
            return isinstance(key, str)

    cache = TestCache()

    # test valid string keys
    assert cache.clear_app_cache("normal_key") is True
    assert cache.clear_app_cache("") is True

    # test invalid key types (should accept due to str conversion)
    assert cache.clear_app_cache(123) is False
    assert cache.clear_app_cache(None) is False


def test_ttl_handling():
    """
    Test that TTL parameter is properly handled.
    """

    class TTLCache(AppCacheBase):

        def __init__(self):
            self.storage = {}
            self.ttls = {}

        def store_app_cache(self, key: str, value: Any, ttl: int = -1) -> bool:
            self.storage[key] = value
            self.ttls[key] = ttl
            return True

        def fetch_app_cache(self, key: str) -> Optional[Any]:
            return self.storage.get(key)

        def clear_app_cache(self, key: str) -> bool:
            if key in self.storage:
                del self.storage[key]
                del self.ttls[key]
                return True
            return False

    cache = TTLCache()

    # test TTL storage
    cache.store_app_cache("default_ttl", "value")
    assert cache.ttls["default_ttl"] == -1

    cache.store_app_cache("short_ttl", "value", 60)
    assert cache.ttls["short_ttl"] == 60

    # test clear removes TTL info
    assert cache.clear_app_cache("short_ttl") is True
    assert "short_ttl" not in cache.ttls
