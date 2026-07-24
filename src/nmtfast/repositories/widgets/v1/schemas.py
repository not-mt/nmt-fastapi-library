# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Pydantic schemas for interacting with the widgets API."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


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

    id: int = Field(..., description="Database ID of the widget.")
    last_task_uuid: str | None = Field(
        None, description="UUID of the most recent zap task."
    )
    last_task_status: str | None = Field(
        None, description="Status of the most recent zap task."
    )
    model_config = ConfigDict(from_attributes=True)


class WidgetUpdate(BaseModel):
    """
    Schema for updating an existing widget.

    All fields are optional to support partial updates.
    """

    name: Optional[str] = None
    height: Optional[str] = None
    mass: Optional[str] = None
    force: Optional[int] = None


class WidgetZap(BaseModel):
    """Schema to initiate zap task on a widget."""

    duration: int = 10


class WidgetZapTask(BaseModel):
    """Base schema for widgets."""

    uuid: str
    state: str = "UNKNOWN"
    widget_id: int
    duration: int
    runtime: int
    result: dict | None = None


class WidgetZapTaskRead(BaseModel):
    """Schema for a persisted zap task history record."""

    task_uuid: str
    state: str = "UNKNOWN"
    widget_id: int
    duration: int
    runtime: int
    result: dict | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class WidgetZapTasksResponse(BaseModel):
    """Response containing a list of zap task history records."""

    tasks: list[WidgetZapTaskRead] = Field(
        ..., description="List of zap task history records."
    )
