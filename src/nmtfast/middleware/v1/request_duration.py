# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Middleware for measuring and logging request durations."""

import logging
import time
from typing import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp


class RequestDurationMiddleware(BaseHTTPMiddleware):
    """
    Middleware to measure and log the duration of HTTP requests.
    """

    def __init__(
        self, app: ASGIApp, remote_headers: list[str] = ["X-Real-IP", "X-Forwarded-For"]
    ) -> None:
        super().__init__(app)
        self.header_names = remote_headers or []

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """
        Measure and log the duration of a request in milliseconds.

        Args:
            request: The incoming request.
            call_next: The next middleware or endpoint in the chain.

        Returns:
            Response: The response that will be returned to the client, or passed
                to the next middleware.
        """
        start_time: float = time.time()
        logger: logging.Logger = logging.getLogger(__name__)
        response: Response = await call_next(request)
        process_time_seconds: float = time.time() - start_time
        process_time_ms: float = process_time_seconds * 1000  # convert to ms
        response.headers["x-nmtfast-request-time-ms"] = str(process_time_ms)

        remote_host: str = request.client.host if request.client else "0.0.0.0"
        remote_port: int = request.client.port if request.client else 0

        # Iterate over header names and use the first found value as remote_host
        for header_name in self.header_names:
            header_value: str | None = request.headers.get(header_name)
            if header_value:
                remote_host = header_value
                break

        client_info: str = f"{remote_host}:{remote_port}"
        logger.info(
            f"{client_info} - {request.method}"
            f" {request.url.path} - {process_time_ms:.2f}ms"
        )

        return response
