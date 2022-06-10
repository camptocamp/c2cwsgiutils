import configparser
import os

from setuptools import find_packages, setup

VERSION = "5.1.0"
HERE = os.path.abspath(os.path.dirname(__file__))


def long_description() -> str:
    """Get the long description."""
    try:
        with open("README.md", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return ""


config = configparser.ConfigParser()
config.read(os.path.join(HERE, "Pipfile"))
INSTALL_REQUIRES = [pkg.strip('"') for pkg, version in config["packages"].items() if pkg != "setuptools"]

setup(
    name="c2cwsgiutils",
    version=VERSION,
    description="Common utilities for Camptocamp WSGI applications",
    long_description=long_description(),
    long_description_content_type="text/markdown",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Plugins",
        "Framework :: Pyramid",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Intended Audience :: Information Technology",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
        "Typing :: Typed",
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
        "standard": [e for e in INSTALL_REQUIRES if e != "redis"],
        "broadcast": ["redis"],
    },
    entry_points={
        "console_scripts": [
            "c2cwsgiutils-genversion = c2cwsgiutils.scripts.genversion:main",
            "c2cwsgiutils-coverage-report = c2cwsgiutils.scripts.coverage_report:main",
            "c2cwsgiutils-stats-db = c2cwsgiutils.scripts.stats_db:main",
            "c2cwsgiutils-test-print = c2cwsgiutils.scripts.test_print:main",
            "c2cwsgiutils-check-es = c2cwsgiutils.scripts.check_es:main",
            # deprecated scripts
            "c2cwsgiutils_genversion.py = c2cwsgiutils.scripts.genversion:deprecated",
            "c2cwsgiutils_coverage_report.py = c2cwsgiutils.scripts.coverage_report:deprecated",
            "c2cwsgiutils_stats_db.py = c2cwsgiutils.scripts.stats_db:deprecated",
            "c2cwsgiutils_test_print.py = c2cwsgiutils.scripts.test_print:deprecated",
            "c2cwsgiutils_check_es.py = c2cwsgiutils.scripts.check_es:deprecated",
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
        "paste.filter_factory": [
            "client_info=c2cwsgiutils.client_info:filter_factory",
            "sentry=c2cwsgiutils.sentry:filter_factory",
        ],
    },
    scripts=["scripts/c2cwsgiutils-run"],
    package_data={"c2cwsgiutils": ["py.typed"]},
)
