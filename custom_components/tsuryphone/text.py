"""Text platform for TsuryPhone."""
import logging
import re
from typing import Any

from homeassistant.components.text import TextEntity, TextMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, MODEL
from .coordinator import TsuryPhoneDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up TsuryPhone text based on a config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities = [
        TsuryPhoneCallNumberText(coordinator),
        TsuryPhoneAddPhonebookText(coordinator),
        TsuryPhoneAddBlockedText(coordinator),
        TsuryPhoneRingPatternText(coordinator),
        TsuryPhoneAddWebhookText(coordinator),
    ]

    async_add_entities(entities)


class TsuryPhoneBaseText(CoordinatorEntity, TextEntity):
    """Base class for TsuryPhone text entities."""

    def __init__(self, coordinator: TsuryPhoneDataUpdateCoordinator, text_type: str) -> None:
        """Initialize the text entity."""
        super().__init__(coordinator)
        self._text_type = text_type
        self._attr_unique_id = f"{coordinator.base_url}_{text_type}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.base_url)},
            "name": "TsuryPhone",
            "manufacturer": MANUFACTURER,
            "model": MODEL,
            "configuration_url": coordinator.base_url,
        }


class TsuryPhoneCallNumberText(TsuryPhoneBaseText):
    """Text entity for calling a specific number."""

    def __init__(self, coordinator: TsuryPhoneDataUpdateCoordinator) -> None:
        """Initialize the text entity."""
        super().__init__(coordinator, "call_number")
        self._attr_name = "Call Custom Number"
        self._attr_icon = "mdi:phone-dial"
        self._attr_mode = TextMode.TEXT
        # More permissive pattern that allows common phone number formats and empty string
        self._attr_pattern = r"^$|^[\d\+\-\(\)\s\.#\*]+$"
        self._attr_native_value = ""
        self._attr_native_max = 25
        self._attr_extra_state_attributes = {
            "description": "Enter phone number to call (e.g., +1234567890 or *67)"
        }

    async def async_set_value(self, value: str) -> None:
        """Set the text value and make the call."""
        # Clean the number (remove spaces, brackets, etc. but keep digits, + and # for special codes)
        clean_number = re.sub(r'[^\d\+#\*]', '', value)
        
        if clean_number:
            try:
                await self.coordinator.call_number(clean_number)
                _LOGGER.info("Called number: %s", clean_number)
                self._attr_native_value = ""  # Clear after calling
                await self.coordinator.async_request_refresh()
            except Exception as err:
                _LOGGER.error("Failed to call number %s: %s", clean_number, err)
                self._attr_native_value = value  # Keep the value if failed
        else:
            self._attr_native_value = ""

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        # Only available when not in a call
        if "status" in self.coordinator.data:
            call = self.coordinator.data["status"].get("call", {})
            return not call.get("active", False)
        return True


class TsuryPhoneAddPhonebookText(TsuryPhoneBaseText):
    """Text entity for adding phonebook entries."""

    def __init__(self, coordinator: TsuryPhoneDataUpdateCoordinator) -> None:
        """Initialize the text entity."""
        super().__init__(coordinator, "add_phonebook")
        self._attr_name = "Add Quick Dial Entry"
        self._attr_icon = "mdi:dialpad"
        self._attr_mode = TextMode.TEXT
        # More flexible pattern for entry number and phone number combinations, allow empty
        self._attr_pattern = r"^$|^.+:\s*.+$"
        self._attr_native_value = ""
        self._attr_native_max = 60
        self._attr_extra_state_attributes = {
            "description": "Format: 'Entry Number: Phone Number' (e.g., '5: +1234567890')"
        }

    async def async_set_value(self, value: str) -> None:
        """Set the text value and add quick dial entry."""
        # Expected format: "Entry Number: Phone Number" (e.g., "5: +1234567890")
        if ":" in value:
            parts = value.split(":", 1)
            if len(parts) == 2:
                entry_number = parts[0].strip()
                phone_number = re.sub(r'[^\d\+#\*]', '', parts[1].strip())
                
                if entry_number and phone_number:
                    try:
                        await self.coordinator.add_phonebook_entry(entry_number, phone_number)
                        _LOGGER.info("Added quick dial entry: %s -> %s", entry_number, phone_number)
                        self._attr_native_value = ""  # Clear after adding
                        await self.coordinator.async_request_refresh()
                    except Exception as err:
                        _LOGGER.error("Failed to add quick dial entry %s: %s", entry_number, err)
                        self._attr_native_value = value  # Keep the value if failed
                else:
                    self._attr_native_value = value
            else:
                self._attr_native_value = value
        else:
            self._attr_native_value = value


class TsuryPhoneRemovePhonebookText(TsuryPhoneBaseText):
    """Text entity for removing phonebook entries."""

    def __init__(self, coordinator: TsuryPhoneDataUpdateCoordinator) -> None:
        """Initialize the text entity."""
        super().__init__(coordinator, "remove_phonebook")
        self._attr_name = "TsuryPhone Remove Phonebook Entry"
        self._attr_icon = "mdi:account-minus"
        self._attr_mode = TextMode.TEXT
        self._attr_native_value = ""
        self._attr_native_max = 30
        self._attr_extra_state_attributes = {
            "description": "Enter the name to remove from phonebook"
        }

    async def async_set_value(self, value: str) -> None:
        """Set the text value and remove phonebook entry."""
        name = value.strip()
        
        if name:
            try:
                await self.coordinator.remove_phonebook_entry(name)
                _LOGGER.info("Removed phonebook entry: %s", name)
                self._attr_native_value = ""  # Clear after removing
                await self.coordinator.async_request_refresh()
            except Exception as err:
                _LOGGER.error("Failed to remove phonebook entry %s: %s", name, err)
                self._attr_native_value = value  # Keep the value if failed
        else:
            self._attr_native_value = ""


