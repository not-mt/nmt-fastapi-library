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
    _resolve_group_acls,
    _resolve_user_acls,
    authenticate_token,
    decode_jwt_part,
    get_claims_jwks,
    get_idp_provider,
)
from nmtfast.settings.v1.schemas import (
    AuthSettings,
    IDProvider,
    IncomingAuthClient,
    IncomingAuthGroup,
    IncomingAuthSettings,
    IncomingAuthUser,
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
@patch("nmtfast.auth.v1.jwt.PyJWKClient")
async def test_get_claims_jwks_with_audience(mock_jwks_client):
    """
    Test that an audience parameter is passed through to jwt.decode.
    """
    mock_key = AsyncMock()
    mock_key.key = "test-key"
    mock_jwks_client.return_value.get_signing_key_from_jwt.return_value = mock_key

    with patch(
        "nmtfast.auth.v1.jwt.jwt.decode",
        return_value={"iss": "test-issuer", "aud": "my-aud"},
    ) as mock_decode:
        claims = await get_claims_jwks(
            "test.token", "https://example.com/jwks", audience="my-aud"
        )
        assert claims == {"iss": "test-issuer", "aud": "my-aud"}
        call_kwargs = mock_decode.call_args
        assert call_kwargs.kwargs["audience"] == "my-aud"


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
        incoming=IncomingAuthSettings(
            clients={
                "client1": IncomingAuthClient(
                    provider="test-idp",
                    claims={"sub": "test-user", "aud": "test-audience"},
                    acls=[SectionACL(section_regex=".*", permissions=["read"])],
                )
            },
            api_keys={},
        ),
    )
    mock_token = "valid.token"
    expected_auth_info = AuthSuccess(
        name="client1",
        acls=[
            SectionACL(
                section_regex=".*", permissions=["read"], principal_name="client1"
            )
        ],
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
        mock_get_claims.assert_called_once_with(
            mock_token, "https://example.com/jwks", None
        )


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
        incoming=IncomingAuthSettings(
            clients={},
            api_keys={},
        ),
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
        incoming=IncomingAuthSettings(
            clients={
                "client1": IncomingAuthClient(
                    provider="test-idp",
                    claims={"sub": "non-matching-user"},
                    acls=[SectionACL(section_regex=".*", permissions=["read"])],
                )
            },
            api_keys={},
        ),
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
        incoming=IncomingAuthSettings(
            clients={
                "client1": IncomingAuthClient(
                    provider="test-idp",
                    claims={"sub": "test-user", "aud": "required-audience"},
                    acls=[SectionACL(section_regex=".*", permissions=["read"])],
                )
            },
            api_keys={},
        ),
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
        incoming=IncomingAuthSettings(
            clients={
                "client1": IncomingAuthClient(
                    provider="test-idp",
                    claims={"sub": "non-matching-user"},
                    acls=[SectionACL(section_regex=".*", permissions=["read"])],
                ),
                "client2": IncomingAuthClient(
                    provider="test-idp",
                    claims={"sub": "correct-user"},
                    acls=[SectionACL(section_regex="specific", permissions=["write"])],
                ),
            },
            api_keys={},
        ),
    )
    mock_token = "valid.token"
    mock_acls = [
        SectionACL(
            section_regex="specific", permissions=["write"], principal_name="client2"
        )
    ]
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
        incoming=IncomingAuthSettings(
            clients={
                "client1": IncomingAuthClient(
                    provider="test-idp",
                    claims={"sub": "test-user"},
                    acls=[SectionACL(section_regex=".*", permissions=["read"])],
                )
            },
            api_keys={},
        ),
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
        incoming=IncomingAuthSettings(
            clients={
                "client1": IncomingAuthClient(
                    provider="test-idp",
                    claims={"sub": "test-user"},
                    acls=[SectionACL(section_regex=".*", permissions=["read"])],
                )
            },
            api_keys={},
        ),
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
        incoming=IncomingAuthSettings(
            clients={
                "client1": IncomingAuthClient(
                    provider="other-idp",  # doesn't match
                    claims={"sub": "test-user"},
                    acls=[SectionACL(section_regex=".*", permissions=["read"])],
                ),
                "client2": IncomingAuthClient(
                    provider="other-idp",  # doesn't match
                    claims={"sub": "test-user"},
                    acls=[SectionACL(section_regex=".*", permissions=["read"])],
                ),
            },
            api_keys={},
        ),
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


