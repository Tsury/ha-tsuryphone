"""Services for TsuryPhone integration."""
import logging
import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SERVICE_CALL_NUMBER = "call_number"
SERVICE_HANGUP = "hangup"
SERVICE_RING_DEVICE = "ring_device"
SERVICE_RESET_DEVICE = "reset_device"
SERVICE_SET_MAINTENANCE_MODE = "set_maintenance_mode"
SERVICE_SWITCH_TO_CALL_WAITING = "switch_to_call_waiting"
SERVICE_ADD_PHONEBOOK_ENTRY = "add_phonebook_entry"
SERVICE_REMOVE_PHONEBOOK_ENTRY = "remove_phonebook_entry"
SERVICE_ADD_BLOCKED_NUMBER = "add_blocked_number"
SERVICE_REMOVE_BLOCKED_NUMBER = "remove_blocked_number"
SERVICE_SET_DND_HOURS = "set_dnd_hours"
SERVICE_SET_DND_FORCE_ENABLED = "set_dnd_force_enabled"
SERVICE_SET_DND_SCHEDULE_ENABLED = "set_dnd_schedule_enabled"
SERVICE_CLEAR_CALL_LOG = "clear_call_log"

CALL_NUMBER_SCHEMA = vol.Schema({
    vol.Required("device_id"): cv.string,
    vol.Required("number"): cv.string,
})

HANGUP_SCHEMA = vol.Schema({
    vol.Required("device_id"): cv.string,
})

RING_DEVICE_SCHEMA = vol.Schema({
    vol.Required("device_id"): cv.string,
    vol.Optional("duration", default=5000): vol.All(vol.Coerce(int), vol.Range(min=500, max=30000)),
})

RESET_DEVICE_SCHEMA = vol.Schema({
    vol.Required("device_id"): cv.string,
})

SET_MAINTENANCE_MODE_SCHEMA = vol.Schema({
    vol.Required("device_id"): cv.string,
    vol.Required("enabled"): cv.boolean,
})

SWITCH_TO_CALL_WAITING_SCHEMA = vol.Schema({
    vol.Required("device_id"): cv.string,
})

PHONEBOOK_ENTRY_SCHEMA = vol.Schema({
    vol.Required("device_id"): cv.string,
    vol.Required("name"): cv.string,
    vol.Required("number"): cv.string,
})

REMOVE_PHONEBOOK_ENTRY_SCHEMA = vol.Schema({
    vol.Required("device_id"): cv.string,
    vol.Required("name"): cv.string,
})

BLOCKED_NUMBER_SCHEMA = vol.Schema({
    vol.Required("device_id"): cv.string,
    vol.Required("number"): cv.string,
})

SET_DND_HOURS_SCHEMA = vol.Schema({
    vol.Required("device_id"): cv.string,
    vol.Required("start_hour"): vol.All(vol.Coerce(int), vol.Range(min=0, max=23)),
    vol.Required("start_minute"): vol.All(vol.Coerce(int), vol.Range(min=0, max=59)),
    vol.Required("end_hour"): vol.All(vol.Coerce(int), vol.Range(min=0, max=23)),
    vol.Required("end_minute"): vol.All(vol.Coerce(int), vol.Range(min=0, max=59)),
})

SET_DND_ENABLED_SCHEMA = vol.Schema({
    vol.Required("device_id"): cv.string,
    vol.Required("enabled"): cv.boolean,
})

CLEAR_CALL_LOG_SCHEMA = vol.Schema({
    vol.Required("device_id"): cv.string,
})


