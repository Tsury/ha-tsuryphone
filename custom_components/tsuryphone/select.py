"""Select platform for TsuryPhone."""
import logging
from typing import Any, List, Optional

from homeassistant.components.select import SelectEntity
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
    """Set up TsuryPhone select based on a config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities = [
        TsuryPhoneCallSelect(coordinator),
        TsuryPhoneScreenedNumbersSelect(coordinator),
        TsuryPhoneRingDurationSelect(coordinator),
        TsuryPhonePhonebookManageSelect(coordinator),
    ]

    async_add_entities(entities)


class TsuryPhoneBaseSelect(CoordinatorEntity, SelectEntity):
    """Base class for TsuryPhone selects."""

    def __init__(self, coordinator: TsuryPhoneDataUpdateCoordinator, select_type: str) -> None:
        """Initialize the select."""
        super().__init__(coordinator)
        self._select_type = select_type
        self._attr_unique_id = f"{coordinator.base_url}_{select_type}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.base_url)},
            "name": "TsuryPhone",
            "manufacturer": MANUFACTURER,
            "model": MODEL,
            "configuration_url": coordinator.base_url,
        }


class TsuryPhoneCallSelect(TsuryPhoneBaseSelect):
    """Select entity for calling phonebook entries or entering custom numbers."""

    def __init__(self, coordinator: TsuryPhoneDataUpdateCoordinator) -> None:
        """Initialize the select."""
        super().__init__(coordinator, "call_phonebook")
        self._attr_name = "TsuryPhone Quick Call"
        self._attr_icon = "mdi:phone-dial"
        
    @property
    def options(self) -> List[str]:
        """Return the list of available options."""
        options = ["Select to call..."]
        
        # Add phonebook entries
        if "phonebook" in self.coordinator.data:
            entries = self.coordinator.data["phonebook"].get("entries", [])
            if entries:
                options.append("--- Phonebook ---")
                options.extend([f"{entry['name']} ({entry['number']})" for entry in entries])
        
        # Add common numbers/shortcuts
        options.extend([
            "--- Quick Actions ---",
            "📞 Call custom number...",
            "🔔 Ring device (5s)",
            "🔄 Refresh data",
        ])
        
        return options

    @property
    def current_option(self) -> Optional[str]:
        """Return the current option."""
        return "Select to call..."

    async def async_select_option(self, option: str) -> None:
        """Change the selected option and perform action."""
        if option in ["Select to call...", "--- Phonebook ---", "--- Quick Actions ---"]:
            return
            
        # Handle phonebook calls
        if "(" in option and ")" in option and not option.startswith("📞"):
            start = option.rfind("(") + 1
            end = option.rfind(")")
            number = option[start:end]
            await self.coordinator.call_number(number)
            _LOGGER.info("Called %s via phonebook selection", number)
        
        # Handle quick actions
        elif option == "📞 Call custom number...":
            # This will prompt user to use the text input entity
            _LOGGER.info("Use 'TsuryPhone Call Number' text input to enter custom number")
        
        elif option == "🔔 Ring device (5s)":
            await self.coordinator.ring_device(5000)
            _LOGGER.info("Rang device for 5 seconds")
        
        elif option == "🔄 Refresh data":
            await self.coordinator.async_request_refresh()
            _LOGGER.info("Refreshed TsuryPhone data")

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        # Only available when not in a call
        if "status" in self.coordinator.data:
            call = self.coordinator.data["status"].get("call", {})
            return not call.get("active", False)
        return True


class TsuryPhoneScreenedNumbersSelect(TsuryPhoneBaseSelect):
    """Select entity for managing screened numbers."""

    def __init__(self, coordinator: TsuryPhoneDataUpdateCoordinator) -> None:
        """Initialize the select."""
        super().__init__(coordinator, "screened_numbers")
        self._attr_name = "TsuryPhone Blocked Numbers"
        self._attr_icon = "mdi:phone-off"
        
    @property
    def options(self) -> List[str]:
        """Return the list of available options."""
        options = ["Manage blocked numbers..."]
        if "screened" in self.coordinator.data:
            entries = self.coordinator.data["screened"].get("numbers", [])
            if entries:
                options.append("--- Blocked Numbers ---")
                for entry in entries:
                    options.append(f"🚫 {entry}")
                    options.append(f"✅ Unblock {entry}")
            else:
                options.append("No blocked numbers")
        
        options.extend([
            "--- Actions ---",
            "➕ Add blocked number...",
        ])
        
        return options

    @property
    def current_option(self) -> Optional[str]:
        """Return the current option."""
        return "Manage blocked numbers..."

    async def async_select_option(self, option: str) -> None:
        """Change the selected option and perform action."""
        if option in ["Manage blocked numbers...", "--- Blocked Numbers ---", "--- Actions ---", "No blocked numbers"]:
            return
            
        if option.startswith("✅ Unblock "):
            # Remove the number from screened list
            number = option.replace("✅ Unblock ", "")
            await self.coordinator.remove_screened_number(number)
            _LOGGER.info("Unblocked number: %s", number)
            await self.coordinator.async_request_refresh()
        
        elif option == "➕ Add blocked number...":
            # This will prompt user to use the text input entity
            _LOGGER.info("Use 'TsuryPhone Add Screened Number' text input to block a number")


class TsuryPhoneRingDurationSelect(TsuryPhoneBaseSelect):
    """Select entity for custom ring duration."""

    def __init__(self, coordinator: TsuryPhoneDataUpdateCoordinator) -> None:
        """Initialize the select."""
        super().__init__(coordinator, "ring_duration")
        self._attr_name = "TsuryPhone Ring Duration"
        self._attr_icon = "mdi:timer"
        self._current_duration = "5 seconds"
        
    @property
    def options(self) -> List[str]:
        """Return the list of available options."""
        return [
            "1 second",
            "2 seconds", 
            "3 seconds",
            "5 seconds",
            "10 seconds",
            "15 seconds",
            "30 seconds",
        ]

    @property
    def current_option(self) -> Optional[str]:
        """Return the current option."""
        return self._current_duration

    async def async_select_option(self, option: str) -> None:
        """Change the selected option and ring for that duration."""
        self._current_duration = option
        
        # Convert option to milliseconds
        duration_map = {
            "1 second": 1000,
            "2 seconds": 2000,
            "3 seconds": 3000,
            "5 seconds": 5000,
            "10 seconds": 10000,
            "15 seconds": 15000,
            "30 seconds": 30000,
        }
        
        duration_ms = duration_map.get(option, 5000)
        
        # Ring the device with the selected duration
        await self.coordinator.ring_device(duration_ms)
        _LOGGER.info("Rang device for %s (%d ms)", option, duration_ms)


class TsuryPhonePhonebookManageSelect(TsuryPhoneBaseSelect):
    """Select entity for managing phonebook entries."""

    def __init__(self, coordinator: TsuryPhoneDataUpdateCoordinator) -> None:
        """Initialize the select."""
        super().__init__(coordinator, "phonebook_manage")
        self._attr_name = "TsuryPhone Phonebook Manager"
        self._attr_icon = "mdi:book-account"
        
    @property
    def options(self) -> List[str]:
        """Return the list of available options."""
        options = ["Manage phonebook..."]
        if "phonebook" in self.coordinator.data:
            entries = self.coordinator.data["phonebook"].get("entries", [])
            for entry in entries:
                options.append(f"📞 {entry['name']} ({entry['number']})")
                options.append(f"🗑️ Remove {entry['name']}")
        return options

    @property
    def current_option(self) -> Optional[str]:
        """Return the current option."""
        return "Manage phonebook..."

    async def async_select_option(self, option: str) -> None:
        """Change the selected option and perform action."""
        if option == "Manage phonebook...":
            return
            
        if option.startswith("📞 "):
            # Extract number and call it
            if "(" in option and ")" in option:
                start = option.rfind("(") + 1
                end = option.rfind(")")
                number = option[start:end]
                await self.coordinator.call_number(number)
                _LOGGER.info("Called %s from phonebook", number)
        
        elif option.startswith("🗑️ Remove "):
            # Extract name and remove from phonebook
            name = option.replace("🗑️ Remove ", "")
            await self.coordinator.remove_phonebook_entry(name)
            _LOGGER.info("Removed %s from phonebook", name)
            await self.coordinator.async_request_refresh()
