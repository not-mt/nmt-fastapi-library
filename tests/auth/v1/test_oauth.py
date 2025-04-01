# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Unit tests for oauth utility functions and classes."""

from fastapi.security import OAuth2

from nmtfast.auth.v1.oauth import OAuth2ClientCredentials


def test_oauth2_client_credentials_init_defaults():
    """
    Test initialization with default parameters.
    """
    token_url = "https://example.com/token"
    scheme = OAuth2ClientCredentials(tokenUrl=token_url)

    assert isinstance(scheme, OAuth2)
    assert scheme.scheme_name == "OAuth2ClientCredentials"
    assert scheme.auto_error is True

    # Access through model.flows.clientCredentials (Pydantic model access)
    assert scheme.model.flows.clientCredentials is not None
    assert scheme.model.flows.clientCredentials.tokenUrl == token_url
    assert scheme.model.flows.clientCredentials.scopes == {}


def test_oauth2_client_credentials_init_custom_scheme_name():
    """
    Test initialization with custom scheme name.
    """
    token_url = "https://example.com/token"
    custom_name = "CustomSchemeName"
    scheme = OAuth2ClientCredentials(tokenUrl=token_url, scheme_name=custom_name)

    assert scheme.scheme_name == custom_name
    assert scheme.auto_error is True
    assert scheme.model.flows.clientCredentials.tokenUrl == token_url


def test_oauth2_client_credentials_init_auto_error_false():
    """
    Test initialization with auto_error set to False.
    """
    token_url = "https://example.com/token"
    scheme = OAuth2ClientCredentials(tokenUrl=token_url, auto_error=False)

    assert scheme.auto_error is False


def test_oauth2_client_credentials_flows_configuration():
    """
    Test that flows are properly configured for client credentials.
    """
    token_url = "https://example.com/token"
    scheme = OAuth2ClientCredentials(tokenUrl=token_url)

    # Access flows through the model attribute
    flows = scheme.model.flows

    assert flows.clientCredentials is not None
    assert flows.clientCredentials.tokenUrl == token_url
    assert flows.clientCredentials.scopes == {}
    assert flows.implicit is None
    assert flows.password is None
    assert flows.authorizationCode is None


def test_oauth2_client_credentials_repr():
    """
    Test string representation of the scheme.
    """
    token_url = "https://example.com/token"
    scheme = OAuth2ClientCredentials(tokenUrl=token_url)

    expected_repr = (
        "OAuth2ClientCredentials("
        f"tokenUrl='{token_url}', "
        "scheme_name='OAuth2ClientCredentials', "
        "auto_error=True)"
    )
    assert repr(scheme) == expected_repr