# ---------------------------------------------------------------------------
# Static user ACL resolution tests
# ---------------------------------------------------------------------------


def test_resolve_user_acls_match():
    """
    Test that _resolve_user_acls returns ACLs when a user's claims match.
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
        incoming=IncomingAuthSettings(
            users={
                "alice": IncomingAuthUser(
                    provider="test-idp",
                    claims={"sub": "alice-uuid"},
                    acls=[SectionACL(section_regex="^admin$", permissions=["*"])],
                )
            },
        ),
    )
    claims = {"sub": "alice-uuid", "iss": "https://example.com"}
    name, acls = _resolve_user_acls(claims, auth_settings, "test-idp")
    assert name == "alice"
    assert len(acls) == 1
    assert acls[0].section_regex == "^admin$"
    assert acls[0].principal_name == "alice"


def test_resolve_user_acls_no_match():
    """
    Test that _resolve_user_acls returns (None, []) when no user matches.
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
        incoming=IncomingAuthSettings(
            users={
                "alice": IncomingAuthUser(
                    provider="test-idp",
                    claims={"sub": "alice-uuid"},
                    acls=[SectionACL(section_regex="^admin$", permissions=["*"])],
                )
            },
        ),
    )
    claims = {"sub": "bob-uuid", "iss": "https://example.com"}
    name, acls = _resolve_user_acls(claims, auth_settings, "test-idp")
    assert name is None
    assert acls == []


def test_resolve_user_acls_wrong_provider():
    """
    Test that _resolve_user_acls skips users with a different provider.
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
        incoming=IncomingAuthSettings(
            users={
                "alice": IncomingAuthUser(
                    provider="other-idp",
                    claims={"sub": "alice-uuid"},
                    acls=[SectionACL(section_regex="^admin$", permissions=["*"])],
                )
            },
        ),
    )
    claims = {"sub": "alice-uuid", "iss": "https://example.com"}
    name, acls = _resolve_user_acls(claims, auth_settings, "test-idp")
    assert name is None
    assert acls == []


def test_resolve_user_acls_empty_users():
    """
    Test backward compatibility when no users are configured.
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
        incoming=IncomingAuthSettings(),
    )
    claims = {"sub": "alice-uuid"}
    name, acls = _resolve_user_acls(claims, auth_settings, "test-idp")
    assert name is None
    assert acls == []


# ---------------------------------------------------------------------------
# Static group ACL resolution tests
# ---------------------------------------------------------------------------


def test_resolve_group_acls_match():
    """
    Test that _resolve_group_acls returns ACLs when JWT groups claim matches.
    """
    auth_settings = AuthSettings(
        swagger_token_url="https://swagger.example.com/token",
        id_providers={
            "test-idp": IDProvider(
                type="jwks",
                issuer_regex=r"^https://example.com/?$",
                jwks_endpoint="https://example.com/jwks",
                groups_claim="groups",
            )
        },
        incoming=IncomingAuthSettings(
            groups={
                "netadmin": IncomingAuthGroup(
                    provider="test-idp",
                    acls=[SectionACL(section_regex="^.*$", permissions=["*"])],
                )
            },
        ),
    )
    claims = {"sub": "alice", "groups": ["netadmin", "users"]}
    acls = _resolve_group_acls(claims, auth_settings, "test-idp")
    assert len(acls) == 1
    assert acls[0].permissions == ["*"]
    assert acls[0].principal_name == "netadmin"


def test_resolve_group_acls_multiple_groups():
    """
    Test that _resolve_group_acls merges ACLs from multiple matched groups.
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
        incoming=IncomingAuthSettings(
            groups={
                "netadmin": IncomingAuthGroup(
                    provider="test-idp",
                    acls=[SectionACL(section_regex="^network$", permissions=["*"])],
                ),
                "devops": IncomingAuthGroup(
                    provider="test-idp",
                    acls=[SectionACL(section_regex="^deploy$", permissions=["read"])],
                ),
            },
        ),
    )
    claims = {"sub": "alice", "groups": ["netadmin", "devops"]}
    acls = _resolve_group_acls(claims, auth_settings, "test-idp")
    assert len(acls) == 2
    regexes = {a.section_regex for a in acls}
    assert regexes == {"^network$", "^deploy$"}
    principals = {a.principal_name for a in acls}
    assert principals == {"netadmin", "devops"}


def test_resolve_group_acls_no_groups_claim():
    """
    Test that _resolve_group_acls returns [] when JWT has no groups claim.
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
        incoming=IncomingAuthSettings(
            groups={
                "netadmin": IncomingAuthGroup(
                    provider="test-idp",
                    acls=[SectionACL(section_regex="^.*$", permissions=["*"])],
                )
            },
        ),
    )
    claims = {"sub": "alice"}
    acls = _resolve_group_acls(claims, auth_settings, "test-idp")
    assert acls == []


