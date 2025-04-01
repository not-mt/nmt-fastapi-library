# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Generic logging support for nmtfast apps."""

import logging
import logging.config

from nmtfast.logging.v1.filters import RequestIDFilter
from nmtfast.settings.v1.protocols import LoggingSettingsProtocol


def create_logging_config(logging_settings: LoggingSettingsProtocol) -> dict:
    """
    Set up a logger with a predefined configuration.

    Args:
        logging_settings: The LoggingSettings object.

    Returns:
        dict: A dictionary containing the logging configuration.
    """
    log_level = getattr(logging, logging_settings.level.upper())
    log_format = logging_settings.format
    #
    # TODO: we need to decide what, if anything else, is customizable here
    #
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": log_format,
            },
        },
        "filters": {
            "request_id_filter": {
                "()": RequestIDFilter,
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default",
                "stream": "ext://sys.stdout",
                "filters": ["request_id_filter"],
            },
        },
        "root": {
            "handlers": ["console"],
            "level": log_level,
        },
    }

    return logging_config
