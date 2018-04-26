#!/usr/bin/env python
# -*- coding: utf-8 -*-
##############################################
#
# This is open source software licensed under the Apache License 2.0
# http://www.apache.org/licenses/LICENSE-2.0
#
##############################################
"""Setup for plantgateway."""

import sys
from setuptools import setup


INSTALL_REQUIRES = ['bluepy==1.1.4', "paho-mqtt", 'pyyaml', "miflora==0.4"]
if sys.version_info < (3, 0):
    INSTALL_REQUIRES.append('mock')


setup(
    name='plantgateway',
    version='0.5.0',
    description='Bluetooth to mqtt gateway for Xiaomi Mi plant sensors',
    author='Christian Kühnel',
    author_email='christian.kuehnel@gmail.com',
    url='https://www.python.org/sigs/distutils-sig/',
    packages=['plantgw'],
    install_requires=INSTALL_REQUIRES,
    scripts=['plantgw/plantgateway'],
    )
