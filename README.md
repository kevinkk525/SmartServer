# SmartServer

This is a python3 based server for SmartHomes based on MQTT to provide device configurations and to collect log messages of devices. 
It is designed to be used with my ``Micropython SmartHome Node`` project [pysmartnode](https://) which runs on esp8266 and esp32.
It can of course be used without using that project just for collecting log messages in your MQTT network.

See the README of the main branch for a documentation of how SmartServer works.
This branch provides the same functionality as 2 separate plugins for Homeassistant.
Refer to the Homeassistant custom components installation if you do not know how to integrate it into homeassistant.
Every component is a switch, therefore put all files into a "switch" directory. The file *pysmartnode_devices.py* is just a common helper.
The 2 components provide a switch, that enables or disables its functionality.

1)  Pysmartnode_config_server

This is the component providing the configuration for the devices

2) Pysmartnode_mqtt_log_collector

Simply collects all log messages over mqtt and logs them locally. WARN,ERROR and CRITICAL will also be logged to homeassistant log.


