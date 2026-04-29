# -*- coding: utf-8 -*-
# Copyright (c) 2026. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""
Pydantic configuration models for the reusable web UI module.

These schemas define field layouts, resource configurations, accent color
palettes, and navigation items used by the data-driven CRUD templates and
the router factory.
"""

import math
from typing import Literal, Optional

from pydantic import BaseModel, computed_field


class FieldConfig(BaseModel):
    """
    Describes a single field on a resource for data-driven template rendering.

    Attributes:
        name: The attribute name on the Pydantic model (used for getattr).
        label: Human-readable column / label text.
        field_type: HTML input type used in the create/edit form.
        required: Whether the form field is required.
        placeholder: Placeholder text shown inside the form input.
        show_in_list: Render this field as a column in the list table.
        show_in_detail: Render this field in the detail panel.
        show_in_form: Render this field in the create / edit form.
        is_id: Marks the field as the resource identifier.
        is_name: Marks the field as the display-name (rendered bold in lists).
        monospace: Render the value in a monospace font.
        truncate: If set, truncate the displayed value to this many characters
            (with a tooltip showing the full value).
        nullable_display: The string to show when the value is None or falsy.
        sortable: Whether the column header is clickable for sorting.
    """

    name: str
    label: str
    field_type: Literal["text", "number", "display_only"] = "text"
    required: bool = False
    placeholder: str = ""
    show_in_list: bool = True
    show_in_detail: bool = True
    show_in_form: bool = True
    is_id: bool = False
    is_name: bool = False
    monospace: bool = False
    truncate: Optional[int] = None
    nullable_display: str = "\u2014"
    sortable: bool = True


class AccentPalette(BaseModel):
    """
    CSS hex colour values for accent shading.

    These are injected as CSS custom properties on the template wrapper so that
    Tailwind arbitrary-value classes (bg-[var(--accent-500)], etc.) resolve
    correctly.

    Attributes:
        shade_50: Lightest tint (backgrounds, hover states).
        shade_100: Light tint (badges, soft backgrounds).
        shade_500: Primary accent (buttons, links).
        shade_600: Darker accent (hover states on primary buttons).
    """

    shade_50: str = "#fff7ed"
    shade_100: str = "#ffedd5"
    shade_500: str = "#f97316"
    shade_600: str = "#ea580c"


class ResourceConfig(BaseModel):
    """
    Complete configuration for a CRUD-managed resource.

    Drives the list table, detail panel, create/edit form, and zap section
    in the reusable templates, as well as the router factory endpoints.

    Attributes:
        name: Singular resource name (e.g. "Widget").
        name_plural: Plural resource name (e.g. "Widgets").
        base_url: URL prefix for this resource (e.g. "/ui/v1/widgets").
        id_field: Name of the field that holds the resource identifier.
        id_type: Python type of the identifier ("str" for document databases
            like MongoDB, "int" for auto-increment SQL primary keys).
        display_name_field: Name of the field used as a human-friendly label
            (shown in delete confirmation, etc.).
        has_zap: Whether the resource supports the "zap" async-task flow.
        accent: Colour palette applied to buttons, links, and focus rings
            for this resource.
        fields: Ordered list of field configurations.
        panel_width: Default slide-out panel width in rem units.
    """

    name: str
    name_plural: str
    base_url: str
    id_field: str = "id"
    id_type: Literal["str", "int"] = "str"
    display_name_field: str = "name"
    has_zap: bool = False
    accent: AccentPalette = AccentPalette()
    fields: list[FieldConfig] = []
    panel_width: int = 28


class NavItem(BaseModel):
    """
    A single entry in the sidebar navigation.

    Attributes:
        label: The text shown next to the icon.
        url: The hx-get URL that loads the page content.
        icon_svg: Raw inline SVG markup for the navigation icon.
        match_prefix: URL prefix used to determine the "active" state.
            Defaults to url if not set.
        section: Optional section header rendered as a divider above this
            item (e.g. "Account").
    """

    label: str
    url: str
    icon_svg: str
    match_prefix: Optional[str] = None
    section: Optional[str] = None


class PaginationMeta(BaseModel):
    """
    Metadata describing the current page of a paginated result set.

    Attributes:
        total: Total number of items across all pages.
        page: The current page number (1-based).
        page_size: Maximum number of items per page.
        sort_by: The field name used for sorting, if any.
        sort_order: The sort direction (asc or desc).
        search: The search filter string, if any.
    """

    total: int = 0
    page: int = 1
    page_size: int = 10
    sort_by: Optional[str] = None
    sort_order: Literal["asc", "desc"] = "asc"
    search: Optional[str] = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_pages(self) -> int:
        """
        Compute the total number of pages.

        Returns:
            int: The total page count, minimum 1.
        """
        if self.page_size <= 0:
            return 1
        return max(1, math.ceil(self.total / self.page_size))


class SettingsSection(BaseModel):
    """
    A single entry in the settings modal sidebar navigation.

    Attributes:
        label: The text shown next to the icon.
        url: The hx-get URL that loads the section content into the
            settings content pane.
        icon_svg: Raw inline SVG markup for the section icon.
        active: Whether this section is currently selected.
    """

    label: str
    url: str
    icon_svg: str
    active: bool = False
