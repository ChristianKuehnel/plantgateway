import unittest
from plantgw.sensor import Sensor
from bluepy.btle import BTLEException


class TestBluetooth(unittest.TestCase):

    def setUp(self):
        self.failcount = 0

    def _fail_for_n(self, n):
        self.failcount += 1
        print(self.failcount)
        if self.failcount < n:
            raise BTLEException(0, 'test exception')
        return self.failcount

    def test_retry1(self):
        Sensor._retry(self._fail_for_n, [1])

    def test_retry6(self):
        try:
            Sensor._retry(self._fail_for_n, [10])
        except BTLEException:
            pass
        else:
            self.fail('should have thrown an exception')

    def test_format_bytes(self):
        self.assertEquals('ff 00 1b', Sensor._format_bytes(bytes([0xff, 0x00, 0x1b])))
