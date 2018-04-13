#!/usr/bin/python
# -*- coding: iso-8859-15 -*-
'''
Created on 17.02.2018

@author: Kevin Köck
'''

__version__ = "1.1"
__updated__ = "2018-04-13"

# changed version of MQTTHandler used in micropython pysmartnode
# uses paho synchronous mqtt client and calling client.loop manually in coro

import json

import config
import logging
from paho.mqtt.client import Client as MQTTClient
from paho.mqtt.client import connack_string
from utils.tree import Tree
import asyncio

log = logging.getLogger("MQTT")


class MQTTHandler(MQTTClient):
    def __init__(self, time_not_looping=0.05):
        self._not_looping = time_not_looping
        self._subscriptions = Tree(config.MQTT_HOME, ["Functions"])
        self.payload_on = ("ON", True, "True")
        self.payload_off = ("OFF", False, "False")
        self._retained = []
        self.mqtt_home = config.MQTT_HOME
        super().__init__()
        self.id = "SmartServer"
        self.enable_logger(log)
        self.username_pw_set(config.MQTT_USER, config.MQTT_PASSWORD)
        self.on_connect = self._connected
        self.on_message = self._execute_sync
        self.on_disconnect = self._on_disconnect
        self.connect(config.MQTT_HOST, 1883, 60)
        asyncio.ensure_future(self._keep_connected())

    def _connected(self, client, userdata, flags, rc):
        log.info("Connection returned result: " + connack_string(rc))
        self._publishDeviceStats()
        self._subscribeTopics()

    def _on_disconnect(self, client, userdata, rc):
        if rc != 0:
            log.warn("Unexpected disconnection.")

    async def _keep_connected(self):
        log.info("Keeping connected")
        while True:
            self.loop(0.05)
            await asyncio.sleep(self._not_looping)

    def _subscribeTopics(self):
        for obj, topic in self._subscriptions.__iter__(with_path=True):
            super().subscribe(topic, qos=1)

    def unsubscribe(self, topic, callback=None):
        if self._isDeviceTopic(topic):
            topic = self.getRealTopic(topic)
        if callback is None:
            log.debug("unsubscribing topic {}".format(topic))
            self._subscriptions.removeObject(topic)
            super().unsubscribe(topic)
        else:
            try:
                cbs = self._subscriptions.getFunctions(topic)
                if type(cbs) not in (tuple, list):
                    self._subscriptions.removeObject(topic)
                    return
                try:
                    cbs = list(cbs)
                    cbs.remove(callback)
                except ValueError:
                    log.warn("Callback to topic {!s} not subscribed".format(topic), local_only=True)
                    return
                self._subscriptions.setFunctions(topic, cbs)
            except ValueError:
                log.warn("Topic {!s} does not exist".format(topic))

    async def subscribe(self, topic, callback, qos=0, check_retained=True):
        if self._isDeviceTopic(topic):
            topic = self.getRealTopic(topic)
        log.debug("Subscribing to topic {}".format(topic))
        self._subscriptions.addObject(topic, callback)
        if check_retained:
            if topic[-4:] == "/set":
                # subscribe to topic without /set to get retained message for this topic state
                # this is done additionally to the retained topic with /set in order to recreate
                # the current state and then get new instructions in /set
                state_topic = topic[:-4]
                self._retained.append(state_topic)
                self._subscriptions.addObject(state_topic, callback)
                super().subscribe(state_topic, qos)
                await self._await_retained(state_topic, callback, True)
                # to give retained state time to process before adding /set subscription
            self._retained.append(topic)
        super().subscribe(topic, qos)
        if check_retained:
            asyncio.ensure_future(self._await_retained(topic, callback))

    def _publishDeviceStats(self):
        pass

    def getDeviceTopic(self, attrib, is_request=False):
        if is_request:
            attrib += "/set"
        return ".{}".format(attrib)

    def _isDeviceTopic(self, topic):
        if topic[:1] == ".":
            return True
        return False

    def getRealTopic(self, device_topic):
        if device_topic[:1] != ".":
            raise ValueError("DeviceTopic does not start with .")
        return "{}/{}/{}".format(self.mqtt_home, self.id, device_topic[1:])

    async def _await_retained(self, topic, cb=None, remove_after=False):
        st = 0
        while topic in self._retained and st <= 8:
            await asyncio.sleep(0.1)
            st += 1
        try:
            log.debug("removing retained topic {}".format(topic))
            self._retained.remove(topic)
        except ValueError:
            pass
        if remove_after:
            self.unsubscribe(topic, cb)

    def _execute_sync(self, client, userdata, msg):
        """mqtt library only handles sync callbacks so add it to async loop"""
        asyncio.ensure_future(self._execute(msg.topic, msg.payload, msg.retain))

    async def _execute(self, topic, msg, retain):
        log.debug("mqtt execution: {!s} {!s}".format(topic, msg))
        msg = msg.decode()
        try:
            msg = json.loads(msg)
        except:
            pass  # maybe not a json string, no way of knowing
        cb = None
        if topic in self._retained:
            retain = True
        else:
            for topicR in self._retained:
                if topicR[-1:] == "#":
                    if topic.find(topicR[:-1]) != -1:
                        retain = True
        if retain:
            try:
                cb = self._subscriptions.getFunctions(topic + "/set")
            except IndexError:
                try:
                    cb = self._subscriptions.getFunctions(topic)
                except IndexError:
                    pass
        if cb is None:
            try:
                cb = self._subscriptions.getFunctions(topic)
            except IndexError:
                log.warn("No cb found for topic {!s}".format(topic))
        if cb:
            for callback in cb if (type(cb) == list or type(cb) == tuple) else [cb]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        res = await callback(topic=topic, msg=msg, retain=retain)
                    else:
                        res = callback(topic=topic, msg=msg, retain=retain)
                    if not retain:
                        if (type(res) == int and res is not None) or res == True:
                            # so that an integer 0 is interpreted as a result to send back
                            if res == True and type(res) != int:
                                res = msg
                                # send original msg back
                            if topic[-4:] == "/set":
                                # if a /set topic is found, send without /set
                                self.publish(topic[:-4], res, retain=True)
                except Exception as e:
                    log.error("Error executing {!s} mqtt topic {!r}: {!s}".format(
                        "retained " if retain else "", topic, e))
            if retain and topic[-2:] != "/#":
                # only remove if it is not a wildcard topic to allow other topics
                # to handle retained messages belonging to this wildcard
                try:
                    self._retained.remove(topic)
                except ValueError:
                    pass
                    # already removed by _await_retained

    def publish(self, topic, msg, retain=False, qos=0):
        if type(msg) == dict or type(msg) == list:
            msg = json.dumps(msg)
        elif type(msg) != str:
            msg = str(msg)
        if self._isDeviceTopic(topic):
            topic = self.getRealTopic(topic)
        super().publish(topic, msg, retain=retain, qos=qos)
