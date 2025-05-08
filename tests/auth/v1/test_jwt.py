# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Unit tests for JWT functions."""

import base64
import json
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from jwt import DecodeError, ExpiredSignatureError, InvalidTokenError

from nmtfast.auth.v1.acl import AuthSuccess
from nmtfast.auth.v1.exceptions import AuthenticationError, AuthorizationError
from nmtfast.auth.v1.jwt import (
    authenticate_token,
    decode_jwt_part,
    get_claims_jwks,
    get_idp_provider,
)
from nmtfast.settings.v1.schemas import (
    AuthClientSettings,
    AuthSettings,
    IDProvider,
    SectionACL,
)


def encode_base64(data):
    """
    Helper function to encode data in base64 with proper padding.
    """
    encoded = base64.urlsafe_b64encode(data.encode("utf-8")).decode("utf-8")
    return encoded.rstrip("=") + "=" * (4 - len(encoded) % 4)


def test_decode_jwt_part():
    """
    Test decoding the three parts of a JWT, and various ways that it can fail.
    """
    valid_payload = json.dumps({"iss": "test-issuer"}).encode("utf-8")
    encoded_payload = (
        base64.urlsafe_b64encode(valid_payload).decode("utf-8").rstrip("=")
    )
    token = f"header.{encoded_payload}.signature"

    assert decode_jwt_part(token, "payload") == {"iss": "test-issuer"}

    with pytest.raises(ValueError, match="Unknown index for part_name 'invalid'"):
        decode_jwt_part(token, "invalid")

    with pytest.raises(ValueError, match="Payload decoding error"):
        decode_jwt_part("header.!.signature", "payload")

    with pytest.raises(ValueError, match="Payload decoding error"):
        decode_jwt_part("header..signature", "payload")

    with pytest.raises(ValueError, match="Header decoding error"):
        decode_jwt_part("invalid_header.payload.signature", "header")

    with pytest.raises(ValueError, match="Payload decoding error"):
        decode_jwt_part("header.invalid_payload.signature", "payload")


@pytest.mark.asyncio
@patch("nmtfast.auth.v1.jwt.PyJWKClient")
async def test_get_claims_jwks(mock_jwks_client):
    """
    Test using JWKS to retrieve claims for a JWT.
    """
    mock_key = AsyncMock()
    mock_key.key = "test-key"
    mock_jwks_client.return_value.get_signing_key_from_jwt.return_value = mock_key

    with patch("nmtfast.auth.v1.jwt.jwt.decode", return_value={"iss": "test-issuer"}):
        claims = await get_claims_jwks("test.token", "https://example.com/jwks")
        assert claims == {"iss": "test-issuer"}

    with patch(
        "nmtfast.auth.v1.jwt.jwt.decode", side_effect=DecodeError("Invalid token")
    ):
        with pytest.raises(AuthenticationError, match="Invalid token"):
            await get_claims_jwks("test.token", "https://example.com/jwks")

    with patch(
        "nmtfast.auth.v1.jwt.jwt.decode",
        side_effect=ExpiredSignatureError("Token expired"),
    ):
        with pytest.raises(AuthenticationError, match="Token expired"):
            await get_claims_jwks("test.token", "https://example.com/jwks")

    with patch(
        "nmtfast.auth.v1.jwt.jwt.decode", side_effect=InvalidTokenError("Invalid")
    ):
        with pytest.raises(AuthenticationError, match="Invalid"):
            await get_claims_jwks("test.token", "https://example.com/jwks")


@pytest.mark.asyncio
async def test_get_idp_provider_invalid_token():
    """
    Test that an invalid token (less than 3 parts) raises an HTTPException.
    """
    auth_settings = AuthSettings(
        swagger_token_url="https://swagger.example.com/token",
        id_providers={
            "test-idp": IDProvider(
                issuer_regex=r"^https://example.com/?$",
                type="jwks",
                jwks_endpoint="https://example.com/jwks",
            )
        },
    )
    token = "invalid.token"

    with pytest.raises(HTTPException, match="Invalid token"):
        await get_idp_provider(token, auth_settings)


@pytest.mark.asyncio
async def test_get_idp_provider_unknown_provider():
    """
    Test that an unknown provider (no matching issuer) raises an AuthenticationError.
    """
    auth_settings = AuthSettings(
        swagger_token_url="https://swagger.example.com/token",
        id_providers={
            "test-idp": IDProvider(
                issuer_regex=r"^https://example.com/?$",
                type="jwks",
                jwks_endpoint="https://example.com/jwks",
            )
        },
    )
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiAiaHR0cHM6Ly9ub25leGFtcGxlLmNvbS8ifQ.DUMMY_SIGNATURE"

    with pytest.raises(AuthenticationError, match="unknown provider"):
        await get_idp_provider(token, auth_settings)


