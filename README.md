# plantgateway
Bluetooth LE to mqtt gateway for Xiaomi Mi plant sensors.

# Use case
For many setups the Xiaomi Mi plant sensors are too far away from your home server to connect directly 
via Bluetooth LE. In such a scenario the plantgatway will poll the data from a list of Xiaomi Mi plant sensors
via Bluetooth LE using [miflora](https://github.com/open-homeautomation/miflora).
The data is then published via mqtt to your home automation server.

The plantgateway is intended to be run on a small Linux machine line a [Raspberry Pi](https://www.raspberrypi.org/)
or a [C.H.I.P](https://getchip.com/) that has both Bluetooth LE and WiFi.

# installation
* install [python 3.5](https://www.python.org/) (or above)
* install [pip](https://pip.pypa.io/en/stable/installing/)
* install the plant gateway from github:
```
pip install https://github.com/ChristianKuehnel/plantgateway/archive/master.zip
```
or if you have multiple python and pip installations:
```
pip3 install https://github.com/ChristianKuehnel/plantgateway/archive/master.zip
```

# configuration
Copy the plantgw.yaml (in this repository) to your home directory and rename it to ".plantgw.yaml".
Then change this file to match your requirements.

# execution
After the installation with pip you can simply run the tool from the command line:
```
plantgateway
```
There are no command line parameters and there is no interaction required.
You probably want to add the script to your cron tab to be executed in regular intervals (e.q. every hour).
