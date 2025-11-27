import json
import os
from typing import Any

CONFIG_FILENAME = "config.json"


def get_config_path() -> str:
    """Get the absolute path to the configuration file."""
    return os.path.join(os.path.dirname(__file__), CONFIG_FILENAME)


def get_config() -> dict[str, Any]:
    """
    Load the configuration from the JSON file.
    Returns an empty dictionary if the file does not exist.
    """
    config_path = get_config_path()
    if not os.path.exists(config_path):
        return {}

    try:
        with open(config_path, encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}


def save_config(config: dict[str, Any]) -> None:
    """
    Save the configuration to the JSON file.

    Args:
        config: The configuration dictionary to save.
    """
    config_path = get_config_path()
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)
