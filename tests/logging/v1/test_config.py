# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Unit tests for logging functions."""

import logging
import logging.config

from nmtfast.logging.v1.config import create_logging_config
from nmtfast.logging.v1.filters import RequestIDFilter
from nmtfast.middleware.v1.request_id import request_id_var
from nmtfast.settings.v1.schemas import LoggingSettings


def test_create_logging_config():
    """
    Test creation of a logging settings dictionary.
    """
    # import sys
    # sys.exit(1)
    logging_settings = LoggingSettings()
    config = create_logging_config(logging_settings)

    assert config["version"] == 1
    assert config["disable_existing_loggers"] is False
    assert config["filters"]["request_id_filter"]["()"] == RequestIDFilter
    assert config["handlers"]["console"]["class"] == "logging.StreamHandler"
    assert config["handlers"]["console"]["formatter"] == "default"
    assert config["handlers"]["console"]["stream"] == "ext://sys.stdout"
    assert config["handlers"]["console"]["filters"] == ["request_id_filter"]
    assert config["root"]["handlers"] == ["console"]
    assert config["root"]["level"] == logging.INFO

    logging_settings.level = "DEBUG"
    config = create_logging_config(logging_settings)
    assert config["root"]["level"] == logging.DEBUG


def test_request_id_filter():
    """
    Test creating a request ID and filter.
    """
    filter_ = RequestIDFilter()
    record = logging.LogRecord("name", logging.INFO, "pathname", 1, "message", (), None)

    # test with a set request ID, and reset it
    token = request_id_var.set("test_request_id")
    result = filter_.filter(record)
    request_id_var.reset(token)

    assert result is True
    assert record.request_id == "test_request_id"

    # test with no set request ID
    result = filter_.filter(record)

    assert result is True
    assert record.request_id is None
