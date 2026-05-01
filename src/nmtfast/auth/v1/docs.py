# -*- coding: utf-8 -*-
# Copyright (c) 2026. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""
Swagger UI customization helpers for nmtfast apps.

Provides a function to register custom /docs and /docs/oauth2-redirect
routes on a FastAPI application with CSS injected to selectively hide the
client_secret field for chosen OAuth2 flow types.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.openapi.docs import (
    get_swagger_ui_html,
    get_swagger_ui_oauth2_redirect_html,
)
from fastapi.responses import HTMLResponse


def _build_hide_client_secret_css(flow_types: list[str]) -> str:
    """
    Build CSS hiding client_secret for chosen OAuth2 flow types.

    Build a <style> block that hides the client_secret row in the
    Swagger UI authorization modal for the given OAuth2 flow types.

    Swagger UI v5 assigns id="client_secret_{flowType}" to each flow's
    input and for="client_secret_{flowType}" to its label.  The generated
    CSS uses the :has() selector to target the wrapper <div> that is
    the direct parent of the label, hiding both the label and its associated
    input (or the ****** code shown when already authorized).

    Args:
        flow_types: OAuth2 flow type identifiers whose client_secret row
            should be hidden (e.g. ["authorizationCode"]).

    Returns:
        str: A <style>...</style> string ready for injection into the HTML
            <head>, or an empty string when flow_types is empty.
    """
    if not flow_types:
        return ""

    rules = "\n".join(
        f'.auth-container *:has(> label[for="client_secret_{ft}"]) {{\n'
        f"    display: none;\n"
        f"}}"
        for ft in flow_types
    )
    return f"\n<style>\n{rules}\n</style>\n"


def _build_extra_scripts() -> str:
    """
    Build extra scripts for Swagger UI customization.

    Returns:
        str: A <script>...</script> string ready for injection into the HTML
            <head>, or an empty string if no extra scripts are needed.
    """
    return """
    <script defer>
        window.addEventListener('load', (event) => {
            const observer = new MutationObserver(() => {
                console.log("api_key_value mutation observer triggered");
                const input = document.getElementById('api_key_value');
                if (input && input.type !== 'password') {
                    input.type = 'password';
                    console.log("api_key_value type set to password");
                }
            });
            observer.observe(document.body, {
                childList: true,
                subtree: true,
            });
            console.log('api_key_value mutation observer created');
        });
        console.log("Custom SwaggerUI scripts loaded!");
    </script>
    """


def register_swagger_ui(
    app: FastAPI,
    *,
    hide_client_secret_for: list[str] | None = None,
) -> None:
    """
    Replace the default Swagger UI routes with customized versions.

    This function **must** be called on a FastAPI instance that was created
    with docs_url=None so that the built-in /docs route does not
    conflict with the custom one registered here.

    A /docs/oauth2-redirect route is also registered to handle the OAuth2
    callback that Swagger UI expects.

    Args:
        app: The FastAPI application to register the routes on.
        hide_client_secret_for: Optional list of OAuth2 flow type identifiers
            (e.g. ["authorizationCode"]) for which the client_secret
            input should be hidden in the Swagger UI authorization modal.
            Defaults to None (no fields hidden).
    """
    extra_head_css: str = _build_hide_client_secret_css(
        hide_client_secret_for or [],
    )
    extra_scripts: str = _build_extra_scripts()

    @app.get("/docs", include_in_schema=False)
    async def custom_swagger_ui_html(request: Request) -> HTMLResponse:
        """
        Serve Swagger UI with optional CSS and script overrides injected.
        """
        root = request.scope.get("root_path", "").rstrip("/")
        openapi_url = root + (app.openapi_url or "/openapi.json")
        oauth2_redirect_url = app.swagger_ui_oauth2_redirect_url
        if oauth2_redirect_url:
            oauth2_redirect_url = root + oauth2_redirect_url
        html_response = get_swagger_ui_html(
            openapi_url=openapi_url,
            title=f"{app.title} - Swagger UI",
            oauth2_redirect_url=oauth2_redirect_url,
            init_oauth=app.swagger_ui_init_oauth,
            swagger_ui_parameters=app.swagger_ui_parameters,
        )
        html_body: str = bytes(html_response.body).decode("utf-8")
        if extra_head_css:
            html_body = html_body.replace("</head>", extra_head_css + "</head>")
        html_body = html_body.replace("</body>", extra_scripts + "</body>")
        return HTMLResponse(content=html_body)

    redirect_url: str = app.swagger_ui_oauth2_redirect_url or "/docs/oauth2-redirect"

    @app.get(redirect_url, include_in_schema=False)
    async def swagger_ui_redirect() -> HTMLResponse:
        """
        Handle the OAuth2 redirect callback for the Swagger UI authorization flow.
        """
        return get_swagger_ui_oauth2_redirect_html()
