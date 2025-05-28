# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""General exceptions and errors in nmtfast microservices and this library."""

import httpx


class BaseUpstreamRepositoryException(Exception):
    """
    Base class for all repository-layer exceptions representing upstream API failures.
    """

    def __init__(self, response: httpx.Response) -> None:
        self.status_code: int = response.status_code
        self.message: str = response.text
        self.req_id: str = response.headers.get("x-request-id", "UNKNOWN")
        super().__init__(
            f"Upstream API response {self.status_code}; "
            f"Request ID: {self.req_id}; Message: {self.message}"
        )


class UpstreamApiException(Exception):
    """
    Generic service-layer exception for upstream API failures.

    Args:
        exc: A repository-layer exception derived from BaseUpstreamRepositoryException.
    """

    def __init__(self, exc: BaseUpstreamRepositoryException) -> None:
        self.status_code: int = exc.status_code
        self.message: str = exc.message
        self.req_id: str = exc.req_id
        self.caller_status_code: int = self._infer_caller_status_code()

        super().__init__(
            f"Upstream API failure! HTTP code: {self.status_code}; "
            f"Request ID: {self.req_id}; Message: {self.message}"
        )

    def _infer_caller_status_code(self) -> int:
        if 400 <= self.status_code < 500:
            return 400
        return 502
