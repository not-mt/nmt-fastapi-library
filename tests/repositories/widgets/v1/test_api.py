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
    WidgetUpdate,
    WidgetZap,
    WidgetZapTask,
)


@pytest.fixture
def fake_api_client():
    """
    Create a fake httpx.AsyncClient mock.
    """
    client = AsyncMock(spec=httpx.AsyncClient)
    return client


@pytest.mark.asyncio
async def test_widget_create_success(fake_api_client):
    """
    Test successful widget creation.
    """
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
    """
    Test widget_create raises WidgetApiException on failure.
    """
    repo = WidgetApiRepository(fake_api_client)
    widget_in = WidgetCreate(name="fail")

    fake_api_client.post.return_value = httpx.Response(
        status_code=400, text="Bad request"
    )

    with pytest.raises(WidgetApiException):
        await repo.widget_create(widget_in)


@pytest.mark.asyncio
async def test_get_by_id_success(fake_api_client):
    """
    Test successful get_by_id.
    """
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
    """
    Test get_by_id raises WidgetApiException on failure.
    """
    repo = WidgetApiRepository(fake_api_client)
    fake_api_client.get.return_value = httpx.Response(status_code=404, text="Not found")

    with pytest.raises(WidgetApiException):
        await repo.get_by_id(999)


@pytest.mark.asyncio
async def test_widget_zap_success(fake_api_client):
    """
    Test successful widget_zap.
    """
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
    """
    Test widget_zap raises WidgetApiException on failure.
    """
    repo = WidgetApiRepository(fake_api_client)
    payload = WidgetZap(duration=10)

    fake_api_client.post.return_value = httpx.Response(status_code=400, text="Bad zap")

    with pytest.raises(WidgetApiException):
        await repo.widget_zap(1, payload)


@pytest.mark.asyncio
async def test_widget_zap_by_uuid_success(fake_api_client):
    """
    Test successful widget_zap_by_uuid.
    """
    repo = WidgetApiRepository(fake_api_client)
    mock_response_data = WidgetZapTask(
        uuid="uuid-456",
        state="SUCCESS",
        id=1,
        duration=10,
        runtime=123,
    ).model_dump()

    fake_api_client.get.return_value = httpx.Response(
        status_code=200,
        json=mock_response_data,
    )
    fake_api_client.get.return_value.json = lambda **kwargs: mock_response_data

    task = await repo.widget_zap_by_uuid(1, "uuid-456")

    assert isinstance(task, WidgetZapTask)
    assert task.uuid == "uuid-456"
    assert task.state == "SUCCESS"


@pytest.mark.asyncio
async def test_widget_zap_by_uuid_failure_raises(fake_api_client):
    """
    Test widget_zap_by_uuid raises WidgetApiException on failure.
    """
    repo = WidgetApiRepository(fake_api_client)
    fake_api_client.get.return_value = httpx.Response(status_code=404, text="Not found")

    with pytest.raises(WidgetApiException):
        await repo.widget_zap_by_uuid(1, "uuid-999")


@pytest.mark.asyncio
async def test_get_all_success(fake_api_client):
    """
    Test successful get_all with pagination.
    """
    repo = WidgetApiRepository(fake_api_client)
    mock_list = [
        WidgetRead(id=1, name="a").model_dump(),
        WidgetRead(id=2, name="b").model_dump(),
    ]

    resp = httpx.Response(status_code=200, json=mock_list)
    resp.json = lambda **kwargs: mock_list
    resp.headers["X-Total-Count"] = "5"
    fake_api_client.get.return_value = resp

    widgets, pagination = await repo.get_all(page=1, page_size=2)
    assert len(widgets) == 2
    assert pagination.total == 5
    assert pagination.page == 1
    assert pagination.page_size == 2


@pytest.mark.asyncio
async def test_get_all_with_search(fake_api_client):
    """
    Test get_all passes search parameter.
    """
    repo = WidgetApiRepository(fake_api_client)
    mock_list = [WidgetRead(id=1, name="match").model_dump()]

    resp = httpx.Response(status_code=200, json=mock_list)
    resp.json = lambda **kwargs: mock_list
    resp.headers["X-Total-Count"] = "1"
    fake_api_client.get.return_value = resp

    widgets, pagination = await repo.get_all(search="match")
    assert len(widgets) == 1
    call_kwargs = fake_api_client.get.call_args
    assert call_kwargs.kwargs["params"]["search"] == "match"


