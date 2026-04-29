# -*- coding: utf-8 -*-
# Copyright (c) 2026. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Tests for webui helper utilities."""

from unittest.mock import MagicMock

from fastapi import Request
from fastapi.responses import HTMLResponse, RedirectResponse

from nmtfast.htmx.v1.helpers import (
    configure_templates,
    is_htmx,
    login_redirect,
    parse_resource_form_fields,
    render_page,
)
from nmtfast.htmx.v1.schemas import FieldConfig, ResourceConfig


def _make_request(htmx: bool = False) -> MagicMock:
    """
    Create a mock FastAPI Request with optional HX-Request header.
    """
    request = MagicMock(spec=Request)
    headers = {"HX-Request": "true"} if htmx else {}
    request.headers = headers
    return request


def test_is_htmx_true():
    """
    Test is_htmx returns True for HTMX requests.
    """
    request = _make_request(htmx=True)
    assert is_htmx(request) is True


def test_is_htmx_false():
    """
    Test is_htmx returns False for non-HTMX requests.
    """
    request = _make_request(htmx=False)
    assert is_htmx(request) is False


def test_login_redirect_htmx():
    """
    Test login_redirect returns HTMLResponse with HX-Redirect for HTMX requests.
    """
    request = _make_request(htmx=True)
    response = login_redirect(request)
    assert isinstance(response, HTMLResponse)
    assert response.status_code == 200
    assert response.headers["HX-Redirect"] == "/ui/v1/login"


def test_login_redirect_non_htmx():
    """
    Test login_redirect returns RedirectResponse for non-HTMX requests.
    """
    request = _make_request(htmx=False)
    response = login_redirect(request)
    assert isinstance(response, RedirectResponse)
    assert response.status_code == 302


def test_configure_templates(tmp_path):
    """
    Test configure_templates creates Jinja2Templates with ChoiceLoader.
    """
    from jinja2 import ChainableUndefined, ChoiceLoader

    templates = configure_templates(str(tmp_path))
    assert isinstance(templates.env.loader, ChoiceLoader)
    assert templates.env.undefined is ChainableUndefined
    assert templates.env.globals["getattr"] is getattr


def test_render_page_htmx():
    """
    Test render_page renders only the partial for HTMX requests.
    """
    request = _make_request(htmx=True)
    mock_templates = MagicMock()
    mock_templates.TemplateResponse.return_value = HTMLResponse(content="partial")

    result = render_page(request, mock_templates, "v1/partial.html", {})
    mock_templates.TemplateResponse.assert_called_once_with(
        request, "v1/partial.html", context={"request": request}
    )
    assert isinstance(result, HTMLResponse)


def test_render_page_non_htmx():
    """
    Test render_page renders base template with _partial context for non-HTMX.
    """
    request = _make_request(htmx=False)
    mock_templates = MagicMock()
    mock_templates.TemplateResponse.return_value = HTMLResponse(content="full")

    result = render_page(request, mock_templates, "v1/partial.html", {})
    mock_templates.TemplateResponse.assert_called_once_with(
        request,
        "v1/base.html",
        context={"request": request, "_partial": "v1/partial.html"},
    )
    assert isinstance(result, HTMLResponse)


def _make_resource_config() -> ResourceConfig:
    """
    Create a minimal ResourceConfig for testing parse_resource_form_fields.
    """
    return ResourceConfig(
        name="Thing",
        name_plural="Things",
        base_url="/ui/v1/things",
        fields=[
            FieldConfig(
                name="id",
                label="ID",
                field_type="display_only",
                is_id=True,
                show_in_form=False,
            ),
            FieldConfig(
                name="name",
                label="Name",
                required=True,
                is_name=True,
            ),
            FieldConfig(
                name="count",
                label="Count",
                field_type="number",
            ),
        ],
    )


def test_parse_resource_form_fields_text_and_number():
    """
    Test parse_resource_form_fields extracts text and number fields.
    """
    config = _make_resource_config()
    form_data = {"name": "Widget A", "count": "42"}

    result = parse_resource_form_fields(form_data, config)

    assert result == {"name": "Widget A", "count": 42}


def test_parse_resource_form_fields_empty_values():
    """
    Test parse_resource_form_fields returns None for empty string values.
    """
    config = _make_resource_config()
    form_data = {"name": "", "count": ""}

    result = parse_resource_form_fields(form_data, config)

    assert result == {"name": None, "count": None}


def test_parse_resource_form_fields_skips_display_only():
    """
    Test parse_resource_form_fields ignores display-only fields.
    """
    config = _make_resource_config()
    form_data = {"id": "abc-123", "name": "Widget A"}

    result = parse_resource_form_fields(form_data, config)

    assert "id" not in result
    assert result == {"name": "Widget A"}


def test_parse_resource_form_fields_skips_missing():
    """
    Test parse_resource_form_fields ignores fields not in form_data.
    """
    config = _make_resource_config()
    form_data = {"name": "Widget A"}

    result = parse_resource_form_fields(form_data, config)

    assert result == {"name": "Widget A"}
    assert "count" not in result


def test_parse_resource_form_fields_empty_form():
    """
    Test parse_resource_form_fields returns empty dict for empty form.
    """
    config = _make_resource_config()

    result = parse_resource_form_fields({}, config)

    assert result == {}
