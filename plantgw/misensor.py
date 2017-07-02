"""Interaction with sensor via Bluetooth LE"""

##############################################
#
# This is open source software licensed under the Apache License 2.0
# http://www.apache.org/licenses/LICENSE-2.0
#
##############################################

import logging
from bluepy.btle import Peripheral, BTLEException

LOGGER = logging.getLogger(__name__)

BYTEORDER = 'little'
INVALID_DATA = b'\xaa\xbb\xcc\xdd\xee\xff\x99\x88wf\x00\x00\x00\x00\x00\x00'


class Sensor(object):
    """Read data from sensor."""

    def __init__(self, mac):
        self.peripheral = Peripheral(mac)
        LOGGER.debug('connected to device %s', mac)
        self.battery = None
        self.version = None
        self.temperature = None
        self.brightness = None
        self.moisture = None
        self.conductivity = None

    def get_data(self):
        """Get all data from sensor."""
        self._fetch_35()
        self._fetch_38()

    def _fetch_38(self):
        """Get data from characteristic 38."""
        result = self.peripheral.readCharacteristic(0x38)
        self._decode_38(result)

    def _decode_38(self, result):
        """Perform byte magic when decoding the data from the sensor."""
        self.battery = int.from_bytes(result[0:1], byteorder=BYTEORDER)
        self.version = result[2:7].decode('ascii')
        LOGGER.debug('Raw data for char 0x38: %s', self._format_bytes(result))
        LOGGER.debug('battery: %d', self.battery)
        LOGGER.debug('version: %s', self.version)

    def _fetch_35(self):
        """Get data from characteristic 35."""
        self.peripheral.writeCharacteristic(0x33, bytes([0xA0, 0x1F]), True)

        result = self.peripheral.readCharacteristic(0x35)
        LOGGER.debug('Raw data for char 0x35: %s', self._format_bytes(result))

        if result == INVALID_DATA:
            msg = 'invalid data received'
            LOGGER.error(msg)
            raise Exception(msg)

        self._decode_35(result)

    def _decode_35(self, result):
        """Perform byte magic when decoding the data from the sensor."""
        # negative numbers are stored in one's complement
        temp_bytes = result[0:2]
        if temp_bytes[1] & 0x80 > 0:
            temp_bytes = [temp_bytes[0] ^ 0xFF, temp_bytes[1] ^ 0xFF]

        # the temperature needs to be scaled by factor of 0.1
        self.temperature = int.from_bytes(temp_bytes, byteorder=BYTEORDER)/10.0
        self.brightness = int.from_bytes(result[3:5], byteorder=BYTEORDER)
        self.moisture = int.from_bytes(result[7:8], byteorder=BYTEORDER)
        self.conductivity = int.from_bytes(result[8:10], byteorder=BYTEORDER)

        LOGGER.debug('temp: %f', self.temperature)
        LOGGER.debug('brightness: %d', self.brightness)
        LOGGER.debug('conductivity: %d', self.conductivity)
        LOGGER.debug('moisture: %d', self.moisture)

    @staticmethod
    def _format_bytes(raw_data):
        """Prettyprint a byte array."""
        return ' '.join([format(c, "02x") for c in raw_data])

    def factory_reset(self):
        """Wipe all characteristics with zeros."""
        for char in range(0, 0x40):
            try:
                print('wiping characteristic {}'.format(char))
                self.peripheral.writeCharacteristic(char, bytes([0, 0, 0, 0]), False)
            except BTLEException:
                pass