async def async_setup_services(hass: HomeAssistant) -> None:
    """Set up services for TsuryPhone integration."""

    async def handle_call_number(call: ServiceCall) -> None:
        """Handle call number service."""
        device_id = call.data.get("device_id")
        number = call.data.get("number")
        
        # Find coordinator for this device
        coordinator = None
        for entry_id, coord in hass.data[DOMAIN].items():
            if hasattr(coord, "base_url") and device_id in coord.base_url:
                coordinator = coord
                break
                
        if coordinator:
            await coordinator.call_number(number)
            await coordinator.async_request_refresh()
            _LOGGER.info("Called %s on device %s", number, device_id)
        else:
            _LOGGER.error("Device %s not found", device_id)

    async def handle_ring_device(call: ServiceCall) -> None:
        """Handle ring device service."""
        device_id = call.data.get("device_id")
        duration = call.data.get("duration", 5000)
        
        # Find coordinator for this device
        coordinator = None
        for entry_id, coord in hass.data[DOMAIN].items():
            if hasattr(coord, "base_url") and device_id in coord.base_url:
                coordinator = coord
                break
                
        if coordinator:
            await coordinator.ring_device(duration)
            await coordinator.async_request_refresh()
            _LOGGER.info("Rang device %s for %d ms", device_id, duration)
        else:
            _LOGGER.error("Device %s not found", device_id)

    async def handle_add_phonebook_entry(call: ServiceCall) -> None:
        """Handle add phonebook entry service."""
        device_id = call.data.get("device_id")
        name = call.data.get("name")
        number = call.data.get("number")
        
        # Find coordinator for this device
        coordinator = None
        for entry_id, coord in hass.data[DOMAIN].items():
            if hasattr(coord, "base_url") and device_id in coord.base_url:
                coordinator = coord
                break
                
        if coordinator:
            await coordinator.add_phonebook_entry(name, number)
            await coordinator.async_request_refresh()
            _LOGGER.info("Added phonebook entry %s: %s on device %s", name, number, device_id)
        else:
            _LOGGER.error("Device %s not found", device_id)

    async def handle_remove_phonebook_entry(call: ServiceCall) -> None:
        """Handle remove phonebook entry service."""
        device_id = call.data.get("device_id")
        name = call.data.get("name")
        
        # Find coordinator for this device
        coordinator = None
        for entry_id, coord in hass.data[DOMAIN].items():
            if hasattr(coord, "base_url") and device_id in coord.base_url:
                coordinator = coord
                break
                
        if coordinator:
            await coordinator.remove_phonebook_entry(name)
            await coordinator.async_request_refresh()
            _LOGGER.info("Removed phonebook entry %s on device %s", name, device_id)
        else:
            _LOGGER.error("Device %s not found", device_id)

    async def handle_add_blocked_number(call: ServiceCall) -> None:
        """Handle add blocked number service."""
        device_id = call.data.get("device_id")
        number = call.data.get("number")
        
        # Find coordinator for this device
        coordinator = None
        for entry_id, coord in hass.data[DOMAIN].items():
            if hasattr(coord, "base_url") and device_id in coord.base_url:
                coordinator = coord
                break
                
        if coordinator:
            await coordinator.add_blocked_number(number)
            await coordinator.async_request_refresh()
            _LOGGER.info("Added blocked number %s on device %s", number, device_id)
        else:
            _LOGGER.error("Device %s not found", device_id)

    async def handle_remove_blocked_number(call: ServiceCall) -> None:
        """Handle remove blocked number service."""
        device_id = call.data.get("device_id")
        number = call.data.get("number")
        
        # Find coordinator for this device
        coordinator = None
        for entry_id, coord in hass.data[DOMAIN].items():
            if hasattr(coord, "base_url") and device_id in coord.base_url:
                coordinator = coord
                break
                
        if coordinator:
            await coordinator.remove_blocked_number(number)
            await coordinator.async_request_refresh()
            _LOGGER.info("Removed blocked number %s on device %s", number, device_id)
        else:
            _LOGGER.error("Device %s not found", device_id)

    async def handle_hangup(call: ServiceCall) -> None:
        """Handle hangup service."""
        device_id = call.data.get("device_id")
        
        coordinator = None
        for entry_id, coord in hass.data[DOMAIN].items():
            if hasattr(coord, "base_url") and device_id in coord.base_url:
                coordinator = coord
                break
                
        if coordinator:
            await coordinator.hangup()
            await coordinator.async_request_refresh()
            _LOGGER.info("Hung up call on device %s", device_id)
        else:
            _LOGGER.error("Device %s not found", device_id)

    async def handle_reset_device(call: ServiceCall) -> None:
        """Handle reset device service."""
        device_id = call.data.get("device_id")
        
        coordinator = None
        for entry_id, coord in hass.data[DOMAIN].items():
            if hasattr(coord, "base_url") and device_id in coord.base_url:
                coordinator = coord
                break
                
        if coordinator:
            await coordinator.reset_device()
            await coordinator.async_request_refresh()
            _LOGGER.info("Reset device %s", device_id)
        else:
            _LOGGER.error("Device %s not found", device_id)

    async def handle_set_maintenance_mode(call: ServiceCall) -> None:
        """Handle set maintenance mode service."""
        device_id = call.data.get("device_id")
        enabled = call.data.get("enabled")
        
        coordinator = None
        for entry_id, coord in hass.data[DOMAIN].items():
            if hasattr(coord, "base_url") and device_id in coord.base_url:
                coordinator = coord
                break
                
        if coordinator:
            await coordinator.set_maintenance_mode(enabled)
            await coordinator.async_request_refresh()
            _LOGGER.info("Set maintenance mode to %s on device %s", enabled, device_id)
        else:
            _LOGGER.error("Device %s not found", device_id)

    async def handle_switch_to_call_waiting(call: ServiceCall) -> None:
        """Handle switch to call waiting service."""
        device_id = call.data.get("device_id")
        
        coordinator = None
        for entry_id, coord in hass.data[DOMAIN].items():
            if hasattr(coord, "base_url") and device_id in coord.base_url:
                coordinator = coord
                break
                
        if coordinator:
            await coordinator.switch_to_call_waiting()
            await coordinator.async_request_refresh()
            _LOGGER.info("Switched to call waiting on device %s", device_id)
        else:
            _LOGGER.error("Device %s not found", device_id)

    async def handle_set_dnd_hours(call: ServiceCall) -> None:
        """Handle set DnD hours service."""
        device_id = call.data.get("device_id")
        start_hour = call.data.get("start_hour")
        start_minute = call.data.get("start_minute")
        end_hour = call.data.get("end_hour")
        end_minute = call.data.get("end_minute")
        
        coordinator = None
        for entry_id, coord in hass.data[DOMAIN].items():
            if hasattr(coord, "base_url") and device_id in coord.base_url:
                coordinator = coord
                break
                
        if coordinator:
            await coordinator.set_dnd_hours(start_hour, start_minute, end_hour, end_minute)
            await coordinator.async_request_refresh()
            _LOGGER.info("Set DnD hours %02d:%02d to %02d:%02d on device %s", start_hour, start_minute, end_hour, end_minute, device_id)
        else:
            _LOGGER.error("Device %s not found", device_id)

    async def handle_set_dnd_force_enabled(call: ServiceCall) -> None:
        """Handle set DnD force enabled service."""
        device_id = call.data.get("device_id")
        enabled = call.data.get("enabled")
        
        coordinator = None
        for entry_id, coord in hass.data[DOMAIN].items():
            if hasattr(coord, "base_url") and device_id in coord.base_url:
                coordinator = coord
                break
                
        if coordinator:
            await coordinator.set_dnd_force_enabled(enabled)
            await coordinator.async_request_refresh()
            _LOGGER.info("Set DnD force enabled to %s on device %s", enabled, device_id)
        else:
            _LOGGER.error("Device %s not found", device_id)

    async def handle_set_dnd_schedule_enabled(call: ServiceCall) -> None:
        """Handle set DnD schedule enabled service."""
        device_id = call.data.get("device_id")
        enabled = call.data.get("enabled")
        
        coordinator = None
        for entry_id, coord in hass.data[DOMAIN].items():
            if hasattr(coord, "base_url") and device_id in coord.base_url:
                coordinator = coord
                break
                
        if coordinator:
            await coordinator.set_dnd_schedule_enabled(enabled)
            await coordinator.async_request_refresh()
            _LOGGER.info("Set DnD schedule enabled to %s on device %s", enabled, device_id)
        else:
            _LOGGER.error("Device %s not found", device_id)

    async def handle_clear_call_log(call: ServiceCall) -> None:
        """Handle clear call log service."""
        device_id = call.data.get("device_id")
        
        # Find coordinator for this device
        coordinator = None
        for entry_id, coord in hass.data[DOMAIN].items():
            if hasattr(coord, "base_url") and device_id in coord.base_url:
                coordinator = coord
                break
                
        if coordinator:
            # Clear the call log
            coordinator._call_log = []
            await coordinator._save_call_log()
            await coordinator.async_request_refresh()
            _LOGGER.info("Cleared call log for device %s", device_id)
        else:
            _LOGGER.error("Device %s not found", device_id)

    # Register services
    hass.services.async_register(
        DOMAIN, SERVICE_CALL_NUMBER, handle_call_number, schema=CALL_NUMBER_SCHEMA
    )
    
    hass.services.async_register(
        DOMAIN, SERVICE_HANGUP, handle_hangup, schema=HANGUP_SCHEMA
    )
    
    hass.services.async_register(
        DOMAIN, SERVICE_RING_DEVICE, handle_ring_device, schema=RING_DEVICE_SCHEMA
    )
    
    hass.services.async_register(
        DOMAIN, SERVICE_RESET_DEVICE, handle_reset_device, schema=RESET_DEVICE_SCHEMA
    )
    
    hass.services.async_register(
        DOMAIN, SERVICE_SET_MAINTENANCE_MODE, handle_set_maintenance_mode, schema=SET_MAINTENANCE_MODE_SCHEMA
    )
    
    hass.services.async_register(
        DOMAIN, SERVICE_SWITCH_TO_CALL_WAITING, handle_switch_to_call_waiting, schema=SWITCH_TO_CALL_WAITING_SCHEMA
    )
    
    hass.services.async_register(
        DOMAIN, SERVICE_ADD_PHONEBOOK_ENTRY, handle_add_phonebook_entry, schema=PHONEBOOK_ENTRY_SCHEMA
    )
    
    hass.services.async_register(
        DOMAIN, SERVICE_REMOVE_PHONEBOOK_ENTRY, handle_remove_phonebook_entry, schema=REMOVE_PHONEBOOK_ENTRY_SCHEMA
    )
    
    hass.services.async_register(
        DOMAIN, SERVICE_ADD_BLOCKED_NUMBER, handle_add_blocked_number, schema=BLOCKED_NUMBER_SCHEMA
    )
    
    hass.services.async_register(
        DOMAIN, SERVICE_REMOVE_BLOCKED_NUMBER, handle_remove_blocked_number, schema=BLOCKED_NUMBER_SCHEMA
    )
    
    hass.services.async_register(
        DOMAIN, SERVICE_SET_DND_HOURS, handle_set_dnd_hours, schema=SET_DND_HOURS_SCHEMA
    )
    
    hass.services.async_register(
        DOMAIN, SERVICE_SET_DND_FORCE_ENABLED, handle_set_dnd_force_enabled, schema=SET_DND_ENABLED_SCHEMA
    )
    
    hass.services.async_register(
        DOMAIN, SERVICE_SET_DND_SCHEDULE_ENABLED, handle_set_dnd_schedule_enabled, schema=SET_DND_ENABLED_SCHEMA
    )
    
    hass.services.async_register(
        DOMAIN, SERVICE_CLEAR_CALL_LOG, handle_clear_call_log, schema=CLEAR_CALL_LOG_SCHEMA
    )


