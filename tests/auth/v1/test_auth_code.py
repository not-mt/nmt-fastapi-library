# -*- coding: utf-8 -*-
# Copyright (c) 2026. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Unit tests for OAuth2 Authorization Code flow helpers."""

import base64
import hashlib
from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import parse_qs, urlparse

import pytest

from nmtfast.auth.v1.auth_code import (
    exchange_code_for_tokens,
    generate_authorization_url,
    generate_pkce_pair,
    refresh_access_token,
)
from nmtfast.auth.v1.exceptions import AuthenticationError
from nmtfast.settings.v1.schemas import IDProvider, WebAuthClientSettings


@pytest.fixture
def idp():
    """
    Provide an IDProvider fixture for testing.
    """
    return IDProvider(
        type="jwks",
        issuer_regex=r"^https://idp\.example\.com$",
        jwks_endpoint="https://idp.example.com/jwks",
        token_endpoint="https://idp.example.com/token",
        authorize_endpoint="https://idp.example.com/authorize",
    )


@pytest.fixture
def web_client():
    """
    Provide a WebAuthClientSettings fixture for testing.
    """
    return WebAuthClientSettings(
        provider="test-idp",
        client_id="my-client-id",
        client_secret="my-client-secret",
        redirect_uri="http://localhost:8000/ui/v1/auth/callback",
        scopes=["openid", "profile"],
        pkce_enabled=False,
        refresh_enabled=False,
    )


@pytest.fixture
def web_client_pkce(web_client):
    """
    Provide a PKCE-enabled WebAuthClientSettings fixture.
    """
    return web_client.model_copy(update={"pkce_enabled": True})


@pytest.fixture
def web_client_post_auth(web_client):
    """
    Provide a WebAuthClientSettings fixture using client_secret_post.
    """
    return web_client.model_copy(
        update={"token_endpoint_auth_method": "client_secret_post"}
    )


# ---- PKCE pair generation ----


def test_generate_pkce_pair_returns_tuple():
    """
    Test that generate_pkce_pair returns a verifier and challenge.
    """
    verifier, challenge = generate_pkce_pair()
    assert isinstance(verifier, str)
    assert isinstance(challenge, str)
    assert len(verifier) > 40


def test_generate_pkce_pair_challenge_matches_verifier():
    """
    Test that the challenge is the S256 hash of the verifier.
    """
    verifier, challenge = generate_pkce_pair()
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    expected_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    assert challenge == expected_challenge


def test_generate_pkce_pair_is_unique():
    """
    Test that successive calls produce different values.
    """
    pair_a = generate_pkce_pair()
    pair_b = generate_pkce_pair()
    assert pair_a[0] != pair_b[0]


# ---- Authorization URL generation ----


def test_generate_authorization_url_basic(idp, web_client):
    """
    Test authorization URL without PKCE.
    """
    url = generate_authorization_url(idp, web_client, state="test-state")
    parsed = urlparse(url)
    params = parse_qs(parsed.query)

    assert parsed.scheme == "https"
    assert parsed.netloc == "idp.example.com"
    assert parsed.path == "/authorize"
    assert params["response_type"] == ["code"]
    assert params["client_id"] == ["my-client-id"]
    assert params["redirect_uri"] == ["http://localhost:8000/ui/v1/auth/callback"]
    assert params["scope"] == ["openid profile"]
    assert params["state"] == ["test-state"]
    assert "code_challenge" not in params


def test_generate_authorization_url_with_pkce(idp, web_client_pkce):
    """
    Test authorization URL with PKCE enabled.
    """
    verifier, _ = generate_pkce_pair()
    url = generate_authorization_url(
        idp, web_client_pkce, state="pkce-state", pkce_verifier=verifier
    )
    parsed = urlparse(url)
    params = parse_qs(parsed.query)

    assert "code_challenge" in params
    assert params["code_challenge_method"] == ["S256"]

    # verify the challenge matches the verifier
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    expected = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    assert params["code_challenge"] == [expected]


def test_generate_authorization_url_pkce_disabled_ignores_verifier(idp, web_client):
    """
    Test that verifier is ignored when PKCE is disabled.
    """
    url = generate_authorization_url(
        idp, web_client, state="s", pkce_verifier="should-be-ignored"
    )
    params = parse_qs(urlparse(url).query)
    assert "code_challenge" not in params


# ---- Token exchange ----


