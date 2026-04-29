# -*- coding: utf-8 -*-
# Copyright (c) 2026. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Tests for HTMX schemas."""

from nmtfast.htmx.v1.schemas import PaginationMeta


def test_total_pages_with_zero_page_size():
    """
    Test that total_pages returns 1 when page_size is zero.
    """
    meta = PaginationMeta(total=10, page=1, page_size=0)
    assert meta.total_pages == 1


def test_total_pages_with_negative_page_size():
    """
    Test that total_pages returns 1 when page_size is negative.
    """
    meta = PaginationMeta(total=10, page=1, page_size=-5)
    assert meta.total_pages == 1


def test_total_pages_normal():
    """
    Test that total_pages computes correctly for positive page_size.
    """
    meta = PaginationMeta(total=25, page=1, page_size=10)
    assert meta.total_pages == 3
