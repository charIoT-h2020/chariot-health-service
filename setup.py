#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""

from setuptools import setup, find_packages

with open('README.md') as readme_file:
    readme = readme_file.read()

requirements = [
    'falcon',
    'influxdb',
    'chariot_base==0.9.3',
    'asyncio',
    'gmqtt',
    'influxdb',
    'pytest',
    'fastecdsa',
    'ecdsa',
    'pycrypto',
    'jaeger-client',
    'pytest-asyncio',
    'pymongo==3.7.2',
    'apscheduler',
    'python-dateutil'
]

setup_requirements = [ ]

test_requirements = [ ]

setup(
    author="George Theofilis",
    author_email='g.theofilis@clmsuk.com',
    classifiers=[
        'License :: OSI Approved :: Eclipse Public License 1.0',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
    ],
    description="CharIoT Health Service",
    install_requires=requirements,
    license="EPL-1.0",
    long_description=readme,
    include_package_data=True,
    keywords='chariot_health_service',
    name='chariot_health_service',
    packages=find_packages(include=[
        'chariot_health_service',
        'chariot_health_service.*'
    ]),
    setup_requires=setup_requirements,
    test_suite='tests',
    tests_require=test_requirements,
    url='https://gitlab.com/chariot-h2020/chariot-health-service',
    version='0.1.2',
    zip_safe=False,
)
