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
from nmtfast.settings.v1.schemas import AuthSettings, IncomingAuthClient

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


async def get_claims_jwks(token: str, jwks_url: str) -> dict[str, str]:
    """
    Parses and verifies a JWT using JWKS.

    Args:
        token: The JWT token string.
        jwks_url: The JWKS endpoint to retrieve public keys.

    Returns:
        dict[str, str]: Decoded JWT claims.

    Raises:
        AuthenticationError: If the token is invalid.
    """
    try:
        jwks_client = PyJWKClient(jwks_url)
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            options={"require": ["exp", "iss"]},
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


async def authenticate_token(token: str, auth_settings: AuthSettings) -> AuthSuccess:
    """
    Authenticate the client using a JWT.

    Args:
        token: The JWT to authenticate.
        auth_settings: The auth section of app configuration.

    Returns:
        AuthSuccess: An object containing the name and ACLs for a JWT.

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
        claims = await get_claims_jwks(token, idp_conf.jwks_endpoint)
    # elif idp_conf.type == "some_other_type":
    # elif idp_conf.type == "some_other_type2":

    if claims == {}:
        raise AuthenticationError("no claims found")

    for keyname, eval_client_conf in auth_clients.items():
        if eval_client_conf.provider != provider:
            continue
        for claim_name, claim_value in eval_client_conf.claims.items():
            # NOTE: claims in config must match ALL specified values; abort if
            #   a single claim does not match
            if claims[claim_name] != claim_value:
                break
        else:
            # NOTE: if the all of the claims match then the client is valid
            auth_info = {"name": keyname, "acls": eval_client_conf.acls}
            break

    if not auth_info:
        raise AuthorizationError("Invalid client (no permissions)")

    return AuthSuccess(**auth_info)
