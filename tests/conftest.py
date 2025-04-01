# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""pytest fixtures for the entire nmtfast-library project."""

import importlib
import importlib.util
import logging
import pathlib

import pytest

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


@pytest.fixture(scope="session", autouse=True)
def discover_all_nmtfast_modules() -> None:
    """
    Fixture that discovers all implicit namespace packages in nmtfast.

    It is necessary to load all packages in order to detect missing code coverage.
    """
    package = "nmtfast"
    spec = importlib.util.find_spec(package)

    if spec is None or not spec.submodule_search_locations:
        raise ImportError(f"Could not find package: {package}")

    package_path = pathlib.Path(next(iter(spec.submodule_search_locations)))

    def discover_modules(path: pathlib.Path, parent: str):
        """
        Recursive inner function to discover all nmtfast modules.
        """
        for entry in path.rglob("*.py"):  # Recursively find all .py files

            if entry.stem == "__init__":
                # NOTE: skip __init__.py files, but we are using implicit
                #   namespace packages so they should not be found
                continue

            # convert file path to module import path
            relative_path = entry.relative_to(path)
            module_name = (
                f"{parent}.{relative_path.with_suffix('').as_posix().replace('/', '.')}"
            )
            try:
                importlib.import_module(module_name)
                logger.info(f"Loaded module: {module_name}")
            except ImportError as exc:
                logger.error(f"Failed to load module: {module_name}, Error: {exc}")

    discover_modules(package_path, package)
    logger.info("Finished loading nmtfast modules.")
