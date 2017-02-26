from bluepy.btle import Peripheral, BTLEException
import logging
import time

logger = logging.getLogger(__name__)

BYTEORDER = 'little'
INVALID_DATA = b'\xaa\xbb\xcc\xdd\xee\xff\x99\x88wf\x00\x00\x00\x00\x00\x00'


class Sensor(object):

    def __init__(self, mac):
        self.peripheral = self._retry(Peripheral, [mac])
        logger.debug('connected to device {}'.format(mac))
        self.battery = None
        self.version = None
        self.temperature = None
        self.brightness = None
        self.moisture = None
        self.conductivity = None

    def get_data(self):
        self._fetch_35()
        self._fetch_38()

    def _fetch_38(self):
        result = self._retry(self.peripheral.readCharacteristic, [0x38])
        self.battery = int.from_bytes(result[0:1], byteorder=BYTEORDER)
        self.version = result[2:7].decode('ascii')
        logger.debug('Raw data for char 0x38: {}'.format(self._format_bytes(result)))
        logger.debug('battery: {}'.format(self.battery))
        logger.debug('version: {}'.format(self.version))

    def _fetch_35(self):
        self._retry(self.peripheral.writeCharacteristic, [0x33, bytes([0xA0, 0x1F]), True])

        result = self._retry(self.peripheral.readCharacteristic, [0x35])
        logger.debug('Raw data for char 0x35: {}'.format(self._format_bytes(result)))

        if result == INVALID_DATA:
            msg = 'invalid data received'
            logger.error(msg)
            raise Exception(msg)

        # negative numbers are stored in one's complement
        temp_bytes = result[0:2]
        if temp_bytes[1] & 0x80 > 0:
            temp_bytes = [temp_bytes[0] ^ 0xFF, temp_bytes[1] ^ 0xFF]

        # the temperature needs to be scaled by factor of 0.1
        self.temperature = int.from_bytes(temp_bytes, byteorder=BYTEORDER)/10.0
        self.brightness = int.from_bytes(result[3:5], byteorder=BYTEORDER)
        self.moisture = int.from_bytes(result[7:8], byteorder=BYTEORDER)
        self.conductivity = int.from_bytes(result[8:10], byteorder=BYTEORDER)

        logger.debug('temp: {}'.format(self.temperature))
        logger.debug('brightness: {}'.format(self.brightness))
        logger.debug('conductivity: {}'.format(self.conductivity))
        logger.debug('moisture: {}'.format(self.moisture))

    @staticmethod
    def _retry(func, args, num_tries=5, sleep_time=0.5):
        for i in range(0, num_tries):
            try:
                return func(*args)
            except BTLEException as e:
                logger.exception(e)
                time.sleep(sleep_time * (2 ^ i))
                if i == num_tries - 1:
                    logger.error('retry finally failed!')
                    raise e
                else:
                    continue

    @staticmethod
    def _format_bytes(b):
        return ' '.join([format(c, "02x") for c in b])
