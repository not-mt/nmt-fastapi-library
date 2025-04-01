# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Logging filter to include request IDs in log records."""

import logging

from nmtfast.middleware.v1.request_id import request_id_var


class RequestIDFilter(logging.Filter):
    """Logging filter that adds the request ID to log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Add the request ID to the log record.

        Args:
            record: The log record to be filtered.

        Returns:
            bool: True, indicating that the record should be included in the logs.
        """
        record.request_id = request_id_var.get()
        return True
