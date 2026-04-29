# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Shared repository layer for interacting with the widgets API."""

import logging
from typing import Literal

import httpx
from tenacity import retry, stop_after_attempt, wait_fixed

from nmtfast.htmx.v1.schemas import PaginationMeta
from nmtfast.repositories.widgets.v1.exceptions import WidgetApiException
from nmtfast.repositories.widgets.v1.schemas import (
    WidgetCreate,
    WidgetRead,
    WidgetUpdate,
    WidgetZap,
    WidgetZapTask,
)
from nmtfast.retry.v1.tenacity import tenacity_retry_log

logger = logging.getLogger(__name__)


class WidgetApiRepository:
    """
    API repository implementation for Widget operations.

    This serves an example of a reusable repository layer that is able to connect to
    an upstream API.

    Args:
        api_client: The httpx client used to communicate with the widgets API.
    """

    def __init__(self, api_client: httpx.AsyncClient) -> None:
        self.api_client: httpx.AsyncClient = api_client

    @retry(
        reraise=True,
        stop=stop_after_attempt(5),
        wait=wait_fixed(0.2),
        after=tenacity_retry_log(logger),
    )
    async def widget_create(self, widget: WidgetCreate) -> WidgetRead:
        """
        Create a new widget through the API.

        Args:
            widget: The widget data transfer object.

        Returns:
            WidgetRead: The newly created widget instance.

        Raises:
            WidgetApiException: Raised when upstream API reports failure status code.
        """
        new_widget = widget.model_dump()
        logger.debug(f"Adding widget: {new_widget}")
        resp = await self.api_client.post("/v1/widgets", json=new_widget)

        if resp.status_code != 201:
            logger.info(f"Failed to created widget: {resp.status_code}: {resp.text}")
            raise WidgetApiException(resp)

        resp_widget = resp.json()
        logger.info(f"Successfully created widget: {resp_widget}")

        return WidgetRead(**resp_widget)

    @retry(
        reraise=True,
        stop=stop_after_attempt(5),
        wait=wait_fixed(0.2),
        after=tenacity_retry_log(logger),
    )
    async def get_by_id(self, widget_id: int) -> WidgetRead:
        """
        Retrieve a widget by its ID through the API.

        Args:
            widget_id: The ID of the widget to retrieve.

        Returns:
            WidgetRead: The retrieved widget instance.

        Raises:
            WidgetApiException: Raised when upstream API reports failure status code.
        """
        logger.debug(f"Fetching widget by ID: {widget_id}")
        resp = await self.api_client.get(f"/v1/widgets/{widget_id}")

        if resp.status_code != 200:
            logger.info(f"Failed to find widget: {resp.status_code}: {resp.text}")
            raise WidgetApiException(resp)

        api_widget = WidgetRead(**resp.json())
        logger.debug(f"Retrieved widget: {api_widget}")

        return api_widget

    @retry(
        reraise=True,
        stop=stop_after_attempt(5),
        wait=wait_fixed(0.2),
        after=tenacity_retry_log(logger),
    )
    async def widget_zap(
        self,
        widget_id: int,
        payload: WidgetZap,
    ) -> WidgetZapTask:
        """
        Retrieve a widget by its ID through the API.

        Args:
            widget_id: The ID of the widget to zap.
            payload: The input payload necessary to start the task.

        Returns:
            WidgetZapTask: Status details about the newly created task.

        Raises:
            WidgetApiException: Raised when upstream API reports failure status code.
        """
        logger.debug(f"Zapping widget by ID: {widget_id}")
        resp = await self.api_client.post(
            f"/v1/widgets/{widget_id}/zap",
            json=payload.model_dump(),
        )

        if resp.status_code != 202:
            logger.info(f"Failed to zap widget: {resp.status_code}: {resp.text}")
            raise WidgetApiException(resp)

        api_task = WidgetZapTask(**resp.json())
        logger.debug(f"Zapped widget: {api_task}")

        return api_task

    @retry(
        reraise=True,
        stop=stop_after_attempt(5),
        wait=wait_fixed(0.2),
        after=tenacity_retry_log(logger),
    )
    async def widget_zap_by_uuid(
        self,
        widget_id: int,
        task_uuid: str,
    ) -> WidgetZapTask:
        """
        Retrieve a zap task by its UUID through the API.

        Args:
            widget_id: The ID of the widget to zap.
            task_uuid: The UUID of the task for which to collect status details.

        Returns:
            WidgetZapTask: Status details about the task.

        Raises:
            WidgetApiException: Raised when upstream API reports failure status code.
        """
        logger.debug(f"Fetching zap task by UUID: {task_uuid}")
        resp = await self.api_client.get(
            f"/v1/widgets/{widget_id}/zap/{task_uuid}/status"
        )

        if resp.status_code != 200:
            logger.info(f"Failed get task by UUID: {resp.status_code}: {resp.text}")
            raise WidgetApiException(resp)

        api_task = WidgetZapTask(**resp.json())
        logger.debug(f"Zapped widget: {api_task}")

        return api_task

    @retry(
        reraise=True,
        stop=stop_after_attempt(5),
        wait=wait_fixed(0.2),
        after=tenacity_retry_log(logger),
    )
    async def get_all(
        self,
        page: int = 1,
        page_size: int = 10,
        sort_by: str = "id",
        sort_order: Literal["asc", "desc"] = "asc",
        search: str | None = None,
    ) -> tuple[list[WidgetRead], PaginationMeta]:
        """
        Retrieve all widgets through the API with pagination and sorting.

        Args:
            page: The page number to retrieve (1-indexed).
            page_size: The number of items per page.
            sort_by: The field name to sort by.
            sort_order: The sort direction ('asc' or 'desc').
            search: Optional search filter string.

        Returns:
            tuple[list[WidgetRead], PaginationMeta]: A list of widgets and pagination
                metadata.

        Raises:
            WidgetApiException: Raised when upstream API reports failure status code.
        """
        logger.debug("Fetching all widgets")
        params: dict[str, str | int] = {
            "page": page,
            "page_size": page_size,
            "sort_by": sort_by,
            "sort_order": sort_order,
        }
        if search:
            params["search"] = search
        resp = await self.api_client.get(
            "/v1/widgets",
            params=params,
        )

        if resp.status_code != 200:
            logger.info(f"Failed to list widgets: {resp.status_code}: {resp.text}")
            raise WidgetApiException(resp)

        widgets = [WidgetRead(**w) for w in resp.json()]
        total = int(resp.headers.get("X-Total-Count", len(widgets)))
        pagination = PaginationMeta(
            total=total,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
            search=search,
        )
        logger.debug(f"Retrieved {len(widgets)} widgets (total: {total})")

        return widgets, pagination

    @retry(
        reraise=True,
        stop=stop_after_attempt(5),
        wait=wait_fixed(0.2),
        after=tenacity_retry_log(logger),
    )
    async def widget_update(
        self,
        widget_id: int,
        data: WidgetUpdate,
    ) -> WidgetRead:
        """
        Update an existing widget through the API.

        Args:
            widget_id: The ID of the widget to update.
            data: The partial update data.

        Returns:
            WidgetRead: The updated widget instance.

        Raises:
            WidgetApiException: Raised when upstream API reports failure status code.
        """
        logger.debug(f"Updating widget ID {widget_id}")
        resp = await self.api_client.patch(
            f"/v1/widgets/{widget_id}",
            json=data.model_dump(exclude_unset=True),
        )

        if resp.status_code != 200:
            logger.info(f"Failed to update widget: {resp.status_code}: {resp.text}")
            raise WidgetApiException(resp)

        updated = WidgetRead(**resp.json())
        logger.debug(f"Updated widget: {updated}")

        return updated

    @retry(
        reraise=True,
        stop=stop_after_attempt(5),
        wait=wait_fixed(0.2),
        after=tenacity_retry_log(logger),
    )
    async def widget_delete(self, widget_id: int) -> None:
        """
        Delete a widget through the API.

        Args:
            widget_id: The ID of the widget to delete.

        Raises:
            WidgetApiException: Raised when upstream API reports failure status code.
        """
        logger.debug(f"Deleting widget ID {widget_id}")
        resp = await self.api_client.delete(f"/v1/widgets/{widget_id}")

        if resp.status_code != 204:
            logger.info(f"Failed to delete widget: {resp.status_code}: {resp.text}")
            raise WidgetApiException(resp)

        logger.debug(f"Deleted widget ID {widget_id}")

    @retry(
        reraise=True,
        stop=stop_after_attempt(5),
        wait=wait_fixed(0.2),
        after=tenacity_retry_log(logger),
    )
    async def widget_bulk_delete(self, ids: list[int]) -> int:
        """
        Bulk delete widgets through the API.

        Args:
            ids: The list of widget IDs to delete.

        Returns:
            int: The number of widgets deleted.

        Raises:
            WidgetApiException: Raised when upstream API reports failure status code.
        """
        logger.debug(f"Bulk deleting widget IDs: {ids}")
        resp = await self.api_client.post(
            "/v1/widgets/actions/bulk/delete",
            json=ids,
        )

        if resp.status_code != 200:
            logger.info(
                f"Failed to bulk delete widgets: {resp.status_code}: {resp.text}"
            )
            raise WidgetApiException(resp)

        deleted = resp.json().get("deleted", 0)
        logger.debug(f"Bulk deleted {deleted} widgets")

        return deleted

    @retry(
        reraise=True,
        stop=stop_after_attempt(5),
        wait=wait_fixed(0.2),
        after=tenacity_retry_log(logger),
    )
    async def widget_bulk_update(
        self,
        ids: list[int],
        data: WidgetUpdate,
    ) -> int:
        """
        Bulk update widgets through the API.

        Args:
            ids: The list of widget IDs to update.
            data: The partial update data to apply to all matched widgets.

        Returns:
            int: The number of widgets updated.

        Raises:
            WidgetApiException: Raised when upstream API reports failure status code.
        """
        logger.debug(f"Bulk updating widget IDs: {ids}")
        resp = await self.api_client.post(
            "/v1/widgets/actions/bulk/update",
            json={"ids": ids, "updates": data.model_dump(exclude_unset=True)},
        )

        if resp.status_code != 200:
            logger.info(
                f"Failed to bulk update widgets: {resp.status_code}: {resp.text}"
            )
            raise WidgetApiException(resp)

        updated = resp.json().get("updated", 0)
        logger.debug(f"Bulk updated {updated} widgets")

        return updated