@pytest.mark.asyncio
async def test_get_idp_provider_bearer_token():
    """
    Test matching an IDP with a valid issuer in a JWT.
    """
    auth_settings = AuthSettings(
        swagger_token_url="https://swagger.example.com/token",
        id_providers={
            "test-idp": IDProvider(
                issuer_regex=r"^https://example.com/?$",
                type="jwks",
                jwks_endpoint="https://example.com/jwks",
            )
        },
    )
    token = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiAiaHR0cHM6Ly9leGFtcGxlLmNvbSJ9.DUMMY_SIGNATURE"
    provider = await get_idp_provider(token, auth_settings)
    assert provider == "test-idp"


@pytest.mark.asyncio
async def test_authenticate_token_success():
    """
    Test successful token authentication with matching claims.
    """
    auth_settings = AuthSettings(
        swagger_token_url="https://swagger.example.com/token",
        id_providers={
            "test-idp": IDProvider(
                type="jwks",
                issuer_regex=r"^https://example.com/?$",
                jwks_endpoint="https://example.com/jwks",
            )
        },
        clients={
            "client1": AuthClientSettings(
                provider="test-idp",
                claims={"sub": "test-user", "aud": "test-audience"},
                acls=[SectionACL(section_regex=".*", permissions=["read"])],
            )
        },
        api_keys={},
    )
    mock_token = "valid.token"
    expected_auth_info = AuthSuccess(
        name="client1", acls=[SectionACL(section_regex=".*", permissions=["read"])]
    )

    mock_claims = {
        "sub": "test-user",
        "aud": "test-audience",
        "iss": "https://example.com",
    }

    with (
        patch(
            "nmtfast.auth.v1.jwt.get_idp_provider",
            return_value="test-idp",  # Return the provider name string, not the object
        ) as mock_get_provider,
        patch(
            "nmtfast.auth.v1.jwt.get_claims_jwks",
            return_value=mock_claims,
        ) as mock_get_claims,
    ):
        result = await authenticate_token(mock_token, auth_settings)
        assert result == expected_auth_info
        mock_get_provider.assert_called_once_with(mock_token, auth_settings)
        mock_get_claims.assert_called_once_with(mock_token, "https://example.com/jwks")


@pytest.mark.asyncio
async def test_authenticate_token_no_claims():
    """
    Test when no claims are found after decoding.
    """
    auth_settings = AuthSettings(
        swagger_token_url="https://swagger.example.com/token",
        id_providers={
            "test-idp": IDProvider(
                type="jwks",
                issuer_regex=r"^https://example.com/?$",
                jwks_endpoint="https://example.com/jwks",
            )
        },
        clients={},
        api_keys={},
    )
    mock_token = "valid.token"

    with (
        patch("nmtfast.auth.v1.jwt.get_idp_provider", return_value="test-idp"),
        patch("nmtfast.auth.v1.jwt.get_claims_jwks", return_value={}),  # Empty claims
    ):
        with pytest.raises(AuthenticationError, match="no claims found"):
            await authenticate_token(mock_token, auth_settings)


@pytest.mark.asyncio
async def test_authenticate_token_no_matching_client():
    """
    Test when no client matches the claims.
    """
    auth_settings = AuthSettings(
        swagger_token_url="https://swagger.example.com/token",
        id_providers={
            "test-idp": IDProvider(
                type="jwks",
                issuer_regex=r"^https://example.com/?$",
                jwks_endpoint="https://example.com/jwks",
            )
        },
        clients={
            "client1": AuthClientSettings(
                provider="test-idp",
                claims={"sub": "non-matching-user"},
                acls=[SectionACL(section_regex=".*", permissions=["read"])],
            )
        },
        api_keys={},
    )
    mock_token = "valid.token"

    with (
        patch("nmtfast.auth.v1.jwt.get_idp_provider", return_value="test-idp"),
        patch(
            "nmtfast.auth.v1.jwt.get_claims_jwks",
            return_value={"sub": "different-user", "iss": "https://example.com"},
        ),
    ):
        with pytest.raises(AuthorizationError, match="Invalid client"):
            await authenticate_token(mock_token, auth_settings)


@pytest.mark.asyncio
async def test_authenticate_token_partial_claims_match():
    """
    Test when some claims match but not all.
    """
    auth_settings = AuthSettings(
        swagger_token_url="https://swagger.example.com/token",
        id_providers={
            "test-idp": IDProvider(
                type="jwks",
                issuer_regex=r"^https://example.com/?$",
                jwks_endpoint="https://example.com/jwks",
            )
        },
        clients={
            "client1": AuthClientSettings(
                provider="test-idp",
                claims={"sub": "test-user", "aud": "required-audience"},
                acls=[SectionACL(section_regex=".*", permissions=["read"])],
            )
        },
        api_keys={},
    )
    mock_token = "valid.token"

    with (
        patch("nmtfast.auth.v1.jwt.get_idp_provider", return_value="test-idp"),
        patch(
            "nmtfast.auth.v1.jwt.get_claims_jwks",
            return_value={
                "sub": "test-user",
                "aud": "wrong-audience",
            },  # one claim matches, one doesn't
        ),
    ):
        with pytest.raises(AuthorizationError, match="Invalid client"):
            await authenticate_token(mock_token, auth_settings)