@pytest.mark.asyncio
async def test_get_all_failure_raises(fake_api_client):
    """
    Test get_all raises WidgetApiException on failure.
    """
    repo = WidgetApiRepository(fake_api_client)
    fake_api_client.get.return_value = httpx.Response(
        status_code=500, text="Server error"
    )

    with pytest.raises(WidgetApiException):
        await repo.get_all()


@pytest.mark.asyncio
async def test_widget_update_success(fake_api_client):
    """
    Test successful widget update.
    """
    repo = WidgetApiRepository(fake_api_client)
    data = WidgetUpdate(name="updated")
    mock_response = WidgetRead(id=1, name="updated").model_dump()

    fake_api_client.patch.return_value = httpx.Response(
        status_code=200,
        json=mock_response,
    )
    fake_api_client.patch.return_value.json = lambda **kwargs: mock_response

    widget = await repo.widget_update(1, data)
    assert isinstance(widget, WidgetRead)
    assert widget.name == "updated"


@pytest.mark.asyncio
async def test_widget_update_failure_raises(fake_api_client):
    """
    Test widget_update raises WidgetApiException on failure.
    """
    repo = WidgetApiRepository(fake_api_client)
    data = WidgetUpdate(name="fail")

    fake_api_client.patch.return_value = httpx.Response(
        status_code=400, text="Bad request"
    )

    with pytest.raises(WidgetApiException):
        await repo.widget_update(1, data)


@pytest.mark.asyncio
async def test_widget_delete_success(fake_api_client):
    """
    Test successful widget delete.
    """
    repo = WidgetApiRepository(fake_api_client)
    fake_api_client.delete.return_value = httpx.Response(status_code=204)

    await repo.widget_delete(1)
    fake_api_client.delete.assert_called_once()


@pytest.mark.asyncio
async def test_widget_delete_failure_raises(fake_api_client):
    """
    Test widget_delete raises WidgetApiException on failure.
    """
    repo = WidgetApiRepository(fake_api_client)
    fake_api_client.delete.return_value = httpx.Response(
        status_code=404, text="Not found"
    )

    with pytest.raises(WidgetApiException):
        await repo.widget_delete(999)


@pytest.mark.asyncio
async def test_widget_bulk_delete_success(fake_api_client):
    """
    Test successful bulk delete.
    """
    repo = WidgetApiRepository(fake_api_client)
    mock_response = {"deleted": 3}

    fake_api_client.post.return_value = httpx.Response(
        status_code=200,
        json=mock_response,
    )
    fake_api_client.post.return_value.json = lambda **kwargs: mock_response

    deleted = await repo.widget_bulk_delete([1, 2, 3])
    assert deleted == 3


@pytest.mark.asyncio
async def test_widget_bulk_delete_failure_raises(fake_api_client):
    """
    Test widget_bulk_delete raises WidgetApiException on failure.
    """
    repo = WidgetApiRepository(fake_api_client)
    fake_api_client.post.return_value = httpx.Response(
        status_code=400, text="Bad request"
    )

    with pytest.raises(WidgetApiException):
        await repo.widget_bulk_delete([1])


@pytest.mark.asyncio
async def test_widget_bulk_update_success(fake_api_client):
    """
    Test successful bulk update.
    """
    repo = WidgetApiRepository(fake_api_client)
    data = WidgetUpdate(name="bulk")
    mock_response = {"updated": 2}

    fake_api_client.post.return_value = httpx.Response(
        status_code=200,
        json=mock_response,
    )
    fake_api_client.post.return_value.json = lambda **kwargs: mock_response

    updated = await repo.widget_bulk_update([1, 2], data)
    assert updated == 2


@pytest.mark.asyncio
async def test_widget_bulk_update_failure_raises(fake_api_client):
    """
    Test widget_bulk_update raises WidgetApiException on failure.
    """
    repo = WidgetApiRepository(fake_api_client)
    data = WidgetUpdate(name="fail")

    fake_api_client.post.return_value = httpx.Response(
        status_code=400, text="Bad request"
    )

    with pytest.raises(WidgetApiException):
        await repo.widget_bulk_update([1], data)
