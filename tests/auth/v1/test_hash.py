# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

import pytest

from nmtfast.auth.v1.hash import fingerprint_hash, secure_hash


@pytest.mark.parametrize(
    "value, secret_key, salt, expected_length",
    [
        # normal case
        (b"test", b"secret", b"salt", 64),
        # empty value and salt
        (b"", b"secret", b"", 64),
        # long input
        (b"long" * 1000, b"secret", b"salt", 64),
        # empty secret key
        (b"test", b"", b"salt", 64),
    ],
)
def test_secure_hash_output_format(value, secret_key, salt, expected_length):
    """
    Test that secure_hash produces correct length hexadecimal output.
    """
    result = secure_hash(value, secret_key, salt)

    assert isinstance(result, str)
    assert len(result) == expected_length
    assert all(c in "0123456789abcdef" for c in result)


def test_secure_hash_with_same_inputs_produces_same_output():
    """
    Test that secure_hash is deterministic with same inputs.
    """
    value = b"test value"
    secret = b"secret key"
    salt = b"salt value"

    result1 = secure_hash(value, secret, salt)
    result2 = secure_hash(value, secret, salt)

    assert result1 == result2


def test_secure_hash_changes_with_different_secrets():
    """
    Test that changing the secret key produces different hashes.
    """
    value = b"test value"
    salt = b"salt value"

    hash1 = secure_hash(value, b"secret1", salt)
    hash2 = secure_hash(value, b"secret2", salt)

    assert hash1 != hash2


def test_secure_hash_changes_with_different_salts():
    """
    Test that changing the salt produces different hashes.
    """
    value = b"test value"
    secret = b"secret key"

    hash1 = secure_hash(value, secret, b"salt1")
    hash2 = secure_hash(value, secret, b"salt2")

    assert hash1 != hash2


@pytest.mark.parametrize(
    "value, salt, expected_length",
    [
        # normal case
        (b"test", b"salt", 64),
        # empty value and salt
        (b"", b"", 64),
        # long input
        (b"long" * 1000, b"salt", 64),
    ],
)
def test_fingerprint_hash_output_format(value, salt, expected_length):
    """
    Test that fingerprint_hash produces correct length hexadecimal output.
    """
    result = fingerprint_hash(value, salt)

    assert isinstance(result, str)
    assert len(result) == expected_length
    assert all(c in "0123456789abcdef" for c in result)


def test_fingerprint_hash_with_same_inputs_produces_same_output():
    """
    Test that fingerprint_hash is deterministic with same inputs.
    """
    value = b"test value"
    salt = b"salt value"

    result1 = fingerprint_hash(value, salt)
    result2 = fingerprint_hash(value, salt)

    assert result1 == result2


def test_fingerprint_hash_changes_with_different_salts():
    """
    Test that changing the salt produces different hashes.
    """
    value = b"test value"

    hash1 = fingerprint_hash(value, b"salt1")
    hash2 = fingerprint_hash(value, b"salt2")

    assert hash1 != hash2


def test_secure_hash_vs_fingerprint_hash_difference():
    """
    Test that secure_hash and fingerprint_hash produce different results.
    """
    value = b"test value"
    secret = b"secret key"
    salt = b"salt value"

    secure = secure_hash(value, secret, salt)
    fingerprint = fingerprint_hash(value, salt)

    assert secure != fingerprint
