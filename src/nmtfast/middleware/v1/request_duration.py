# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Middleware for measuring and logging request durations."""

import logging
import time
from typing import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class RequestDurationMiddleware(BaseHTTPMiddleware):
    """Middleware to measure and log the duration of requests."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """
        Measures and logs the duration of a request in milliseconds.

        Args:
            request: The incoming request.
            call_next: The next middleware or endpoint in the chain.

        Returns:
            Response: The response from the next middleware or endpoint.
        """
        start_time: float = time.time()
        logger = logging.getLogger(__name__)
        response: Response = await call_next(request)
        process_time_seconds: float = time.time() - start_time
        process_time_ms: float = process_time_seconds * 1000  # convert to ms
        logger.info(f"{request.method} {request.url.path} - {process_time_ms:.2f}ms")
        response.headers["X-Process-Time-Milliseconds"] = str(process_time_ms)
        return response
