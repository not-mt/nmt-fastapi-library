# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Helper functions to hash application data with optional salting."""

import hashlib
import hmac


def secure_hash(value: bytes, secret_key: bytes, salt: bytes = b"") -> str:
    """
    Compute a secure HMAC-SHA256 hash of a value using a secret key and optional salt.

    This is suitable for sensitive operations where a secret-based fingerprint is
    needed (e.g., authentication token masking). Salting adds entropy to prevent
    hash reuse or matching in different environments.

    Args:
        value: The byte string to be hashed.
        secret_key: The secret key as bytes used to create the HMAC.
        salt: Optional salt to prepend to the value before hashing.

    Returns:
        str: A hexadecimal string representation of the HMAC-SHA256 hash.
    """
    return hmac.new(secret_key, salt + value, hashlib.sha256).hexdigest()


def fingerprint_hash(value: bytes, salt: bytes = b"") -> str:
    """
    Compute a salted SHA256 hash of a byte string.

    This is suitable for generating consistent, non-secret cache keys or identifiers
    that do not require secrecy. Salting reduces the risk of collision and helps avoid
    predictable hash outputs.

    Args:
        value: The byte string to be hashed.
        salt: Optional salt to prepend to the value before hashing.

    Returns:
        str: A hexadecimal string representation of the SHA256 hash.
    """
    return hashlib.sha256(salt + value).hexdigest()
