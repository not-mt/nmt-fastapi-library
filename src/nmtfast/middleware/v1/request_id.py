# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Middleware for generating and managing request IDs."""

import contextvars
import secrets
from typing import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

REQUEST_ID_CONTEXTVAR: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id", default=None
)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware to generate and manage request IDs for log correlation."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """
        Generate a unique ID for short-lived log correlation and sets it in the context.

        Args:
            request: The incoming request.
            call_next: The next middleware or endpoint in the chain.

        Returns:
            Response: The response from the next middleware or endpoint.
        """
        request_id: str = str(f"R{secrets.token_hex(64)[:5]}")
        REQUEST_ID_CONTEXTVAR.set(request_id)
        response: Response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
