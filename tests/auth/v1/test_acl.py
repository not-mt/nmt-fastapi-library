# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Unit tests for auth functions."""

import pytest

from nmtfast.auth.v1.acl import check_acl
from nmtfast.settings.v1.schemas import SectionACL


@pytest.mark.asyncio
async def test_check_acl_payload_none():
    """
    Tests the check_acl function when the payload argument is None.

    Ensures that the function correctly handles the case where no payload is provided.
    """
    acls = [SectionACL(section_regex="widgets", permissions=["read"])]
    result = await check_acl(section="widgets", acls=acls, method="read", payload=None)
    assert result is True


@pytest.mark.asyncio
async def test_check_acl_section_regex_no_match():
    """
    Tests the check_acl function when the section_regex does not match the section.

    Verifies that the function returns False when the section does not match any ACL.
    """
    acls = [SectionACL(section_regex="users", permissions=["read"])]
    result = await check_acl(section="widgets", acls=acls, method="read")
    assert result is False


@pytest.mark.asyncio
async def test_check_acl_permission_star():
    """
    Tests the check_acl function when the permissions list contains "*".

    Ensures that the function grants access when the permissions list contains "*".
    """
    acls = [SectionACL(section_regex="widgets", permissions=["*"])]
    result = await check_acl(section="widgets", acls=acls, method="delete")
    assert result is True


@pytest.mark.asyncio
async def test_check_acl_permission_specific():
    """
    Tests the check_acl function when the permissions list contains specific methods.

    Verifies that the function grants access when the method is in the permissions list.
    """
    acls = [SectionACL(section_regex="widgets", permissions=["read", "write"])]
    result = await check_acl(section="widgets", acls=acls, method="write")
    assert result is True


@pytest.mark.asyncio
async def test_check_acl_permission_denied():
    """
    Tests the check_acl function when the method is not in the permissions list.

    Ensures that the function denies access when the method is not in the permissions list.
    """
    acls = [SectionACL(section_regex="widgets", permissions=["read"])]
    result = await check_acl(section="widgets", acls=acls, method="delete")
    assert result is False


# Placeholders for future filter tests


@pytest.mark.asyncio
async def test_check_acl_filter_allow():
    """
    Placeholder for future filter tests when filters are added (allow).

    This test will be implemented when filter functionality is added to check_acl.
    """
    # TODO: Implement filter tests when filters are added
    pass


@pytest.mark.asyncio
async def test_check_acl_filter_deny():
    """
    Placeholder for future filter tests when filters are added (deny).

    This test will be implemented when filter functionality is added to check_acl.
    """
    # TODO: Implement filter tests when filters are added
    pass
