import os
from setuptools import setup, find_packages


VERSION = '0.13.1'
HERE = os.path.abspath(os.path.dirname(__file__))
INSTALL_REQUIRES = open(os.path.join(HERE, 'rel_requirements.txt')).read().splitlines()

setup(
    name='c2cwsgiutils',
    version=VERSION,
    description="Common utilities for Camptocamp WSGI applications",
    long_description=open('README.md').read(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Plugins",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.5",
        "Intended Audience :: Information Technology",
        "License :: OSI Approved :: MIT License",
        "Topic :: Scientific/Engineering :: GIS",
    ],
    keywords='geo gis sqlalchemy orm wsgi',
    author='Camptocamp',
    author_email='info@camptocamp.com',
    url='https://github.com/camptocamp/c2cwsgiutils',
    license='FreeBSD',
    packages=find_packages(exclude=['ez_setup', 'acceptance_tests', 'tests', 'docs']),
    include_package_data=True,
    zip_safe=False,
    install_requires=INSTALL_REQUIRES,
    entry_points={
        'console_scripts': [
        ]
    },
    scripts=[
        'c2cwsgiutils_run',
        'c2cwsgiutils_genversion.py',
        'c2cwsgiutils_coverage_report.py',
        'c2cwsgiutils_stats_db.py'
    ]
)
