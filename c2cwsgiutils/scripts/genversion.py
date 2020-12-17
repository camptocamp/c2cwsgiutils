#!/usr/bin/env python3
import json
import logging
import os
import re
import subprocess
import sys
from typing import Dict, Optional, Tuple, cast

SRC_VERSION_RE = re.compile(r"^.*\(([^=]*)===?([^=]*)\)$")
VERSION_RE = re.compile(r"^([^=]*)==([^=]*)$")
LOG = logging.getLogger(__name__)


def _get_package_version(comp: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Parse plain and editable versions. See test_genversion.py for examples.
    """
    src_matcher = SRC_VERSION_RE.match(comp)
    matcher = src_matcher or VERSION_RE.match(comp)
    if matcher:
        return cast(Tuple[str, str], matcher.groups())
    else:
        if len(comp) > 0 and not comp[:3] == "-e ":
            print("Cannot parse package version: " + comp)
        return None, None


def _get_packages_version() -> Dict[str, str]:
    result = {}
    with open(os.devnull, "w") as devnull:
        for comp in (
            subprocess.check_output(["python3", "-m", "pip", "freeze"], stderr=devnull)
            .decode()
            .strip()
            .split("\n")
        ):
            name, version = _get_package_version(comp)
            if name is not None and version is not None:
                result[name] = version
    return result


def deprecated() -> None:
    LOG.warning("c2cwsgiutils_genversion.py is deprecated; use c2cwsgiutils-genversion instead")
    return main()


def main() -> None:
    if len(sys.argv) == 2:
        git_tag = None
        git_hash = sys.argv[1]
    else:
        git_tag = sys.argv[1]
        git_hash = sys.argv[2]
    report = {"main": {"git_hash": git_hash}, "packages": _get_packages_version()}
    if git_tag is not None:
        report["main"]["git_tag"] = git_tag
    with open("versions.json", "w") as file:
        json.dump(report, file, indent=2)


if __name__ == "__main__":
    main()