def test_resolve_group_acls_wrong_provider():
    """
    Test that _resolve_group_acls skips groups with a different provider.
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
        incoming=IncomingAuthSettings(
            groups={
                "netadmin": IncomingAuthGroup(
                    provider="other-idp",
                    acls=[SectionACL(section_regex="^.*$", permissions=["*"])],
                )
            },
        ),
    )
    claims = {"sub": "alice", "groups": ["netadmin"]}
    acls = _resolve_group_acls(claims, auth_settings, "test-idp")
    assert acls == []


def test_resolve_group_acls_custom_claim_name():
    """
    Test that _resolve_group_acls respects IDProvider.groups_claim.
    """
    auth_settings = AuthSettings(
        swagger_token_url="https://swagger.example.com/token",
        id_providers={
            "test-idp": IDProvider(
                type="jwks",
                issuer_regex=r"^https://example.com/?$",
                jwks_endpoint="https://example.com/jwks",
                groups_claim="roles",
            )
        },
        incoming=IncomingAuthSettings(
            groups={
                "admin_role": IncomingAuthGroup(
                    provider="test-idp",
                    acls=[SectionACL(section_regex="^admin$", permissions=["*"])],
                )
            },
        ),
    )
    # "groups" is present but the provider uses "roles"
    claims = {"sub": "alice", "groups": ["admin_role"], "roles": ["admin_role"]}
    acls = _resolve_group_acls(claims, auth_settings, "test-idp")
    assert len(acls) == 1
    assert acls[0].section_regex == "^admin$"


def test_resolve_group_acls_non_string_group_name():
    """
    Test that _resolve_group_acls skips non-string entries in the groups claim.
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
        incoming=IncomingAuthSettings(
            groups={
                "netadmin": IncomingAuthGroup(
                    provider="test-idp",
                    acls=[SectionACL(section_regex="^.*$", permissions=["*"])],
                )
            },
        ),
    )
    claims = {"sub": "alice", "groups": [123, None, "netadmin"]}
    acls = _resolve_group_acls(claims, auth_settings, "test-idp")
    assert len(acls) == 1
    assert acls[0].principal_name == "netadmin"


def test_resolve_group_acls_unknown_provider():
    """
    Test that _resolve_group_acls returns [] when provider is not in id_providers.
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
        incoming=IncomingAuthSettings(),
    )
    claims = {"sub": "alice", "groups": ["netadmin"]}
    acls = _resolve_group_acls(claims, auth_settings, "nonexistent-idp")
    assert acls == []


def test_resolve_group_acls_empty_groups_config():
    """
    Test backward compatibility when no groups are configured.
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
        incoming=IncomingAuthSettings(),
    )
    claims = {"sub": "alice", "groups": ["netadmin"]}
    acls = _resolve_group_acls(claims, auth_settings, "test-idp")
    assert acls == []


