"""Config flow for TsuryPhone integration."""
import logging
from typing import Any, Dict, Optional
import voluptuous as vol
import aiohttp
import asyncio

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
import homeassistant.helpers.config_validation as cv

from .const import (
    DOMAIN, 
    CONF_HOST, 
    CONF_PORT, 
    CONF_HA_SERVER_URL,
    CONF_DEVICE_NAME,
    DEFAULT_PORT,
    DEFAULT_HA_SERVER_PORT,
    DEFAULT_DEVICE_NAME
)

import re

_LOGGER = logging.getLogger(__name__)


def validate_device_name(device_name: str) -> bool:
    """Validate device name format."""
    # Must start with a letter, only lowercase letters, numbers, and dashes
    # Cannot have two sequential dashes or end with dash
    if not device_name:
        return False
    
    # Check basic format: starts with letter, contains only valid chars
    pattern = r'^[a-z][a-z0-9-]*$'
    if not re.match(pattern, device_name):
        _LOGGER.debug("Device name '%s' failed basic pattern check", device_name)
        return False
    
    # Cannot have consecutive dashes
    if '--' in device_name:
        _LOGGER.debug("Device name '%s' contains consecutive dashes", device_name)
        return False
    
    # Cannot end with dash
    if device_name.endswith('-'):
        _LOGGER.debug("Device name '%s' ends with dash", device_name)
        return False
    
    _LOGGER.debug("Device name '%s' is valid", device_name)
    return True


def get_ha_server_url(hass: HomeAssistant) -> str:
    """Get the Home Assistant server URL with port included."""
    # Try to get the external URL first
    if hass.config.external_url:
        return hass.config.external_url
    
    # Fall back to internal URL
    if hass.config.internal_url:
        return hass.config.internal_url
    
    # Last resort - construct from local IP with default port
    return f"http://homeassistant.local:{DEFAULT_HA_SERVER_PORT}"


STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): cv.port,
        vol.Required(CONF_DEVICE_NAME, default=DEFAULT_DEVICE_NAME): cv.string,
    }
)


def get_ha_server_step_schema(hass: HomeAssistant) -> vol.Schema:
    """Get the schema for the HA server configuration step."""
    default_url = get_ha_server_url(hass)
    return vol.Schema(
        {
            vol.Required(CONF_HA_SERVER_URL, default=default_url): cv.string,
        }
    )


async def validate_input(hass: HomeAssistant, data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate the user input allows us to connect."""
    host = data[CONF_HOST]
    port = data[CONF_PORT]
    device_name = data[CONF_DEVICE_NAME]
    
    _LOGGER.debug("Validating input: host=%s, port=%s, device_name=%s", host, port, device_name)
    
    # Validate device name format
    if not validate_device_name(device_name):
        _LOGGER.warning("Device name validation failed for: %s", device_name)
        raise InvalidDeviceName
    
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            url = f"http://{host}:{port}/"
            async with session.get(url) as response:
                response.raise_for_status()
                device_info = await response.json()
                
                # Validate this is actually a TsuryPhone device
                if "device" not in device_info or device_info.get("device") != "tsuryphone":
                    raise InvalidDevice
                
                return {
                    "title": f"TsuryPhone ({device_name})",
                    "device_info": device_info
                }
                
    except asyncio.TimeoutError:
        raise CannotConnect
    except aiohttp.ClientError:
        raise CannotConnect


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for TsuryPhone."""

    VERSION = 1

    def __init__(self):
        """Initialize the config flow."""
        self._device_info = None
        self._device_config = None

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        errors = {}

        try:
            info = await validate_input(self.hass, user_input)
        except CannotConnect:
            errors["base"] = "cannot_connect"
        except InvalidDevice:
            errors["base"] = "invalid_device"
        except InvalidDeviceName:
            errors[CONF_DEVICE_NAME] = "invalid_device_name"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            # Store device info for next step
            self._device_info = info
            self._device_config = user_input
            
            # Move to HA server configuration step
            return await self.async_step_ha_server()

        return self.async_show_form(
            step_id="user", 
            data_schema=vol.Schema({
                vol.Required(CONF_HOST, default=user_input.get(CONF_HOST, "")): cv.string,
                vol.Required(CONF_PORT, default=user_input.get(CONF_PORT, DEFAULT_PORT)): cv.port,
                vol.Required(CONF_DEVICE_NAME, default=user_input.get(CONF_DEVICE_NAME, DEFAULT_DEVICE_NAME)): cv.string,
            }), 
            errors=errors
        )

    async def async_step_ha_server(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle the HA server configuration step."""
        if user_input is None:
            return self.async_show_form(
                step_id="ha_server", 
                data_schema=get_ha_server_step_schema(self.hass),
                description_placeholders={
                    "device_name": self._device_info["title"]
                }
            )

        errors = {}

        try:
            # Combine device and HA server configuration
            combined_config = {**self._device_config, **user_input}
            
            # Send HA server and device name configuration to device
            await self._configure_device(combined_config)
            
            # Create unique ID based on device info
            device_info = self._device_info["device_info"]
            unique_id = f"{self._device_config[CONF_HOST]}_{self._device_config[CONF_PORT]}"
            
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=self._device_info["title"], 
                data=combined_config
            )
            
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception during HA server configuration")
            errors["base"] = "unknown"

        return self.async_show_form(
            step_id="ha_server", 
            data_schema=get_ha_server_step_schema(self.hass),
            errors=errors,
            description_placeholders={
                "device_name": self._device_info["title"]
            }
        )

    async def _configure_device(self, config: Dict[str, Any]) -> None:
        """Configure the HA server URL and device name on the device."""
        host = config[CONF_HOST]
        port = config[CONF_PORT]
        ha_server_url = config[CONF_HA_SERVER_URL]
        device_name = config[CONF_DEVICE_NAME]
        
        # Ensure the URL has a protocol
        if not ha_server_url.startswith(('http://', 'https://')):
            ha_server_url = f"http://{ha_server_url}"
        
        # Send HA server configuration to device
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            url = f"http://{host}:{port}/webhooks"
            data = {"server_url": ha_server_url}
            
            async with session.post(url, json=data) as response:
                response.raise_for_status()
                _LOGGER.info("Successfully configured HA server URL on TsuryPhone device")
        
        # Send device name configuration to device
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            url = f"http://{host}:{port}/action"
            data = {"action": "set_device_name", "device_name": device_name}
            
            async with session.post(url, json=data) as response:
                response.raise_for_status()
                _LOGGER.info("Successfully configured device name on TsuryPhone device: %s", device_name)


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidDevice(HomeAssistantError):
    """Error to indicate device is not a TsuryPhone."""


class InvalidDeviceName(HomeAssistantError):
    """Error to indicate device name format is invalid."""
