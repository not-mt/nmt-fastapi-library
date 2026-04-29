# -*- coding: utf-8 -*-
# Copyright (c) 2026. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""
Reusable helper utilities for HTMX-based web UIs.

Provides request inspection, Jinja2 template configuration with a
ChoiceLoader (app-first, library-fallback), and an HTMX-aware
page renderer.
"""

import logging
from collections.abc import Mapping
from typing import Any

from fastapi import Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from jinja2 import ChainableUndefined, ChoiceLoader, FileSystemLoader, PackageLoader

from nmtfast.htmx.v1.schemas import ResourceConfig

logger = logging.getLogger(__name__)


def is_htmx(request: Request) -> bool:
    """
    Check whether the incoming request was made by HTMX.

    Args:
        request: The incoming HTTP request.

    Returns:
        bool: True if the HX-Request header is present and equals
            "true".
    """
    return request.headers.get("HX-Request") == "true"


def login_redirect(
    request: Request,
    login_url: str = "/ui/v1/login",
) -> HTMLResponse | RedirectResponse:
    """
    Redirect to the login page.

    Works for both HTMX and standard browser requests.
    For HTMX requests a 200 response with an HX-Redirect header is
    returned so that HTMX performs a full-page navigation instead of
    swapping content into the current target element.  For normal browser
    requests a standard 302 redirect is used.

    Args:
        request: The incoming HTTP request.
        login_url: The URL of the login page.

    Returns:
        HTMLResponse | RedirectResponse: A redirect that always navigates
            the full page.
    """
    if is_htmx(request):
        response = HTMLResponse(content="", status_code=200)
        response.headers["HX-Redirect"] = login_url
        return response

    return RedirectResponse(url=login_url, status_code=302)


def configure_templates(app_template_dir: str) -> Jinja2Templates:
    """
    Create a Jinja2Templates instance backed by a ChoiceLoader.

    The loader searches the application's own template directory first,
    then falls back to the templates shipped inside the nmtfast package.
    This lets consuming applications override any library template simply
    by placing a file at the same relative path.

    A getattr global is registered so that data-driven templates can
    access model attributes dynamically (e.g.
    {{ getattr(item, field.name) }}).

    Args:
        app_template_dir: Filesystem path to the application's template
            directory (e.g. "src/app/templates").

    Returns:
        Jinja2Templates: A configured template engine ready for use with
            FastAPI route handlers.
    """
    loader = ChoiceLoader(
        [
            FileSystemLoader(app_template_dir),
            PackageLoader("nmtfast", "htmx"),
        ]
    )

    templates = Jinja2Templates(directory=app_template_dir)
    templates.env.loader = loader
    templates.env.undefined = ChainableUndefined
    templates.env.globals["getattr"] = getattr

    return templates


def render_page(
    request: Request,
    templates: Jinja2Templates,
    partial_name: str,
    context: dict[str, Any],
    base_template: str = "v1/base.html",
) -> HTMLResponse:
    """
    Render an HTMX partial or a full page depending on the request type.

    When the request originates from HTMX (HX-Request header present),
    only the partial template is rendered.  For regular browser navigations
    the partial is embedded inside the base layout via the _partial
    context variable.

    Args:
        request: The incoming HTTP request.
        templates: The configured Jinja2Templates instance.
        partial_name: Template path of the partial to render
            (e.g. "v1/partials/crud/list.html").
        context: Template context dictionary.  request is added
            automatically if not already present.
        base_template: Template path of the base layout.

    Returns:
        HTMLResponse: The rendered HTML response.
    """
    context.setdefault("request", request)

    if is_htmx(request):
        return templates.TemplateResponse(request, partial_name, context=context)

    return templates.TemplateResponse(
        request,
        base_template,
        context={**context, "_partial": partial_name},
    )


def parse_resource_form_fields(
    form_data: Mapping[str, Any],
    resource_config: ResourceConfig,
) -> dict[str, str | int | None]:
    """
    Extract and coerce form field values using a ResourceConfig.

    Iterates the resource configuration's field list and pulls matching
    values from the submitted form data, converting them according to
    each field's declared type.  Only fields with show_in_form=True
    that are present in the form data are included in the result.

    Args:
        form_data: A mapping of submitted form field names to their raw
            values (typically from request.form()).
        resource_config: The resource configuration whose fields drive
            the extraction and coercion rules.

    Returns:
        dict[str, str | int | None]: A mapping of field names to their
            coerced values, ready for use in an update schema.
    """
    update_fields: dict[str, str | int | None] = {}
    for field in resource_config.fields:
        if field.show_in_form and field.name in form_data:
            raw_value = str(form_data[field.name])
            if field.field_type == "number":
                update_fields[field.name] = int(raw_value) if raw_value else None
            else:
                update_fields[field.name] = raw_value if raw_value else None
    return update_fields
