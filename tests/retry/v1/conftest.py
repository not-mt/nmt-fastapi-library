# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""pytest fixtures for unit / integration tests."""

import logging
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_logger():
    """
    Fixture providing a mock logger.
    """
    return MagicMock(spec=logging.Logger)
