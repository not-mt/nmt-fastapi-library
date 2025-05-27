# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Library functions to handle OAuth for connecting to discovered services."""

import json
import logging
from typing import Any, Dict, Optional

import httpx
from authlib.integrations.httpx_client import AsyncOAuth2Client
from authlib.oauth2.rfc6749.errors import OAuth2Error
from tenacity import retry, stop_after_attempt, wait_fixed

from nmtfast.cache.v1.base import AppCacheBase
from nmtfast.discovery.v1.exceptions import ServiceConnectionError
from nmtfast.retry.v1.tenacity import tenacity_retry_log
from nmtfast.settings.v1.schemas import (
    AuthSettings,
    DiscoveredService,
    IDProvider,
    OutgoingAuthClient,
    OutgoingAuthHeaders,
    ServiceDiscoverySettings,
)

CACHE_KEY_PREFIX: str = ":api_client_token"
logger: logging.Logger = logging.getLogger(__name__)


@retry(
    reraise=True,
    stop=stop_after_attempt(20),
    wait=wait_fixed(15),
    after=tenacity_retry_log(logger),
)
async def get_oauth_client(
    service_config: DiscoveredService,
    id_provider: IDProvider,
    client_settings: OutgoingAuthClient,
    cached_token: Optional[Dict[str, Any]] = None,
) -> AsyncOAuth2Client:
    """
    Retrieves or creates an Authlib AsyncOAuth2Client for a given provider.

    This function initializes an AsyncOAuth2Client with the necessary
    client credentials and provider details. It is configured with timeouts,
    connection limits, and retries based on the service configuration.

    Args:
        service_config: Configuration for the discovered service, including
            base URL, timeouts, and headers.
        id_provider: Configuration for the identity provider, including
            the token endpoint.
        client_settings: Settings for the outgoing OAuth client, including
            client ID, secret, and authentication method.
        cached_token: An optional dictionary containing a previously cached
            access token. If provided, the client will attempt to use this token.

    Returns:
        AsyncOAuth2Client: An initialized httpx OAuth 2 client.
    """
    client: AsyncOAuth2Client = AsyncOAuth2Client(
        client_id=client_settings.client_id,
        client_secret=client_settings.client_secret,
        token=cached_token,  # only if this was passed in from cache
        token_endpoint=id_provider.token_endpoint,
        token_endpoint_auth_method=client_settings.token_endpoint_auth_method,
        scope=service_config.scope,
        base_url=service_config.base_url,
        compliance_hook={"refresh_token_request": lambda params: params},
        follow_redirects=True,
        timeout=httpx.Timeout(
            service_config.timeout,
            connect=service_config.connect_timeout,
        ),
        limits=httpx.Limits(
            max_keepalive_connections=1,
        ),
        transport=httpx.AsyncHTTPTransport(
            retries=service_config.retries,
        ),
        headers=service_config.headers,
    )
    return client


@retry(
    reraise=True,
    stop=stop_after_attempt(20),
    wait=wait_fixed(15),
    after=tenacity_retry_log(logger),
)
async def create_api_client(
    auth: AuthSettings,
    discovery: ServiceDiscoverySettings,
    service_name: str,
    cache: AppCacheBase,
) -> httpx.AsyncClient:
    """Creates and configures an httpx.AsyncClient for a discovered service.

    This function retrieves the configuration for a specified service,
    and initializes an httpx.AsyncClient. If the service requires
    client credentials authentication, it attempts to retrieve a token
    from cache or acquire a new one using Authlib.

    Args:
        auth: Application authentication settings.
        discovery: Application service discovery settings.
        service_name: The name of the service to create a client for.
        cache: An instance of AppCacheBase for token caching.

    Returns:
        httpx.AsyncClient: An httpx.AsyncClient instance, potentially pre-configured
            with authentication headers for OAuth.

    Raises:
        ServiceConnectionError: If the service is not found, or if there
            are issues with authentication client/provider lookup or token acquisition.
    """
    if service_name not in discovery.services:
        raise ServiceConnectionError(
            f"Service '{service_name}' not found in discovery settings."
        )

    service_config: DiscoveredService = discovery.services[service_name]

    # Initialize http_client with a default httpx.AsyncClient.
    # This covers cases where no specific auth method is needed or for API keys.
    http_client: httpx.AsyncClient = httpx.AsyncClient(
        base_url=service_config.base_url,
        follow_redirects=True,
        timeout=httpx.Timeout(
            service_config.timeout,
            connect=service_config.connect_timeout,
        ),
        limits=httpx.Limits(
            max_keepalive_connections=1,
        ),
        transport=httpx.AsyncHTTPTransport(
            retries=service_config.retries,
        ),
        headers=service_config.headers,
    )

    if service_config.auth_method == "client_credentials":
        cached_token: Optional[Dict[str, Any]] = None
        token_key: str = f"{CACHE_KEY_PREFIX}:{service_name}"

        # NOTE: look for a cached access token first, instead of always trying to
        #   acquire one when an app starts
        if raw_cached_token := cache.fetch_app_cache(token_key):
            cached_token = json.loads(raw_cached_token.decode("utf-8"))
            logger.debug(f"Found cached API client token for {service_name}")

        outgoing_client_name: str = service_config.auth_principal
        outgoing_client = auth.outgoing.clients.get(outgoing_client_name)

        if not outgoing_client:
            raise ServiceConnectionError(
                f"Outgoing client '{outgoing_client_name}' not found in auth settings."
            )

        id_provider_name: str = outgoing_client.provider
        id_provider = auth.id_providers.get(id_provider_name)

        if not id_provider:
            raise ServiceConnectionError(
                f"ID Provider '{id_provider_name}' not found in auth settings."
            )

        try:
            oauth_client = await get_oauth_client(
                service_config,
                id_provider,
                outgoing_client,
                cached_token,
            )

            # Check if existing token from cache is still valid
            if cached_token and not oauth_client.token.is_expired():
                logger.debug(f"Returning cached API client for {service_name}")
                http_client = oauth_client
                return http_client

            # NOTE: authlib fetch_token will automatically get a new token or refresh
            # an expired one if the client is not already configured with a valid
            # token.
            token: dict = await oauth_client.fetch_token()
            if not token or not token.get("access_token"):
                raise ServiceConnectionError(
                    f"Authlib failed to retrieve token for service '{service_name}'."
                )

            # Authlib token object is not directly JSON serializable,
            #   use its internal data dictionary
            cache.store_app_cache(token_key, json.dumps(oauth_client.token))
            logger.debug(
                f"Cached {service_name} access token "
                f"for {outgoing_client.cache_ttl} seconds"
            )

            # NOTE: no need to manually add "Authorization" header here, Authlib
            #   handles it
            http_client = oauth_client

        except OAuth2Error as exc:
            raise ServiceConnectionError(
                f"OAuth error while getting token for service '{service_name}': "
                f"{exc.description}"
            ) from exc
        except Exception as exc:
            raise ServiceConnectionError(
                "An unexpected error occurred during OAuth token acquisition "
                f"for service '{service_name}': {exc}"
            ) from exc

    # NOTE: setting this to elif causes missing code coverage?!
    if service_config.auth_method == "headers":
        # NOTE: auth headers can be blank if no authentication is required
        outgoing_auth_name: str = service_config.auth_principal
        outgoing_auth: OutgoingAuthHeaders = auth.outgoing.headers[outgoing_auth_name]
        logger.debug(f"Using static auth headers for '{outgoing_auth_name}' client")
        http_client.headers.update(outgoing_auth.headers)

    return http_client
