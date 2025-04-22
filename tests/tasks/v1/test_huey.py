# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Tests for Huey background task helpers."""

from unittest.mock import MagicMock

from huey import Huey
from huey.exceptions import TaskException
from huey.storage import MemoryStorage, RedisStorage

from nmtfast.tasks.v1.huey import (
    fetch_task_metadata,
    fetch_task_result,
    store_task_metadata,
)


def test_store_task_metadata(mock_huey):
    """
    Test storing metadata with Redis storage.
    """
    mock_huey.storage = MagicMock(spec=RedisStorage)
    mock_huey.storage.name = "test_app"
    mock_huey.storage.conn = MagicMock()

    result = store_task_metadata(mock_huey, "test123", {"status": "running"})

    assert result is True
    mock_huey.put.assert_called_once_with("md_test123", {"status": "running"})
    mock_huey.storage.conn.expire.assert_called_once()


def test_store_task_metadata_non_redis():
    """
    Test with explicit non-Redis storage.
    """
    huey = MagicMock(spec=Huey)
    huey.storage = MagicMock(spec=MemoryStorage)

    result = store_task_metadata(huey, "test123", {"status": "running"})

    assert result is True
    huey.put.assert_called_once()
    assert not hasattr(huey.storage, "conn")


def test_fetch_task_metadata_found(mock_huey):
    """
    Test fetching existing metadata.
    """
    mock_huey.get.return_value = {"status": "complete"}

    result = fetch_task_metadata(mock_huey, "test123")

    assert result == {"status": "complete"}
    mock_huey.get.assert_called_once_with(key="md_test123", peek=True)


def test_fetch_task_metadata_not_found(mock_huey):
    """
    Test fetching non-existent metadata.
    """
    mock_huey.get.return_value = None

    result = fetch_task_metadata(mock_huey, "test123")

    assert result is None
    mock_huey.get.assert_called_once()


def test_fetch_task_result_success(mock_huey):
    """
    Test fetching successful task result.
    """
    mock_huey.result.return_value = {"output": "success"}

    result = fetch_task_result(mock_huey, "test123")

    assert result == {"output": "success"}
    mock_huey.result.assert_called_once_with("test123", preserve=True)


def test_fetch_task_result_exception(mock_huey):
    """
    Test fetching failed task result.
    """
    mock_huey.result.side_effect = TaskException("Failed")
    mock_huey.get.return_value = {"error": "failed"}

    result = fetch_task_result(mock_huey, "test123")

    assert result == {"error": "failed"}
    mock_huey.result.assert_called_once()
    mock_huey.get.assert_called_once()
