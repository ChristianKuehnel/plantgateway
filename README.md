# plantgateway
Bluetooth LE to mqtt gateway for Xiaomi Mi plant sensors. For more details see the [documentation overview](doc/overview.md).

# Use case
For many setups the Xiaomi Mi plant sensors are too far away from your 
home server to connect directly via Bluetooth LE. 
In such a scenario the plantgatway will poll the data from a list of 
Xiaomi Mi plant sensors via Bluetooth LE using 
[miflora](https://github.com/open-homeautomation/miflora).
The data is then published via mqtt to your home automation server.

The plantgateway is intended to be run on a small Linux machine (e.g. 
[Raspberry Pi](https://www.raspberrypi.org/)
or a [C.H.I.P](https://getchip.com/)) that has both Bluetooth LE and WiFi.

# installation & update
* install [python 3.4](https://www.python.org/) (or above)
and [pip](https://pip.pypa.io/en/stable/installing/)
```
sudo apt-get install python3-pip build-essential libglib2.0-dev libyaml-dev
```
* install the plant gateway from pypi:
```
sudo pip install --upgrade plantgateway
```
or if you have multiple python and pip installations:
```
sudo pip3 install --upgrade plantgateway
```
* To update your installation just run pip again. 

If you have problems with the PyYaml installation, update your pip version 
with `sudo pip3 install --upgrade pip` and try again.

# configuration
Copy the [plantgw.yaml](plantgw.yaml) (in this repository) to your home directory and
rename it to ".plantgw.yaml".
Then change this file to match your requirements.

# execution
After the installation with pip you can simply run the tool from the command line:
```
plantgateway
```
There are no command line parameters and there is no interaction required.
You probably want to add the script to your cron tab to be executed 
in regular intervals (e.q. every hour).

# integration in home automation

## HomeAssistant
If you enable the [MQTT discovery](https://www.home-assistant.io/docs/mqtt/discovery/) 
feature by setting the `discovery_prefix` parameter in
the config file, all configured sensors are automatically available in HomeAssistant.
To monitor the state of your plants, you can use the 
["plant" component](https://www.home-assistant.io/components/plant/).


## fhem
To check your plants in the home automation tool [fhem](http://fhem.de/), 
you can use the 
[gardener](https://github.com/ChristianKuehnel/fhem-gardener) module. 
The installation is explained on the github page of the module.

If you haven't done so, you need to configure your MQTT server in fhem with 
a [MQTT](http://fhem.de/commandref.html#MQTT) module.
For each sensor you have, set up a [MQTT_Device](http://fhem.de/commandref.html#MQTT_DEVICE) 
and make it auto subscribe to the topic 
you configured in the plantgateway:
```
define <plant_name> MQTT_Device
attr <plant_name> autoSubscribeReadings <prefix_in_config>/<plant alias>/+
```

After that configure the gardener to match your requirements

# Security
A remark on security:
Before running your MQTT server on the internet make sure that you enable
SSL/TLS encryption and client authentication.

# Problem analysis
In case you have any problem with plantgateway, please check:

- Is you configuration file a valid YAML file?
- Does your Bluetooth dongle support Bluetooh Low Energy? Check with `sudo hcitool lescan`, this should list all Low Energy devices.
- If you have connection issues, please try a system update `sudo apt update; sudo apt dist-upgrade`. This fixes these issues usually.

If all this does not help, please file a bug ticket in github.

# License
Unless stated otherwise all software in this repository is licensed under the Apache License 2.0
http://www.apache.org/licenses/LICENSE-2.0
