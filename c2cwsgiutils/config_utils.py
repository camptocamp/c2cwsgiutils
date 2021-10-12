"""Private utilities."""
import os
from typing import Any, Callable, Mapping, Optional, cast

import pyramid.config


def get_base_path(config: pyramid.config.Configurator) -> str:
    """Get the base path of all the views."""
    return cast(str, env_or_config(config, "C2C_BASE_PATH", "c2c.base_path", "/c2c"))


def env_or_config(
    config: Optional[pyramid.config.Configurator],
    env_name: Optional[str] = None,
    config_name: Optional[str] = None,
    default: Any = None,
    type_: Callable[[str], Any] = str,
) -> Any:
    """Get the setting from the environment or from the config file."""
    return env_or_settings(
        config.get_settings() if config is not None else {}, env_name, config_name, default, type_
    )


def env_or_settings(
    settings: Optional[Mapping[str, Any]],
    env_name: Optional[str] = None,
    settings_name: Optional[str] = None,
    default: Any = None,
    type_: Callable[[str], Any] = str,
) -> Any:
    """Get the setting from the environment or from the config file."""
    if env_name is not None and env_name in os.environ and os.environ[env_name] != "":
        return type_(os.environ[env_name])
    if settings is not None and settings_name is not None and settings_name in settings:
        return type_(settings[settings_name])
    return default


def config_bool(value: Optional[str]) -> bool:
    """Get boolean from the value."""
    if value is None:
        return False
    return value.lower() in ("true", "t", "yes", "1")
