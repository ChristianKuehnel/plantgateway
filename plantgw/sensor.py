

from bluepy.btle import Peripheral
import logging


BYTEORDER = 'little'
INVALID_DATA = b'\xaa\xbb\xcc\xdd\xee\xff\x99\x88wf\x00\x00\x00\x00\x00\x00'

class Sensor(object):

    def __init__(self, mac):
        self.peripheral = Peripheral(mac)
        self.battery = None
        self.version = None
        self.temperature = None

    def fetch_38(self):
        result = self.peripheral.readCharacteristic(0x38)
        self.battery = int.from_bytes(result[0:1],byteorder=BYTEORDER)
        self.version = result[2:7].decode('ascii')

    def fetch_35(self):
        result = self.peripheral.writeCharacteristic(0x33, bytes.fromhex('A01F'),withResponse=True)
        if result['rsp'] != ['wr']:
            print('writing failed')
            #TODO improve error handling
        result = self.peripheral.readCharacteristic(0x35)
        if result == INVALID_DATA:
            print('data invalid')
            #TODO improve error handling
        print(self._format_bytes(result))
        self.temperature = int.from_bytes(result[0:1],byteorder=BYTEORDER)/10.0
        self.brightness = int.from_bytes(result[3:4],byteorder=BYTEORDER)
        self.moisture = int.from_bytes(result[7:7],byteorder=BYTEORDER)
        self.conductivity = int.from_bytes(result[8:9],byteorder=BYTEORDER)

    @staticmethod
    def _format_bytes(b):
        result = ''
        count = 0
        for c in bytes.hex(b):
            result += c
            count += 1
            if count%2 == 0:
                result += ' '
            if count%8 == 0:
                result += ' '
        return result



s = Sensor('C4:7C:8D:60:D6:1C')
#s = Sensor('C4:7C:8D:60:D6:41')

s.fetch_35()
print('temp: {}'.format(s.temperature))
print('brightness: {}'.format(s.brightness))
print('conductivity: {}'.format(s.conductivity))
print('moisture: {}'.format(s.moisture))