@pytest.mark.asyncio
async def test_exchange_code_for_tokens_basic_auth(idp, web_client):
    """
    Test code exchange using client_secret_basic authentication.
    """
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "access_token": "at_123",
        "id_token": "idt_456",
        "expires_in": 3600,
    }

    with patch("nmtfast.auth.v1.auth_code.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_cls.return_value = mock_client

        result = await exchange_code_for_tokens(idp, web_client, code="auth-code-123")

    assert result["access_token"] == "at_123"
    call_kwargs = mock_client.post.call_args
    assert call_kwargs.args[0] == "https://idp.example.com/token"
    assert call_kwargs.kwargs["data"]["grant_type"] == "authorization_code"
    assert call_kwargs.kwargs["data"]["code"] == "auth-code-123"
    assert "Authorization" in call_kwargs.kwargs["headers"]


@pytest.mark.asyncio
async def test_exchange_code_for_tokens_post_auth(idp, web_client_post_auth):
    """
    Test code exchange using client_secret_post authentication.
    """
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"access_token": "at_post"}

    with patch("nmtfast.auth.v1.auth_code.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_cls.return_value = mock_client

        result = await exchange_code_for_tokens(
            idp, web_client_post_auth, code="code-456"
        )

    assert result["access_token"] == "at_post"
    call_kwargs = mock_client.post.call_args
    assert call_kwargs.kwargs["data"]["client_id"] == "my-client-id"
    assert call_kwargs.kwargs["data"]["client_secret"] == "my-client-secret"
    assert "Authorization" not in call_kwargs.kwargs["headers"]


@pytest.mark.asyncio
async def test_exchange_code_for_tokens_with_pkce(idp, web_client_pkce):
    """
    Test code exchange includes code_verifier when PKCE is enabled.
    """
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"access_token": "at_pkce"}

    with patch("nmtfast.auth.v1.auth_code.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_cls.return_value = mock_client

        result = await exchange_code_for_tokens(
            idp, web_client_pkce, code="code-789", pkce_verifier="verifier123"
        )

    call_kwargs = mock_client.post.call_args
    assert call_kwargs.kwargs["data"]["code_verifier"] == "verifier123"
    assert result["access_token"] == "at_pkce"


@pytest.mark.asyncio
async def test_exchange_code_for_tokens_failure(idp, web_client):
    """
    Test that a non-200 response raises AuthenticationError.
    """
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.text = "invalid_grant"

    with patch("nmtfast.auth.v1.auth_code.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_cls.return_value = mock_client

        with pytest.raises(AuthenticationError, match="Token exchange failed"):
            await exchange_code_for_tokens(idp, web_client, code="bad-code")


# ---- Refresh token ----


@pytest.mark.asyncio
async def test_refresh_access_token_success(idp, web_client):
    """
    Test successful token refresh.
    """
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "access_token": "new_at",
        "expires_in": 3600,
    }

    with patch("nmtfast.auth.v1.auth_code.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_cls.return_value = mock_client

        result = await refresh_access_token(idp, web_client, refresh_token="rt_old")

    assert result["access_token"] == "new_at"
    call_kwargs = mock_client.post.call_args
    assert call_kwargs.kwargs["data"]["grant_type"] == "refresh_token"
    assert call_kwargs.kwargs["data"]["refresh_token"] == "rt_old"


@pytest.mark.asyncio
async def test_refresh_access_token_failure(idp, web_client):
    """
    Test that a failed refresh raises AuthenticationError.
    """
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.text = "invalid_grant"

    with patch("nmtfast.auth.v1.auth_code.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_cls.return_value = mock_client

        with pytest.raises(AuthenticationError, match="Token refresh failed"):
            await refresh_access_token(idp, web_client, refresh_token="rt_expired")


@pytest.mark.asyncio
async def test_refresh_access_token_post_auth(idp, web_client_post_auth):
    """
    Test token refresh using client_secret_post authentication.
    """
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "access_token": "new_at_post",
        "expires_in": 3600,
    }

    with patch("nmtfast.auth.v1.auth_code.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_cls.return_value = mock_client

        result = await refresh_access_token(
            idp, web_client_post_auth, refresh_token="rt_old"
        )

    assert result["access_token"] == "new_at_post"
    call_kwargs = mock_client.post.call_args
    assert call_kwargs.kwargs["data"]["client_id"] == "my-client-id"
    assert call_kwargs.kwargs["data"]["client_secret"] == "my-client-secret"
    assert "Authorization" not in call_kwargs.kwargs["headers"]
