# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Unit tests for settings functions."""

import tempfile
from pathlib import Path

import yaml

from nmtfast.settings.v1.config_files import (
    deep_merge,
    get_config_files,
    load_config,
    load_yaml,
)


def create_temp_yaml(data: dict) -> Path:
    """
    Helper function to create a temporary YAML file.
    """
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".yaml")

    with open(temp_file.name, "w") as f:
        yaml.dump(data, f)

    return Path(temp_file.name)


def test_load_yaml():
    """
    Test that load_yaml correctly loads a YAML file into a dictionary.
    """
    test_data = {"key": "value", "nested": {"subkey": "subvalue"}}
    temp_yaml = create_temp_yaml(test_data)

    assert load_yaml(temp_yaml) == test_data
    temp_yaml.unlink()  # Clean up temp file


def test_load_yaml_nonexistent():
    """
    Test that load_yaml returns an empty dictionary for a nonexistent file.
    """
    assert load_yaml(Path("/nonexistent.yaml")) == {}


def test_deep_merge():
    """
    Test that deep_merge correctly merges nested dictionaries.
    """
    dict1 = {"a": 1, "b": {"x": 10, "y": 20}}
    dict2 = {"b": {"y": 25, "z": 30}, "c": 3}
    expected = {"a": 1, "b": {"x": 10, "y": 25, "z": 30}, "c": 3}

    assert deep_merge(dict1, dict2) == expected


def test_load_config():
    """
    Test that load_config loads and merges multiple YAML files in order.
    """
    base_config = {"setting1": "default", "nested": {"key1": "value1"}}
    env_config = {"nested": {"key1": "override", "key2": "added"}}
    service_config = {"service_specific": True}

    base_yaml = create_temp_yaml(base_config)
    env_yaml = create_temp_yaml(env_config)
    service_yaml = create_temp_yaml(service_config)

    config_files = [str(base_yaml), str(env_yaml), str(service_yaml)]
    merged_config = load_config(config_files)
    expected_config = {
        "setting1": "default",
        "nested": {"key1": "override", "key2": "added"},
        "service_specific": True,
    }

    assert merged_config == expected_config

    for temp_yaml in [base_yaml, env_yaml, service_yaml]:
        temp_yaml.unlink()  # Clean up temp files


def test_get_config_files(monkeypatch):
    """
    Test that get_config_files respects APP_CONFIG_FILES environment variable.
    """
    monkeypatch.setenv("APP_CONFIG_FILES", "/custom/path1.yaml,/custom/path2.yaml")
    assert get_config_files() == ["/custom/path1.yaml", "/custom/path2.yaml"]

    monkeypatch.delenv("APP_CONFIG_FILES", raising=False)
    assert get_config_files() == [
        "./src/nmtfast-config-default.yaml",
        "./nmtfast-config-default.yaml",
        "./conf/nmtfast-config.yaml",
        "./nmtfast-config.yaml",
        "../nmtfast-config.yaml",
    ]


def test_load_config_file_existence_handling(tmp_path, capsys):
    """
    Test that load_config properly handles both existing and non-existent files,
    specifically covering the Path(file).exists() conditional.
    """
    # create one real file
    existing_file = tmp_path / "existing.yaml"
    existing_file.write_text("key: value")

    # use one non-existent file
    non_existent_file = tmp_path / "nonexistent.yaml"

    # run with both files
    result = load_config([str(existing_file), str(non_existent_file)])

    # verify the merge still occurred with just the existing file
    assert result == {"key": "value"}

    # verify the print output shows we only loaded the existing file
    captured = capsys.readouterr()
    assert f"Looking for config file: {existing_file} ..." in captured.out
    assert f"Loading config file: {existing_file}" in captured.out
    assert f"Looking for config file: {non_existent_file} ..." in captured.out
    assert f"Loading config file: {non_existent_file}" not in captured.out
