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
import paho.mqtt.client as mqtt
from miflora.miflora_poller import MiFloraPoller, MI_BATTERY, MI_LIGHT, MI_CONDUCTIVITY, MI_MOISTURE, MI_TEMPERATURE
from miflora import miflora_scanner
from btlewrap.bluepy import BluepyBackend

from plantgw import __version__
from plantgw.config import Configuration, SensorConfig


class Sensor:
    """A miflora sensor."""

    def __init__(self, mac:str):
        self.mac = mac
        self.last_seen = datetime.now()
        self.last_polled = None
        self.last_data = None
        self.last_read_attempt = None

    def poll(self):
        # TODO: handle errors
        logging.info('polling sensor %s', self.mac)
        self.last_read_attempt = datetime.now()
        poller = MiFloraPoller(self.mac, BluepyBackend)
        data = {
            'battery': poller.parameter_value(MI_BATTERY),
            'temperature': '{0:.1f}'.format(poller.parameter_value(MI_TEMPERATURE)),
            'brightness': poller.parameter_value(MI_LIGHT),
            'moisture': poller.parameter_value(MI_MOISTURE),
            'conductivity': poller.parameter_value(MI_CONDUCTIVITY),
            'timestamp': datetime.now().isoformat(),
        }
        self.last_data = data
        self.last_polled = datetime.now()
        self.last_seen = self.last_polled
        logging.info('polling completed')
        logging.debug('data from %s was %s', self.mac, self.last_data)


class MQTTClient:

    def __init__(self, config:Configuration):
        self.config = config
        self.mqtt_client = None
        self.connected = False

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

        def _on_disconnect(client, _, flags, return_code):
            self.connected = False
            logging.info("MQTT connection terminated: %s", mqtt.connack_string(return_code))

        self.mqtt_client.on_connect = _on_connect
        self.mqtt_client.on_disconnect= _on_disconnect

        self.mqtt_client.connect(self.config.mqtt_server, self.config.mqtt_port, 60)
        self.mqtt_client.loop_start()

    def publish(self, sensor: Sensor):
        # TODO: handle errors
        self.start_client()
        prefix_fmt = '{}/{}'
        if self.config.mqtt_trailing_slash:
            prefix_fmt += '/'
        prefix = prefix_fmt.format(self.config.mqtt_prefix, sensor.mac)
        json_payload = json.dumps(sensor.last_data)
        self.mqtt_client.publish(prefix, json_payload, qos=1, retain=True)
        logging.info('sent data to topic %s', prefix)

    # TODO: announce new sensors in Homeassistant compatible way


class PlantGateway:
    """Main class of the module."""

    def __init__(self, config_file_path='~/.plantgw.yaml'):
        config_file_path = os.path.abspath(os.path.expanduser(config_file_path))
        self.config = Configuration(config_file_path)
        logging.info('PlantGateway version %s', __version__)
        logging.info('loaded config file from %s', config_file_path)
        self.mqtt_client = MQTTClient(self.config)
        self.sensors = dict()  # type: Dict[str, Sensor]
        self.last_scan = None

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

    def scan_for_sensors(self):
        logging.info('Scanning for sensors...')
        macs = miflora_scanner.scan(BluepyBackend, 10)
        for mac in macs:
            if mac not in self.sensors:
                self.sensors[mac] = Sensor(mac)
            else:
                self.sensors[mac].seen()
        self.last_scan = datetime.now()
        logging.info('Scan completed. Found %d sensors: %s', len(macs), ', '.join(macs))

    def start_daemon(self):
        """Run plantgateway as daemon"""
        while True:
            logging.info('main loop')
            if self.last_scan is None:
                self.scan_for_sensors()
            for sensor in self.sensors.values():
                sensor.poll()
                self.mqtt_client.publish(sensor)

            time.sleep(60)
