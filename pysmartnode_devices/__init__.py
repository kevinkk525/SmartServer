__author = "Kevin Köck"

__version__ = "1.0.2"
__updated__ = "2018-09-01"

import json
import yaml
import logging
import logging.handlers
import asyncio
import os
import shutil

locks = {}

log = logging.getLogger("pysmartnode_devices")

DEVICE_DIR_NAME = "pysmartnode_devices"
DEVICE_NAMES_FILE = "pysmartnode_device_names.yaml"


async def getClient(hass, device, version=None):
    if device not in locks:
        locks[device] = asyncio.Lock()
    await locks[device].acquire()
    return Client(hass, device, version)


def getDeviceName(hass, device):
    # print("getDeviceName: {!s}".format(device))
    if os.path.exists(os.path.join(hass.config.config_dir,
                                   DEVICE_NAMES_FILE)) is False:
        f = open(os.path.join(hass.config.config_dir, DEVICE_NAMES_FILE), "w")
        f.close()
    with open(os.path.join(hass.config.config_dir, DEVICE_NAMES_FILE), "r") as f:
        try:
            names = yaml.load(f)
            if names is None:
                names = {}
        except Exception as e:
            log.error("Could not load {!s}.yaml: {!s}".format(DEVICE_NAMES_FILE, e))
            return device
        if device in names:
            if names[device] is not None:
                return names[device]
            else:
                return device
        else:
            names[device] = None
    with open(os.path.join(hass.config.config_dir, DEVICE_NAMES_FILE), "w") as f:
        yaml.dump(names, f, default_flow_style=False)
        return device


class Client:
    """ Temporary wrapper representing a client object with logger """

    def __init__(self, hass, device, version=None):
        self.hass = hass
        self.id = device
        self.version = version
        if os.path.exists(os.path.join(hass.config.config_dir,
                                       DEVICE_DIR_NAME)) is False:
            os.mkdir(os.path.join(hass.config.config_dir, DEVICE_DIR_NAME))
        oslist = os.listdir(os.path.join(hass.config.config_dir, DEVICE_DIR_NAME))
        self.device_name = getDeviceName(hass, self.id)
        self.log = logging.getLogger("{!s}.{!s}".format(__name__, self.device_name))
        ###
        # has no effect, still gets logged to homeassistant log
        handlers = self.log.handlers[:]
        for handler in handlers:
            handler.close()
            self.log.removeHandler(handler)
        self.log.setLevel(logging.DEBUG)
        ###
        # print("Got device name {!s}".format(self.device_name))
        if self.device_name not in oslist:
            if self.id in oslist:
                shutil.move(os.path.join(hass.config.config_dir,
                                         DEVICE_DIR_NAME, self.id),
                            os.path.join(hass.config.config_dir,
                                         DEVICE_DIR_NAME,
                                         self.device_name))
                shutil.move(os.path.join(hass.config.config_dir,
                                         DEVICE_DIR_NAME, self.device_name,
                                         "{!s}.log".format(self.id)),
                            os.path.join(hass.config.config_dir,
                                         DEVICE_DIR_NAME,
                                         self.device_name,
                                         "{!s}.log".format(self.device_name)))
                log.debug("Moved device {!r} to {!r}".format(self.id,
                                                             self.device_name))
            else:
                os.mkdir(os.path.join(hass.config.config_dir, DEVICE_DIR_NAME,
                                      self.device_name))
                log.debug("Created device {!r}".format(self.device_name))
        oslist = os.listdir(os.path.join(hass.config.config_dir, DEVICE_DIR_NAME,
                                         self.device_name))
        if "config" not in oslist:
            os.mkdir(os.path.join(hass.config.config_dir, DEVICE_DIR_NAME,
                                  self.device_name, "config"))
        handler = logging.handlers.RotatingFileHandler(os.path.join(
            hass.config.config_dir, DEVICE_DIR_NAME, self.device_name,
            "{!s}.log".format(self.device_name)), maxBytes=100 * 1024,
            backupCount=5)
        formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s')
        handler.setFormatter(formatter)
        self.log.addHandler(handler)
        # log.debug("Created Client object {!s}".format(self.device_name))

    def __del__(self):
        # log.debug("Closing Client object {!s}".format(self.device_name))
        locks[self.id].release()
        handlers = self.log.handlers[:]
        for handler in handlers:
            handler.close()
            self.log.removeHandler(handler)

    def getConfig(self):
        import hjson
        log.debug("Get config")
        oslist = os.listdir(os.path.join(self.hass.config.config_dir,
                                         DEVICE_DIR_NAME, self.device_name))
        if "config.json" in oslist or "config.hjson" in oslist:
            file = "config.hjson" if "config.hjson" in oslist else "config.json"
            with open(os.path.join(self.hass.config.config_dir, DEVICE_DIR_NAME,
                                   self.device_name, file), "r") as f:
                try:
                    if file.rfind(".hjson") != -1:
                        return dict(hjson.load(f))
                    elif file.rfind(".json") != -1:
                        return json.load(f)
                except Exception as e:
                    log.error("Error loading {!s}: {!s}".format(file, e))
                    return {"_order": []}
        conf = {}
        oslist = os.listdir(os.path.join(self.hass.config.config_dir, DEVICE_DIR_NAME,
                                         self.device_name, "config"))
        for file in oslist:
            component = file.rstrip(".json").rstrip(".hjson")
            with open(os.path.join(self.hass.config.config_dir, DEVICE_DIR_NAME,
                                   self.device_name, "config", file), "r") as f:
                try:
                    if file.rfind(".hjson") != -1:
                        com_conf = hjson.load(f)
                        conf[component] = com_conf
                    elif file.rfind(".json") != -1:
                        com_conf = json.load(f)
                        conf[component] = com_conf
                    else:
                        log.error("Unsupported config file format: {!s}".format(f))
                except Exception as e:
                    self.log.error(
                        "[SmartServer] Could not load config component "
                        "{!s}:{!s}".format(component, e))
                    log.error("Could not load config component "
                              "{!s}:{!s}".format(component, e))
        # _order is being added at device anyway actually
        if "_order" not in conf:
            # easy configs might not need any dependencies
            order = []
            for component in conf:
                order.append(component)
            conf["_order"] = order
        return conf
        # TODO: add possibility to make config with dependencies and automatic resolve
