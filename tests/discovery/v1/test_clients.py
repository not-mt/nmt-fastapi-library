# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Tests for OAuth client handling in nmtfast.discovery.v1.clients."""

import json
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from authlib.integrations.httpx_client import AsyncOAuth2Client
from authlib.oauth2.rfc6749.errors import OAuth2Error

from nmtfast.cache.v1.base import AppCacheBase
from nmtfast.discovery.v1.exceptions import ServiceConnectionError
from nmtfast.settings.v1.schemas import (
    AuthSettings,
    DiscoveredService,
    IDProvider,
    OutgoingAuthClient,
    OutgoingAuthHeaders,
    OutgoingAuthSettings,
    ServiceDiscoverySettings,
)

# NOTE: we cannot import create_api_client, get_oauth_client outside of tests
#   they MUST be imported inside of the test so that the patch_retry_and_reload()
#   fixture will intercept tenacity retry and disable it


@pytest.fixture(autouse=True)
def patch_retry_and_reload():
    """
    Patch the retry decorator and reload nmtfast.discovery.v1.clients.

    This incredibly useful (but difficult to discover) use of fixtures will prevent
    tenacity retry from firing. Basically, we need to strip out the retry decorator
    before the module is loaded and cached by the interpreter.
    """
    from importlib import import_module

    # save original module if exists
    original = sys.modules.get("nmtfast.discovery.v1.clients")

    # remove module so reload works fresh
    sys.modules.pop("nmtfast.discovery.v1.clients", None)

    # patch tenacity or retry symbol before import if needed
    import tenacity

    original_retry = tenacity.retry
    tenacity.retry = lambda *args, **kwargs: lambda f: f

    # import fresh module with retry patched
    module = import_module("nmtfast.discovery.v1.clients")

    # restore tenacity.retry after import
    tenacity.retry = original_retry

    yield module

    # NOTE: this cleanup runs AFTER the test is complete

    # reload original module after test to avoid side effects
    if original is not None:
        sys.modules["nmtfast.discovery.v1.clients"] = original
    else:
        sys.modules.pop("nmtfast.discovery.v1.clients", None)


@pytest.fixture
def mock_id_provider():
    """
    Fixture to return a mock identity provider.
    """
    return IDProvider(
        token_endpoint="https://auth.example.com/token",
        jwks_endpoint="https://auth.example.com/jwks",
    )


@pytest.fixture
def mock_outgoing_client():
    """
    Fixture to return a mock outgoing API client.
    """
    return OutgoingAuthClient(
        provider="test_provider",
        client_id="client_id",
        client_secret="client_secret",
        token_endpoint_auth_method="client_secret_basic",
    )


@pytest.fixture
def mock_outgoing_headers():
    """
    Fixture to return a mock outgoing auth headers principal.
    """
    return OutgoingAuthHeaders(
        contact="some contact",
        memo="some memo",
        headers={
            "x-api-key": "static header here",
        },
    )


@pytest.fixture
def mock_service_config():
    """
    Fixture to return a mock discovered service.
    """
    return DiscoveredService(
        base_url="https://api.example.com",
        auth_method="client_credentials",
        auth_principal="test_client",
        timeout=10.0,
        connect_timeout=5.0,
        retries=3,
    )


@pytest.fixture
def mock_auth_settings(mock_id_provider, mock_outgoing_client, mock_outgoing_headers):
    """
    Fixture to return mock discovery settings.
    """
    return AuthSettings(
        swagger_token_url="https://example.com/swagger/token",
        id_providers={"test_provider": mock_id_provider},
        outgoing=OutgoingAuthSettings(
            clients={"test_client": mock_outgoing_client},
            headers={"test_headers": mock_outgoing_headers},
        ),
    )


@pytest.fixture
def mock_discovery_settings(mock_service_config):
    """
    Fixture to return mock discovery settings.
    """
    return ServiceDiscoverySettings(services={"test_service": mock_service_config})


@pytest.fixture
def mock_cache():
    """
    Fixture to return a mock AppCacheBase object.
    """
    cache = MagicMock(spec=AppCacheBase)
    cache.fetch_app_cache.return_value = None
    cache.store_app_cache = MagicMock()
    return cache


