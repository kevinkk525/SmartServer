#!/usr/bin/python3
# -*- coding: iso-8859-15 -*-
'''
Created on 25.03.2018

@author: Kevin Köck
'''

__version__ = "1.3.1"
__updated__ = "2018-04-24"

import os
import json

os.chdir(os.path.dirname(os.path.realpath(__file__)))
if "config.py" not in os.listdir():
    import shutil

    shutil.copy("config_example.py", "config.py")
import config
from utils import logging_config
from utils.mqtt import MQTTHandler
import asyncio
import logging
from utils import clients

log = logging.getLogger("Main")

loop = asyncio.get_event_loop()
mqtt = MQTTHandler()


async def sendConfig(topic, msg, retain):
    log.debug("sendConfig main: {!s},{!s}".format(topic, msg))
    if topic == "{!s}/login".format(config.MQTT_HOME):
        # compatibility mode, gets dict: {"command": "login", "id": self.id, "version": config.VERSION})
        # version <3.4.0
        log.debug("config compatibility")
        device = msg["id"]
        version = msg["version"]
    elif topic.rfind("/set") == -1:
        # own answer to a login topic
        return
    else:
        log.debug("config requested")
        device = topic[topic.find("{!s}/login/".format(config.MQTT_HOME)) +
                       len("{!s}/login/".format(config.MQTT_HOME)):topic.rfind("/set")]
        version = msg
        try:
            version, platform, wait = json.loads(version)
        except:
            platform = None
            wait = None
    log.info(
        "Config request from {!s} version {!s} platform {!s}".format(device, version, platform))
    client = await clients.getClient(device, version)
    conf = client.getConfig()
    log.debug("Config for {!s}: {!s}".format(device, conf))
    if platform is None:
        mqtt.publish("{!s}/login/{!s}".format(config.MQTT_HOME, device),
                     conf, retain=False, qos=1)
    else:
        i = len(conf["_order"])
        mqtt.publish("{!s}/login/{!s}".format(config.MQTT_HOME, device), i, qos=1)
        for component in conf["_order"]:
            await asyncio.sleep(wait)
            mqtt.publish("{!s}/login/{!s}/{!s}".format(config.MQTT_HOME, device, component),
                         json.dumps(conf[component]), qos=1)


async def getLog(topic, msg, retain):
    topic = topic.split("/")
    if len(topic) < 4:
        log.error("Unsupported logging topic: {!s}".format(topic))
        return
    level = topic[2]
    device = topic[3]
    client = await clients.getClient(device)
    if level not in ["critical", "error", "warn", "info", "debug"]:
        log.error("Client {!s}, Loglevel not supported: {!s}".format(device, level))
        client.log.error("[SmartServer] Loglevel not supported: {!s}".format(level))
        return False
    clg = getattr(client.log, level)
    clg(msg)


async def main():
    await mqtt.subscribe("{!s}/login/#".format(config.MQTT_HOME), sendConfig, check_retained=False)
    await mqtt.subscribe("{!s}/log/#".format(config.MQTT_HOME), getLog, check_retained=False)
    log.info("Starting main loop")
    while True:
        await asyncio.sleep(1)


try:
    loop.run_until_complete(main())
except KeyboardInterrupt:
    loop.close()
except Exception as e:
    log.info("Got Exception: {!s}".format(e))
log.info("Stopping SmartServer")
