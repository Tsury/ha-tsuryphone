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
        TsuryPhonePhonebookSelect(coordinator),
        TsuryPhoneBlockedNumbersSelect(coordinator),
        TsuryPhoneRemovePhonebookSelect(coordinator),
        TsuryPhoneRemoveBlockedSelect(coordinator),
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


class TsuryPhonePhonebookSelect(TsuryPhoneBaseSelect):
    """Select entity for calling phonebook entries."""

    def __init__(self, coordinator: TsuryPhoneDataUpdateCoordinator) -> None:
        """Initialize the select."""
        super().__init__(coordinator, "phonebook")
        self._attr_name = "Call Quick Dial"
        self._attr_icon = "mdi:phone-dial"
        
    @property
    def options(self) -> List[str]:
        """Return the list of available options."""
        options = ["Select quick dial to call..."]
        
        if "phonebook" in self.coordinator.data:
            entries = self.coordinator.data["phonebook"].get("entries", [])
            if entries:
                # Only show call options - entry number and phone number
                for entry in entries:
                    options.append(f"{entry['name']}: {entry['number']}")
            else:
                options.append("No quick dial entries")
        
        return options

    @property
    def current_option(self) -> Optional[str]:
        """Return the current option."""
        return "Select quick dial to call..."

    async def async_select_option(self, option: str) -> None:
        """Change the selected option and perform action."""
        if option in ["Select quick dial to call...", "No quick dial entries"]:
            return
            
        # Format: "45: +1234567890"
        if ": " in option:
            entry_number = option.split(": ")[0]
            await self.coordinator.call_number(entry_number)
            _LOGGER.info("Called quick dial %s from phonebook", entry_number)
            await self.coordinator.async_request_refresh()

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        # Always available
        return True


class TsuryPhoneBlockedNumbersSelect(TsuryPhoneBaseSelect):
    """Select entity for blocked numbers management."""

    def __init__(self, coordinator: TsuryPhoneDataUpdateCoordinator) -> None:
        """Initialize the select."""
        super().__init__(coordinator, "blocked_numbers")
        self._attr_name = "TsuryPhone Blocked Numbers"
        self._attr_icon = "mdi:phone-off"
        
    @property
    def options(self) -> List[str]:
        """Return the list of available options."""
        options = ["Select blocked number action..."]
        
        if "blocked" in self.coordinator.data:
            entries = self.coordinator.data["blocked"].get("blocked_numbers", [])
            if entries:
                options.append("--- Unblock Number ---")
                # Only show unblock options
                for entry in entries:
                    options.append(f"✅ {entry}")
            else:
                options.append("No blocked numbers")
        
        return options

    @property
    def current_option(self) -> Optional[str]:
        """Return the current option."""
        return "Select blocked number action..."

    async def async_select_option(self, option: str) -> None:
        """Change the selected option and perform action."""
        if option in ["Select blocked number action...", "--- Unblock Number ---", "No blocked numbers"]:
            return
            
        if option.startswith("✅ "):
            # Remove the number from blocked list
            number = option.replace("✅ ", "")
            await self.coordinator.remove_blocked_number(number)
            _LOGGER.info("Unblocked number: %s", number)
            await self.coordinator.async_request_refresh()

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        # Always available
        return True


class TsuryPhoneRemovePhonebookSelect(TsuryPhoneBaseSelect):
    """Select entity for removing phonebook entries."""

    def __init__(self, coordinator: TsuryPhoneDataUpdateCoordinator) -> None:
        """Initialize the select."""
        super().__init__(coordinator, "remove_phonebook")
        self._attr_name = "Remove Quick Dial Entry"
        self._attr_icon = "mdi:dialpad-minus"
        
    @property
    def options(self) -> List[str]:
        """Return the list of available options."""
        options = ["Select quick dial to remove..."]
        
        if "phonebook" in self.coordinator.data:
            entries = self.coordinator.data["phonebook"].get("entries", [])
            if entries:
                # Show remove options with entry number and phone number for clarity
                for entry in entries:
                    options.append(f"🗑️ {entry['name']}: {entry['number']}")
            else:
                options.append("No quick dial entries")
        
        return options

    @property
    def current_option(self) -> Optional[str]:
        """Return the current option."""
        return "Select quick dial to remove..."

    async def async_select_option(self, option: str) -> None:
        """Change the selected option and perform action."""
        if option in ["Select quick dial to remove...", "No quick dial entries"]:
            return
            
        if option.startswith("🗑️ "):
            # Extract entry number and remove from phonebook
            # Format: "🗑️ 5: +1234567890"
            if ": " in option:
                entry_number = option.split(": ")[0].replace("🗑️ ", "")
                await self.coordinator.remove_phonebook_entry(entry_number)
                _LOGGER.info("Removed quick dial entry %s from phonebook", entry_number)
                await self.coordinator.async_request_refresh()

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        # Always available
        return True


class TsuryPhoneRemoveBlockedSelect(TsuryPhoneBaseSelect):
    """Select entity for removing blocked numbers."""

    def __init__(self, coordinator: TsuryPhoneDataUpdateCoordinator) -> None:
        """Initialize the select."""
        super().__init__(coordinator, "remove_blocked")
        self._attr_name = "Remove Blocked Number"
        self._attr_icon = "mdi:phone-check"
        
    @property
    def options(self) -> List[str]:
        """Return the list of available options."""
        options = ["Select number to unblock..."]
        
        if "blocked" in self.coordinator.data:
            entries = self.coordinator.data["blocked"].get("blocked_numbers", [])
            if entries:
                # Show unblock options
                for entry in entries:
                    options.append(f"✅ {entry}")
            else:
                options.append("No blocked numbers")
        
        return options

    @property
    def current_option(self) -> Optional[str]:
        """Return the current option."""
        return "Select number to unblock..."

    async def async_select_option(self, option: str) -> None:
        """Change the selected option and perform action."""
        if option in ["Select number to unblock...", "No blocked numbers"]:
            return
            
        if option.startswith("✅ "):
            # Remove the number from blocked list
            number = option.replace("✅ ", "")
            await self.coordinator.remove_blocked_number(number)
            _LOGGER.info("Unblocked number: %s", number)
            await self.coordinator.async_request_refresh()

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        # Always available
        return True