@pytest.mark.asyncio
async def test_get_oauth_client(
    mock_service_config, mock_id_provider, mock_outgoing_client, monkeypatch
):
    """
    Test get_oauth_client creates a properly configured client.
    """
    # NOTE: we must load nmtfast.discovery.v1.clients functions INSIDE of the test
    #   in order for the patch_retry_and_reload() autouse fixture to intercept
    #   tenacity retry, and disable it
    from nmtfast.discovery.v1.clients import get_oauth_client

    with (
        patch(
            "nmtfast.discovery.v1.clients.AsyncOAuth2Client", autospec=True
        ) as mock_client_class,
        patch(
            "httpx.AsyncHTTPTransport",
            return_value="MOCK_TRANSPORT",
        ),
    ):
        mock_client_instance = MagicMock()
        mock_client_class.return_value = mock_client_instance

        await get_oauth_client(
            service_config=mock_service_config,
            id_provider=mock_id_provider,
            client_settings=mock_outgoing_client,
        )

        # Assert the client was created with expected parameters
        mock_client_class.assert_called_once()
        call_args = mock_client_class.call_args.kwargs
        assert call_args["client_id"] == "client_id"
        assert call_args["client_secret"] == "client_secret"
        assert call_args["token_endpoint"] == "https://auth.example.com/token"
        assert call_args["token_endpoint_auth_method"] == "client_secret_basic"
        assert call_args["base_url"] == "https://api.example.com"
        assert isinstance(call_args["timeout"], httpx.Timeout)
        assert call_args["timeout"].connect == 5.0
        assert call_args["timeout"].read == 10.0


@pytest.mark.asyncio
async def test_create_api_client_with_client_credentials(
    mock_auth_settings, mock_discovery_settings, mock_cache
):
    """
    Test create_api_client works with client credentials auth.
    """
    # NOTE: we must load nmtfast.discovery.v1.clients functions INSIDE of the test
    #   in order for the patch_retry_and_reload() autouse fixture to intercept
    #   tenacity retry, and disable it
    from nmtfast.discovery.v1.clients import create_api_client

    mock_cache.fetch_app_cache.return_value = None

    with patch("nmtfast.discovery.v1.clients.AsyncOAuth2Client") as MockOAuthClient:

        # create a proper mock client and the entire token flow
        mock_client = AsyncMock(spec=AsyncOAuth2Client)
        mock_client.fetch_token = AsyncMock(
            return_value={
                "access_token": "test_token",
                "token_type": "Bearer",
                "expires_in": 3600,
            }
        )
        mock_client.token = {
            "access_token": "test_token",
            "token_type": "Bearer",
            "expires_in": 3600,
        }
        MockOAuthClient.return_value = mock_client

        # Mock the transport to prevent real network calls
        with patch("httpx.AsyncHTTPTransport") as MockHTTPTransport:
            mock_transport_instance = MagicMock()
            mock_transport_instance.handle_async_request = AsyncMock(
                return_value=httpx.Response(
                    200, request=httpx.Request("GET", "http://test.com")
                )
            )
            MockHTTPTransport.return_value = mock_transport_instance  # Ensure the constructor returns our mock instance

            await create_api_client(
                auth=mock_auth_settings,
                discovery=mock_discovery_settings,
                service_name="test_service",
                cache=mock_cache,
            )

        # Verify the client was properly configured
        MockOAuthClient.assert_called_once()
        mock_client.fetch_token.assert_awaited_once()
        mock_cache.store_app_cache.assert_called_once()


@pytest.mark.asyncio
async def test_create_api_client_with_valid_cached_token(
    mock_auth_settings, mock_discovery_settings, mock_cache
):
    """
    Test create_api_client uses valid cached token.
    """
    # NOTE: we must load nmtfast.discovery.v1.clients functions INSIDE of the test
    #   in order for the patch_retry_and_reload() autouse fixture to intercept
    #   tenacity retry, and disable it
    from nmtfast.discovery.v1.clients import create_api_client

    cached_token = {
        "access_token": "valid_token",
        "token_type": "Bearer",
        "expires_at": 9999999999,
    }
    mock_cache.fetch_app_cache.return_value = json.dumps(cached_token).encode()

    with patch("nmtfast.discovery.v1.clients.AsyncOAuth2Client") as MockOAuthClient:

        # create mock client and mock token validation
        mock_client = AsyncMock(spec=AsyncOAuth2Client)
        mock_token = MagicMock()
        mock_token.is_expired.return_value = False
        mock_client.token = mock_token
        MockOAuthClient.return_value = mock_client

        # mock the transport so no network traffic happens
        with patch("httpx.AsyncHTTPTransport"):

            await create_api_client(
                auth=mock_auth_settings,
                discovery=mock_discovery_settings,
                service_name="test_service",
                cache=mock_cache,
            )

        mock_client.fetch_token.assert_not_called()


