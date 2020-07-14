import os

import pipfile
from setuptools import find_packages, setup

VERSION = "4.0.0"
HERE = os.path.abspath(os.path.dirname(__file__))


def long_description() -> str:
    try:
        with open("README.md") as f:
            return f.read()
    except FileNotFoundError:
        return ""


setup(
    name="c2cwsgiutils",
    version=VERSION,
    description="Common utilities for Camptocamp WSGI applications",
    long_description=long_description(),
    long_description_content_type="text/markdown",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Plugins",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.7",
        "Intended Audience :: Information Technology",
        "License :: OSI Approved :: MIT License",
        "Topic :: Scientific/Engineering :: GIS",
    ],
    keywords="geo gis sqlalchemy orm wsgi",
    author="Camptocamp",
    author_email="info@camptocamp.com",
    url="https://github.com/camptocamp/c2cwsgiutils",
    license="FreeBSD",
    packages=find_packages(exclude=["ez_setup", "acceptance_tests", "tests", "docs"]),
    include_package_data=True,
    zip_safe=False,
    install_requires=[],
    extras_require={
        "standard": [
            e[0] for e in pipfile.load().data["default"].items() if e[0] != "redis"
        ],
        "profiler": ["linesman"],
        "broadcast": ["redis"],
    },
    entry_points={
        "console_scripts": [
            "c2cwsgiutils-genversion = c2cwsgiutils.scripts.genversion:main",
            "c2cwsgiutils-coverage-report = c2cwsgiutils.scripts.coverage_report:main",
            "c2cwsgiutils-stats-db = c2cwsgiutils.scripts.stats_db:main",
            "c2cwsgiutils-test-print = c2cwsgiutils.scripts.test_print:main",
            "c2cwsgiutils-check-es = c2cwsgiutils.scripts.check_es:main",
        ],
        "plaster.loader_factory": [
            "c2c=c2cwsgiutils.loader:Loader",
            "c2c+ini=c2cwsgiutils.loader:Loader",
            "c2c+egg=c2cwsgiutils.loader:Loader",
        ],
        "plaster.wsgi_loader_factory": [
            "c2c=c2cwsgiutils.loader:Loader",
            "c2c+ini=c2cwsgiutils.loader:Loader",
            "c2c+egg=c2cwsgiutils.loader:Loader",
        ],
    },
    scripts=["scripts/c2cwsgiutils-run"],
)
