##############################################
#
# This is open source software licensed under the Apache License 2.0
# http://www.apache.org/licenses/LICENSE-2.0
#
##############################################

import sys
import unittest
import logging
import binascii
from plantgw.misensor import Sensor
from bluepy.btle import BTLEException
if sys.version_info < (3, 0):
    import mock
else:
    import unittest.mock as mock

# setup logging
logger = logging.getLogger()
logger.level = logging.DEBUG
stream_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(stream_handler)


class TestMiSensor(unittest.TestCase):

    def setUp(self):
        self.failcount = 0

    def _fail_for_n(self, n):
        self.failcount += 1
        if self.failcount < n:
            raise BTLEException(0, 'test exception')
        return self.failcount

    def test_format_bytes(self):
        self.assertEquals('ff 00 1b', Sensor._format_bytes(bytes([0xff, 0x00, 0x1b])))

    @mock.patch('plantgw.misensor.Peripheral')
    def test_decode_38(self, mock_peripheral):
        test_data = self._str2bytearray("62 1d 32 2e 38 2e 36")
        s = Sensor('11:22:33', 0)
        s._decode_38(test_data)
        self.assertEqual(s.battery, 98)
        self.assertEqual(s.version, '2.8.6')

    @mock.patch('plantgw.misensor.Peripheral')
    def test_decode_35(self, mock_peripheral):
        test_data = self._str2bytearray("ce 00 00 35 00 00 00 1c c8 00 02 3c 00 fb 34 9b")
        s = Sensor('11:22:33', 0)
        s._decode_35(test_data)
        self.assertEqual(s.temperature, 20.6)
        self.assertEqual(s.moisture, 28)
        self.assertEqual(s.conductivity, 200)
        self.assertEqual(s.brightness, 53)

    @staticmethod
    def _str2bytearray(hex_string):
        return binascii.unhexlify(hex_string.replace(' ', ''))
