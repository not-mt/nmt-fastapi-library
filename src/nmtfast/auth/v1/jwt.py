# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Library functions to process JSON Web Tokens."""

import base64
import binascii
import json
import logging
import re

import jwt
from fastapi import HTTPException
from jwt import DecodeError, PyJWKClient

from nmtfast.auth.v1.acl import AuthSuccess
from nmtfast.settings.v1.schemas import (
    AuthSettings,
    IncomingAuthClient,
    SectionACL,
)

from .exceptions import AuthenticationError, AuthorizationError

logger = logging.getLogger(__name__)


def decode_jwt_part(token: str, part_name: str) -> dict:
    """
    Decodes a base64url-encoded JWT part (header or payload).

    Args:
        token: base64url-encoded token (str).
        part_name: The name of the part ("header" or "payload").

    Returns:
        dict: The decoded JSON object (dict).

    Raises:
        ValueError: If base64 decoding or JSON parsing fails.
    """
    encoded_parts = token.split(".")
    if part_name == "header":
        encoded_part = encoded_parts[0]
    elif part_name == "payload":
        encoded_part = encoded_parts[1]
    else:
        raise ValueError(f"Unknown index for part_name '{part_name}'")

    try:
        padding = len(encoded_part) % 4
        if padding > 0:
            encoded_part += "=" * (4 - padding)
        decoded_bytes = base64.urlsafe_b64decode(encoded_part)
        decoded_json = decoded_bytes.decode("utf-8")
        decoded_object = json.loads(decoded_json)
        # logger.debug(f"{part_name}: {decoded_object}")
        return decoded_object
    except (
        ValueError,
        IndexError,
        binascii.Error,
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as e:
        # logger.error(f"{part_name.capitalize()} decoding error: {e}")
        raise ValueError(f"{part_name.capitalize()} decoding error: {e}")


async def get_claims_jwks(
    token: str,
    jwks_url: str,
    audience: str | None = None,
) -> dict[str, str]:
    """
    Parses and verifies a JWT using JWKS.

    Args:
        token: The JWT token string.
        jwks_url: The JWKS endpoint to retrieve public keys.
        audience: Optional expected audience claim. When provided, the aud claim
            is validated against this value.

    Returns:
        dict[str, str]: Decoded JWT claims.

    Raises:
        AuthenticationError: If the token is invalid.
    """
    try:
        jwks_client = PyJWKClient(jwks_url)
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        decode_options: dict = {"require": ["exp", "iss"]}
        decode_kwargs: dict = {
            "algorithms": ["RS256"],
            "options": decode_options,
            "leeway": 15,
        }
        if audience:
            decode_kwargs["audience"] = audience
        claims = jwt.decode(
            token,
            signing_key.key,
            **decode_kwargs,
        )
        return claims
    except (DecodeError, jwt.ExpiredSignatureError, jwt.InvalidTokenError) as exc:
        raise AuthenticationError(f"{exc}")


async def get_idp_provider(token: str, auth_settings: AuthSettings) -> str:
    """
    Authenticate the client using either API key or OAuth2 token.

    Args:
        token: The JWT to authenticate.
        auth_settings: The auth section of app configuration.

    Returns:
        str: The provider name which matches the issuer claim.

    Raises:
        AuthenticationError: If JWT issuer does not match any provider.
        HTTPException: If the token does not have 3 parts.
    """
    if token.startswith("Bearer "):
        token = token[7:]  # Remove "Bearer " (7 characters)

    if len(token.split(".")) != 3:
        raise HTTPException(status_code=403, detail="Invalid token")

    jwt_payload: dict = decode_jwt_part(token, "payload")
    provider: str = ""

    for idp, idp_conf in auth_settings.id_providers.items():
        if not re.search(idp_conf.issuer_regex, jwt_payload["iss"]):
            continue
        provider = idp

    if provider == "":
        raise AuthenticationError("unknown provider")

    return provider


def _resolve_user_acls(
    claims: dict,
    auth_settings: AuthSettings,
    provider: str,
) -> tuple[str | None, list[SectionACL]]:
    """
    Resolve ACLs from static user configurations by matching JWT claims.

    Iterates through configured users and returns the first match where the
    provider matches and all configured claims are present in the JWT.

    Args:
        claims: Decoded JWT claims.
        auth_settings: The auth section of app configuration.
        provider: The matched identity provider name.

    Returns:
        tuple[str | None, list[SectionACL]]: A tuple of (user_name, user_acls).
            Returns (None, []) if no user matches.
    """
    for user_name, user_conf in auth_settings.incoming.users.items():
        if user_conf.provider != provider:
            continue
        for claim_name, claim_value in user_conf.claims.items():
            if claims.get(claim_name) != claim_value:
                break
        else:
            logger.debug(f"Matched static user '{user_name}'")
            return user_name, [
                acl.model_copy(update={"principal_name": user_name})
                for acl in user_conf.acls
            ]

    return None, []


def _resolve_group_acls(
    claims: dict,
    auth_settings: AuthSettings,
    provider: str,
) -> list[SectionACL]:
    """
    Resolve ACLs from static group configurations by matching JWT group claims.

    Reads the groups claim from the JWT (claim name is configured via
    IDProvider.groups_claim) and matches each group name against the configured
    groups for the same provider.

    Args:
        claims: Decoded JWT claims.
        auth_settings: The auth section of app configuration.
        provider: The matched identity provider name.

    Returns:
        list[SectionACL]: Merged ACLs from all matching groups, or [] if none match.
    """
    idp_conf = auth_settings.id_providers.get(provider)
    if idp_conf is None:
        return []

    groups_claim = idp_conf.groups_claim
    token_groups = claims.get(groups_claim)
    if not isinstance(token_groups, list):
        return []

    group_acls: list[SectionACL] = []
    for group_name in token_groups:
        if not isinstance(group_name, str):
            continue
        group_conf = auth_settings.incoming.groups.get(group_name)
        if group_conf is None or group_conf.provider != provider:
            continue
        logger.debug(f"Matched static group '{group_name}'")
        group_acls.extend(
            acl.model_copy(update={"principal_name": group_name})
            for acl in group_conf.acls
        )

    return group_acls


async def authenticate_token(
    token: str,
    auth_settings: AuthSettings,
    audience: str | None = None,
) -> AuthSuccess:
    """
    Authenticate the client using a JWT.

    After matching a client, this function also resolves any configured static
    user and group ACLs matching the JWT claims and merges them into a composite
    ACL list (client + user + groups).

    Args:
        token: The JWT to authenticate.
        auth_settings: The auth section of app configuration.
        audience: Optional expected audience claim for token validation.

    Returns:
        AuthSuccess: An object containing the name and composite ACLs for a JWT.

    Raises:
        AuthenticationError: If JWT is invalid (expired, inauthentic, etc).
        AuthorizationError: If client associated with JWT has no ACLs.
    """
    provider: str = await get_idp_provider(token, auth_settings)
    claims: dict = {}
    auth_info: dict = {}
    auth_clients: dict[str, IncomingAuthClient] = auth_settings.incoming.clients

    idp_conf = auth_settings.id_providers[provider]
    if idp_conf.type == "jwks":
        claims = await get_claims_jwks(token, idp_conf.jwks_endpoint, audience)
    # elif idp_conf.type == "some_other_type":
    # elif idp_conf.type == "some_other_type2":

    if claims == {}:
        raise AuthenticationError("no claims found")

    for keyname, eval_client_conf in auth_clients.items():
        if eval_client_conf.provider != provider:
            continue
        for claim_name, claim_value in eval_client_conf.claims.items():
            # NOTE: claims in config must match ALL specified values; abort if
            #   a single claim does not match or is missing from the token
            if claims.get(claim_name) != claim_value:
                break
        else:
            # NOTE: if the all of the claims match then the client is valid
            auth_info = {
                "name": keyname,
                "acls": [
                    # NOTE: stamp each ACL with the principal_name for logging
                    acl.model_copy(update={"principal_name": keyname})
                    for acl in eval_client_conf.acls
                ],
            }
            break

    if not auth_info:
        raise AuthorizationError("Invalid client (no permissions)")

    # resolve composite ACLs from static users and groups
    user_name, user_acls = _resolve_user_acls(claims, auth_settings, provider)
    group_acls = _resolve_group_acls(claims, auth_settings, provider)

    composite_acls: list[SectionACL] = auth_info["acls"] + user_acls + group_acls
    resolved_name: str = user_name if user_name else auth_info["name"]

    return AuthSuccess(name=resolved_name, acls=composite_acls)
