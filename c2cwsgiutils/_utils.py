"""
Private utilities.
"""
import os


def get_base_path(config):
    return env_or_config(config, 'C2C_BASE_PATH', 'c2c.base_path', '')


def env_or_config(config, env_name, config_name, default):
    return env_or_settings(config.get_settings(), env_name, config_name, default)


def env_or_settings(settings, env_name, settings_name, default):
    if env_name in os.environ:
        return os.environ[env_name]
    return settings.get(settings_name, default)