class TsuryPhoneAddBlockedText(TsuryPhoneBaseText):
    """Text entity for adding blocked numbers."""

    def __init__(self, coordinator: TsuryPhoneDataUpdateCoordinator) -> None:
        """Initialize the text entity."""
        super().__init__(coordinator, "add_blocked")
        self._attr_name = "Add Blocked Number"
        self._attr_icon = "mdi:phone-off"
        self._attr_mode = TextMode.TEXT
        self._attr_pattern = r"^$|^[\d\+\-\(\)\s\.#\*]+$"
        self._attr_native_value = ""
        self._attr_native_max = 25
        self._attr_extra_state_attributes = {
            "description": "Enter phone number to block"
        }

    async def async_set_value(self, value: str) -> None:
        """Set the text value and add blocked number."""
        # Clean the number (remove spaces, brackets, etc. but keep digits, + and special codes)
        clean_number = re.sub(r'[^\d\+#\*]', '', value)
        
        if clean_number:
            try:
                await self.coordinator.add_blocked_number(clean_number)
                _LOGGER.info("Added blocked number: %s", clean_number)
                self._attr_native_value = ""  # Clear after adding
                await self.coordinator.async_request_refresh()
            except Exception as err:
                _LOGGER.error("Failed to add blocked number %s: %s", clean_number, err)
                self._attr_native_value = value  # Keep the value if failed
        else:
            self._attr_native_value = ""


class TsuryPhoneRemoveBlockedText(TsuryPhoneBaseText):
    """Text entity for removing blocked numbers."""

    def __init__(self, coordinator: TsuryPhoneDataUpdateCoordinator) -> None:
        """Initialize the text entity."""
        super().__init__(coordinator, "remove_blocked")
        self._attr_name = "TsuryPhone Remove Blocked Number"
        self._attr_icon = "mdi:phone-check"
        self._attr_mode = TextMode.TEXT
        self._attr_pattern = r"^$|^[\d\+\-\(\)\s\.#\*]+$"
        self._attr_native_value = ""
        self._attr_native_max = 25
        self._attr_extra_state_attributes = {
            "description": "Enter phone number to unblock"
        }

    async def async_set_value(self, value: str) -> None:
        """Set the text value and remove blocked number."""
        # Clean the number (remove spaces, brackets, etc. but keep digits, + and special codes)
        clean_number = re.sub(r'[^\d\+#\*]', '', value)
        
        if clean_number:
            try:
                await self.coordinator.remove_blocked_number(clean_number)
                _LOGGER.info("Removed blocked number: %s", clean_number)
                self._attr_native_value = ""  # Clear after removing
                await self.coordinator.async_request_refresh()
            except Exception as err:
                _LOGGER.error("Failed to remove blocked number %s: %s", clean_number, err)
                self._attr_native_value = value  # Keep the value if failed
        else:
            self._attr_native_value = ""


class TsuryPhoneRingPatternText(TsuryPhoneBaseText):
    """Text entity for setting ring pattern."""

    def __init__(self, coordinator: TsuryPhoneDataUpdateCoordinator) -> None:
        """Initialize the text entity."""
        super().__init__(coordinator, "ring_pattern")
        self._attr_name = "TsuryPhone Ring Pattern"
        self._attr_icon = "mdi:bell-ring-outline"
        self._attr_mode = TextMode.TEXT
        # Pattern for ring patterns: comma-separated numbers optionally followed by xN for repeats
        self._attr_pattern = r"^$|^(\d+,)*\d+(x\d+)?$"
        self._attr_native_value = "500,500,500,500x3"  # Default pattern
        self._attr_native_max = 50
        self._attr_extra_state_attributes = {
            "description": "Ring pattern (e.g., '500,500,1000,500x2' means ring 500ms, pause 500ms, ring 1000ms, pause 500ms, repeat 2 times)"
        }

    async def async_set_value(self, value: str) -> None:
        """Set the ring pattern."""
        # Store the pattern - it will be used by the ring button
        self._attr_native_value = value if value else "500,500,500,500x3"


class TsuryPhoneAddWebhookText(TsuryPhoneBaseText):
    """Text entity for adding webhook shortcuts."""

    def __init__(self, coordinator: TsuryPhoneDataUpdateCoordinator) -> None:
        """Initialize the text entity."""
        super().__init__(coordinator, "add_webhook")
        self._attr_name = "TsuryPhone Add Webhook Shortcut"
        self._attr_icon = "mdi:webhook"
        self._attr_mode = TextMode.TEXT
        self._attr_pattern = r"^$|^[a-zA-Z0-9]+:https?://.+$"
        self._attr_native_value = ""
        self._attr_native_max = 200
        self._attr_extra_state_attributes = {
            "description": "Add webhook shortcut as 'name:url' (e.g., 'alarm:http://example.com/webhook')"
        }

    async def async_set_value(self, value: str) -> None:
        """Set the text value and add webhook shortcut."""
        if value and ':' in value:
            try:
                name, url = value.split(':', 1)
                name = name.strip()
                url = url.strip()
                
                if name and url:
                    await self.coordinator.add_webhook_shortcut(name, url)
                    _LOGGER.info("Added webhook shortcut: %s -> %s", name, url)
                    self._attr_native_value = ""  # Clear after adding
                    await self.coordinator.async_request_refresh()
                else:
                    self._attr_native_value = value  # Keep if invalid format
            except Exception as err:
                _LOGGER.error("Failed to add webhook shortcut %s: %s", value, err)
                self._attr_native_value = value  # Keep the value if failed
        else:
            self._attr_native_value = ""
