#!/usr/bin/env python
# -*- coding: utf-8 -*-
##############################################
#
# This is open source software licensed under the Apache License 2.0
# http://www.apache.org/licenses/LICENSE-2.0
#
##############################################
"""Setup for plantgateway."""

from setuptools import setup
from plantgw import __version__

INSTALL_REQUIRES = ['bluepy==1.1.4', "paho-mqtt", 'pyyaml>=4.2b1', "miflora==0.4"]

setup(
    name='plantgateway',
    version=__version__,
    description='Bluetooth to mqtt gateway for Xiaomi Mi plant sensors',
    author='Christian Kühnel',
    author_email='christian.kuehnel@gmail.com',
    url='https://www.python.org/sigs/distutils-sig/',
    packages=['plantgw'],
    install_requires=INSTALL_REQUIRES,
    entry_points = {
        'console_scripts': ['plantgatewayd=plantgw.daemon:main'],
    }
    )
