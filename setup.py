#!/usr/bin/env python
# -*- coding: utf-8 -*-
##############################################
#
# This is open source software licensed under the Apache License 2.0
# http://www.apache.org/licenses/LICENSE-2.0
#
##############################################

import sys
from distutils.core import setup

install_requires = ['bluepy==1.1.4', "paho-mqtt", 'pyyaml']
if sys.version_info < (3, 0):
    install_requires.append('mock')


setup(name='plantgateway',
      version='0.3.8',
      description='Bluetooth to mqtt gateway for Xiaomi Mi plant sensors',
      author='Christian Kühnel',
      author_email='christian.kuehnel@gmail.com',
      url='https://www.python.org/sigs/distutils-sig/',
      packages=['plantgw'],
      install_requires=install_requires,
      scripts=['plantgw/plantgateway'],
      )
