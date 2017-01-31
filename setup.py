from setuptools import setup, find_packages


version = '0.0.1'

setup(
    name='c2cwsgiutils',
    version=version,
    description="Common utilities for Camptocamp WSGI applications",
    long_description=open('README.md').read(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Plugins",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Intended Audience :: Information Technology",
        "License :: OSI Approved :: MIT License",
        "Topic :: Scientific/Engineering :: GIS",
    ],
    keywords='geo gis sqlalchemy orm wsgi',
    author='Camptocamp',
    author_email='info@camptocamp.com',
    url='http://camptocamp.com/',
    license='MIT',
    packages=find_packages(exclude=['ez_setup', 'acceptance_tests', 'tests', 'doc']),
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'alembic==0.8.10',
        'cee_syslog_handler==0.3.4',
        'psycopg2==2.6.2',
        'pyramid==1.7.3',
        'pyramid_tm==1.1.1',
        'SQLAlchemy==1.1.5',
        'zope.interface==4.3.3',
        'zope.sqlalchemy==0.7.7',
    ],
    entry_points="""
    # -*- Entry points: -*-
    """,
)

