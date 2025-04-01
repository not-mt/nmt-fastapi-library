# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""OAuth classes and utility functions for nmtfast apps."""

from typing import Optional

from fastapi.security import OAuth2


class OAuth2ClientCredentials(OAuth2):
    """
    Custom OAuth2 scheme to enforce client credentials flow.

    Args:
        tokenUrl: The URL for obtaining OAuth2 tokens.
        scheme_name: Optional name for the security scheme. Defaults to
            "OAuth2ClientCredentials".
        auto_error: Whether to automatically raise errors for missing credentials.
            Defaults to True.
    """

    def __init__(
        self,
        tokenUrl: str,
        scheme_name: Optional[str] = None,
        auto_error: bool = True,
    ) -> None:
        super().__init__(
            flows={
                "clientCredentials": {
                    "tokenUrl": tokenUrl,
                    "scopes": {},
                }
            },
            scheme_name=scheme_name or "OAuth2ClientCredentials",
        )
        self.auto_error = auto_error
        self._tokenUrl = tokenUrl
        self._scheme_name = scheme_name or "OAuth2ClientCredentials"

    def __repr__(self) -> str:
        """
        Return unambiguous string representation of OAuth2 client credentials.

        The representation includes the token URL, scheme name, and auto_error setting
        in a format that could be used to recreate the object.

        Returns:
            str: String showing configuration in format:
                OAuth2ClientCredentials(tokenUrl='...', scheme_name='...',
                auto_error=...)
        """
        return (
            f"OAuth2ClientCredentials("
            f"tokenUrl='{self._tokenUrl}', "
            f"scheme_name='{self._scheme_name}', "
            f"auto_error={self.auto_error})"
        )
