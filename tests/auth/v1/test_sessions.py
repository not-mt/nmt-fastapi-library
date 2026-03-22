# -*- coding: utf-8 -*-
# Copyright (c) 2026. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Unit tests for server-side session management."""

import time
from unittest.mock import MagicMock

import pytest

from nmtfast.auth.v1.sessions import SessionData, SessionManager
from nmtfast.settings.v1.schemas import SectionACL, SessionSettings


@pytest.fixture
def mock_cache():
    """
    Provide a mock AppCacheBase for testing.
    """
    cache = MagicMock()
    cache.store_app_cache.return_value = True
    cache.fetch_app_cache.return_value = None
    cache.clear_app_cache.return_value = True
    return cache


@pytest.fixture
def session_settings():
    """
    Provide default SessionSettings for testing.
    """
    return SessionSettings(session_ttl=1800)


@pytest.fixture
def session_manager(mock_cache, session_settings):
    """
    Provide a SessionManager instance for testing.
    """
    return SessionManager(mock_cache, session_settings)


@pytest.fixture
def sample_session_data():
    """
    Provide sample SessionData for testing.
    """
    return SessionData(
        user_id="user-123",
        user_name="test-user",
        user_claims={"sub": "user-123", "email": "test@example.com"},
        acls=[
            SectionACL(section_regex="^widgets$", permissions=["*"]),
        ],
        access_token="access_token_abc",
        refresh_token="refresh_token_xyz",
        token_expires_at=time.time() + 3600,
        created_at=time.time(),
    )


def test_create_session_returns_id(session_manager, sample_session_data):
    """
    Test that create_session returns a non-empty session ID string.
    """
    session_id = session_manager.create_session(sample_session_data)
    assert isinstance(session_id, str)
    assert len(session_id) > 20


def test_create_session_stores_in_cache(
    session_manager, mock_cache, sample_session_data
):
    """
    Test that create_session calls store_app_cache with correct arguments.
    """
    session_manager.create_session(sample_session_data)
    mock_cache.store_app_cache.assert_called_once()
    call_args = mock_cache.store_app_cache.call_args
    key = call_args.args[0]
    assert key.startswith("nmt_session_")
    assert call_args.args[2] == 1800  # session_ttl


def test_create_session_unique_ids(session_manager, sample_session_data):
    """
    Test that successive sessions get unique IDs.
    """
    id_a = session_manager.create_session(sample_session_data)
    id_b = session_manager.create_session(sample_session_data)
    assert id_a != id_b


def test_get_session_returns_data(session_manager, mock_cache, sample_session_data):
    """
    Test that get_session deserializes cached data correctly.
    """
    serialized = sample_session_data.model_dump_json()
    mock_cache.fetch_app_cache.return_value = serialized

    result = session_manager.get_session("some-session-id")
    assert result is not None
    assert result.user_name == "test-user"
    assert result.access_token == "access_token_abc"
    assert len(result.acls) == 1
    assert result.acls[0].section_regex == "^widgets$"


def test_get_session_returns_none_for_missing(session_manager, mock_cache):
    """
    Test that get_session returns None when session is not in cache.
    """
    mock_cache.fetch_app_cache.return_value = None
    result = session_manager.get_session("nonexistent")
    assert result is None


def test_get_session_returns_none_for_corrupt_data(session_manager, mock_cache):
    """
    Test that get_session returns None when cached data is invalid.
    """
    mock_cache.fetch_app_cache.return_value = "not-valid-json{{"
    result = session_manager.get_session("corrupt-id")
    assert result is None


def test_destroy_session(session_manager, mock_cache):
    """
    Test that destroy_session calls clear_app_cache.
    """
    result = session_manager.destroy_session("sess-id-123")
    assert result is True
    mock_cache.clear_app_cache.assert_called_once_with("nmt_session_sess-id-123")


def test_is_token_expired_false(sample_session_data):
    """
    Test that a token with future expiry is not expired.
    """
    assert SessionManager.is_token_expired(sample_session_data) is False


def test_is_token_expired_true(sample_session_data):
    """
    Test that a token with past expiry is expired.
    """
    sample_session_data.token_expires_at = time.time() - 60
    assert SessionManager.is_token_expired(sample_session_data) is True


def test_session_data_serialization_roundtrip(sample_session_data):
    """
    Test that SessionData survives JSON serialization/deserialization.
    """
    json_str = sample_session_data.model_dump_json()
    restored = SessionData.model_validate_json(json_str)
    assert restored.user_name == sample_session_data.user_name
    assert restored.access_token == sample_session_data.access_token
    assert restored.refresh_token == sample_session_data.refresh_token
    assert len(restored.acls) == len(sample_session_data.acls)


def test_session_data_without_refresh_token():
    """
    Test SessionData works when refresh_token is not provided.
    """
    data = SessionData(
        user_id="u1",
        user_name="no-refresh-user",
        user_claims={"sub": "u1"},
        acls=[],
        access_token="at_only",
        token_expires_at=time.time() + 3600,
        created_at=time.time(),
    )
    assert data.refresh_token is None
    json_str = data.model_dump_json()
    restored = SessionData.model_validate_json(json_str)
    assert restored.refresh_token is None
