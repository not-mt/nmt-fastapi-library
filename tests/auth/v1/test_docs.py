# -*- coding: utf-8 -*-
# Copyright (c) 2026. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Unit tests for Swagger UI customization helpers."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from nmtfast.auth.v1.docs import (
    _build_hide_client_secret_css,
    register_swagger_ui,
)

# ---------------------------------------------------------------------------
# _build_hide_client_secret_css
# ---------------------------------------------------------------------------


def test_build_css_empty_list_returns_empty_string():
    """
    An empty flow list should produce no CSS output.
    """
    assert _build_hide_client_secret_css([]) == ""


def test_build_css_single_flow():
    """
    A single flow type should produce one CSS rule targeting its label.
    """
    css = _build_hide_client_secret_css(["authorizationCode"])
    assert 'label[for="client_secret_authorizationCode"]' in css
    assert "<style>" in css
    assert "</style>" in css


def test_build_css_multiple_flows():
    """
    Multiple flow types should each get their own CSS rule.
    """
    css = _build_hide_client_secret_css(["authorizationCode", "implicit"])
    assert 'label[for="client_secret_authorizationCode"]' in css
    assert 'label[for="client_secret_implicit"]' in css


# ---------------------------------------------------------------------------
# register_swagger_ui
# ---------------------------------------------------------------------------


@pytest.fixture
def docs_app() -> FastAPI:
    """
    Create a minimal FastAPI app with docs_url disabled for testing.
    """
    return FastAPI(title="test-app", docs_url=None)


def test_register_swagger_ui_creates_docs_route(docs_app: FastAPI):
    """
    After registration the /docs endpoint should return 200.
    """
    register_swagger_ui(docs_app)
    client = TestClient(docs_app)
    resp = client.get("/docs")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]


def test_register_swagger_ui_creates_redirect_route(docs_app: FastAPI):
    """
    After registration the /docs/oauth2-redirect endpoint should return 200.
    """
    register_swagger_ui(docs_app)
    client = TestClient(docs_app)
    resp = client.get("/docs/oauth2-redirect")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]


def test_register_swagger_ui_injects_css_when_flows_specified(docs_app: FastAPI):
    """
    When hide_client_secret_for is provided the /docs HTML should contain the
    matching CSS rule.
    """
    register_swagger_ui(docs_app, hide_client_secret_for=["authorizationCode"])
    client = TestClient(docs_app)
    resp = client.get("/docs")
    body = resp.text
    assert 'label[for="client_secret_authorizationCode"]' in body
    assert "display: none" in body


def test_register_swagger_ui_no_css_by_default(docs_app: FastAPI):
    """
    When hide_client_secret_for is not provided the /docs HTML should not
    contain the hide-client-secret CSS.
    """
    register_swagger_ui(docs_app)
    client = TestClient(docs_app)
    resp = client.get("/docs")
    body = resp.text
    assert "client_secret_authorizationCode" not in body


def test_register_swagger_ui_no_oauth2_redirect_url():
    """
    When swagger_ui_oauth2_redirect_url is None the /docs endpoint should still
    return 200 and the oauth2RedirectUrl line should not appear in the HTML.
    """
    no_redirect_app = FastAPI(
        title="test-app",
        docs_url=None,
        swagger_ui_oauth2_redirect_url=None,
    )
    register_swagger_ui(no_redirect_app)
    client = TestClient(no_redirect_app)
    resp = client.get("/docs")
    assert resp.status_code == 200
    assert "oauth2RedirectUrl" not in resp.text


def test_register_swagger_ui_prepends_root_path():
    """
    If the app has a root_path set, the /docs HTML should have the openapi_url
    and oauth2_redirect_url correctly prefixed with the root path.
    """
    root_app = FastAPI(
        title="test-app",
        docs_url=None,
        root_path="/some/root/path",
    )
    register_swagger_ui(root_app)
    client = TestClient(root_app, root_path="/some/root/path")
    resp = client.get("/docs")
    body = resp.text
    assert "url: '/some/root/path/openapi.json'" in body
