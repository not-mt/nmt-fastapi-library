# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Huey cache classes and utility functions for nmtfast apps."""

import json
import zlib
from unittest.mock import Mock

import pytest
from huey import Huey
from huey.storage import RedisStorage, SqliteStorage

from nmtfast.cache.v1.huey import HueyAppCache


@pytest.fixture
def mock_huey_redis():
    """
    Fixture providing a fully mocked Huey instance with RedisStorage.
    """
    huey = Mock(spec=Huey)

    huey.storage = Mock(spec=RedisStorage)
    huey.storage.name = "test-redis"
    huey.storage.conn = Mock()

    huey.put = Mock(return_value=True)
    huey.get = Mock(return_value=None)
    huey.delete = Mock(return_value=True)

    return huey


@pytest.fixture
def mock_huey_sqlite():
    """
    Fixture providing a Huey instance with SqliteStorage.
    """
    huey = Mock(spec=Huey)
    storage = Mock(spec=SqliteStorage)

    # NOTE: ensure no conn attribute exists
    if hasattr(storage, "conn"):
        delattr(storage, "conn")

    huey.storage = storage
    huey.put = Mock(return_value=True)
    huey.get = Mock(return_value=None)
    huey.delete = Mock(return_value=True)

    return huey


def test_initialization(mock_huey_redis):
    """
    Test that HueyAppCache initializes correctly.
    """
    cache = HueyAppCache(mock_huey_redis, "test_cache", 3600, compress_threshold=8192)

    assert cache.name == "test_cache"
    assert cache.default_ttl == 3600
    assert cache.compress_threshold == 8192
    assert cache.huey_app == mock_huey_redis


def test_get_storage_keyname(mock_huey_redis):
    """
    Test the key name generation.
    """
    cache = HueyAppCache(mock_huey_redis, "test_cache", 3600)

    assert cache._get_storage_keyname("key") == "app_cache_test_cache_key"
    assert cache._get_storage_keyname("") == "app_cache_test_cache_"


def test_store_app_cache_with_redis(mock_huey_redis):
    """
    Test storing with RedisStorage including TTL setting.
    """
    cache = HueyAppCache(mock_huey_redis, "test_cache", 3600)
    test_value = b"value1"

    assert cache.store_app_cache("key1", test_value) is True

    mock_huey_redis.put.assert_called_once()
    args, _ = mock_huey_redis.put.call_args
    assert args[0] == "app_cache_test_cache_key1"
    assert isinstance(args[1], bytes)
    mock_huey_redis.storage.conn.expire.assert_called_once_with(
        "huey.r.test-redis.app_cache_test_cache_key1", 3600
    )


def test_store_app_cache_with_sqlite(mock_huey_sqlite):
    """
    Test storing with SqliteStorage (no TTL support).
    """
    cache = HueyAppCache(mock_huey_sqlite, "test_cache", 3600)
    test_value = b"value1"

    assert cache.store_app_cache("key1", test_value) is True

    mock_huey_sqlite.put.assert_called_once()
    args, _ = mock_huey_sqlite.put.call_args
    assert args[0] == "app_cache_test_cache_key1"
    assert isinstance(args[1], bytes)
    assert not hasattr(mock_huey_sqlite.storage, "conn")


def test_store_app_cache_with_custom_ttl(mock_huey_redis):
    """
    Test storing with custom TTL.
    """
    cache = HueyAppCache(mock_huey_redis, "test_cache", 3600)
    test_value = b"value1"

    assert cache.store_app_cache("key1", test_value, 60) is True
    mock_huey_redis.storage.conn.expire.assert_called_once_with(
        "huey.r.test-redis.app_cache_test_cache_key1", 60
    )


def test_fetch_app_cache_hit(mock_huey_redis):
    """
    Test successful cache fetch.
    """
    test_value = b"cached_value"
    mock_huey_redis.get.return_value = test_value
    cache = HueyAppCache(mock_huey_redis, "test_cache", 3600)

    result = cache.fetch_app_cache("existing_key")

    assert result == test_value
    mock_huey_redis.get.assert_called_once_with(
        key="app_cache_test_cache_existing_key", peek=True
    )