async def async_unload_services(hass: HomeAssistant) -> None:
    """Unload services for TsuryPhone integration."""
    hass.services.async_remove(DOMAIN, SERVICE_CALL_NUMBER)
    hass.services.async_remove(DOMAIN, SERVICE_HANGUP)
    hass.services.async_remove(DOMAIN, SERVICE_RING_DEVICE)
    hass.services.async_remove(DOMAIN, SERVICE_RESET_DEVICE)
    hass.services.async_remove(DOMAIN, SERVICE_SET_MAINTENANCE_MODE)
    hass.services.async_remove(DOMAIN, SERVICE_SWITCH_TO_CALL_WAITING)
    hass.services.async_remove(DOMAIN, SERVICE_ADD_PHONEBOOK_ENTRY)
    hass.services.async_remove(DOMAIN, SERVICE_REMOVE_PHONEBOOK_ENTRY)
    hass.services.async_remove(DOMAIN, SERVICE_ADD_BLOCKED_NUMBER)
    hass.services.async_remove(DOMAIN, SERVICE_REMOVE_BLOCKED_NUMBER)
    hass.services.async_remove(DOMAIN, SERVICE_SET_DND_HOURS)
    hass.services.async_remove(DOMAIN, SERVICE_SET_DND_FORCE_ENABLED)
    hass.services.async_remove(DOMAIN, SERVICE_SET_DND_SCHEDULE_ENABLED)
    hass.services.async_remove(DOMAIN, SERVICE_CLEAR_CALL_LOG)
