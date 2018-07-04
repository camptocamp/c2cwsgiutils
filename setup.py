import os
from setuptools import setup, find_packages


VERSION = '2.8.0'
HERE = os.path.abspath(os.path.dirname(__file__))
INSTALL_REQUIRES = [
    pkg.split('==')[0]
    for pkg in open(os.path.join(HERE, 'requirements.txt')).read().splitlines()
]


def long_description():
    try:
        return open('README.md').read()
    except FileNotFoundError:
        return ""


setup(
    name='c2cwsgiutils',
    version=VERSION,
    description="Common utilities for Camptocamp WSGI applications",
    long_description=long_description(),
    long_description_content_type='text/markdown',
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Plugins",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
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
    extras_require={
        'profiler': ['linesman'],
        'broadcast': ['redis']
    },
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
