##############################################
#
# This is open source software licensed under the Apache License 2.0
# http://www.apache.org/licenses/LICENSE-2.0
#
##############################################

import paho.mqtt.client as mqtt
from miflora.miflora_poller import MiFloraPoller, \
    MI_CONDUCTIVITY, MI_MOISTURE, MI_LIGHT, MI_TEMPERATURE, MI_BATTERY
import os
import yaml
import logging


class Configuration(object):

    def __init__(self, config_file_path):
        with open(config_file_path, 'r') as config_file:
            config = yaml.load(config_file)

        if 'logfile' in config:
            logfile = os.path.abspath(os.path.expanduser(config['logfile']))
            logging.basicConfig(filename=logfile, level=logging.INFO)
        else:
            logging.basicConfig(level=logging.INFO)

        self.mqtt_port = 8883
        self.mqtt_user = None
        self.mqtt_password = None
        self.mqtt_ca_cert = None
        self.sensors = []

        if 'port' in config['mqtt']:
            self.mqtt_port = config['mqtt']['port']

        if 'user' in config['mqtt']:
            self.mqtt_user = config['mqtt']['user']

        if 'password' in config['mqtt']:
            self.mqtt_password = config['mqtt']['password']

        if 'ca_cert' in config['mqtt']:
            self.mqtt_ca_cert = config['mqtt']['ca_cert']

        self.mqtt_server = config['mqtt']['server']
        self.mqtt_prefix = config['mqtt']['prefix']

        for s in config['sensors']:
            self.sensors.append(Sensor(s['mac'], s['alias']))


class Sensor(object):

    def __init__(self, mac, alias=None):
        if mac is None:
            msg = 'mac of sensor must not be None'
            logging.error(msg)
            raise Exception('mac of sensor must not be None')
        self.mac = mac
        self.alias = alias

    def get_path(self):
        if self.alias is not None:
            return self.alias
        return self.mac


class PlantGateway(object):

    def __init__(self, config_file_path='~/.plantgw.yaml'):
        config_file_path = os.path.abspath(os.path.expanduser(config_file_path))
        self.config = Configuration(config_file_path)
        logging.info('loaded config file from {}'.format(config_file_path))
        self.mqtt_client = None
        self.connected = False
        self._start_client()

    def _start_client(self):
        self.mqtt_client = mqtt.Client()
        if self.config.mqtt_user is not None:
            self.mqtt_client.username_pw_set(self.config.mqtt_user,self.config.mqtt_password)
        if self.config.mqtt_ca_cert is not None:
            self.mqtt_client.tls_set(self.config.mqtt_ca_cert, cert_reqs=mqtt.ssl.CERT_REQUIRED)

        def on_connect(client, _, flags, rc):
            self.connected = True
            logging.info("MQTT connection returned result: {}".format(mqtt.connack_string(rc)))
        self.mqtt_client.on_connect = on_connect

        self.mqtt_client.connect(self.config.mqtt_server, self.config.mqtt_port, 60)
        self.mqtt_client.loop_start()

    def _publish(self, sensor, batt, temp, brightness, moisture, conductivity):
        if not self.connected:
            raise Exception('not connected to MQTT server')
        prefix = '{}/{}/'.format(self.config.mqtt_prefix, sensor.get_path())
        data = {
            'battery': batt,
            'temperature': '{0:.1f}'.format(temp),
            'brightness': brightness,
            'moisture': moisture,
            'conductivity': conductivity,
        }
        for topic, payload in data.items():
            self.mqtt_client.publish(prefix+topic, payload, qos=1)
        logging.info('sent data to topic {}'.format(prefix))

    def process_mac(self, sensor):
        logging.info('Getting data from sensor {}'.format(sensor.get_path()))
        poller = MiFloraPoller(sensor.mac)
        temp = poller.parameter_value(MI_TEMPERATURE)
        moisture = poller.parameter_value(MI_MOISTURE)
        brightness = poller.parameter_value(MI_LIGHT)
        conductivity = poller.parameter_value(MI_CONDUCTIVITY)
        batt = poller.parameter_value(MI_BATTERY)
        self._publish(sensor, batt, temp, brightness, moisture, conductivity)

    def process_all(self):
        error_count = 0
        try:
            for sensor in self.config.sensors:
                self.process_mac(sensor)
            logging.info('exiting successfully')
        except:
            msg = "could not read data from {} ({})".format(sensor.mac,sensor.alias)
            logging.exception(msg)
            print(msg)
            error_count += 1
        return error_count
