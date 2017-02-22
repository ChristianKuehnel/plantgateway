

from bluepy.btle import Peripheral
import logging


BYTEORDER = 'little'
INVALID_DATA = b'\xaa\xbb\xcc\xdd\xee\xff\x99\x88wf\x00\x00\x00\x00\x00\x00'

class Sensor(object):

    def __init__(self, mac):
        self.peripheral = Peripheral(mac)
        self.battery = None
        self.version = None

    def fetch_38(self):
        result = self.peripheral.readCharacteristic(0x38)
        self.battery = int.from_bytes(result[0:1],byteorder=BYTEORDER)
        self.version = result[2:7].decode('ascii')

    def fetch_35(self):


        result = self.peripheral.readCharacteristic(0x35)
        if result == INVALID_DATA:
            print('data invalid')
            #TODO improve error handling


s = Sensor('C4:7C:8D:60:D6:1C')
s.fetch_35()