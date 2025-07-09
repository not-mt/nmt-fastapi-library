# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""pydantic-settings schemas that can be re-used in nmtfast-derived apps."""

from typing import Literal, Optional

from pydantic import BaseModel


class IDProvider(BaseModel):
    """
    ID provider/platform settings.

    Attributes:
        type: Provider type.
        issuer_regex: Regex pattern for validating issuer claims.
        jwks_endpoint: URL for JWKS endpoint.
        token_endpoint: URL for acquiring access/refresh tokens.
        authorize_endpoint: URL for auth code flow.
        introspection_enabled: Whether token introspection is enabled.
        introspection_endpoint: URL for token introspection endpoint.
        keyid_enabled: Whether key ID verification is enabled.
        keyid_endpoint: URL for key ID verification endpoint.
    """

    type: str = "jwks"
    issuer_regex: str = "__REAL_REGEX_GOES_HERE__"
    jwks_endpoint: str = "http://localhost/jwks"
    token_endpoint: str = "http://localhost/token"
    authorize_endpoint: str = "http://localhost/authorize"
    introspection_enabled: bool = False
    introspection_endpoint: str = "http://localhost/introspection"
    keyid_enabled: bool = False
    keyid_endpoint: str = "http://localhost/keyid"


# TODO: add support for filters later
# class FilterACL(BaseModel):
#     """Access for a client/key to specific section(s) matching a regex pattern."""
#
#     scope: str = "payload_or_params"
#     action: str = "allow_or_deny"
#     field: str = "not_a_real_field"
#     match_regex: str = ".*"


class SectionACL(BaseModel):
    """
    Access control for sections matching a regex pattern.

    Attributes:
        section_regex: Regex pattern for matching section names.
        permissions: List of granted permissions (e.g., ["read", "write"]).
    """

    section_regex: str
    permissions: list[str]
    # TODO: add support for filters later
    # filters: list[FilterACL] = []


class IncomingAuthClient(BaseModel):
    """
    Incoming OAuth client configuration.

    Attributes:
        contact: Contact information for the client.
        memo: Additional notes about the client.
        provider: Associated ID provider name.
        claims: Dictionary of claims required for this client.
        acls: List of section access control rules.
    """

    contact: str = ""
    memo: str = ""
    provider: str
    claims: dict[str, str]
    acls: list[SectionACL]


class IncomingAuthApiKey(BaseModel):
    """
    Incoming API key configuration.

    Attributes:
        contact: Contact information for the API key holder.
        memo: Additional notes about the API key.
        algo: Hashing algorithm used.
        hash: Hashed API key value.
        acls: List of section access control rules.
    """

    contact: str = ""
    memo: str = ""
    algo: str = "argon2"
    hash: str = ""
    acls: list[SectionACL]


class IncomingAuthSettings(BaseModel):
    """
    Incoming authentication settings.

    Attributes:
        clients: Dictionary of OAuth client configurations.
        api_keys: Dictionary of API key configurations.
    """

    clients: dict[str, IncomingAuthClient] = {}
    api_keys: dict[str, IncomingAuthApiKey] = {}


class OutgoingAuthClient(BaseModel):
    """
    Outgoing OAuth client configuration.

    Attributes:
        contact: Contact information for the client.
        memo: Additional notes about the client.
        provider: Associated ID provider name.
        grant_type: OAuth 2.0 grant type used (e.g. client_credentials, auth_code).
        cache_ttl: Number of seconds to cache access tokens for this client.
        client_id: The client ID for the OAuth client.
        client_secret: The client secret for the OAuth client.
        token_endpoint_auth_method: Use "basic" or "post" to send credentials.
    """

    contact: str = ""
    memo: str = ""
    provider: str
    grant_type: str = "client_credentials"
    cache_ttl: int = 1800
    client_id: str
    client_secret: str
    token_endpoint_auth_method: Literal[
        "client_secret_basic",
        "client_secret_post",
    ] = "client_secret_basic"


