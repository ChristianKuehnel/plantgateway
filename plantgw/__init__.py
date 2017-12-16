"""Forward measurements from Xiaomi Mi plant sensor via MQTT.

See https://github.com/ChristianKuehnel/plantgateway for more details.
"""

##############################################
#
# This is open source software licensed under the Apache License 2.0
# http://www.apache.org/licenses/LICENSE-2.0
#
##############################################


import os
import logging
import json
import time
from datetime import datetime
import yaml
import paho.mqtt.client as mqtt
from miflora.miflora_poller import MiFloraPoller, MI_BATTERY, MI_LIGHT, MI_CONDUCTIVITY, MI_MOISTURE, MI_TEMPERATURE
from miflora.backends.bluepy import BluepyBackend


# pylint: disable-msg=too-many-instance-attributes
class Configuration(object):
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


class SensorConfig(object):
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


class PlantGateway(object):
    """Main class of the module."""

    def __init__(self, config_file_path='~/.plantgw.yaml', start_client=True):
        config_file_path = os.path.abspath(os.path.expanduser(config_file_path))
        self.config = Configuration(config_file_path)
        logging.info('loaded config file from %s', config_file_path)
        self.mqtt_client = None
        self.connected = False
        if start_client:
            self._start_client()

    def start_client(self):
        """Start the mqtt client."""
        if not self.connected:
            self._start_client()

    def stop_client(self):
        """Stop the mqtt client."""
        if self.connected:
            self.mqtt_client.disconnect()
            self.connected = False
        self.mqtt_client.loop_stop()
        logging.info('Disconnected MQTT connection')

    def _start_client(self):
        self.mqtt_client = mqtt.Client(self.config.mqtt_client_id)
        if self.config.mqtt_user is not None:
            self.mqtt_client.username_pw_set(self.config.mqtt_user, self.config.mqtt_password)
        if self.config.mqtt_ca_cert is not None:
            self.mqtt_client.tls_set(self.config.mqtt_ca_cert, cert_reqs=mqtt.ssl.CERT_REQUIRED)

        def _on_connect(client, _, flags, return_code):
            self.connected = True
            logging.info("MQTT connection returned result: %s", mqtt.connack_string(return_code))
        self.mqtt_client.on_connect = _on_connect

        self.mqtt_client.connect(self.config.mqtt_server, self.config.mqtt_port, 60)
        self.mqtt_client.loop_start()

    def _publish(self, sensor_config, poller):
        if not self.connected:
            raise Exception('not connected to MQTT server')

        prefix_fmt = '{}/{}'
        if self.config.mqtt_trailing_slash:
            prefix_fmt += '/'
        prefix = prefix_fmt.format(self.config.mqtt_prefix, sensor_config.get_topic())

        data = {
            'battery': poller.parameter_value(MI_BATTERY),
            'temperature': '{0:.1f}'.format(poller.parameter_value(MI_TEMPERATURE)),
            'brightness': poller.parameter_value(MI_LIGHT),
            'moisture': poller.parameter_value(MI_MOISTURE),
            'conductivity': poller.parameter_value(MI_CONDUCTIVITY),
            'timestamp': datetime.now().isoformat(),
        }
        for key, value in data.items():
            logging.debug("%s: %s", key, value)
        if self.config.mqtt_timestamp_format is not None:
            data['timestamp'] = datetime.now().strftime(self.config.mqtt_timestamp_format)
        json_payload = json.dumps(data)
        self.mqtt_client.publish(prefix, json_payload, qos=1, retain=True)
        logging.info('sent data to topic %s', prefix)

    def process_mac(self, sensor_config):
        """Get data from one Sensor."""
        logging.info('Getting data from sensor %s', sensor_config.get_topic())
        poller = MiFloraPoller(sensor_config.mac, BluepyBackend)
        self._publish(sensor_config, poller)

    def process_all(self):
        """Get data from all sensors."""
        next_list = self.config.sensors
        timeout = 1  # initial timeout in seconds
        max_retry = 6  # number of retries
        retry_count = 0

        while retry_count < max_retry and next_list:
            # if this is not the first try: wait some time before trying again
            if retry_count > 0:
                logging.info('try %d of %d: could not process sensor(s) %s. Waiting %d sec for next try',
                             retry_count, max_retry, SensorConfig.get_name_string(next_list), timeout)
                time.sleep(timeout)
                timeout *= 2  # exponential backoff-time

            current_list = next_list
            retry_count += 1
            next_list = []
            for sensor in current_list:
                try:
                    self.process_mac(sensor)
                # pylint: disable=bare-except, broad-except
                except Exception as exception:
                    next_list.append(sensor)  # if it failed, we'll try again in the next round
                    msg = "could not read data from {} ({}) with reason: {}".format(
                        sensor.mac, sensor.alias, str(exception))
                    if sensor.fail_silent:
                        logging.error(msg)
                        logging.warning('fail_silent is set for sensor %s, so not raising an exception.', sensor.alias)
                    else:
                        logging.exception(msg)
                        print(msg)

        # return sensors that could not be processed after max_retry
        return next_list
