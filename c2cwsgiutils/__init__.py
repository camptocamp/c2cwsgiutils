import ast
import configparser
import logging
import os
import sys
from configparser import SectionProxy
from typing import Any

_LOG = logging.getLogger(__name__)


def get_config_defaults() -> dict[str, str]:
    """
    Get the environment variables as defaults for configparser.

    configparser does not support duplicated defaults with different cases, this function filter
    the second one to avoid the issue.

    configparser interpret the % then we need to escape them
    """
    result: dict[str, str] = {}
    lowercase_keys: set[str] = set()
    for key, value in os.environ.items():
        if key.lower() in lowercase_keys:
            _LOG.warning("The environment variable '%s' is duplicated with different case, ignoring", key)
            continue
        lowercase_keys.add(key.lower())
        result[key] = value.replace("%", "%%")
    return result


def _create_handlers(config: configparser.ConfigParser) -> dict[str, Any]:
    handlers = [k.strip() for k in config["handlers"]["keys"].split(",")]
    d_handlers: dict[str, Any] = {}
    for hh in handlers:
        block = config[f"handler_{hh}"]
        if "args" in block:
            message = f"Can not parse args of handlers {hh}, use kwargs instead."
            raise ValueError(message)
        c = block["class"]
        if "." not in c:
            # classes like StreamHandler does not need the prefix in the ini so we add it here
            c = f"logging.{c}"
        conf = {
            "class": c,
        }
        if "level" in block:
            conf["level"] = block["level"]
        if "formatter" in block:
            conf["formatter"] = block["formatter"]
        if "filters" in block:
            conf["filters"] = block["filters"]
        if "kwargs" in block:
            kwargs = ast.literal_eval(block["kwargs"])
            conf.update(kwargs)
        d_handlers[hh] = conf
    return d_handlers


def _filter_logger(block: SectionProxy) -> dict[str, Any]:
    out: dict[str, Any] = {"level": block["level"]}
    handlers = block.get("handlers", "")
    if handlers != "":
        out["handlers"] = [k.strip() for k in block["handlers"].split(",")]
    return out


###
# logging configuration
# https://docs.python.org/3/library/logging.config.html#logging-config-dictschema
###
def get_logconfig_dict(filename: str) -> dict[str, Any]:
    """
    Create a logconfig dictionary based on the provided ini file.

    It is interpolated.
    """
    config = configparser.ConfigParser(defaults=get_config_defaults())
    config.read(filename)
    loggers = [k.strip() for k in config["loggers"]["keys"].split(",")]
    formatters = [k.strip() for k in config["formatters"]["keys"].split(",")]

    d_loggers: dict[str, Any] = {}
    root: dict[str, Any] = {}
    for ll in loggers:
        block = config[f"logger_{ll}"]
        if ll == "root":
            root = _filter_logger(block)
            continue
        qualname = block["qualname"]
        d_loggers[qualname] = _filter_logger(block)

    d_formatters: dict[str, Any] = {}
    for ff in formatters:
        block = config[f"formatter_{ff}"]
        d_formatters[ff] = {
            "format": block.get("format", raw=True),
            "datefmt": block.get("datefmt", fallback="[%Y-%m-%d %H:%M:%S %z]", raw=True),
            "class": block.get("class", fallback="logging.Formatter", raw=True),
        }
    return {
        "version": 1,
        "root": root,
        "loggers": d_loggers,
        "handlers": _create_handlers(config),
        "formatters": d_formatters,
    }


def get_paste_config() -> str:
    """
    Resolve the ini file configuration.

    The value is taken first on command argument and fallback to C2CWSGIUTILS_CONFIG.
    """
    next_one = False
    for val in sys.argv:
        if next_one:
            return val
        if val.startswith(("--paste=", "--paster=")):
            return val.split("=")[1]
        if val in ["--paste", "--paster"]:
            next_one = True

    return os.environ.get("C2CWSGIUTILS_CONFIG", "production.ini")
