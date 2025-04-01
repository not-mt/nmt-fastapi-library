# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""pydantic-settings schemas that can be re-used in nmtfast-derived apps."""

from pydantic import BaseModel


class IDProvider(BaseModel):
    """
    ID provider/platform settings.

    Attributes:
        type: Provider type (default: "jwks").
        issuer_regex: Regex pattern for validating issuer claims.
        jwks_endpoint: URL for JWKS endpoint (default: "http://localhost/jwks").
        introspection_enabled: Whether token introspection is enabled (default: False).
        introspection_endpoint: URL for token introspection endpoint.
        keyid_enabled: Whether key ID verification is enabled (default: False).
        keyid_endpoint: URL for key ID verification endpoint.
    """

    type: str = "jwks"
    issuer_regex: str = "__REAL_REGEX_GOES_HERE__"
    jwks_endpoint: str = "http://localhost/jwks"
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


class AuthClientSettings(BaseModel):
    """
    OAuth client configuration.

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


class AuthApiKeySettings(BaseModel):
    """
    API key configuration.

    Attributes:
        contact: Contact information for the API key holder.
        memo: Additional notes about the API key.
        algo: Hashing algorithm used (default: "argon2").
        hash: Hashed API key value.
        acls: List of section access control rules.
    """

    contact: str = ""
    memo: str = ""
    algo: str = "argon2"
    hash: str = ""
    acls: list[SectionACL]


class AuthSettings(BaseModel):
    """
    Authentication and authorization configuration.

    Attributes:
        swagger_token_url: URL for Swagger/OpenAPI token authentication.
        id_providers: Dictionary of configured ID providers.
        clients: Dictionary of OAuth client configurations.
        api_keys: Dictionary of API key configurations.
    """

    swagger_token_url: str
    id_providers: dict[str, IDProvider]
    clients: dict[str, AuthClientSettings] = {}
    api_keys: dict[str, AuthApiKeySettings] = {}


class LoggingSettings(BaseModel):
    """
    Logging configuration.

    Attributes:
        level: Logging level (default: "INFO").
        format: Log message format string.
        loggers: List of logger-specific configurations.
    """

    level: str = "INFO"
    format: str = (
        "[ts=%(asctime)s] [pid=%(process)d] [tid=%(thread)d] [rid=%(request_id)s] "
        "[level=%(levelname)s] [name=%(name)s] [file=%(filename)s:%(lineno)d] "
        "[message=%(message)s]"
    )
    loggers: list[dict] = []
