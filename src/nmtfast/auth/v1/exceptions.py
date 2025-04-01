# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Exceptions related to authentication and authorization."""


class AuthenticationError(Exception):
    """Raised when authentication fails (invalid token, expired, etc)."""

    pass


class AuthorizationError(Exception):
    """Raised when a client does not have permission for a resource."""

    pass
