# -*- coding: utf-8 -*-
# Copyright (c) 2026. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Pydantic schemas for interacting with the gadgets API."""

from typing import Optional

from pydantic import BaseModel, ConfigDict


class GadgetBase(BaseModel):
    """Base schema for gadgets."""

    name: str
    height: Optional[str] = None
    mass: Optional[str] = None
    force: Optional[int] = None


class GadgetCreate(GadgetBase):
    """Schema for creating a new gadget."""

    pass


class GadgetRead(GadgetBase):
    """Schema for reading a gadget, including additional attributes."""

    id: str
    model_config = ConfigDict(from_attributes=True)


class GadgetUpdate(BaseModel):
    """
    Schema for updating an existing gadget.

    All fields are optional to support partial updates.
    """

    name: Optional[str] = None
    height: Optional[str] = None
    mass: Optional[str] = None
    force: Optional[int] = None


class GadgetZap(BaseModel):
    """Schema to initiate zap task on a gadget."""

    duration: int = 10


class GadgetZapTask(BaseModel):
    """Schema for gadget zap task status."""

    uuid: str
    state: str = "UNKNOWN"
    id: str
    duration: int
    runtime: int
