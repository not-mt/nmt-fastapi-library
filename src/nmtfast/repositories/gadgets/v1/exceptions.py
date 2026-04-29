# -*- coding: utf-8 -*-
# Copyright (c) 2026. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""API-specific exceptions for gadget resources."""

from nmtfast.errors.v1.exceptions import BaseUpstreamRepositoryException


class GadgetApiException(BaseUpstreamRepositoryException):
    """Repository exception for the Gadgets API."""

    pass
