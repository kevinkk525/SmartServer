"""
Support for MQTT log message collection.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/pysmartnode_mqtt_log_collector.switch/
"""

__author = "Kevin Köck"

__version__ = "1.0.2"
__updated__ = "2019-04-25"

import asyncio
import logging
import json
from typing import Optional

import voluptuous as vol

from homeassistant.core import callback
from homeassistant.components import mqtt
from homeassistant.components.switch import SwitchDevice, PLATFORM_SCHEMA
from homeassistant.const import CONF_NAME
from homeassistant.helpers.script import Script
from homeassistant.components.mqtt import CONF_COMMAND_TOPIC
from .. import pysmartnode_devices
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

CONF_OFF_ACTION = "turn_off"
CONF_ON_ACTION = "turn_on"
CONF_UNIQUE_ID = 'unique_id'
DEFAULT_NAME = 'Pysmartnode mqtt log collector'

DEPENDENCIES = ['mqtt']

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    # Integrations shouldn't never expose unique_id through configuration
    # this here is an exception because MQTT is a msg transport, not a protocol
    vol.Optional(CONF_UNIQUE_ID):                  cv.string,
    vol.Optional(CONF_OFF_ACTION):                 cv.SCRIPT_SCHEMA,
    vol.Optional(CONF_ON_ACTION):                  cv.SCRIPT_SCHEMA,
})


@asyncio.coroutine
def async_setup_platform(hass, config, async_add_entities,
                         discovery_info=None):
    """Set up the MQTT binary sensor."""
    if discovery_info is not None:
        config = PLATFORM_SCHEMA(discovery_info)

    async_add_entities([PysmartnodeMQTTLogCollector(
        hass,
        config.get(CONF_NAME),
        config.get(CONF_COMMAND_TOPIC),
        config.get(CONF_UNIQUE_ID),
        config.get(CONF_ON_ACTION),
        config.get(CONF_OFF_ACTION)
    )])


class PysmartnodeMQTTLogCollector(SwitchDevice):
    """Representation of a pysmartnode_mqtt_log_collector."""

    def __init__(self, hass, name, command_topic,
                 unique_id: Optional[str], on_action, off_action):
        """Initialize the mqtt log collector."""
        self._name = name
        self._state = True
        self._command_topic = command_topic or "home/log/#"
        self._unique_id = unique_id
        self._off_script = Script(hass, off_action) if off_action else None
        self._on_script = Script(hass, on_action) if on_action else None

    async def _receive_log(self, device, level, msg):
        client = await pysmartnode_devices.getClient(self.hass, device)
        if level not in ["critical", "error", "warn", "info", "debug"]:
            _LOGGER.error("Client {!s}, Log level not supported: {!s}".format(device, level))
            client.log.error("[{!s}] Loglevel not supported: {!s}".format(self._name, level))
            return False
        clg = getattr(client.log, level)
        clg(msg)

    @callback
    def _command_message_received(self, msg):
        """Handle a new received MQTT state message."""
        if self._state is False:
            return  # component not active
        # workaround for bug https://github.com/home-assistant/home-assistant/issues/16354
        if msg.topic.find("home/log/") == -1:
            return
        #
        topic = msg.topic.split("/")
        if len(topic) != len(self._command_topic.split("/")) + 1:
            _LOGGER.error("Unsupported logging topic: {!s}".format(topic))
            return
        level = topic[len(self._command_topic.split("/")) - 1]
        device = topic[len(self._command_topic.split("/"))]
        asyncio.ensure_future(self._receive_log(device, level, msg.payload))

    @asyncio.coroutine
    def async_added_to_hass(self):
        """Subscribe mqtt events."""

        yield from mqtt.async_subscribe(
            self.hass, self._command_topic, self._command_message_received, qos=1)

    @property
    def should_poll(self):
        """Return the polling state."""
        return False

    @property
    def name(self):
        """Return the name of the switch."""
        return self._name

    @property
    def is_on(self):
        """Return true if switch is on."""
        return self._state

    @property
    def unique_id(self):
        """Return a unique ID."""
        return self._unique_id

    def turn_on(self, **kwargs):
        self._state = True
        if self._on_script is not None:
            self._on_script.run()
        self.async_schedule_update_ha_state()

    def turn_off(self, **kwargs):
        self._state = False
        if self._off_script is not None:
            self._off_script.run()
        self.async_schedule_update_ha_state()
