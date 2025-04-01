# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Unit tests for request duration middleware."""

from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from nmtfast.middleware.v1.request_duration import RequestDurationMiddleware


def test_request_duration_middleware():
    """
    Test whether request duration is recorded in headers.
    """
    app = FastAPI()
    app.add_middleware(RequestDurationMiddleware)
    client = TestClient(app)

    @app.get("/")
    async def read_root():
        return {"Hello": "World"}

    with patch("logging.Logger.info") as mock_logger:
        response = client.get("/")

    assert response.status_code == 200
    assert "X-Process-Time-Milliseconds" in response.headers
    assert mock_logger.called
