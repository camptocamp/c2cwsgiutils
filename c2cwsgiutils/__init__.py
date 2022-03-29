import logging
import os
import configparser
from typing import Dict, Set, Any

LOG = logging.getLogger(__name__)


def get_config_defaults() -> Dict[str, str]:
    """
    Get the environment variables as defaults for configparser.

    configparser does not support duplicated defaults with different cases, this function filter
    the second one to avoid the issue.

    configparser interpretate the % then we need to escape them
    """
    result: Dict[str, str] = {}
    lowercase_keys: Set[str] = set()
    for key, value in os.environ.items():
        if key.lower() in lowercase_keys:
            LOG.warning("The environment variable '%s' is duplicated with different case, ignoring", key)
            continue
        lowercase_keys.add(key.lower())
        result[key] = value.replace("%", "%%")
    return result


def _create_handlers(config: configparser.ConfigParser) -> Dict[str, Any]:
    handlers = [k.strip() for k in config['handlers']['keys'].split(',')]
    d_handlers: Dict[str, Any] = {}
    for hh in handlers:
        block = config[f'handler_{hh}']
        c = block['class']
        if c == 'StreamHandler':
            c = 'logging.StreamHandler'
        conf = {
            'class': c,
            'stream': block['args'].replace('(sys.stdout,)', 'ext://sys.stdout'),
        }
        if 'formatter' in block:
            conf['formatter'] = block['formatter']
        d_handlers[hh] = conf
    return d_handlers


###
# logging configuration
# https://docs.python.org/3/library/logging.config.html#logging-config-dictschema
###
def get_logconfig_dict(filename: str) -> Dict[str, Any]:
    """
    Create a logconfig dictionary based on the provided ini file.

    It is interpolated.
    """
    config = configparser.ConfigParser(defaults=get_config_defaults())
    config.read(filename)
    loggers = [k.strip() for k in config['loggers']['keys'].split(',')]
    formatters = [k.strip() for k in config['formatters']['keys'].split(',')]

    d_loggers: Dict[str, Any] = {}
    root: Dict[str, Any] = {}
    for ll in loggers:
        block = config[f'logger_{ll}']
        if ll == 'root':
            root = {
                'level': block['level'],
                'handlers': [block['handlers']]
            }
            continue
        qualname = block['qualname']
        d_loggers[qualname] = {
            "level": block['level']
        }

    d_formatters: Dict[str, Any] = {}
    for ff in formatters:
        block = config[f'formatter_{ff}']
        d_formatters[ff] = {
            'format': block.get('format', raw=True),
            "datefmt": "[%Y-%m-%d %H:%M:%S %z]",
            "class": "logging.Formatter"
        }
    return {
        "version": 1,
        "root": root,
        "loggers": d_loggers,
        "handlers": _create_handlers(config),
        "formatters": d_formatters
    }
