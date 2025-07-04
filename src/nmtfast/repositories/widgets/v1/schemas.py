# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Pydantic schemas for interacting with the widgets API."""

from typing import Optional

from pydantic import BaseModel, ConfigDict


class WidgetBase(BaseModel):
    """Base schema for widgets."""

    name: str
    height: Optional[str] = None
    mass: Optional[str] = None
    force: Optional[int] = None


class WidgetCreate(WidgetBase):
    """Schema for creating a new widget."""

    pass


class WidgetRead(WidgetBase):
    """Schema for reading a widget, including additional attributes."""

    id: int
    model_config = ConfigDict(from_attributes=True)


class WidgetZap(BaseModel):
    """Schema to initiate zap task on a widget."""

    duration: int = 10


class WidgetZapTask(BaseModel):
    """Base schema for widgets."""

    uuid: str
    state: str = "UNKNOWN"
    id: int
    duration: int
    runtime: int
