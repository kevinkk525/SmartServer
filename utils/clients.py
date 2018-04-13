'''
Created on 10.04.2018

@author: Kevin
'''

import json
import yaml
import logging
import logging.handlers
log = logging.getLogger("Clients")
import asyncio
import os
import shutil
try:
    import hjson
    HJSON_AVAILABLE = True
except Exception:
    log.debug("Library hjson not available, .hjson files won't be recognized")
    HJSON_AVAILABLE = False

locks = {}


async def getClient(device, version=None):
    if device not in locks:
        locks[device] = asyncio.Lock()
    await locks[device].acquire()
    return Client(device, version)


def getDeviceName(device):
    #print("getDeviceName: {!s}".format(device))
    if os.path.exists("device_names.yaml") == False:
        f = open("device_names.yaml", "w")
        f.close()
    with open("device_names.yaml", "r") as f:
        try:
            names = yaml.load(f)
            if names is None:
                names = {}
        except Exception as e:
            log.error("Could not load device_names.yaml: {!s}".format(e))
            return device
        if device in names:
            if names[device] is not None:
                return names[device]
            else:
                return device
        else:
            names[device] = None
    with open("device_names.yaml", "w") as f:
        yaml.dump(names, f, default_flow_style=False)
        return device


class Client:
    """ Temporary wrapper representing a client object with logger """

    def __init__(self, device, version=None):
        self.id = device
        self.version = version
        self.log = logging.getLogger(self.id)
        self.log.setLevel(logging.DEBUG)
        oslist = os.listdir(os.getcwd())
        if "Clients" not in oslist:
            os.mkdir("Clients")
        oslist = os.listdir(os.getcwd() + "/Clients")
        self.device_name = getDeviceName(self.id)
        #print("Got device name {!s}".format(self.device_name))
        if self.device_name not in oslist:
            if self.id in oslist:
                shutil.move(os.getcwd() + "/Clients/" + self.id,
                            os.getcwd() + "/Clients/" + self.device_name)
                log.info("Moved device {!r} to {!r}".format(self.id, self.device_name))
            else:
                os.mkdir("Clients/{!s}".format(self.device_name))
                log.info("Created device {!r}".format(self.device_name))
        oslist = os.listdir(os.getcwd() + "/Clients/" + self.device_name)
        if "config" not in oslist:
            os.mkdir(os.getcwd() + "/Clients/" + self.device_name + "/config")
        handler = logging.handlers.RotatingFileHandler("{!s}/Clients/{!s}/{!s}.log".format(
            os.getcwd(), self.device_name, self.device_name), maxBytes=1024 * 1024, backupCount=5)
        formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s')
        handler.setFormatter(formatter)
        self.log.addHandler(handler)
        #log.debug("Created Client object {!s}".format(self.device_name))

    def __del__(self):
        #log.debug("Closing Client object {!s}".format(self.device_name))
        locks[self.id].release()
        handlers = self.log.handlers[:]
        for handler in handlers:
            handler.close()
            self.log.removeHandler(handler)

    def getConfig(self):
        """ At the moment config directory has to have an _order.json file to get dependencies right"""
        log.debug("Get config")
        oslist = os.listdir(os.getcwd() + "/Clients/" + self.device_name)
        if "config.json" in oslist or "config.hjson" in oslist:
            file = "config.hjson" if "config.hjson" in oslist else "config.json"
            if file == "config.hjson" and HJSON_AVAILABLE == False:
                log.critical("Found config.hjson but hjson library unavailable")
                return {"_order": []}
            with open(os.getcwd() + "/Clients/" + self.device_name + "/" + file, "r") as f:
                try:
                    if file.rfind(".hjson") != -1:
                        return dict(hjson.load(f))
                    elif file.rfind(".json") != -1:
                        return json.load(f)
                except Exception as e:
                    log.error("Error loading {!s}: {!s}".format(file, e))
                    return {"_order": []}
        conf = {}
        oslist = os.listdir(os.getcwd() + "/Clients/" + self.device_name + "/config/")
        for file in oslist:
            component = file.rstrip(".json").rstrip(".hjson")
            if file.rfind(".hjson") == -1 or HJSON_AVAILABLE == True:
                with open(os.getcwd() + "/Clients/" + self.device_name + "/config/" + file, "r") as f:
                    try:
                        if file.rfind(".hjson") != -1:
                            com_conf = hjson.load(f)
                            conf[component] = com_conf
                        elif file.rfind(".json") != -1:
                            com_conf = json.load(f)
                            conf[component] = com_conf
                        else:
                            log.error("Unsupported config file format: {!s}".format(f))
                    except:
                        self.log.error(
                            "[SmartServer] Could not load config component {!s}:{!s}".format(component, e))
                        log.error("Could not load config component {!s}:{!s}".format(component, e))
            else:
                log.warn("config file {!s} could not be loaded as hjson library is missing".format(file))
        if "_order" not in conf:
            # easy configs might not need any dependencies
            order = []
            for component in conf:
                order.append(component)
            conf["_order"] = order
        return conf
        # TODO: add possibility to make config with dependencies and automatic resolve
