#!/usr/bin/env python3
import json
import os
import re
import subprocess
import sys

VERSION_RE = re.compile(r'^(.*)==(.*)$')


def _get_git_versions(root):
    git_hash = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root).strip()
    try:
        with open(os.devnull, "w") as devnull:
            git_tag = subprocess.check_output(["git", "describe", "--tags", "--first-parent"],
                                              stderr=devnull, cwd=root).strip()
        git_tag = re.sub(r"-g[a-f0-9]+$", "", git_tag)
    except:
        git_tag = None
    return {
        "git_hash": git_hash,
        "git_tag": git_tag
    }


def _get_packages_version():
    result = {}
    with open(os.devnull, "w") as devnull:
        for comp in subprocess.check_output(["pip3", "freeze"], stderr=devnull).decode().strip().split('\n'):
            matcher = VERSION_RE.match(comp)
            if matcher:
                name, version = matcher.groups()
                result[name] = version
            else:
                print("Cannot parse package version: " + comp)
    return result


def main():
    git_tag = sys.argv[1]
    git_hash = sys.argv[2]
    report = {
        'main': {
            "git_hash": git_hash,
            "git_tag": git_tag
        },
        'packages': _get_packages_version()
    }
    with open('versions.json', 'w') as file:
        json.dump(report, file, indent=2)


if __name__ == "__main__":
    main()
