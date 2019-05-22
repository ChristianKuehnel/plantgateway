import yaml
import logging
import os


# pylint: disable-msg=too-many-instance-attributes
class Configuration:
    """Stores the program configuration."""

    def __init__(self, config_file_path):
        with open(config_file_path, 'r') as config_file:
            config = yaml.load(config_file)

        self._configure_logging(config)

        self.interface = 0
        if 'interface' in config:
            self.interface = config['interface']

        self.mqtt_port = 8883
        self.mqtt_user = None
        self.mqtt_password = None
        self.mqtt_ca_cert = None
        self.mqtt_client_id = None
        self.mqtt_trailing_slash = True
        self.mqtt_timestamp_format = None
        self.sensors = []

        if 'port' in config['mqtt']:
            self.mqtt_port = config['mqtt']['port']

        if 'user' in config['mqtt']:
            self.mqtt_user = config['mqtt']['user']

        if 'password' in config['mqtt']:
            self.mqtt_password = config['mqtt']['password']

        if 'ca_cert' in config['mqtt']:
            self.mqtt_ca_cert = config['mqtt']['ca_cert']

        if 'client_id' in config['mqtt']:
            self.mqtt_client_id = config['mqtt']['client_id']

        if 'trailing_slash' in config['mqtt'] and not config['mqtt']['trailing_slash']:
            self.mqtt_trailing_slash = False

        if 'timestamp_format' in config['mqtt']:
            self.mqtt_timestamp_format = config['mqtt']['timestamp_format']

        self.mqtt_server = config['mqtt']['server']
        self.mqtt_prefix = config['mqtt']['prefix']

        for sensor_config in config['sensors']:
            fail_silent = 'fail_silent' in sensor_config
            self.sensors.append(SensorConfig(sensor_config['mac'], sensor_config['alias'], fail_silent))

    @staticmethod
    def _configure_logging(config):
        timeform = '%a, %d %b %Y %H:%M:%S'
        logform = '%(asctime)s %(levelname)-8s %(message)s'
        loglevel = logging.INFO
        if 'debug' in config:
            loglevel = logging.DEBUG

        if 'logfile' in config:
            logfile = os.path.abspath(os.path.expanduser(config['logfile']))
            logging.basicConfig(filename=logfile, level=loglevel, datefmt=timeform, format=logform)
        else:
            logging.basicConfig(level=loglevel, datefmt=timeform, format=logform)


class SensorConfig:
    """Stores the configuration of a sensor."""

    def __init__(self, mac, alias=None, fail_silent=False):
        if mac is None:
            msg = 'mac of sensor must not be None'
            logging.error(msg)
            raise Exception('mac of sensor must not be None')
        self.mac = mac
        self.alias = alias
        self.fail_silent = fail_silent

    def get_topic(self):
        """Get the topic name for the sensor."""
        if self.alias is not None:
            return self.alias
        return self.mac

    def __str__(self):
        result = self.alias
        if self.fail_silent:
            result += ' (fail silent)'
        return result

    @staticmethod
    def get_name_string(sensor_list):
        """Convert a list of sensor objects to a nice string."""
        return ', '.join([str(sensor) for sensor in sensor_list])

