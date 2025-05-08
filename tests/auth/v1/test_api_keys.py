# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Unit tests for API keys functions."""

import pytest
from argon2 import PasswordHasher

from nmtfast.auth.v1.acl import AuthSuccess
from nmtfast.auth.v1.api_keys import authenticate_api_key, verify_api_key
from nmtfast.auth.v1.exceptions import AuthenticationError, AuthorizationError
from nmtfast.settings.v1.schemas import AuthApiKeySettings, AuthSettings, SectionACL

ph = PasswordHasher()


@pytest.mark.asyncio
async def test_verify_api_key_correct():
    """
    Tests verify_api_key with a correct API key.

    Verifies that the function returns True when the provided API key matches the stored hash.
    """
    api_key = "test_api_key"
    hashed_key = ph.hash(api_key)
    result = await verify_api_key(algo="argon2", api_key=api_key, hashed_key=hashed_key)

    assert result is True


@pytest.mark.asyncio
async def test_verify_api_key_incorrect():
    """
    Tests verify_api_key with an incorrect API key.

    Verifies that the function returns False when the provided API key does not match the stored hash.
    """
    api_key = "test_api_key"
    hashed_key = ph.hash("wrong_api_key")
    result = await verify_api_key(algo="argon2", api_key=api_key, hashed_key=hashed_key)

    assert result is False


@pytest.mark.asyncio
async def test_verify_api_key_unsupported_algo():
    """
    Tests verify_api_key with an unsupported algorithm.

    Verifies that the function raises an AuthenticationError when an unsupported algorithm is provided.
    """
    with pytest.raises(AuthenticationError):
        await verify_api_key(algo="unsupported", api_key="test", hashed_key="hash")


@pytest.mark.asyncio
async def test_authenticate_api_key_valid_with_acls():
    """
    Tests authenticate_api_key with a valid API key and ACLs.

    Verifies that the function returns the correct list of ACLs when a valid API key is provided.
    """
    api_key = "test_api_key"
    hashed_key = ph.hash(api_key)
    mock_acls = [SectionACL(section_regex=".*", permissions=["read"])]
    mock_auth_info = AuthSuccess(name=api_key, acls=mock_acls)

    auth_settings = AuthSettings(
        swagger_token_url="test",
        id_providers={},
        api_keys={
            api_key: AuthApiKeySettings(
                algo="argon2",
                hash=hashed_key,
                acls=mock_acls,
            )
        },
    )
    result = await authenticate_api_key(api_key=api_key, auth_settings=auth_settings)

    assert result == mock_auth_info


@pytest.mark.asyncio
async def test_authenticate_api_key_valid_no_acls():
    """
    Tests authenticate_api_key with a valid API key but no ACLs.

    Verifies that the function raises an AuthorizationError when a valid API key has no associated ACLs.
    """
    api_key = "test_api_key"
    hashed_key = ph.hash(api_key)
    auth_settings = AuthSettings(
        swagger_token_url="test",
        id_providers={},
        api_keys={
            "test_key": AuthApiKeySettings(algo="argon2", hash=hashed_key, acls=[])
        },
    )
    with pytest.raises(AuthorizationError):
        await authenticate_api_key(api_key=api_key, auth_settings=auth_settings)


@pytest.mark.asyncio
async def test_authenticate_api_key_invalid():
    """
    Tests authenticate_api_key with an invalid API key.

    Verifies that the function raises an AuthenticationError when an invalid API key is provided.
    """
    auth_settings = AuthSettings(swagger_token_url="test", id_providers={}, api_keys={})

    with pytest.raises(AuthenticationError):
        await authenticate_api_key(
            api_key="invalid_api_key", auth_settings=auth_settings
        )


@pytest.mark.asyncio
async def test_authenticate_api_key_incorrect_api_key():
    """
    Tests authenticate_api_key with an incorrect api key.

    Verifies that the function raises an AuthenticationError.
    """
    api_key = "test_api_key"
    incorrect_api_key = "incorrect_api_key"
    hashed_key = ph.hash(api_key)

    auth_settings = AuthSettings(
        swagger_token_url="test",
        id_providers={},
        api_keys={
            "test_key": AuthApiKeySettings(algo="argon2", hash=hashed_key, acls=[])
        },
    )
    with pytest.raises(AuthenticationError):
        await authenticate_api_key(
            api_key=incorrect_api_key, auth_settings=auth_settings
        )
