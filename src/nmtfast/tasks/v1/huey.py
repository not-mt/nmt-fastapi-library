# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Helper functions for Huey async tasks and metadata."""

import logging

# import huey.signals as HSIG
from huey import Huey

# from huey.api import Task
from huey.exceptions import TaskException
from huey.storage import RedisStorage
from tenacity import retry, stop_after_attempt, wait_fixed

from nmtfast.retry.v1.tenacity import tenacity_retry_log

logger = logging.getLogger(__name__)


@retry(
    reraise=True,
    stop=stop_after_attempt(5),
    wait=wait_fixed(0.001),
    after=tenacity_retry_log(logger),
)
def store_task_metadata(
    huey_app: Huey,
    uuid: str,
    metadata: dict,
    ttl: int = 3600 * 4,
) -> bool:
    """
    Store/replace async metadata for given UUID.
    """
    logger.debug(f"Updating metadata for task {uuid} (TTL: {ttl}) ...")
    md_key = f"md_{uuid}"

    huey_app.put(md_key, metadata)

    # NOTE: even when using RedisExpireStorage, we have to manually set a TTL
    if isinstance(huey_app.storage, RedisStorage):
        app_name = huey_app.storage.name
        redis_key = f"huey.r.{app_name}.{md_key}"
        huey_app.storage.conn.expire(redis_key, ttl)

    return True


@retry(
    reraise=True,
    stop=stop_after_attempt(5),
    wait=wait_fixed(0.001),
    after=tenacity_retry_log(logger),
)
def fetch_task_metadata(huey_app: Huey, uuid: str) -> dict | None:
    """
    Return long_async_task metadata.
    """
    logger.debug(f"Fetching metadata for task {uuid} ...")
    md_key = f"md_{uuid}"

    meta_d: dict | None = huey_app.get(key=md_key, peek=True)
    if not meta_d:
        logger.warning(f"No metadata found for key {md_key}")

    return meta_d


@retry(
    reraise=True,
    stop=stop_after_attempt(5),
    wait=wait_fixed(0.001),
    after=tenacity_retry_log(logger),
)
def fetch_task_result(huey_app: Huey, uuid: str) -> dict | None:
    """
    Return a long_async_task by UUID.
    """
    logger.debug(f"Fetching result for task {uuid} ...")

    try:
        result_d = huey_app.result(uuid, preserve=True)
    except TaskException:
        result_d = fetch_task_metadata(huey_app, uuid)
        logger.warning(
            f"Result for task {uuid} is an exception! "
            f"Returning metadata instead: {result_d}"
        )
    # FIXME: huey_app.result() does not have stubs, so it is implicitly Any
    return result_d  # type: ignore
