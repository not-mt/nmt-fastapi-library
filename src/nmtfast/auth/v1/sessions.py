# -*- coding: utf-8 -*-
# Copyright (c) 2026. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Server-side session management backed by AppCacheBase."""

import logging
import secrets
import time
from typing import Optional

from pydantic import BaseModel

from nmtfast.cache.v1.base import AppCacheBase
from nmtfast.settings.v1.schemas import SectionACL, SessionSettings

logger = logging.getLogger(__name__)

SESSION_KEY_PREFIX = "nmt_session_"


class SessionData(BaseModel):
    """
    Data stored in a server-side session.

    Attributes:
        user_id:  Principal identifier for the logged-in user.
        user_name: Display name for the logged-in user.
        user_claims: JWT claims extracted from the ID token.
        acls: Access control list entries for this user.
        access_token: The OAuth2 access token.
        refresh_token: The OAuth2 refresh token (if granted).
        token_expires_at: UTC timestamp when the access token expires.
        created_at: UTC timestamp when the session was created.
    """

    user_id: str
    user_name: str
    user_claims: dict[str, str]
    acls: list[SectionACL]
    access_token: str
    refresh_token: Optional[str] = None
    token_expires_at: float
    created_at: float


class SessionManager:
    """
    Manages server-side sessions using an AppCacheBase backend.

    Args:
        cache: An implementation of AppCacheBase for session storage.
        settings: Session configuration (cookie name, TTL, etc.).
    """

    def __init__(self, cache: AppCacheBase, settings: SessionSettings) -> None:
        self.cache = cache
        self.settings = settings

    def _session_key(self, session_id: str) -> str:
        """
        Build the cache key for a session.

        Args:
            session_id: The session identifier.

        Returns:
            str: The prefixed cache key.
        """
        return f"{SESSION_KEY_PREFIX}{session_id}"

    def create_session(self, data: SessionData) -> str:
        """
        Create a new session and store it in the cache.

        Args:
            data: The session data to store.

        Returns:
            str: The generated session ID.
        """
        session_id = secrets.token_urlsafe(32)
        key = self._session_key(session_id)
        serialized = data.model_dump_json()
        self.cache.store_app_cache(key, serialized, self.settings.session_ttl)
        logger.info(f"Session created for user ID '{data.user_id}'")
        return session_id

    def get_session(self, session_id: str) -> Optional[SessionData]:
        """
        Retrieve a session from the cache.

        Args:
            session_id: The session identifier.

        Returns:
            Optional[SessionData]: The session data, or None if not found or expired.
        """
        key = self._session_key(session_id)
        raw = self.cache.fetch_app_cache(key)
        if raw is None:
            return None

        try:
            return SessionData.model_validate_json(raw)
        except Exception:
            logger.warning(f"Failed to deserialize session '{session_id}'")
            return None

    def destroy_session(self, session_id: str) -> bool:
        """
        Remove a session from the cache.

        Args:
            session_id: The session identifier.

        Returns:
            bool: True if the session was removed.
        """
        key = self._session_key(session_id)
        logger.info(f"Session destroyed for session ID '{session_id}'")
        return self.cache.clear_app_cache(key)

    @staticmethod
    def is_token_expired(data: SessionData) -> bool:
        """
        Check whether the access token in a session has expired.

        Args:
            data: The session data to check.

        Returns:
            bool: True if the token is expired.
        """
        return time.time() >= data.token_expires_at
