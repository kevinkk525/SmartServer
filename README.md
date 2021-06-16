# SmartServer

This is a python3 based server for SmartHomes based on MQTT to provide device configurations and to collect log messages of devices. 
It is designed to be used with my ``Micropython SmartHome Node`` project [pysmartnode](https://github.com/kevinkk525/pysmartnode) which runs on esp8266 and esp32.
It can of course be used without using that project just for collecting log messages in your MQTT network.

See the README of the main branch for a documentation of how SmartServer works.
This branch provides the same functionality as 2 separate plugins for Homeassistant.
Refer to the Homeassistant custom components installation if you do not know how to integrate it into homeassistant.
Put all folders/files in the *custom_components* directory of your homeassistant installation. The directory *pysmartnode_devices* is just a common helper.
The 2 components provide a switch that enables or disables its functionality.

1)  Pysmartnode_config_server

This is the component providing the configuration for the devices

2) Pysmartnode_mqtt_log_collector

Simply collects all log messages over mqtt and logs them locally. WARN,ERROR and CRITICAL will also be logged to homeassistant log.

To use this component add this to your configuration.yaml:

```
pysmartnode_devices:

switches:
  - platform: pysmartnode_config
    name: pysmartnode_config_server
  - platform: pysmartnode_log
    name: pysmartnode_mqtt_log_collector
```