def test_fetch_app_cache_miss(mock_huey_redis):
    """
    Test cache miss scenario.
    """
    mock_huey_redis.get.return_value = None
    cache = HueyAppCache(mock_huey_redis, "test_cache", 3600)

    result = cache.fetch_app_cache("missing_key")
    assert result is None


def test_store_app_cache_retry(mock_huey_redis):
    """
    Test retry behavior on store operations.
    """
    test_value = b"value"
    mock_huey_redis.put.side_effect = [Exception("Error 1"), Exception("Error 2"), True]
    cache = HueyAppCache(mock_huey_redis, "test_cache", 3600)

    assert cache.store_app_cache("key", test_value) is True
    assert mock_huey_redis.put.call_count == 3


def test_fetch_app_cache_retry(mock_huey_redis):
    """
    Test retry behavior on fetch operations.
    """
    test_value = b"success"
    mock_huey_redis.get.side_effect = [
        Exception("Error 1"),
        Exception("Error 2"),
        test_value,
    ]
    cache = HueyAppCache(mock_huey_redis, "test_cache", 3600)

    assert cache.fetch_app_cache("key") == test_value
    assert mock_huey_redis.get.call_count == 3


def test_store_app_cache_complex_object(mock_huey_redis):
    """
    Test storage of complex Python objects with JSON serialization.

    Verifies that:
      1. Complex objects are properly serialized to bytes
      2. JSON round-trip produces equivalent Python objects
      3. Tuples are converted to lists (JSON limitation)
    """
    # Create test data with tuple that will become list after JSON round-trip
    original_obj = {"list": [1, 2, 3], "dict": {"a": 1}, "nested": {"tuple": (1, 2)}}
    cache = HueyAppCache(mock_huey_redis, "test_cache", 3600)

    assert cache.store_app_cache("complex", original_obj) is True
    mock_huey_redis.put.assert_called_once()

    args, _ = mock_huey_redis.put.call_args
    assert args[0] == "app_cache_test_cache_complex"
    assert isinstance(args[1], bytes)

    # verify round-trip with JSON tuple->list conversion
    stored_data = args[1]
    if stored_data.startswith(HueyAppCache.COMPRESSION_HEADER):
        stored_data = zlib.decompress(
            stored_data[len(HueyAppCache.COMPRESSION_HEADER) :]
        )

    # create expected object with tuples converted to lists
    expected_obj = {
        "list": [1, 2, 3],
        "dict": {"a": 1},
        "nested": {"tuple": [1, 2]},  # Note list instead of tuple
    }
    assert json.loads(stored_data.decode("utf-8")) == expected_obj


def test_store_app_cache_with_bytes(mock_huey_redis):
    """
    Test storing raw bytes.
    """
    cache = HueyAppCache(mock_huey_redis, "test_cache", 3600)
    data = b"raw_bytes"

    assert cache.store_app_cache("bytes", data) is True

    mock_huey_redis.put.assert_called_once()
    args, _ = mock_huey_redis.put.call_args

    assert args[1] == data or args[1].endswith(data)  # possible compression


def test_store_app_cache_with_string(mock_huey_redis):
    """
    Test storing regular string.
    """
    cache = HueyAppCache(mock_huey_redis, "test_cache", 3600)
    data = "regular string"

    assert cache.store_app_cache("string", data) is True

    args, _ = mock_huey_redis.put.call_args
    stored = args[1]

    if stored.startswith(HueyAppCache.COMPRESSION_HEADER):
        stored = zlib.decompress(stored[len(HueyAppCache.COMPRESSION_HEADER) :])

    assert stored == data.encode("utf-8")


def test_store_app_cache_with_json_string(mock_huey_redis):
    """
    Test storing string that happens to be JSON.
    """
    cache = HueyAppCache(mock_huey_redis, "test_cache", 3600)
    data = '{"key": "value"}'  # Valid JSON string

    assert cache.store_app_cache("json", data) is True

    args, _ = mock_huey_redis.put.call_args
    stored = args[1]
    if stored.startswith(HueyAppCache.COMPRESSION_HEADER):
        stored = zlib.decompress(stored[len(HueyAppCache.COMPRESSION_HEADER) :])

    assert stored == data.encode("utf-8")  # Not double-encoded


