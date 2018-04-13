# SmartServer

This is a python3 based server for SmartHomes based on MQTT to provide device configurations and to collect log messages of devices. 
It is designed to be used with my ``Micropython SmartHome Node`` project [pysmartnode](https://) which runs on esp8266 and esp32.
It can of course be used without using that project just for collecting log messages in your MQTT network.

## 1. How it works

### Providing configurations

In order to be able to quickly change some settings for my ESP8266/ESP32 I wanted a central place I could easily change some values and the microcontroller would pick it up on reset.
So if a device publishes to ``home/login/<device-id>/set`` the server knows that the device ``<device-id>`` is requesting its configuration, loads it from files and publishes it to ``home/login/<device-id>``.
The structure of the configuration is completely up to you and depends on the implementation on the microcontroller. The server only loads the files and publishes it.
More details about how the configuration is saved can be found under 3.2.

### Collecting log messages

The server listens to the topic ``home/log/#``. Every publish topic should have the structure ``home/log/<log_level>/<device_id>``.
The standard python log levels are supported. Every log messages is being saved to the general log file to have everything in one place as well as to a client log file where only the messages of that clients are saved.

I decided to use this structure for logging messages as it makes it easy to subscribe to all error or critical log messages of all devices without knowing which devices are actually used. That way I could have a MQTT-Client on my phone subscribing to ``home/log/critical/#`` and I will get notified if one device has a serious problem.

## 2. Dependencies

The library depends on the paho mqtt library and python3 as asyncio is used.
If you want to use the [hjson](https://hjson.org/) file syntax, you should have that library installed. I prefer it as it is more readable than json and makes comments possible. 
If hjson is not installed, it will be ignored and no .hjson file will be loaded.
Pyyaml is also needed as the file mapping device-ids to a custom name uses the yaml format as it is easier to read.

So in a short list, this project depends on:

- Python 3
- [paho-mqtt](https://pypi.python.org/pypi/paho-mqtt/1.3.1)
- [pyyaml](https://pypi.python.org/pypi/PyYAML)
- [hjson](https://hjson.org/) (optional)

## 3. Getting started

### 3.1. Configuration

The included ``config_example.py`` can be copied to ``config.py`` otherwise this will be done on the first startup. Change the MQTT configuration as needed.

### 3.2. Providing device configurations

As soon as a device publishes to the configuration request topic ``home/login/<device-id>/set`` a new directory is created within the ``Clients`` directory in the root of the project. The name of this directory defaults to the device-id in the topic. Inside that directory the client log file is created as well as a ``config`` directory.

There are 2 general possibilities to provide a configuration, either by having a ``config.json`` or ``config.hjson`` file in the root of the client directory (not in the config directory) or by providing a file for each component in the config directory.

#### config.hjson / config.json

If this file is provided, the server does not check for files inside the config directory. 
The file will be read and published "as-is" as json, without modifying any of its content.

#### files inside config

This configuration method can be easier as you can just drop off the configuration of a certain component as .json or .hjson and do not need to paste it into a single configuration file.
The server will create a dictionary with the filename (without the extension .json/.hjson) as the key and the content of that file as the value.

Additionally to the component configuration files it is possible to create a file ``_order.(h)json`` that contains a list of the components in the order in which they have to be loaded by the microcontroller. 
Example:

```
[
  i2c
  htu
]
```

This way you can make sure that the dependencies of ``htu`` are matched by loading the component ``i2c`` before htu gets loaded.
If this file is not found, the server adds a generic ``_order`` entry in the dict containing the list of components as value.

### 3.3. Changing a configuration

Changing the configuration of a client is possible at all times as the files are being reloaded every time the server receives a config request or log message for that client.

### 3.4. Changing a device name

As it can be quite challenging to keep in mind which device-id belonged to which device, it is possible to define a custom name in the file ``device_names.yaml`` in the root of the project. You just have to replace the ``null`` after the device-id with the name you would like your device to have.
Once the server receives a new configuration request or log message to that device, the device's configuration directory will be renamed to the name you chose. And so will be the log file. 
Of course the directory can be renamed manually after the name has been put into the device_names.yaml.