@pytest.mark.asyncio
async def test_authenticate_token_multiple_clients():
    """
    Test with multiple clients where second one matches.
    """
    auth_settings = AuthSettings(
        swagger_token_url="https://swagger.example.com/token",
        id_providers={
            "test-idp": IDProvider(
                type="jwks",
                issuer_regex=r"^https://example.com/?$",
                jwks_endpoint="https://example.com/jwks",
            )
        },
        clients={
            "client1": AuthClientSettings(
                provider="test-idp",
                claims={"sub": "non-matching-user"},
                acls=[SectionACL(section_regex=".*", permissions=["read"])],
            ),
            "client2": AuthClientSettings(
                provider="test-idp",
                claims={"sub": "correct-user"},
                acls=[SectionACL(section_regex="specific", permissions=["write"])],
            ),
        },
        api_keys={},
    )
    mock_token = "valid.token"
    mock_acls = [SectionACL(section_regex="specific", permissions=["write"])]
    mock_auth_info = AuthSuccess(name="client2", acls=mock_acls)

    with (
        patch("nmtfast.auth.v1.jwt.get_idp_provider", return_value="test-idp"),
        patch(
            "nmtfast.auth.v1.jwt.get_claims_jwks",
            return_value={"sub": "correct-user", "iss": "https://example.com"},
        ),
    ):
        result = await authenticate_token(mock_token, auth_settings)
        assert result == mock_auth_info


@pytest.mark.asyncio
async def test_authenticate_token_unsupported_provider_type():
    """
    Test when the ID provider type is not supported.
    """
    auth_settings = AuthSettings(
        swagger_token_url="https://swagger.example.com/token",
        id_providers={
            "test-idp": IDProvider(
                type="unsupported_type",  # not "jwks"
                issuer_regex=r"^https://example.com/?$",
                jwks_endpoint="https://example.com/jwks",
            )
        },
        clients={
            "client1": AuthClientSettings(
                provider="test-idp",
                claims={"sub": "test-user"},
                acls=[SectionACL(section_regex=".*", permissions=["read"])],
            )
        },
        api_keys={},
    )
    mock_token = "valid.token"

    with (
        patch("nmtfast.auth.v1.jwt.get_idp_provider", return_value="test-idp"),
        patch(
            "nmtfast.auth.v1.jwt.get_claims_jwks",
            return_value={"sub": "test-user", "iss": "https://example.com"},
        ),
    ):
        with pytest.raises(AuthenticationError, match="no claims found"):
            await authenticate_token(mock_token, auth_settings)


@pytest.mark.asyncio
async def test_authenticate_token_future_provider_type():
    """
    Test when a new provider type is added but not yet implemented.
    """
    auth_settings = AuthSettings(
        swagger_token_url="https://swagger.example.com/token",
        id_providers={
            "test-idp": IDProvider(
                type="future_type",  # not yet implemented
                issuer_regex=r"^https://example.com/?$",
                jwks_endpoint="https://example.com/jwks",
            )
        },
        clients={
            "client1": AuthClientSettings(
                provider="test-idp",
                claims={"sub": "test-user"},
                acls=[SectionACL(section_regex=".*", permissions=["read"])],
            )
        },
        api_keys={},
    )
    mock_token = "valid.token"

    with patch("nmtfast.auth.v1.jwt.get_idp_provider", return_value="test-idp"):
        with pytest.raises(AuthenticationError, match="no claims found"):
            await authenticate_token(mock_token, auth_settings)


@pytest.mark.asyncio
async def test_authenticate_token_only_wrong_provider_clients():
    """
    Test when all clients have wrong providers.
    """
    auth_settings = AuthSettings(
        swagger_token_url="https://swagger.example.com/token",
        id_providers={
            "test-idp": IDProvider(
                type="jwks",
                issuer_regex=r"^https://example.com/?$",
                jwks_endpoint="https://example.com/jwks",
            ),
            "other-idp": IDProvider(
                type="jwks",
                issuer_regex=r"^https://other.com/?$",
                jwks_endpoint="https://other.com/jwks",
            ),
        },
        clients={
            "client1": AuthClientSettings(
                provider="other-idp",  # doesn't match
                claims={"sub": "test-user"},
                acls=[SectionACL(section_regex=".*", permissions=["read"])],
            ),
            "client2": AuthClientSettings(
                provider="other-idp",  # doesn't match
                claims={"sub": "test-user"},
                acls=[SectionACL(section_regex=".*", permissions=["read"])],
            ),
        },
        api_keys={},
    )
    mock_token = "valid.token"

    with (
        patch(
            "nmtfast.auth.v1.jwt.get_idp_provider",
            return_value="test-idp",
        ),
        patch(
            "nmtfast.auth.v1.jwt.get_claims_jwks",
            return_value={"sub": "test-user", "iss": "https://example.com"},
        ),
    ):
        with pytest.raises(AuthorizationError, match="Invalid client"):
            await authenticate_token(mock_token, auth_settings)
