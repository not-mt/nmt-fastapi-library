# -*- coding: utf-8 -*-
# Copyright (c) 2026. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Tests for gadget repository methods."""

from unittest.mock import AsyncMock

import httpx
import pytest

from nmtfast.repositories.gadgets.v1.api import GadgetApiRepository
from nmtfast.repositories.gadgets.v1.exceptions import GadgetApiException
from nmtfast.repositories.gadgets.v1.schemas import (
    GadgetCreate,
    GadgetRead,
    GadgetUpdate,
    GadgetZap,
    GadgetZapTask,
)


@pytest.fixture
def fake_api_client():
    """
    Create a fake httpx.AsyncClient mock.
    """
    client = AsyncMock(spec=httpx.AsyncClient)
    return client


@pytest.mark.asyncio
async def test_gadget_create_success(fake_api_client):
    """
    Test successful gadget creation.
    """
    repo = GadgetApiRepository(fake_api_client)
    gadget_in = GadgetCreate(name="test")

    mock_response = GadgetRead(id="g1", name="test").model_dump()

    fake_api_client.post.return_value = httpx.Response(
        status_code=201,
        json=mock_response,
    )
    fake_api_client.post.return_value.json = lambda **kwargs: mock_response

    gadget_out = await repo.gadget_create(gadget_in)
    assert isinstance(gadget_out, GadgetRead)
    assert gadget_out.id == "g1"


@pytest.mark.asyncio
async def test_gadget_create_failure_raises(fake_api_client):
    """
    Test gadget_create raises GadgetApiException on failure.
    """
    repo = GadgetApiRepository(fake_api_client)
    gadget_in = GadgetCreate(name="fail")

    fake_api_client.post.return_value = httpx.Response(
        status_code=400, text="Bad request"
    )

    with pytest.raises(GadgetApiException):
        await repo.gadget_create(gadget_in)


@pytest.mark.asyncio
async def test_get_by_id_success(fake_api_client):
    """
    Test successful get_by_id.
    """
    repo = GadgetApiRepository(fake_api_client)
    mock_response = GadgetRead(id="g2", name="found").model_dump()

    fake_api_client.get.return_value = httpx.Response(
        status_code=200,
        json=mock_response,
    )
    fake_api_client.get.return_value.json = lambda **kwargs: mock_response

    gadget = await repo.get_by_id("g2")
    assert isinstance(gadget, GadgetRead)
    assert gadget.id == "g2"


@pytest.mark.asyncio
async def test_get_by_id_failure_raises(fake_api_client):
    """
    Test get_by_id raises GadgetApiException on failure.
    """
    repo = GadgetApiRepository(fake_api_client)
    fake_api_client.get.return_value = httpx.Response(status_code=404, text="Not found")

    with pytest.raises(GadgetApiException):
        await repo.get_by_id("missing")


@pytest.mark.asyncio
async def test_get_all_success(fake_api_client):
    """
    Test successful get_all with pagination.
    """
    repo = GadgetApiRepository(fake_api_client)
    mock_list = [
        GadgetRead(id="g1", name="a").model_dump(),
        GadgetRead(id="g2", name="b").model_dump(),
    ]

    resp = httpx.Response(status_code=200, json=mock_list)
    resp.json = lambda **kwargs: mock_list
    resp.headers["X-Total-Count"] = "5"
    fake_api_client.get.return_value = resp

    gadgets, pagination = await repo.get_all(page=1, page_size=2)
    assert len(gadgets) == 2
    assert pagination.total == 5
    assert pagination.page == 1
    assert pagination.page_size == 2


@pytest.mark.asyncio
async def test_get_all_with_search(fake_api_client):
    """
    Test get_all passes search parameter.
    """
    repo = GadgetApiRepository(fake_api_client)
    mock_list = [GadgetRead(id="g1", name="match").model_dump()]

    resp = httpx.Response(status_code=200, json=mock_list)
    resp.json = lambda **kwargs: mock_list
    resp.headers["X-Total-Count"] = "1"
    fake_api_client.get.return_value = resp

    gadgets, pagination = await repo.get_all(search="match")
    assert len(gadgets) == 1
    call_kwargs = fake_api_client.get.call_args
    assert call_kwargs.kwargs["params"]["search"] == "match"


@pytest.mark.asyncio
async def test_get_all_failure_raises(fake_api_client):
    """
    Test get_all raises GadgetApiException on failure.
    """
    repo = GadgetApiRepository(fake_api_client)
    fake_api_client.get.return_value = httpx.Response(
        status_code=500, text="Server error"
    )

    with pytest.raises(GadgetApiException):
        await repo.get_all()


@pytest.mark.asyncio
async def test_gadget_update_success(fake_api_client):
    """
    Test successful gadget update.
    """
    repo = GadgetApiRepository(fake_api_client)
    data = GadgetUpdate(name="updated")
    mock_response = GadgetRead(id="g1", name="updated").model_dump()

    fake_api_client.patch.return_value = httpx.Response(
        status_code=200,
        json=mock_response,
    )
    fake_api_client.patch.return_value.json = lambda **kwargs: mock_response

    gadget = await repo.gadget_update("g1", data)
    assert isinstance(gadget, GadgetRead)
    assert gadget.name == "updated"


