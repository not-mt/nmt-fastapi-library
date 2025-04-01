# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Helper functions to load configuration files."""

import logging
import os
from pathlib import Path
from typing import Dict, List

import yaml

logger = logging.getLogger(__name__)


def load_yaml(file_path: Path) -> Dict:
    """
    Load a YAML file and return its contents as a dictionary.

    Args:
        file_path: The path to the YAML file.

    Returns:
        Dict: The contents of the YAML file as a dictionary. Returns an empty dictionary if the file does not exist.
    """
    if file_path.exists():
        with open(file_path, "r") as file_reader:
            return yaml.safe_load(file_reader) or {}

    return {}


def deep_merge(dict1: Dict, dict2: Dict) -> Dict:
    """Recursively merges two dictionaries.

    Args:
        dict1: The base dictionary.
        dict2: The dictionary to merge into dict1.

    Returns:
        Dict: A new dictionary with dict2 merged into dict1.
    """
    merged = dict1.copy()

    for key, value in dict2.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value

    return merged


def load_config(config_files: List[str]) -> Dict:
    """
    Loads configuration from a list of YAML files in the given order.

    Args:
        config_files: List of file paths to load and merge.

    Returns:
        Dict: The merged configuration dictionary.
    """
    config: Dict = {}

    for file in config_files:
        print(f"Looking for config file: {Path(file)} ...")
        if Path(file).exists():
            print(f"Loading config file: {Path(file)}")
        config = deep_merge(config, load_yaml(Path(file)))

    return config


def get_config_files() -> List[str]:
    """
    Determines the list of configuration files to load, prioritizing APP_CONFIG_FILES.

    Returns:
        List[str]: A list of configuration file paths in the order they should be merged.
    """
    if app_config_files := os.getenv("APP_CONFIG_FILES"):
        return app_config_files.split(",")

    # NOTE: cwd might be in the src directory of the app or one directory "up", and we can
    #   try some sensible defaults in case APP_CONFIG_FILES is not defined.
    return [
        "./src/nmtfast-config-default.yaml",
        "./nmtfast-config-default.yaml",
        "./conf/nmtfast-config.yaml",
        "./nmtfast-config.yaml",
        "../nmtfast-config.yaml",
    ]
