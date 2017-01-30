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
            logging.basicConfig(filename=config['logfile'], level=logging.INFO)
        else:
            logging.basicConfig(level=logging.INFO)

        self.mqtt_port = 1883
        # self.mqtt_user = None
        # self.mqtt_password = None
        self.sensors = []

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
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.connect(self.config.mqtt_server, self.config.mqtt_port, 60)
        self.mqtt_client.loop_start()
        logging.info('connected to mqtt server {}:{}'.format(
            self.config.mqtt_server,
            self.config.mqtt_port))

    def _publish(self, sensor, batt, temp, brightness, moisture, conductivity):
        prefix = '{}/{}/'.format(self.config.mqtt_prefix, sensor.get_path())
        data = {
            'battery': batt,
            'temp': '{0:.1f}'.format(temp),
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
        try:
            for sensor in self.config.sensors:
                self.process_mac(sensor)
            logging.info('exiting successfully')
        except:
            logging.exception('')
            raise
