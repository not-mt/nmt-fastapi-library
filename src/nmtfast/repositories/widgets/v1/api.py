# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Shared repository layer for interacting with the widgets API."""

import logging

import httpx
from tenacity import retry, stop_after_attempt, wait_fixed

from nmtfast.repositories.widgets.v1.exceptions import WidgetApiException
from nmtfast.repositories.widgets.v1.schemas import (
    WidgetCreate,
    WidgetRead,
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