@pytest.mark.asyncio
async def test_create_api_client_service_not_found(
    mock_auth_settings, mock_discovery_settings, mock_cache
):
    """
    Test create_api_client raises for unknown services.
    """
    # NOTE: we must load nmtfast.discovery.v1.clients functions INSIDE of the test
    #   in order for the patch_retry_and_reload() autouse fixture to intercept
    #   tenacity retry, and disable it
    from nmtfast.discovery.v1.clients import create_api_client

    with pytest.raises(ServiceConnectionError):
        await create_api_client(
            auth=mock_auth_settings,
            discovery=mock_discovery_settings,
            service_name="missing_service",
            cache=mock_cache,
        )


@pytest.mark.asyncio
async def test_create_api_client_service_not_found_alt1(
    mock_auth_settings, mock_discovery_settings, mock_cache
):
    """Test create_api_client raises ServiceConnectionError when service not found."""
    from nmtfast.discovery.v1.clients import create_api_client

    with pytest.raises(ServiceConnectionError) as excinfo:
        await create_api_client(
            auth=mock_auth_settings,
            discovery=mock_discovery_settings,
            service_name="nonexistent_service",
            cache=mock_cache,
        )
    assert "nonexistent_service" in str(excinfo.value)


@pytest.mark.asyncio
async def test_create_api_client_outgoing_client_not_found(
    mock_auth_settings, mock_cache, mock_service_config
):
    """
    Test create_api_client raises when outgoing client not found in auth settings.
    """
    # NOTE: we must load nmtfast.discovery.v1.clients functions INSIDE of the test
    #   in order for the patch_retry_and_reload() autouse fixture to intercept
    #   tenacity retry, and disable it
    from nmtfast.discovery.v1.clients import create_api_client

    mock_service_config.auth_principal = "missing_client"

    # manipulate the service config to use a missing client name
    bad_discovery = ServiceDiscoverySettings(
        services={
            "test_service": mock_service_config,
        }
    )
    with pytest.raises(ServiceConnectionError) as excinfo:
        await create_api_client(
            auth=mock_auth_settings,
            discovery=bad_discovery,
            service_name="test_service",
            cache=mock_cache,
        )

    assert "Outgoing client 'missing_client' not found" in str(excinfo.value)


@pytest.mark.asyncio
async def test_create_api_client_id_provider_not_found(
    mock_auth_settings,
    mock_cache,
    mock_outgoing_client,
    mock_service_config,
):
    """
    Test create_api_client raises when ID provider not found.
    """
    from nmtfast.discovery.v1.clients import create_api_client

    mock_outgoing_client.provider = "missing_provider"

    bad_auth_settings = AuthSettings(
        swagger_token_url=mock_auth_settings.swagger_token_url,
        id_providers={},  # no providers
        outgoing=OutgoingAuthSettings(clients={"test_client": mock_outgoing_client}),
    )

    # service discovery uses auth_principal 'test_client'
    good_discovery = ServiceDiscoverySettings(
        services={"test_service": mock_service_config}
    )
    with pytest.raises(ServiceConnectionError) as excinfo:
        await create_api_client(
            auth=bad_auth_settings,
            discovery=good_discovery,
            service_name="test_service",
            cache=mock_cache,
        )

    assert "ID Provider 'missing_provider' not found" in str(excinfo.value)


