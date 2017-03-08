from setuptools import setup, find_packages


version = '0.4.0'

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
        "Programming Language :: Python :: 3.5",
        "Intended Audience :: Information Technology",
        "License :: OSI Approved :: MIT License",
        "Topic :: Scientific/Engineering :: GIS",
    ],
    keywords='geo gis sqlalchemy orm wsgi',
    author='Camptocamp',
    author_email='info@camptocamp.com',
    url='https://github.com/camptocamp/c2cwsgiutils',
    license='MIT',
    packages=find_packages(exclude=['ez_setup', 'acceptance_tests', 'tests', 'doc']),
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'cee_syslog_handler==0.3.4',
        'cornice==2.4.0',
        'gunicorn==19.6.0',
        'lxml==3.7.3',
        'netifaces==0.10.5',
        'psycopg2==2.6.2',
        'pyramid==1.8.2',
        'pyramid_tm==1.1.1',
        'pytest==3.0.6',
        'requests==2.13.0',
        'SQLAlchemy==1.1.6',
        'zope.interface==4.3.3',
        'zope.sqlalchemy==0.7.7',
    ],
    entry_points={
        'console_scripts': [
        ]
    },
    scripts=[
        'c2cwsgiutils_run'
    ]
)

