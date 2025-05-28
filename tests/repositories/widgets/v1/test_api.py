# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Tests for widget repository methods."""

from unittest.mock import AsyncMock

import httpx
import pytest

from nmtfast.repositories.widgets.v1.api import WidgetApiRepository
from nmtfast.repositories.widgets.v1.exceptions import WidgetApiException
from nmtfast.repositories.widgets.v1.schemas import (
    WidgetCreate,
    WidgetRead,
    WidgetZap,
    WidgetZapTask,
)


@pytest.fixture
def fake_api_client():
    """Create a fake httpx.AsyncClient mock."""
    client = AsyncMock(spec=httpx.AsyncClient)
    return client


@pytest.mark.asyncio
async def test_widget_create_success(fake_api_client):
    """Test successful widget creation."""
    repo = WidgetApiRepository(fake_api_client)
    widget_in = WidgetCreate(name="test")

    mock_response = WidgetRead(id=1, name="test").model_dump()

    fake_api_client.post.return_value = httpx.Response(
        status_code=201,
        json=mock_response,
    )
    fake_api_client.post.return_value.json = lambda **kwargs: mock_response

    widget_out = await repo.widget_create(widget_in)
    assert isinstance(widget_out, WidgetRead)
    assert widget_out.id == 1


@pytest.mark.asyncio
async def test_widget_create_failure_raises(fake_api_client):
    """Test widget_create raises WidgetApiException on failure."""
    repo = WidgetApiRepository(fake_api_client)
    widget_in = WidgetCreate(name="fail")

    fake_api_client.post.return_value = httpx.Response(
        status_code=400, text="Bad request"
    )

    with pytest.raises(WidgetApiException):
        await repo.widget_create(widget_in)


@pytest.mark.asyncio
async def test_get_by_id_success(fake_api_client):
    """Test successful get_by_id."""
    repo = WidgetApiRepository(fake_api_client)

    mock_response = WidgetRead(id=2, name="found").model_dump()

    fake_api_client.get.return_value = httpx.Response(
        status_code=200,
        json=mock_response,
    )
    fake_api_client.get.return_value.json = lambda **kwargs: mock_response

    widget = await repo.get_by_id(2)
    assert isinstance(widget, WidgetRead)
    assert widget.id == 2


@pytest.mark.asyncio
async def test_get_by_id_failure_raises(fake_api_client):
    """Test get_by_id raises WidgetApiException on failure."""
    repo = WidgetApiRepository(fake_api_client)

    fake_api_client.get.return_value = httpx.Response(status_code=404, text="Not found")

    with pytest.raises(WidgetApiException):
        await repo.get_by_id(999)


@pytest.mark.asyncio
async def test_widget_zap_success(fake_api_client):
    """Test successful widget_zap."""
    repo = WidgetApiRepository(fake_api_client)
    payload = WidgetZap(duration=10)

    mock_response = WidgetZapTask(
        uuid="uuid-123",
        state="PENDING",
        id=1,
        duration=10,
        runtime=0,
    ).model_dump()

    fake_api_client.post.return_value = httpx.Response(
        status_code=202,
        json=mock_response,
    )
    fake_api_client.post.return_value.json = lambda **kwargs: mock_response

    task = await repo.widget_zap(1, payload)
    assert isinstance(task, WidgetZapTask)
    assert task.uuid == "uuid-123"


@pytest.mark.asyncio
async def test_widget_zap_failure_raises(fake_api_client):
    """Test widget_zap raises WidgetApiException on failure."""
    repo = WidgetApiRepository(fake_api_client)
    payload = WidgetZap(duration=10)

    fake_api_client.post.return_value = httpx.Response(status_code=400, text="Bad zap")

    with pytest.raises(WidgetApiException):
        await repo.widget_zap(1, payload)


@pytest.mark.asyncio
async def test_widget_zap_by_uuid_success(fake_api_client):
    """Test successful widget_zap_by_uuid."""
    repo = WidgetApiRepository(fake_api_client)

    mock_response = WidgetZapTask(
        uuid="uuid-456",
        state="SUCCESS",
        id=1,
        duration=10,
        runtime=123,
    ).model_dump()

    fake_api_client.post.return_value = httpx.Response(
        status_code=200,
        json=mock_response,
    )
    fake_api_client.post.return_value.json = lambda **kwargs: mock_response

    task = await repo.widget_zap_by_uuid(1, "uuid-456")
    assert isinstance(task, WidgetZapTask)
    assert task.uuid == "uuid-456"


@pytest.mark.asyncio
async def test_widget_zap_by_uuid_failure_raises(fake_api_client):
    """Test widget_zap_by_uuid raises WidgetApiException on failure."""
    repo = WidgetApiRepository(fake_api_client)

    fake_api_client.post.return_value = httpx.Response(
        status_code=404, text="Not found"
    )

    with pytest.raises(WidgetApiException):
        await repo.widget_zap_by_uuid(1, "uuid-999")
