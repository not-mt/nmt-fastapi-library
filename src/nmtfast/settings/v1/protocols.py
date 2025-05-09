# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Protocols which can be used for static type hinting of pydantic-settings objects."""

from typing import Protocol


class LoggingSettingsProtocol(Protocol):
    """
    Protocol defining the interface for logging settings implementations.

    This protocol ensures type safety for objects that need to conform to the logging
    settings structure without requiring inheritance.

    Attributes:
        level: Minimum logging level (e.g., "DEBUG", "INFO", "WARNING").
        format: Format string for log messages.
        loggers: Dictionary of logger-specific configurations as dictionaries.
    """

    level: str
    format: str
    loggers: dict[str, dict]
