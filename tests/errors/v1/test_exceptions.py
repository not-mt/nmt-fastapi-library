# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Tests for nmtfast.errors.v1.exceptions."""

import httpx
import pytest

from nmtfast.errors.v1.exceptions import (
    BaseUpstreamRepositoryException,
    UpstreamApiException,
)


def make_response(status_code=500, text="Server error", headers=None):
    """
    Helper to create a fake httpx.Response with given parameters.
    """
    return httpx.Response(
        status_code=status_code,
        text=text,
        headers=headers or {"x-request-id": "abc-123"},
    )


def test_base_upstream_repository_exception_defaults():
    """
    Test BaseUpstreamRepositoryException sets attributes from response.
    """
    response = make_response()
    exc = BaseUpstreamRepositoryException(response)

    assert exc.status_code == 500
    assert exc.message == "Server error"
    assert exc.req_id == "abc-123"
    assert "Upstream API response 500" in str(exc)


@pytest.mark.parametrize(
    "status_code, expected_caller_code",
    [
        (400, 400),
        (404, 400),
        (499, 400),
        (500, 502),
        (503, 502),
    ],
)
def test_upstream_api_exception_infer_status(status_code, expected_caller_code):
    """
    Test UpstreamApiException caller_status_code based on status_code.
    """
    response = make_response(status_code=status_code)
    repo_exc = BaseUpstreamRepositoryException(response)
    service_exc = UpstreamApiException(repo_exc)

    assert service_exc.status_code == status_code
    assert service_exc.message == "Server error"
    assert service_exc.req_id == "abc-123"
    assert service_exc.caller_status_code == expected_caller_code
    assert f"HTTP code: {status_code}" in str(service_exc)
