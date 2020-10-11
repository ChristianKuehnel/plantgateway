"""Forward measurements from Xiaomi Mi plant sensor via MQTT.

See https://github.com/ChristianKuehnel/plantgateway for more details.
"""

##############################################
#
# This is open source software licensed under the Apache License 2.0
# http://www.apache.org/licenses/LICENSE-2.0
#
##############################################


from enum import Enum
import os
import logging
import json
import time
from datetime import datetime
from typing import List, Optional
import yaml
import paho.mqtt.client as mqtt
from miflora.miflora_poller import MiFloraPoller, MI_BATTERY, MI_LIGHT, MI_CONDUCTIVITY, MI_MOISTURE, MI_TEMPERATURE
from btlewrap.bluepy import BluepyBackend

from plantgw import __version__


class MQTTAttributes(Enum):
    """Attributes sent in the json dict."""
    BATTERY = 'battery'
    TEMPERATURE = 'temperature'
    BRIGHTNESS = 'brightness'
    MOISTURE = 'moisture'
    CONDUCTIVITY = 'conductivity'
    TIMESTAMP = 'timestamp'


# unit of measurement for the different attributes
UNIT_OF_MEASUREMENT = {
    MQTTAttributes.BATTERY:      '%',
    MQTTAttributes.TEMPERATURE:  '°C',
    MQTTAttributes.BRIGHTNESS:   'lux',
    MQTTAttributes.MOISTURE:     '%',
    MQTTAttributes.CONDUCTIVITY: 'µS/cm',
    MQTTAttributes.TIMESTAMP:     's',
}


# home assistant device classes for the different attributes
DEVICE_CLASS = {
    MQTTAttributes.BATTERY:      'battery',
    MQTTAttributes.TEMPERATURE:  'temperature',
    MQTTAttributes.BRIGHTNESS:   'illuminance',
    MQTTAttributes.MOISTURE:     None,
    MQTTAttributes.CONDUCTIVITY: None,
    MQTTAttributes.TIMESTAMP:    'timestamp',
}


# pylint: disable-msg=too-many-instance-attributes
class Configuration:
    """Stores the program configuration."""

    def __init__(self, config_file_path):
        with open(config_file_path, 'r') as config_file:
            config = yaml.load(config_file, Loader=yaml.FullLoader)

        self._configure_logging(config)

        self.interface = 0
        if 'interface' in config:
            self.interface = config['interface']

        self.mqtt_port = 8883  # type: int
        self.mqtt_user = None  # type: Optional[str]
        self.mqtt_password = None  # type: Optional[str]
        self.mqtt_ca_cert = None  # type: Optional[str]
        self.mqtt_client_id = None  # type: Optional[str]
        self.mqtt_trailing_slash = True  # type:bool
        self.mqtt_timestamp_format = None  # type: Optional[str]
        self.mqtt_discovery_prefix = None  # type: Optional[str]
        self.sensors = []  # type: List[SensorConfig]

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

        if 'discovery_prefix' in config['mqtt']:
            self.mqtt_discovery_prefix = config['mqtt']['discovery_prefix']

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

    def __init__(self, mac: str, alias: str = None, fail_silent: bool = False):
        if mac is None:
            msg = 'mac of sensor must not be None'
            logging.error(msg)
            raise Exception('mac of sensor must not be None')
        self.mac = mac
        self.alias = alias
        self.fail_silent = fail_silent

    def get_topic(self) -> str:
        """Get the topic name for the sensor."""
        if self.alias is not None:
            return self.alias
        return self.mac

    def __str__(self) -> str:
        if self.alias:
            result = self.alias
        else:
            result = self.mac
        if self.fail_silent:
            result += ' (fail silent)'
        return result

    @property
    def short_mac(self):
        """Get the sensor mac without ':' in it."""
        return self.mac.replace(':', '')

    @staticmethod
    def get_name_string(sensor_list) -> str:
        """Convert a list of sensor objects to a nice string."""
        return ', '.join([str(sensor) for sensor in sensor_list])