@pytest.mark.asyncio
async def test_create_api_client_oauth2_error(
    mock_auth_settings, mock_discovery_settings, mock_cache
):
    """
    Test create_api_client handles OAuth2Error during token fetch.
    """
    # NOTE: we must load nmtfast.discovery.v1.clients functions INSIDE of the test
    #   in order for the patch_retry_and_reload() autouse fixture to intercept
    #   tenacity retry, and disable it
    from nmtfast.discovery.v1.clients import create_api_client

    mock_cache.fetch_app_cache.return_value = None

    with patch(
        "nmtfast.discovery.v1.clients.get_oauth_client",
        new_callable=AsyncMock,
    ) as mock_get_oauth_client:

        # simulate fetch_token raising OAuth2Error
        mock_oauth_client = AsyncMock()
        mock_oauth_client.fetch_token.side_effect = OAuth2Error(
            description="Invalid client"
        )
        mock_get_oauth_client.return_value = mock_oauth_client

        with pytest.raises(ServiceConnectionError) as excinfo:
            await create_api_client(
                auth=mock_auth_settings,
                discovery=mock_discovery_settings,
                service_name="test_service",
                cache=mock_cache,
            )
        assert "test_service" in str(excinfo.value)


@pytest.mark.asyncio
async def test_create_api_client_unexpected_exception(
    mock_auth_settings, mock_discovery_settings, mock_cache
):
    """
    Test create_api_client handles unexpected exceptions during token fetch.
    """
    # NOTE: we must load nmtfast.discovery.v1.clients functions INSIDE of the test
    #   in order for the patch_retry_and_reload() autouse fixture to intercept
    #   tenacity retry, and disable it
    from nmtfast.discovery.v1.clients import create_api_client

    mock_cache.fetch_app_cache.return_value = None

    with patch(
        "nmtfast.discovery.v1.clients.get_oauth_client", new_callable=AsyncMock
    ) as mock_get_oauth_client:

        # simulate fetch_token raising generic Exception
        mock_oauth_client = AsyncMock()
        mock_oauth_client.fetch_token.side_effect = Exception("Connection lost")
        mock_get_oauth_client.return_value = mock_oauth_client

        with pytest.raises(ServiceConnectionError) as excinfo:
            await create_api_client(
                auth=mock_auth_settings,
                discovery=mock_discovery_settings,
                service_name="test_service",
                cache=mock_cache,
            )
        assert "error" in str(excinfo.value)


@pytest.mark.asyncio
async def test_create_api_client_returns_auth_headers(mock_auth_settings, mock_cache):
    """
    Test create_api_client returns AsyncClient for non-client_credentials auth method.
    """
    from nmtfast.discovery.v1.clients import create_api_client

    # Setup service config with headers auth
    service_config = DiscoveredService(
        base_url="https://api.example.com",
        auth_method="headers",
        auth_principal="test_headers",  # matches mock_outgoing_headers fixture
        timeout=10.0,
        connect_timeout=5.0,
        retries=2,
    )
    discovery = ServiceDiscoverySettings(services={"test_service": service_config})

    # Call the function
    client = await create_api_client(
        auth=mock_auth_settings,
        discovery=discovery,
        service_name="test_service",
        cache=mock_cache,
    )

    # Verify the client
    assert isinstance(client, httpx.AsyncClient)
    assert client.base_url == "https://api.example.com"
    assert (
        client.headers["x-api-key"] == "static header here"
    )  # From mock_outgoing_headers


@pytest.mark.asyncio
async def test_create_api_client_with_cached_token_returned(
    mock_auth_settings, mock_discovery_settings, mock_cache
):
    """
    Test create_api_client returns cached client if token is valid.
    """
    # NOTE: we must load nmtfast.discovery.v1.clients functions INSIDE of the test
    #   in order for the patch_retry_and_reload() autouse fixture to intercept
    #   tenacity retry, and disable it
    from nmtfast.discovery.v1.clients import create_api_client

    # setup a fake cached token JSON string
    cached_token_data = {
        "access_token": "cached_token",
        "token_type": "Bearer",
        "expires_in": 3600,
    }
    cached_token_json = json.dumps(cached_token_data)
    mock_cache.fetch_app_cache.return_value = cached_token_json.encode("utf-8")

    # patch AsyncOAuth2Client and its token.is_expired() to False to simulate
    #   valid token
    with patch("nmtfast.discovery.v1.clients.AsyncOAuth2Client") as MockOAuthClient:
        mock_client = AsyncMock(spec=AsyncOAuth2Client)
        mock_token = MagicMock()
        mock_token._data = cached_token_data
        mock_token.is_expired.return_value = False
        mock_client.token = mock_token
        MockOAuthClient.return_value = mock_client

        http_client = await create_api_client(
            auth=mock_auth_settings,
            discovery=mock_discovery_settings,
            service_name="test_service",
            cache=mock_cache,
        )

        # it should return the OAuth client directly using cached token
        assert http_client is mock_client
        mock_cache.fetch_app_cache.assert_called_once()
        MockOAuthClient.assert_called_once()


