#!/usr/bin/env python3
import json
import os
import re
import subprocess
import sys

VERSION_RE = re.compile(r"^(.*)==(.*)$")


def _get_packages_version():
    result = {}
    with open(os.devnull, "w") as devnull:
        for comp in subprocess.check_output(["pip3", "freeze"], stderr=devnull).decode().strip().split("\n"):
            matcher = VERSION_RE.match(comp)
            if matcher:
                name, version = matcher.groups()
                result[name] = version
            else:
                print("Cannot parse package version: " + comp)
    return result


def main():
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