class OutgoingAuthHeaders(BaseModel):
    """
    Outgoing header configuration.

    Attributes:
        contact: Contact information for the client.
        memo: Additional notes about the client.
        headers: A dictionary of authentication-related header names and header values.
    """

    contact: str = ""
    memo: str = ""
    headers: dict[str, str]


class OutgoingAuthSettings(BaseModel):
    """
    Outgoing authentication settings.

    Attributes:
        clients: Dictionary of OAuth client configurations.
        headers: Dictionary of security header configurations.
    """

    clients: dict[str, OutgoingAuthClient] = {}
    headers: dict[str, OutgoingAuthHeaders] = {}


class AuthSettings(BaseModel):
    """
    Authentication and authorization configuration.

    Attributes:
        swagger_token_url: URL for Swagger/OpenAPI token authentication.
        id_providers: Dictionary of configured ID providers.
        incoming: Settings related to incoming authentication clients, keys, etc.
        outgoing: Settings related to outgoing authentication to other services.
    """

    swagger_token_url: str
    id_providers: dict[str, IDProvider]
    incoming: IncomingAuthSettings = IncomingAuthSettings()
    outgoing: OutgoingAuthSettings = OutgoingAuthSettings()


class DiscoveredService(BaseModel):
    """
    Configuration for a single discovered external service.

    Attributes:
        base_url: The base URL or endpoint for the service.
        headers: A dictionary of static (non-security) headers to send with each
            request.
        auth_method: The authentication method to use for this service.
        auth_principal: The name of the outgoing authentication principal to use.
            This is derived by th auth_method field; for example, specifying
            client_credentials in auth_method will mean that the auth_principal
            is a key in auth.outgoing.clients.
        scope: Scope that should be included when requesting an access token.
        timeout: Timeout for reads/writes to this service, in seconds.
        connect_timeout: Timeout for opening connections to this service, in seconds.
        retries: Number of retries for failed requests to this service.
    """

    base_url: str
    headers: dict[str, str] = {}
    auth_method: Literal["client_credentials", "headers"]
    auth_principal: str
    scope: Optional[str] = None
    timeout: float = 10.0
    connect_timeout: float = 5.0
    retries: int = 3


class ServiceDiscoverySettings(BaseModel):
    """
    Configuration for service discovery within the application.

    Attributes:
        mode: The mode of service discovery (e.g., "manual").
        services: A dictionary where keys are names of services and the values
            are service configurations.
    """

    mode: Literal["manual"] = "manual"
    services: dict[str, DiscoveredService] = {}


class LoggingSettings(BaseModel):
    """
    Logging configuration.

    Attributes:
        level: Logging level.
        format: Log message format string.
        loggers: Dictionary of logger-specific configurations.
        client_host_headers: List of headers to use for identifying the client host.
    """

    level: str = "INFO"
    format: str = (
        "[ts=%(asctime)s] [pid=%(process)d] [tid=%(thread)d] [rid=%(request_id)s] "
        "[level=%(levelname)s] [name=%(name)s] [file=%(filename)s:%(lineno)d] "
        "[message=%(message)s]"
    )
    loggers: dict = {}
    client_host_headers: list[str] = ["X-Real-IP", "X-Forwarded-For"]


class TaskSettings(BaseModel):
    """
    Define parameters for async tasks.

    Attributes:
        name: Name of queue / metadata in async engine.
        backend: Type of backend to schedule and report tasks.
        url: URL string for backend (if applicable).
        sqlite_filename: Path to sqlite file (ignored unless backend="sqlite").
    """

    name: str
    backend: str = "sqlite"
    url: str = "redis://:FIXME_password@FIXME_host:6379/"
    sqlite_filename: str = "./huey.sqlite"


class CacheSettings(BaseModel):
    """
    Define parameters for data caching.

    Attributes:
        name: Name of queue / metadata in async engine.
        backend: Type of backend to store cache data.
        ttl: Number of seconds before expiring backend data (if supported)
    """

    name: str
    backend: str = "huey"  # TODO: add mongo support
    ttl: int = 3600 * 4
    # mongo_dbname = "FIXME"
