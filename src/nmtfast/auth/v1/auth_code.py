# -*- coding: utf-8 -*-
# Copyright (c) 2026. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""OAuth2 Authorization Code flow helpers for interactive web login."""

import base64
import hashlib
import logging
import secrets
from urllib.parse import urlencode

import httpx

from nmtfast.auth.v1.exceptions import AuthenticationError
from nmtfast.settings.v1.schemas import IDProvider, WebAuthClientSettings

logger = logging.getLogger(__name__)


def generate_pkce_pair() -> tuple[str, str]:
    """
    Generate a PKCE code verifier and its S256 code challenge.

    Returns:
        tuple[str, str]: A (code_verifier, code_challenge) pair.
    """
    code_verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return code_verifier, code_challenge


def generate_authorization_url(
    provider: IDProvider,
    client: WebAuthClientSettings,
    state: str,
    pkce_verifier: str | None = None,
) -> str:
    """
    Build the full authorization URL for the OAuth2 Authorization Code flow.

    Args:
        provider: The identity provider configuration.
        client: The web auth client settings.
        state: An opaque CSRF state parameter.
        pkce_verifier: Optional PKCE code verifier. When provided and PKCE is
            enabled, the corresponding S256 code challenge is included.

    Returns:
        str: The complete authorization URL to redirect the user to.
    """
    params: dict[str, str] = {
        "response_type": "code",
        "client_id": client.client_id,
        "redirect_uri": client.redirect_uri,
        "scope": " ".join(client.scopes),
        "state": state,
    }

    if client.pkce_enabled and pkce_verifier:
        digest = hashlib.sha256(pkce_verifier.encode("ascii")).digest()
        code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
        params["code_challenge"] = code_challenge
        params["code_challenge_method"] = "S256"

    return f"{provider.authorize_endpoint}?{urlencode(params)}"


async def exchange_code_for_tokens(
    provider: IDProvider,
    client: WebAuthClientSettings,
    code: str,
    pkce_verifier: str | None = None,
) -> dict:
    """
    Exchange an authorization code for tokens at the provider's token endpoint.

    Args:
        provider: The identity provider configuration.
        client: The web auth client settings.
        code: The authorization code received from the provider callback.
        pkce_verifier: Optional PKCE code verifier to include in the request.

    Returns:
        dict: The token response containing access_token, id_token,
            refresh_token (if granted), and expires_in.

    Raises:
        AuthenticationError: If the token exchange fails.
    """
    data: dict[str, str] = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": client.redirect_uri,
    }

    if client.pkce_enabled and pkce_verifier:
        data["code_verifier"] = pkce_verifier

    headers: dict[str, str] = {}
    if client.token_endpoint_auth_method == "client_secret_basic":
        auth_value = base64.b64encode(
            f"{client.client_id}:{client.client_secret}".encode()
        ).decode()
        headers["Authorization"] = f"Basic {auth_value}"
    else:
        data["client_id"] = client.client_id
        data["client_secret"] = client.client_secret

    async with httpx.AsyncClient() as http_client:
        response = await http_client.post(
            provider.token_endpoint,
            data=data,
            headers=headers,
        )

    if response.status_code != 200:
        logger.error(f"Token exchange failed: {response.status_code} {response.text}")
        raise AuthenticationError(
            f"Token exchange failed (HTTP {response.status_code})"
        )

    return response.json()


async def refresh_access_token(
    provider: IDProvider,
    client: WebAuthClientSettings,
    refresh_token: str,
) -> dict:
    """
    Use a refresh token to obtain a new access token.

    Args:
        provider: The identity provider configuration.
        client: The web auth client settings.
        refresh_token: The refresh token from a previous token response.

    Returns:
        dict: The token response containing a new access_token (and possibly
            a new refresh_token).

    Raises:
        AuthenticationError: If the refresh request fails.
    """
    data: dict[str, str] = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }

    headers: dict[str, str] = {}
    if client.token_endpoint_auth_method == "client_secret_basic":
        auth_value = base64.b64encode(
            f"{client.client_id}:{client.client_secret}".encode()
        ).decode()
        headers["Authorization"] = f"Basic {auth_value}"
    else:
        data["client_id"] = client.client_id
        data["client_secret"] = client.client_secret

    async with httpx.AsyncClient() as http_client:
        response = await http_client.post(
            provider.token_endpoint,
            data=data,
            headers=headers,
        )

    if response.status_code != 200:
        logger.error(f"Token refresh failed: {response.status_code} {response.text}")
        raise AuthenticationError(f"Token refresh failed (HTTP {response.status_code})")

    return response.json()