def test_store_app_cache_serialization_errors(mock_huey_redis):
    """
    Test error handling for non-serializable values in store_app_cache.
    """
    cache = HueyAppCache(mock_huey_redis, "test_cache", 3600)

    # create test cases that will DEFINITELY fail JSON serialization
    class Unserializable:
        pass

    test_cases = [
        # custom class instance that will not work
        ("raw_object", Unserializable()),
        # function object
        ("function", lambda x: x),
        # class type object
        ("class_type", Unserializable),
    ]

    for key, value in test_cases:
        with pytest.raises(ValueError) as excinfo:
            cache.store_app_cache(key, value)

        assert isinstance(excinfo.value.__cause__, TypeError)


def test_prepare_data_compression(mock_huey_redis):
    """
    Test data preparation with compression.
    """
    cache = HueyAppCache(mock_huey_redis, "test_cache", 3600, compress_threshold=10)
    large_data = b"a" * 100  # Should be compressed

    result = cache._prepare_data(large_data)

    assert result.startswith(HueyAppCache.COMPRESSION_HEADER)
    assert len(result) < len(large_data)


def test_prepare_data_no_compression(mock_huey_redis):
    """
    Test data preparation without compression.
    """
    cache = HueyAppCache(mock_huey_redis, "test_cache", 3600, compress_threshold=1000)
    small_data = b"a" * 10  # Should not be compressed

    result = cache._prepare_data(small_data)

    assert not result.startswith(HueyAppCache.COMPRESSION_HEADER)
    assert result == small_data


def test_prepare_data_invalid_type(mock_huey_redis):
    """
    Test type validation in _prepare_data.

    Verifies that:
      1. Non-bytes inputs raise TypeError
      2. Error message includes the actual type
      3. Valid bytes inputs pass through
    """
    cache = HueyAppCache(mock_huey_redis, "test_cache", 3600)

    invalid_inputs = [
        "string input",
        12345,
        {"key": "value"},
        None,
        ["list", "of", "strings"],
    ]

    for invalid in invalid_inputs:
        with pytest.raises(TypeError) as excinfo:
            cache._prepare_data(invalid)  # type: ignore
        assert str(type(invalid)) in str(excinfo.value)


def test_restore_data_compressed(mock_huey_redis):
    """
    Test restoring compressed data.
    """
    cache = HueyAppCache(mock_huey_redis, "test_cache", 3600)
    original_data = b"test data"
    compressed = zlib.compress(original_data)
    compressed_data = HueyAppCache.COMPRESSION_HEADER + compressed

    result = cache._restore_data(compressed_data)

    assert result == original_data


def test_restore_data_uncompressed(mock_huey_redis):
    """
    Test restoring uncompressed data.
    """
    cache = HueyAppCache(mock_huey_redis, "test_cache", 3600)
    original_data = b"test data"

    result = cache._restore_data(original_data)

    assert result == original_data


def test_restore_data_invalid_type(mock_huey_redis):
    """
    Test restoring with invalid data type.
    """
    cache = HueyAppCache(mock_huey_redis, "test_cache", 3600)

    with pytest.raises(TypeError):
        cache._restore_data("not bytes")  # type: ignore


def test_restore_data_corrupted_compressed(mock_huey_redis, caplog):
    """
    Test corrupted data handling with logging verification.
    """
    cache = HueyAppCache(mock_huey_redis, "test_cache", 3600)

    # create corrupted data that looks like compressed data
    fake_header = cache.COMPRESSION_HEADER
    corrupted = fake_header + b"invalid_compressed_content"

    with pytest.raises(zlib.error):
        cache._restore_data(corrupted)


def test_clear_app_cache(mock_huey_redis):
    """
    Test clearing cache data.
    """
    cache = HueyAppCache(mock_huey_redis, "test_cache", 3600)

    assert cache.clear_app_cache("key1") is True
    mock_huey_redis.delete.assert_called_once_with(key="app_cache_test_cache_key1")


def test_clear_app_cache_failure(mock_huey_redis):
    """
    Test cache clearing failure scenario.
    """
    mock_huey_redis.delete.return_value = False
    cache = HueyAppCache(mock_huey_redis, "test_cache", 3600)

    assert cache.clear_app_cache("key1") is False
