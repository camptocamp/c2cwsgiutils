"""
Private utilities.
"""

import os


def get_base_path(config):
    return env_or_config(config, 'C2C_BASE_PATH', 'c2c.base_path', '')


def env_or_config(config, env_name, config_name, default):
    if env_name in os.environ:
        return os.environ[env_name]
    return config.get_settings().get(config_name, default)
