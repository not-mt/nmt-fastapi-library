# -*- coding: utf-8 -*-
# Copyright (c) 2026. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Shared repository layer for interacting with the gadgets API."""

import logging
from typing import Literal

import httpx
from tenacity import retry, stop_after_attempt, wait_fixed

from nmtfast.htmx.v1.schemas import PaginationMeta
from nmtfast.repositories.gadgets.v1.exceptions import GadgetApiException
from nmtfast.repositories.gadgets.v1.schemas import (
    GadgetCreate,
    GadgetRead,
    GadgetUpdate,
    GadgetZap,
    GadgetZapTask,
)
from nmtfast.retry.v1.tenacity import tenacity_retry_log

logger = logging.getLogger(__name__)


class GadgetApiRepository:
    """
    API repository implementation for Gadget operations.

    This serves as a reusable repository layer that is able to connect to
    an upstream API.

    Args:
        api_client: The httpx client used to communicate with the gadgets API.
    """

    def __init__(self, api_client: httpx.AsyncClient) -> None:
        self.api_client: httpx.AsyncClient = api_client

    @retry(
        reraise=True,
        stop=stop_after_attempt(5),
        wait=wait_fixed(0.2),
        after=tenacity_retry_log(logger),
    )
    async def gadget_create(self, gadget: GadgetCreate) -> GadgetRead:
        """
        Create a new gadget through the API.

        Args:
            gadget: The gadget data transfer object.

        Returns:
            GadgetRead: The newly created gadget instance.

        Raises:
            GadgetApiException: Raised when upstream API reports failure status code.
        """
        new_gadget = gadget.model_dump()
        logger.debug(f"Adding gadget: {new_gadget}")
        resp = await self.api_client.post("/v1/gadgets", json=new_gadget)

        if resp.status_code != 201:
            logger.info(f"Failed to create gadget: {resp.status_code}: {resp.text}")
            raise GadgetApiException(resp)

        resp_gadget = resp.json()
        logger.info(f"Successfully created gadget: {resp_gadget}")

        return GadgetRead(**resp_gadget)

    @retry(
        reraise=True,
        stop=stop_after_attempt(5),
        wait=wait_fixed(0.2),
        after=tenacity_retry_log(logger),
    )
    async def get_by_id(self, gadget_id: str) -> GadgetRead:
        """
        Retrieve a gadget by its ID through the API.

        Args:
            gadget_id: The ID of the gadget to retrieve.

        Returns:
            GadgetRead: The retrieved gadget instance.

        Raises:
            GadgetApiException: Raised when upstream API reports failure status code.
        """
        logger.debug(f"Fetching gadget by ID: {gadget_id}")
        resp = await self.api_client.get(f"/v1/gadgets/{gadget_id}")

        if resp.status_code != 200:
            logger.info(f"Failed to find gadget: {resp.status_code}: {resp.text}")
            raise GadgetApiException(resp)

        api_gadget = GadgetRead(**resp.json())
        logger.debug(f"Retrieved gadget: {api_gadget}")

        return api_gadget

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
    ) -> tuple[list[GadgetRead], PaginationMeta]:
        """
        Retrieve all gadgets through the API with pagination and sorting.

        Args:
            page: The page number to retrieve (1-indexed).
            page_size: The number of items per page.
            sort_by: The field name to sort by.
            sort_order: The sort direction ('asc' or 'desc').
            search: Optional search filter string.

        Returns:
            tuple[list[GadgetRead], PaginationMeta]: A list of gadgets and pagination
                metadata.

        Raises:
            GadgetApiException: Raised when upstream API reports failure status code.
        """
        logger.debug("Fetching all gadgets")
        params: dict[str, str | int] = {
            "page": page,
            "page_size": page_size,
            "sort_by": sort_by,
            "sort_order": sort_order,
        }
        if search:
            params["search"] = search
        resp = await self.api_client.get(
            "/v1/gadgets",
            params=params,
        )

        if resp.status_code != 200:
            logger.info(f"Failed to list gadgets: {resp.status_code}: {resp.text}")
            raise GadgetApiException(resp)

        gadgets = [GadgetRead(**g) for g in resp.json()]
        total = int(resp.headers.get("X-Total-Count", len(gadgets)))
        pagination = PaginationMeta(
            total=total,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
            search=search,
        )
        logger.debug(f"Retrieved {len(gadgets)} gadgets (total: {total})")

        return gadgets, pagination

    @retry(
        reraise=True,
        stop=stop_after_attempt(5),
        wait=wait_fixed(0.2),
        after=tenacity_retry_log(logger),
    )
    async def gadget_update(
        self,
        gadget_id: str,
        data: GadgetUpdate,
    ) -> GadgetRead:
        """
        Update an existing gadget through the API.

        Args:
            gadget_id: The ID of the gadget to update.
            data: The partial update data.

        Returns:
            GadgetRead: The updated gadget instance.

        Raises:
            GadgetApiException: Raised when upstream API reports failure status code.
        """
        logger.debug(f"Updating gadget ID {gadget_id}")
        resp = await self.api_client.patch(
            f"/v1/gadgets/{gadget_id}",
            json=data.model_dump(exclude_unset=True),
        )

        if resp.status_code != 200:
            logger.info(f"Failed to update gadget: {resp.status_code}: {resp.text}")
            raise GadgetApiException(resp)

        updated = GadgetRead(**resp.json())
        logger.debug(f"Updated gadget: {updated}")

        return updated

    @retry(
        reraise=True,
        stop=stop_after_attempt(5),
        wait=wait_fixed(0.2),
        after=tenacity_retry_log(logger),
    )
    async def gadget_delete(self, gadget_id: str) -> None:
        """
        Delete a gadget through the API.

        Args:
            gadget_id: The ID of the gadget to delete.

        Raises:
            GadgetApiException: Raised when upstream API reports failure status code.
        """
        logger.debug(f"Deleting gadget ID {gadget_id}")
        resp = await self.api_client.delete(f"/v1/gadgets/{gadget_id}")

        if resp.status_code != 204:
            logger.info(f"Failed to delete gadget: {resp.status_code}: {resp.text}")
            raise GadgetApiException(resp)

        logger.debug(f"Deleted gadget ID {gadget_id}")

    @retry(
        reraise=True,
        stop=stop_after_attempt(5),
        wait=wait_fixed(0.2),
        after=tenacity_retry_log(logger),
    )
    async def gadget_bulk_delete(self, ids: list[str]) -> int:
        """
        Bulk delete gadgets through the API.

        Args:
            ids: The list of gadget IDs to delete.

        Returns:
            int: The number of gadgets deleted.

        Raises:
            GadgetApiException: Raised when upstream API reports failure status code.
        """
        logger.debug(f"Bulk deleting gadget IDs: {ids}")
        resp = await self.api_client.post(
            "/v1/gadgets/actions/bulk/delete",
            json=ids,
        )

        if resp.status_code != 200:
            logger.info(
                f"Failed to bulk delete gadgets: {resp.status_code}: {resp.text}"
            )
            raise GadgetApiException(resp)

        deleted = resp.json().get("deleted", 0)
        logger.debug(f"Bulk deleted {deleted} gadgets")

        return deleted

    @retry(
        reraise=True,
        stop=stop_after_attempt(5),
        wait=wait_fixed(0.2),
        after=tenacity_retry_log(logger),
    )
    async def gadget_bulk_update(
        self,
        ids: list[str],
        data: GadgetUpdate,
    ) -> int:
        """
        Bulk update gadgets through the API.

        Args:
            ids: The list of gadget IDs to update.
            data: The partial update data to apply to all matched gadgets.

        Returns:
            int: The number of gadgets updated.

        Raises:
            GadgetApiException: Raised when upstream API reports failure status code.
        """
        logger.debug(f"Bulk updating gadget IDs: {ids}")
        resp = await self.api_client.post(
            "/v1/gadgets/actions/bulk/update",
            json={"ids": ids, "updates": data.model_dump(exclude_unset=True)},
        )

        if resp.status_code != 200:
            logger.info(
                f"Failed to bulk update gadgets: {resp.status_code}: {resp.text}"
            )
            raise GadgetApiException(resp)

        updated = resp.json().get("updated", 0)
        logger.debug(f"Bulk updated {updated} gadgets")

        return updated

    @retry(
        reraise=True,
        stop=stop_after_attempt(5),
        wait=wait_fixed(0.2),
        after=tenacity_retry_log(logger),
    )
    async def gadget_zap(
        self,
        gadget_id: str,
        payload: GadgetZap,
    ) -> GadgetZapTask:
        """
        Zap a gadget through the API.

        Args:
            gadget_id: The ID of the gadget to zap.
            payload: The input payload necessary to start the task.

        Returns:
            GadgetZapTask: Status details about the newly created task.

        Raises:
            GadgetApiException: Raised when upstream API reports failure status code.
        """
        logger.debug(f"Zapping gadget by ID: {gadget_id}")
        resp = await self.api_client.post(
            f"/v1/gadgets/{gadget_id}/zap",
            json=payload.model_dump(),
        )

        if resp.status_code != 202:
            logger.info(f"Failed to zap gadget: {resp.status_code}: {resp.text}")
            raise GadgetApiException(resp)

        api_task = GadgetZapTask(**resp.json())
        logger.debug(f"Zapped gadget: {api_task}")

        return api_task

    @retry(
        reraise=True,
        stop=stop_after_attempt(5),
        wait=wait_fixed(0.2),
        after=tenacity_retry_log(logger),
    )
    async def gadget_zap_by_uuid(
        self,
        gadget_id: str,
        task_uuid: str,
    ) -> GadgetZapTask:
        """
        Retrieve a zap task by its UUID through the API.

        Args:
            gadget_id: The ID of the gadget.
            task_uuid: The UUID of the task for which to collect status details.

        Returns:
            GadgetZapTask: Status details about the task.

        Raises:
            GadgetApiException: Raised when upstream API reports failure status code.
        """
        logger.debug(f"Fetching zap task by UUID: {task_uuid}")
        resp = await self.api_client.get(
            f"/v1/gadgets/{gadget_id}/zap/{task_uuid}/status"
        )

        if resp.status_code != 200:
            logger.info(f"Failed get task by UUID: {resp.status_code}: {resp.text}")
            raise GadgetApiException(resp)

        api_task = GadgetZapTask(**resp.json())
        logger.debug(f"Gadget zap task: {api_task}")

        return api_task