@pytest.mark.asyncio
async def test_create_api_client_raises_when_token_missing_access_token(
    mock_auth_settings,
    mock_discovery_settings,
    monkeypatch,
    mock_cache,
):
    # NOTE: we must load nmtfast.discovery.v1.clients functions INSIDE of the test
    #   in order for the patch_retry_and_reload() autouse fixture to intercept
    #   tenacity retry, and disable it
    from nmtfast.discovery.v1.clients import ServiceConnectionError, create_api_client

    # Patch the AsyncOAuth2Client.fetch_token to return a token without access_token
    class MockOAuth2Client:
        def __init__(self, *args, **kwargs):
            pass

        async def fetch_token(self):
            return {"expires_in": 3600}  # Missing 'access_token'

    monkeypatch.setattr(
        "nmtfast.discovery.v1.clients.AsyncOAuth2Client",
        MockOAuth2Client,
    )

    # explicitly add a get() method to the mock cache
    mock_cache.get = MagicMock(return_value=None)

    with pytest.raises(ServiceConnectionError) as excinfo:
        await create_api_client(
            auth=mock_auth_settings,
            discovery=mock_discovery_settings,
            service_name="test_service",
            cache=mock_cache,
        )

    assert "Authlib failed to retrieve token" in str(excinfo.value)


@pytest.mark.asyncio
async def test_create_api_client_raises_when_outgoing_client_missing(
    mock_auth_settings, mock_discovery_settings, mock_cache
):
    """
    Test create_api_client raises if outgoing client not found in auth settings.
    """
    # NOTE: we must load nmtfast.discovery.v1.clients functions INSIDE of the test
    #   in order for the patch_retry_and_reload() autouse fixture to intercept
    #   tenacity retry, and disable it
    from nmtfast.discovery.v1.clients import create_api_client

    # remove the outgoing client entry
    mock_auth_settings.outgoing.clients.pop("test_client", None)

    with pytest.raises(ServiceConnectionError) as excinfo:
        await create_api_client(
            auth=mock_auth_settings,
            discovery=mock_discovery_settings,
            service_name="test_service",
            cache=mock_cache,
        )
    assert "test_client" in str(excinfo.value)


@pytest.mark.asyncio
async def test_create_api_client_raises_when_id_provider_missing(
    mock_auth_settings,
    mock_discovery_settings,
    mock_cache,
):
    """
    Test create_api_client raises if ID provider not found in auth settings.
    """
    # NOTE: we must load nmtfast.discovery.v1.clients functions INSIDE of the test
    #   in order for the patch_retry_and_reload() autouse fixture to intercept
    #   tenacity retry, and disable it
    from nmtfast.discovery.v1.clients import create_api_client

    # remove the id provider entry so it is missing
    mock_auth_settings.id_providers.pop("test_provider", None)
    with pytest.raises(ServiceConnectionError) as excinfo:
        await create_api_client(
            auth=mock_auth_settings,
            discovery=mock_discovery_settings,
            service_name="test_service",
            cache=mock_cache,
        )

    assert "ID Provider 'test_provider' not found" in str(excinfo.value)


@pytest.mark.asyncio
async def test_create_api_client_raises_when_id_provider_missing_alt1(
    mock_auth_settings, mock_discovery_settings, mock_cache
):
    # NOTE: we must load nmtfast.discovery.v1.clients functions INSIDE of the test
    #   in order for the patch_retry_and_reload() autouse fixture to intercept
    #   tenacity retry, and disable it
    from nmtfast.discovery.v1.clients import create_api_client

    # remove the id provider entry
    mock_auth_settings.id_providers.pop("test_provider", None)
    with pytest.raises(ServiceConnectionError) as excinfo:
        await create_api_client(
            auth=mock_auth_settings,
            discovery=mock_discovery_settings,
            service_name="test_service",
            cache=mock_cache,
        )

    assert "ID Provider 'test_provider' not found" in str(excinfo.value)
