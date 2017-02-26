#!/usr/bin/env python
##############################################
#
# This is open source software licensed under the Apache License 2.0
# http://www.apache.org/licenses/LICENSE-2.0
#
##############################################

from distutils.core import setup

setup(name='plantgateway',
      version='0.2.0',
      description='Bluetooth to mqtt gateway for Xiaomi Mi plant sensors',
      author='Christian Kühnel',
      author_email='christian.kuehnel@gmail.com',
      url='https://www.python.org/sigs/distutils-sig/',
      packages=['plantgw'],
      install_requires=['bluepy', "paho-mqtt", 'pyyaml'],
      scripts=['plantgw/plantgateway'],
      )
