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
        TsuryPhoneRemovePhonebookText(coordinator),
        TsuryPhoneAddScreenedText(coordinator),
        TsuryPhoneRemoveScreenedText(coordinator),
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
        self._attr_name = "TsuryPhone Call Custom Number"
        self._attr_icon = "mdi:phone-dial"
        self._attr_mode = TextMode.TEXT
        # More permissive pattern that allows common phone number formats
        self._attr_pattern = r"^[\d\+\-\(\)\s\.#\*]+$"
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
        self._attr_name = "TsuryPhone Add Phonebook Entry"
        self._attr_icon = "mdi:account-plus"
        self._attr_mode = TextMode.TEXT
        # More flexible pattern for name and number combinations
        self._attr_pattern = r"^.+:\s*.+$"
        self._attr_native_value = ""
        self._attr_native_max = 60
        self._attr_extra_state_attributes = {
            "description": "Format: 'Name: Number' (e.g., 'John Smith: +1234567890')"
        }

    async def async_set_value(self, value: str) -> None:
        """Set the text value and add phonebook entry."""
        # Expected format: "Name: Number"
        if ":" in value:
            parts = value.split(":", 1)
            if len(parts) == 2:
                name = parts[0].strip()
                number = re.sub(r'[^\d\+#\*]', '', parts[1].strip())
                
                if name and number:
                    try:
                        await self.coordinator.add_phonebook_entry(name, number)
                        _LOGGER.info("Added phonebook entry: %s -> %s", name, number)
                        self._attr_native_value = ""  # Clear after adding
                        await self.coordinator.async_request_refresh()
                    except Exception as err:
                        _LOGGER.error("Failed to add phonebook entry %s: %s", name, err)
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


class TsuryPhoneAddScreenedText(TsuryPhoneBaseText):
    """Text entity for adding screened numbers."""

    def __init__(self, coordinator: TsuryPhoneDataUpdateCoordinator) -> None:
        """Initialize the text entity."""
        super().__init__(coordinator, "add_screened")
        self._attr_name = "TsuryPhone Add Blocked Number"
        self._attr_icon = "mdi:phone-off"
        self._attr_mode = TextMode.TEXT
        self._attr_pattern = r"^[\d\+\-\(\)\s\.#\*]+$"
        self._attr_native_value = ""
        self._attr_native_max = 25
        self._attr_extra_state_attributes = {
            "description": "Enter phone number to block"
        }

    async def async_set_value(self, value: str) -> None:
        """Set the text value and add screened number."""
        # Clean the number (remove spaces, brackets, etc. but keep digits, + and special codes)
        clean_number = re.sub(r'[^\d\+#\*]', '', value)
        
        if clean_number:
            try:
                await self.coordinator.add_screened_number(clean_number)
                _LOGGER.info("Added screened number: %s", clean_number)
                self._attr_native_value = ""  # Clear after adding
                await self.coordinator.async_request_refresh()
            except Exception as err:
                _LOGGER.error("Failed to add screened number %s: %s", clean_number, err)
                self._attr_native_value = value  # Keep the value if failed
        else:
            self._attr_native_value = ""


class TsuryPhoneRemoveScreenedText(TsuryPhoneBaseText):
    """Text entity for removing screened numbers."""

    def __init__(self, coordinator: TsuryPhoneDataUpdateCoordinator) -> None:
        """Initialize the text entity."""
        super().__init__(coordinator, "remove_screened")
        self._attr_name = "TsuryPhone Remove Blocked Number"
        self._attr_icon = "mdi:phone-check"
        self._attr_mode = TextMode.TEXT
        self._attr_pattern = r"^[\d\+\-\(\)\s\.#\*]+$"
        self._attr_native_value = ""
        self._attr_native_max = 25
        self._attr_extra_state_attributes = {
            "description": "Enter phone number to unblock"
        }

    async def async_set_value(self, value: str) -> None:
        """Set the text value and remove screened number."""
        # Clean the number (remove spaces, brackets, etc. but keep digits, + and special codes)
        clean_number = re.sub(r'[^\d\+#\*]', '', value)
        
        if clean_number:
            try:
                await self.coordinator.remove_screened_number(clean_number)
                _LOGGER.info("Removed screened number: %s", clean_number)
                self._attr_native_value = ""  # Clear after removing
                await self.coordinator.async_request_refresh()
            except Exception as err:
                _LOGGER.error("Failed to remove screened number %s: %s", clean_number, err)
                self._attr_native_value = value  # Keep the value if failed
        else:
            self._attr_native_value = ""
