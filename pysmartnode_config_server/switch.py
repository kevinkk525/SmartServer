"""
Support for MQTT SmartServer providing device configurations.
"""

__author = "Kevin Köck"

__version__ = "1.0.5"
__updated__ = "2019-07-13"

import asyncio
import logging
import json
from typing import Optional

import voluptuous as vol

from homeassistant.core import callback
from homeassistant.components import mqtt
from homeassistant.components.switch import SwitchDevice, PLATFORM_SCHEMA
from homeassistant.const import (CONF_NAME, CONF_VALUE_TEMPLATE)
from homeassistant.helpers.script import Script
from homeassistant.components.mqtt import (
    CONF_COMMAND_TOPIC)
from .. import pysmartnode_devices
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

CONF_OFF_ACTION = "turn_off"
CONF_ON_ACTION = "turn_on"
CONF_UNIQUE_ID = 'unique_id'
DEFAULT_NAME = 'Pysmartnode config server'

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

    value_template = config.get(CONF_VALUE_TEMPLATE)
    if value_template is not None:
        value_template.hass = hass

    async_add_entities([PysmartnodeConfigServer(
        hass,
        config.get(CONF_NAME),
        config.get(CONF_COMMAND_TOPIC),
        value_template,
        config.get(CONF_UNIQUE_ID),
        config.get(CONF_ON_ACTION),
        config.get(CONF_OFF_ACTION)
    )])


class PysmartnodeConfigServer(SwitchDevice):
    """Representation of a pysmartnode_config_server."""

    def __init__(self, hass, name, command_topic, value_template,
                 unique_id: Optional[str], on_action, off_action):
        """Initialize the MQTT SmartServer."""
        self._name = name
        self._state = True
        self._command_topic = command_topic or "home/login/+/set"
        self._template = value_template
        self._unique_id = unique_id
        self._off_script = Script(hass, off_action) if off_action else None
        self._on_script = Script(hass, on_action) if on_action else None

    async def _send_config(self, device, version, platform, wait):
        client = await pysmartnode_devices.getClient(self.hass, device, version)
        conf = client.getConfig()
        _LOGGER.debug("Config for {!s}: {!s}".format(device, conf))
        if platform is None:
            mqtt.async_publish(self.hass,
                               "{!s}{!s}".format("home/login/", device),
                               json.dumps(conf), qos=1)
        else:
            i = len(conf["_order"])
            mqtt.async_publish(self.hass, "{!s}{!s}".format("home/login/", device), i, qos=1)
            for component in conf["_order"]:
                await asyncio.sleep(wait)
                mqtt.async_publish(self.hass, "{!s}{!s}/{!s}".format("home/login/", device, component),
                                   json.dumps(conf[component]), qos=1)

    @callback
    def _command_message_received(self, msg):
        """Handle a new received MQTT state message."""
        if self._template is not None:
            payload = self._template.async_render_with_possible_json_value(
                msg.payload)
        if self._state is False:
            return  # component not active
        if msg.topic.rfind("/set") == -1:
            # own answer to a login topic
            return
        device = msg.topic[msg.topic.find("home/login/") +
                           len("home/login/"):
                           msg.topic.rfind("/set")]
        version = msg.payload
        try:
            version, platform, wait = json.loads(version)
        except:
            platform = None
            wait = None
        _LOGGER.debug("Config request from {!s} version {!s} platform {!s}".format(device, version, platform))
        asyncio.ensure_future(self._send_config(device, version, platform, wait))

    @asyncio.coroutine
    def async_added_to_hass(self):
        """Subscribe mqtt events."""
        yield from asyncio.sleep(2) # time to get mqtt set up properly
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