@pytest.mark.asyncio
async def test_gadget_update_failure_raises(fake_api_client):
    """
    Test gadget_update raises GadgetApiException on failure.
    """
    repo = GadgetApiRepository(fake_api_client)
    data = GadgetUpdate(name="fail")

    fake_api_client.patch.return_value = httpx.Response(
        status_code=400, text="Bad request"
    )

    with pytest.raises(GadgetApiException):
        await repo.gadget_update("g1", data)


@pytest.mark.asyncio
async def test_gadget_delete_success(fake_api_client):
    """
    Test successful gadget delete.
    """
    repo = GadgetApiRepository(fake_api_client)
    fake_api_client.delete.return_value = httpx.Response(status_code=204)

    await repo.gadget_delete("g1")
    fake_api_client.delete.assert_called_once()


@pytest.mark.asyncio
async def test_gadget_delete_failure_raises(fake_api_client):
    """
    Test gadget_delete raises GadgetApiException on failure.
    """
    repo = GadgetApiRepository(fake_api_client)
    fake_api_client.delete.return_value = httpx.Response(
        status_code=404, text="Not found"
    )

    with pytest.raises(GadgetApiException):
        await repo.gadget_delete("missing")


@pytest.mark.asyncio
async def test_gadget_bulk_delete_success(fake_api_client):
    """
    Test successful bulk delete.
    """
    repo = GadgetApiRepository(fake_api_client)
    mock_response = {"deleted": 3}

    fake_api_client.post.return_value = httpx.Response(
        status_code=200,
        json=mock_response,
    )
    fake_api_client.post.return_value.json = lambda **kwargs: mock_response

    deleted = await repo.gadget_bulk_delete(["g1", "g2", "g3"])
    assert deleted == 3


@pytest.mark.asyncio
async def test_gadget_bulk_delete_failure_raises(fake_api_client):
    """
    Test gadget_bulk_delete raises GadgetApiException on failure.
    """
    repo = GadgetApiRepository(fake_api_client)
    fake_api_client.post.return_value = httpx.Response(
        status_code=400, text="Bad request"
    )

    with pytest.raises(GadgetApiException):
        await repo.gadget_bulk_delete(["g1"])


@pytest.mark.asyncio
async def test_gadget_bulk_update_success(fake_api_client):
    """
    Test successful bulk update.
    """
    repo = GadgetApiRepository(fake_api_client)
    data = GadgetUpdate(name="bulk")
    mock_response = {"updated": 2}

    fake_api_client.post.return_value = httpx.Response(
        status_code=200,
        json=mock_response,
    )
    fake_api_client.post.return_value.json = lambda **kwargs: mock_response

    updated = await repo.gadget_bulk_update(["g1", "g2"], data)
    assert updated == 2


@pytest.mark.asyncio
async def test_gadget_bulk_update_failure_raises(fake_api_client):
    """
    Test gadget_bulk_update raises GadgetApiException on failure.
    """
    repo = GadgetApiRepository(fake_api_client)
    data = GadgetUpdate(name="fail")

    fake_api_client.post.return_value = httpx.Response(
        status_code=400, text="Bad request"
    )

    with pytest.raises(GadgetApiException):
        await repo.gadget_bulk_update(["g1"], data)


@pytest.mark.asyncio
async def test_gadget_zap_success(fake_api_client):
    """
    Test successful gadget_zap.
    """
    repo = GadgetApiRepository(fake_api_client)
    payload = GadgetZap(duration=10)
    mock_response = GadgetZapTask(
        uuid="uuid-123",
        state="PENDING",
        id="g1",
        duration=10,
        runtime=0,
    ).model_dump()

    fake_api_client.post.return_value = httpx.Response(
        status_code=202,
        json=mock_response,
    )
    fake_api_client.post.return_value.json = lambda **kwargs: mock_response

    task = await repo.gadget_zap("g1", payload)
    assert isinstance(task, GadgetZapTask)
    assert task.uuid == "uuid-123"


@pytest.mark.asyncio
async def test_gadget_zap_failure_raises(fake_api_client):
    """
    Test gadget_zap raises GadgetApiException on failure.
    """
    repo = GadgetApiRepository(fake_api_client)
    payload = GadgetZap(duration=10)

    fake_api_client.post.return_value = httpx.Response(status_code=400, text="Bad zap")

    with pytest.raises(GadgetApiException):
        await repo.gadget_zap("g1", payload)


@pytest.mark.asyncio
async def test_gadget_zap_by_uuid_success(fake_api_client):
    """
    Test successful gadget_zap_by_uuid.
    """
    repo = GadgetApiRepository(fake_api_client)
    mock_response_data = GadgetZapTask(
        uuid="uuid-456",
        state="SUCCESS",
        id="g1",
        duration=10,
        runtime=123,
    ).model_dump()

    fake_api_client.get.return_value = httpx.Response(
        status_code=200,
        json=mock_response_data,
    )
    fake_api_client.get.return_value.json = lambda **kwargs: mock_response_data

    task = await repo.gadget_zap_by_uuid("g1", "uuid-456")

    assert isinstance(task, GadgetZapTask)
    assert task.uuid == "uuid-456"
    assert task.state == "SUCCESS"


@pytest.mark.asyncio
async def test_gadget_zap_by_uuid_failure_raises(fake_api_client):
    """
    Test gadget_zap_by_uuid raises GadgetApiException on failure.
    """
    repo = GadgetApiRepository(fake_api_client)
    fake_api_client.get.return_value = httpx.Response(status_code=404, text="Not found")

    with pytest.raises(GadgetApiException):
        await repo.gadget_zap_by_uuid("g1", "uuid-999")