# ---------------------------------------------------------------------------
# Composite ACL tests (authenticate_token with users + groups)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_authenticate_token_composite_client_and_user():
    """
    Test that authenticate_token merges client and user ACLs, and returns the
    user name instead of the client name.
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
        incoming=IncomingAuthSettings(
            clients={
                "web_client": IncomingAuthClient(
                    provider="test-idp",
                    claims={"azp": "web-app"},
                    acls=[SectionACL(section_regex="^widgets$", permissions=["read"])],
                )
            },
            users={
                "alice": IncomingAuthUser(
                    provider="test-idp",
                    claims={"sub": "alice-uuid"},
                    acls=[SectionACL(section_regex="^admin$", permissions=["*"])],
                )
            },
        ),
    )
    mock_claims = {
        "sub": "alice-uuid",
        "azp": "web-app",
        "iss": "https://example.com",
    }

    with (
        patch("nmtfast.auth.v1.jwt.get_idp_provider", return_value="test-idp"),
        patch("nmtfast.auth.v1.jwt.get_claims_jwks", return_value=mock_claims),
    ):
        result = await authenticate_token("valid.token", auth_settings)
        assert result.name == "alice"
        assert len(result.acls) == 2
        regexes = {a.section_regex for a in result.acls}
        assert regexes == {"^widgets$", "^admin$"}
        principals = {a.principal_name for a in result.acls}
        assert principals == {"web_client", "alice"}


@pytest.mark.asyncio
async def test_authenticate_token_composite_client_and_groups():
    """
    Test that authenticate_token merges client and group ACLs when no user
    matches (client name is kept).
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
        incoming=IncomingAuthSettings(
            clients={
                "web_client": IncomingAuthClient(
                    provider="test-idp",
                    claims={"azp": "web-app"},
                    acls=[SectionACL(section_regex="^widgets$", permissions=["read"])],
                )
            },
            groups={
                "netadmin": IncomingAuthGroup(
                    provider="test-idp",
                    acls=[SectionACL(section_regex="^network$", permissions=["*"])],
                )
            },
        ),
    )
    mock_claims = {
        "azp": "web-app",
        "iss": "https://example.com",
        "groups": ["netadmin"],
    }

    with (
        patch("nmtfast.auth.v1.jwt.get_idp_provider", return_value="test-idp"),
        patch("nmtfast.auth.v1.jwt.get_claims_jwks", return_value=mock_claims),
    ):
        result = await authenticate_token("valid.token", auth_settings)
        assert result.name == "web_client"
        assert len(result.acls) == 2
        regexes = {a.section_regex for a in result.acls}
        assert regexes == {"^widgets$", "^network$"}
        principals = {a.principal_name for a in result.acls}
        assert principals == {"web_client", "netadmin"}


@pytest.mark.asyncio
async def test_authenticate_token_composite_all_sources():
    """
    Test that authenticate_token merges client + user + groups ACLs.
    User name takes precedence.
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
        incoming=IncomingAuthSettings(
            clients={
                "web_client": IncomingAuthClient(
                    provider="test-idp",
                    claims={"azp": "web-app"},
                    acls=[SectionACL(section_regex="^widgets$", permissions=["read"])],
                )
            },
            users={
                "alice": IncomingAuthUser(
                    provider="test-idp",
                    claims={"sub": "alice-uuid"},
                    acls=[SectionACL(section_regex="^admin$", permissions=["*"])],
                )
            },
            groups={
                "netadmin": IncomingAuthGroup(
                    provider="test-idp",
                    acls=[SectionACL(section_regex="^network$", permissions=["*"])],
                ),
                "devops": IncomingAuthGroup(
                    provider="test-idp",
                    acls=[SectionACL(section_regex="^deploy$", permissions=["write"])],
                ),
            },
        ),
    )
    mock_claims = {
        "sub": "alice-uuid",
        "azp": "web-app",
        "iss": "https://example.com",
        "groups": ["netadmin", "devops"],
    }

    with (
        patch("nmtfast.auth.v1.jwt.get_idp_provider", return_value="test-idp"),
        patch("nmtfast.auth.v1.jwt.get_claims_jwks", return_value=mock_claims),
    ):
        result = await authenticate_token("valid.token", auth_settings)
        assert result.name == "alice"
        assert len(result.acls) == 4
        regexes = {a.section_regex for a in result.acls}
        assert regexes == {"^widgets$", "^admin$", "^network$", "^deploy$"}
        principals = {a.principal_name for a in result.acls}
        assert principals == {"web_client", "alice", "netadmin", "devops"}


@pytest.mark.asyncio
async def test_authenticate_token_backward_compat_no_users_no_groups():
    """
    Test that authenticate_token behavior is identical to prior versions when
    no users or groups are configured.
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
        incoming=IncomingAuthSettings(
            clients={
                "client1": IncomingAuthClient(
                    provider="test-idp",
                    claims={"sub": "test-user"},
                    acls=[SectionACL(section_regex=".*", permissions=["read"])],
                )
            },
        ),
    )
    mock_claims = {"sub": "test-user", "iss": "https://example.com"}

    with (
        patch("nmtfast.auth.v1.jwt.get_idp_provider", return_value="test-idp"),
        patch("nmtfast.auth.v1.jwt.get_claims_jwks", return_value=mock_claims),
    ):
        result = await authenticate_token("valid.token", auth_settings)
        assert result.name == "client1"
        assert len(result.acls) == 1
        assert result.acls[0].section_regex == ".*"
        assert result.acls[0].principal_name == "client1"
