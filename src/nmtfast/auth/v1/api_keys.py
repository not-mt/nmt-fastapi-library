# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Library functions to process JSON Web Tokens and authenticate API keys."""

import logging

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from nmtfast.settings.v1.schemas import AuthSettings, SectionACL

from .exceptions import AuthenticationError, AuthorizationError

logger = logging.getLogger(__name__)
ph = PasswordHasher()  # Create a single PasswordHasher instance for reuse


async def verify_api_key(algo: str, api_key: str, hashed_key: str) -> bool:
    """
    Verify an API key against the stored hash.

    Args:
        algo: The hashing algorithm used.
        api_key: The API key provided by the client.
        hashed_key: The stored hash for comparison.

    Returns:
        bool: True if the API key matches the stored hash, False otherwise.

    Raises:
        AuthenticationError: If an unsupported algorithm is specified.
    """
    if algo == "argon2":
        try:
            result = ph.verify(hashed_key, api_key)
            return result
        except VerifyMismatchError:
            return False
    # elif algo == "something_else_here":
    else:
        raise AuthenticationError(f"Unknown password algorithm: {algo}")


async def authenticate_api_key(
    api_key: str, auth_settings: AuthSettings
) -> list[SectionACL]:
    """
    Authenticate an API key and retrieve associated ACLs.

    Args:
        api_key: The API key provided by the client.
        auth_settings: The authentication settings containing valid API keys.

    Returns:
        list[SectionACL]: A list of ACLs associated with the authenticated API key.

    Raises:
        AuthenticationError: If the API key is unknown.
        AuthorizationError: If the API key is valid but has no assigned ACLs.
    """
    for eval_key_conf in auth_settings.api_keys.values():
        if await verify_api_key(eval_key_conf.algo, api_key, eval_key_conf.hash):
            if eval_key_conf.acls:
                return eval_key_conf.acls
            raise AuthorizationError("Invalid API key (no permissions)")

    raise AuthenticationError("Unknown API key")
