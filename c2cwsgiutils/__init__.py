import configparser
import logging
import os
import re
import sys
from configparser import SectionProxy
from typing import Any, Dict, Set

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
    handlers = [k.strip() for k in config["handlers"]["keys"].split(",")]
    d_handlers: Dict[str, Any] = {}
    stream_re = re.compile(r"\((.*?),\)")
    for hh in handlers:
        block = config[f"handler_{hh}"]
        stream_match = stream_re.match(block["args"])
        if stream_match is None:
            raise Exception(f"Could not parse args of handler {hh}")
        args = stream_match.groups()[0]
        c = block["class"]
        if "." not in c:
            # classes like StreamHandler does not need the prefix in the ini so we add it here
            c = f"logging.{c}"
        conf = {
            "class": c,
            "stream": f"ext://{args}",  # like ext://sys.stdout
        }
        if "formatter" in block:
            conf["formatter"] = block["formatter"]
        d_handlers[hh] = conf
    return d_handlers


def _filter_logger(block: SectionProxy) -> Dict[str, Any]:
    out: Dict[str, Any] = {"level": block["level"]}
    handlers = block.get("handlers", "")
    if handlers != "":
        out["handlers"] = [block["handlers"]]
    return out


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
    loggers = [k.strip() for k in config["loggers"]["keys"].split(",")]
    formatters = [k.strip() for k in config["formatters"]["keys"].split(",")]

    d_loggers: Dict[str, Any] = {}
    root: Dict[str, Any] = {}
    for ll in loggers:
        block = config[f"logger_{ll}"]
        if ll == "root":
            root = _filter_logger(block)
            continue
        qualname = block["qualname"]
        d_loggers[qualname] = _filter_logger(block)

    d_formatters: Dict[str, Any] = {}
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
        if val.startswith("--paste=") or val.startswith("--paster="):
            return val.split("=")[1]
        if val in ["--paste", "--paster"]:
            next_one = True

    fallback = os.environ.get("C2CWSGIUTILS_CONFIG", "production.ini")
    return fallback
