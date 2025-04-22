# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Tests for tenacity_retry_log helper."""

import logging
from unittest.mock import MagicMock, PropertyMock

from tenacity import Future, stop_after_attempt

from nmtfast.retry.v1.tenacity import tenacity_retry_log


def test_none_outcome(mock_logger):
    """
    Test when outcome is None.
    """
    retry_state = MagicMock()
    retry_state.attempt_number = 1
    retry_state.outcome = None

    tenacity_retry_log(mock_logger)(retry_state)

    mock_logger.log.assert_called_once_with(
        logging.WARNING, "Retry 1: outcome is None."
    )


def test_with_exception(mock_logger):
    """
    Test normal exception case.
    """
    # Create a simple mock exception
    mock_exc = MagicMock(spec=Exception)
    mock_exc.__str__.return_value = "Test error"

    # Mock traceback as properties
    type(mock_exc).__traceback__ = PropertyMock(
        return_value=MagicMock(tb_frame=MagicMock(), tb_lineno=42)
    )

    outcome = MagicMock(spec=Future)
    outcome.exception.return_value = mock_exc

    retry_state = MagicMock()
    retry_state.attempt_number = 1
    retry_state.outcome = outcome
    retry_state.fn = None
    retry_state.retry_object.stop = stop_after_attempt(3)

    tenacity_retry_log(mock_logger)(retry_state)

    assert "Retry 1 of 3" in mock_logger.log.call_args[0][1]
    assert "Test error" in mock_logger.log.call_args[0][1]


def test_with_decorated_function(mock_logger):
    """
    Test decorated function case.
    """
    # Create mock exception with traceback chain
    mock_exc = MagicMock(spec=Exception)
    mock_exc.__str__.return_value = "Wrapper error"

    # Setup traceback chain using PropertyMock
    inner_tb = MagicMock(tb_frame=MagicMock(), tb_lineno=100)
    outer_tb = MagicMock(tb_next=inner_tb)
    type(mock_exc).__traceback__ = PropertyMock(return_value=outer_tb)

    outcome = MagicMock(spec=Future)
    outcome.exception.return_value = mock_exc

    retry_state = MagicMock()
    retry_state.attempt_number = 1
    retry_state.outcome = outcome
    retry_state.fn = "some_function"  # signal decorated function

    tenacity_retry_log(mock_logger)(retry_state)

    assert "line 100" in mock_logger.log.call_args[0][1]
