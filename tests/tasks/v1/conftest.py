# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""pytest fixtures for unit / integration tests."""

from unittest.mock import MagicMock

import pytest
from huey import Huey


@pytest.fixture
def mock_huey():
    """
    Fixture providing a mock Huey instance.
    """
    huey = MagicMock(spec=Huey)
    huey.storage = MagicMock()

    return huey