class PlantGateway:
    """Main class of the module."""

    def __init__(self, config_file_path: str = '~/.plantgw.yaml'):
        config_file_path = os.path.abspath(os.path.expanduser(config_file_path))
        self.config = Configuration(config_file_path)  # type: Configuration
        logging.info('PlantGateway version %s', __version__)
        logging.info('loaded config file from %s', config_file_path)
        self.mqtt_client = None
        self.connected = False  # type: bool

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

    def _publish(self, sensor_config: SensorConfig, poller: MiFloraPoller):
        self.start_client()
        state_topic = self._get_state_topic(sensor_config)

        data = {
            MQTTAttributes.BATTERY.value:      poller.parameter_value(MI_BATTERY),
            MQTTAttributes.TEMPERATURE.value:  '{0:.1f}'.format(poller.parameter_value(MI_TEMPERATURE)),
            MQTTAttributes.BRIGHTNESS.value:   poller.parameter_value(MI_LIGHT),
            MQTTAttributes.MOISTURE.value:     poller.parameter_value(MI_MOISTURE),
            MQTTAttributes.CONDUCTIVITY.value: poller.parameter_value(MI_CONDUCTIVITY),
            MQTTAttributes.TIMESTAMP.value:    datetime.now().isoformat(),
        }
        for key, value in data.items():
            logging.debug("%s: %s", key, value)
        if self.config.mqtt_timestamp_format is not None:
            data['timestamp'] = datetime.now().strftime(self.config.mqtt_timestamp_format)
        json_payload = json.dumps(data)
        self.mqtt_client.publish(state_topic, json_payload, qos=1, retain=True)
        logging.info('sent data to topic %s', state_topic)

    def _get_state_topic(self, sensor_config: SensorConfig) -> str:
        prefix_fmt = '{}/{}'
        if self.config.mqtt_trailing_slash:
            prefix_fmt += '/'
        prefix = prefix_fmt.format(self.config.mqtt_prefix,
                                   sensor_config.get_topic())
        return prefix

    def process_mac(self, sensor_config: SensorConfig):
        """Get data from one Sensor."""
        logging.info('Getting data from sensor %s', sensor_config.get_topic())
        poller = MiFloraPoller(sensor_config.mac, BluepyBackend)
        self.announce_sensor(sensor_config)
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

    def announce_sensor(self, sensor_config: SensorConfig):
        """Announce the sensor via Home Assistant MQTT Discovery.

           see https://www.home-assistant.io/docs/mqtt/discovery/
        """
        if self.config.mqtt_discovery_prefix is None:
            return
        self.start_client()
        device_name = 'plant_{}'.format(sensor_config.short_mac)
        for attribute in MQTTAttributes:
            topic = '{}/sensor/{}_{}/config'.format(self.config.mqtt_discovery_prefix, device_name, attribute.value)
            payload = {
                'state_topic':         self._get_state_topic(sensor_config),
                'unit_of_measurement': UNIT_OF_MEASUREMENT[attribute],
                'value_template':      '{{value_json.'+attribute.value+'}}',
                'force_update':        True,
                'unique_id':           'sensor.plant_{}'.format(sensor_config.short_mac)
            }
            if sensor_config.alias is not None:
                payload['name'] = '{}_{}'.format(sensor_config.alias, attribute.value)

            if sensor_config.alias is not None:
                payload['unique_id'] = 'sensor.{}_{}'.format(sensor_config.alias, attribute.value)
 
            if DEVICE_CLASS[attribute] is not None:
                payload['device_class'] = DEVICE_CLASS[attribute]

            json_payload = json.dumps(payload)
            self.mqtt_client.publish(topic, json_payload, qos=1, retain=True)
            logging.info('sent sensor config to topic %s', topic)
