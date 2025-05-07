# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Helper classes and functions for caching using Huey as cache backend."""

import json
import logging
import zlib
from typing import Any, Optional

from huey import Huey
from huey.storage import RedisStorage
from tenacity import retry, stop_after_attempt, wait_fixed

from nmtfast.cache.v1.base import AppCacheBase
from nmtfast.retry.v1.tenacity import tenacity_retry_log

logger = logging.getLogger(__name__)


class HueyAppCache(AppCacheBase):
    """
    Caching implementation that uses Huey as backend storage.

    Args:
        huey_app: The Huey instance to use as backend
        name: Prefix for all keys stored in the cache
        default_ttl: Default TTL for cached items, in seconds
        compress_threshold: Minimum size in bytes to compress (default: 4096)

    Attributes:
        COMPRESSION_HEADER: Byte string identifying compressed data (default: b'zlib1:')
    """

    COMPRESSION_HEADER = b"zlib1:"

    def __init__(
        self,
        huey_app: Huey,
        name: str,
        default_ttl: int,
        compress_threshold: int = 4096,
    ) -> None:
        self.huey_app: Huey = huey_app
        self.name: str = name
        self.default_ttl: int = default_ttl
        self.compress_threshold: int = compress_threshold
        logger.debug(
            "Initialized HueyAppCache with compression "
            f"threshold of {compress_threshold} bytes"
        )

    def _get_storage_keyname(self, key: str) -> str:
        """
        Construct the full key name used in backend storage.
        """
        return f"app_cache_{self.name}_{key}"

    def _prepare_data(self, data: bytes) -> bytes:
        """
        Prepare bytes data for storage by optionally compressing based on size.

        Args:
            data: Input data (must be bytes)

        Returns:
            bytes: Prepared bytes data (compressed if over threshold)

        Raises:
            TypeError: Raised if the input data is not bytes
        """
        if not isinstance(data, bytes):
            raise TypeError("Input data must be bytes, got {}".format(type(data)))

        logger.debug(f"Preparing data for storage. Original size: {len(data)} bytes")

        # only compress if over threshold
        if len(data) >= self.compress_threshold:
            compressed = zlib.compress(data)
            compression_ratio = len(data) / len(compressed)
            logger.debug(
                f"Compressing data (threshold: {self.compress_threshold} bytes). "
                f"Compressed size: {len(compressed)} bytes (ratio: {compression_ratio:.1f}x)"
            )
            return self.COMPRESSION_HEADER + compressed

        logger.debug("Data below compression threshold, storing uncompressed")
        return data

    def _restore_data(self, data: bytes) -> bytes:
        """
        Restore bytes data by decompressing if it was compressed.

        Args:
            data: Bytes data from cache, optionally compressed

        Returns:
            bytes: Original bytes data (decompressed if needed)

        Raises:
            TypeError: If input is not bytes
            zlib.error: If compressed data is corrupted
        """
        if not isinstance(data, bytes):
            raise TypeError(f"Cache data must be bytes, got {type(data)}")

        if data.startswith(self.COMPRESSION_HEADER):
            original_size = len(data)
            try:
                decompressed = zlib.decompress(data[len(self.COMPRESSION_HEADER) :])
                logger.debug(
                    f"Decompressed data. Original size: {original_size} bytes, "
                    f"Decompressed size: {len(decompressed)} bytes"
                )
                return decompressed
            except zlib.error as exc:
                logger.warning(f"Decompression failed: {exc}")
                raise  # re-raise to let caller handle corrupted data

        logger.debug("Data was not compressed, returning as-is")
        return data

    @retry(
        reraise=True,
        stop=stop_after_attempt(5),
        wait=wait_fixed(0.001),
        after=tenacity_retry_log(logger),
    )
    def store_app_cache(self, key: str, value: Any, ttl: int = -1) -> bool:
        """
        Store or replace cache data in the Huey backend.

        Automatically serializes non-bytes values to JSON-encoded bytes. For bytes input,
        stores directly with optional compression based on size thresholds.

        Args:
            key: Cache key identifier as string.
            value: Data to store. Can be any JSON-serializable object or raw bytes.
            ttl: Time-to-live in seconds. Uses default TTL if <= 0.

        Returns:
            bool: True if storage was successful.

        Raises:
            ValueError: If value cannot be JSON-serialized (for non-bytes input).
            RuntimeError: If underlying storage operation fails after retries.
        """
        ttl = ttl if ttl > 0 else self.default_ttl
        logger.debug(f"Storing key '{key}' (TTL: {ttl}s)")
        storage_keyname = self._get_storage_keyname(key)

        # convert value to bytes if not already
        if isinstance(value, bytes):
            prepared_value = value
        elif isinstance(value, str):
            prepared_value = value.encode("utf-8")
        else:
            try:
                prepared_value = json.dumps(value).encode("utf-8")
            except (TypeError, ValueError) as exc:
                logger.error(f"Failed to serialize value for key '{key}': {exc}")
                raise ValueError(
                    "Value must be JSON-serializable or bytes type"
                ) from exc

        try:
            prepared_value = self._prepare_data(prepared_value)
            self.huey_app.put(storage_keyname, prepared_value)

            if isinstance(self.huey_app.storage, RedisStorage):
                app_name = self.huey_app.storage.name
                redis_key = f"huey.r.{app_name}.{storage_keyname}"
                self.huey_app.storage.conn.expire(redis_key, ttl)

            return True
        except Exception as exc:
            logger.error(f"Failed to store value for key '{key}': {exc}")
            raise RuntimeError("Cache storage operation failed") from exc

    @retry(
        reraise=True,
        stop=stop_after_attempt(5),
        wait=wait_fixed(0.001),
        after=tenacity_retry_log(logger),
    )
    def fetch_app_cache(self, key: str) -> Optional[Any]:
        """
        Fetch cached data from the Huey backend.
        """
        logger.debug(f"Fetching data for key '{key}'")
        storage_keyname = self._get_storage_keyname(key)

        cache_value = self.huey_app.get(key=storage_keyname, peek=True)
        if not cache_value:
            logger.warning(f"No cache entry found for storage key '{storage_keyname}'")
            return None

        return self._restore_data(cache_value)

    @retry(
        reraise=True,
        stop=stop_after_attempt(5),
        wait=wait_fixed(0.001),
        after=tenacity_retry_log(logger),
    )
    def clear_app_cache(self, key: str) -> bool:
        """
        Clear cached data from the Huey backend.
        """
        logger.debug(f"Clearing data for key '{key}'")
        storage_keyname = self._get_storage_keyname(key)

        if not self.huey_app.delete(key=storage_keyname):
            logger.warning(f"Failed to delete storage key '{storage_keyname}'")
            return False

        logger.debug(f"Cleared data for key '{key}'")

        return True
