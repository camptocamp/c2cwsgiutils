"""
Private utilities.
"""
import os
import pyramid.config
from typing import Mapping, Any, Optional, Callable


def get_base_path(config: pyramid.config.Configurator) -> str:
    return env_or_config(config, 'C2C_BASE_PATH', 'c2c.base_path', '')


def env_or_config(config: Optional[pyramid.config.Configurator], env_name: str, config_name: str,
                  default: Any=None, type_: Callable[[str], Any]=str) -> Any:
    return env_or_settings(config.get_settings() if config is not None else {},
                           env_name, config_name, default, type_)


def env_or_settings(settings: Optional[Mapping[str, Any]], env_name: str, settings_name: str,
                    default: Any=None, type_: Callable[[str], Any]=str) -> Any:
    if env_name in os.environ:
        return type_(os.environ[env_name])
    if settings is not None and settings_name in settings:
        return type_(settings[settings_name])
    return default


def config_bool(value: Optional[str]) -> bool:
    if value is None:
        return False
    return value.lower() in ('true', 't', 'yes', '1')
