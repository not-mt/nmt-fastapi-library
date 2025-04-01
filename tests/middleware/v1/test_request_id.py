# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Unit tests for request ID middleware."""

from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from nmtfast.middleware.v1.request_id import RequestIDMiddleware


def test_request_id_middleware():
    """
    Test whether request ID is recorded in headers.
    """
    app = FastAPI()
    app.add_middleware(RequestIDMiddleware)
    client = TestClient(app)

    @app.get("/")
    async def read_root():
        return {"Hello": "World"}

    with patch("secrets.token_hex") as mock_token:
        mock_token.return_value = "0" * 128
        response = client.get("/")

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "R00000"

    with patch("secrets.token_hex") as mock_token2:
        mock_token2.return_value = "1" * 128
        response = client.get("/")

    assert response.headers["X-Request-ID"] == "R11111"
