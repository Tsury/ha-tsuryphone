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
    """Select entity for phonebook management - call or remove entries."""

    def __init__(self, coordinator: TsuryPhoneDataUpdateCoordinator) -> None:
        """Initialize the select."""
        super().__init__(coordinator, "phonebook")
        self._attr_name = "TsuryPhone Phonebook"
        self._attr_icon = "mdi:book-account"
        
    @property
    def options(self) -> List[str]:
        """Return the list of available options."""
        options = ["Select phonebook action..."]
        
        if "phonebook" in self.coordinator.data:
            entries = self.coordinator.data["phonebook"].get("entries", [])
            if entries:
                options.append("--- Call Contact ---")
                # Only show call options, no remove mixed in
                for entry in entries:
                    options.append(f"📞 {entry['name']} ({entry['number']})")
                
                options.append("--- Remove Contact ---")
                # Only show remove options with phone numbers for clarity
                for entry in entries:
                    options.append(f"🗑️ {entry['name']} ({entry['number']})")
            else:
                options.append("No contacts in phonebook")
        
        return options

    @property
    def current_option(self) -> Optional[str]:
        """Return the current option."""
        return "Select phonebook action..."

    async def async_select_option(self, option: str) -> None:
        """Change the selected option and perform action."""
        if option in ["Select phonebook action...", "--- Call Contact ---", "--- Remove Contact ---", "No contacts in phonebook"]:
            return
            
        if option.startswith("📞 "):
            # Extract number and call it
            if "(" in option and ")" in option:
                start = option.rfind("(") + 1
                end = option.rfind(")")
                number = option[start:end]
                await self.coordinator.call_number(number)
                _LOGGER.info("Called %s from phonebook", number)
                await self.coordinator.async_request_refresh()
        
        elif option.startswith("🗑️ "):
            # Extract name and remove from phonebook (handle name with phone number format)
            name = option.replace("🗑️ ", "")
            # If format is "Name (Number)", extract just the name
            if " (" in name and name.endswith(")"):
                name = name.split(" (")[0]
            await self.coordinator.remove_phonebook_entry(name)
            _LOGGER.info("Removed %s from phonebook", name)
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
        
        if "screened" in self.coordinator.data:
            entries = self.coordinator.data["screened"].get("numbers", [])
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
            # Remove the number from screened list
            number = option.replace("✅ ", "")
            await self.coordinator.remove_screened_number(number)
            _LOGGER.info("Unblocked number: %s", number)
            await self.coordinator.async_request_refresh()

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        # Always available
        return True
