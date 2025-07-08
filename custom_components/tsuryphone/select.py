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
        TsuryPhoneWebhookShortcutsSelect(coordinator),
        TsuryPhoneRemoveWebhookSelect(coordinator),
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
                    options.append(f"📞 {entry['name']}: {entry['number']}")
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
            
        # Format: "📞 211: 0546662771"
        if ": " in option and option.startswith("📞 "):
            # Remove the call icon prefix first
            option_without_prefix = option.replace("📞 ", "")
            entry_name = option_without_prefix.split(": ")[0]
            phone_number = option_without_prefix.split(": ")[1]
            await self.coordinator.call_number(phone_number)
            _LOGGER.info("Called quick dial %s (%s) from phonebook", entry_name, phone_number)
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
        options = ["Select number to unblock..."]
        
        if "blocked" in self.coordinator.data:
            entries = self.coordinator.data["blocked"].get("blocked_numbers", [])
            if entries:
                # Only show unblock options
                for entry in entries:
                    options.append(f"🗑️ {entry}")
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
            
        if option.startswith("🗑️ "):
            # Remove the number from blocked list
            number = option.replace("🗑️ ", "")
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


class TsuryPhoneWebhookShortcutsSelect(TsuryPhoneBaseSelect):
    """Select entity for webhook shortcuts - allows calling webhooks."""

    def __init__(self, coordinator: TsuryPhoneDataUpdateCoordinator) -> None:
        """Initialize the select."""
        super().__init__(coordinator, "webhook_shortcuts")
        self._attr_name = "TsuryPhone Webhook Shortcuts"
        self._attr_icon = "mdi:webhook"

    @property
    def options(self) -> List[str]:
        """Return the list of available options."""
        base_options = ["Select webhook to execute..."]
        
        if "webhooks" in self.coordinator.data:
            webhook_data = self.coordinator.data["webhooks"]
            if isinstance(webhook_data, dict) and "entries" in webhook_data:
                webhook_entries = webhook_data["entries"]
                if webhook_entries:
                    for name, url in webhook_entries.items():
                        # Truncate long URLs for display
                        display_url = url[:40] + "..." if len(url) > 40 else url
                        base_options.append(f"🔗 {name}: {display_url}")
                else:
                    base_options.append("No webhook shortcuts")
            else:
                base_options.append("No webhook shortcuts")
        else:
            base_options.append("No webhook shortcuts")
            
        return base_options

    @property
    def current_option(self) -> Optional[str]:
        """Return the current option."""
        return "Select webhook to execute..."

    async def async_select_option(self, option: str) -> None:
        """Change the selected option and execute webhook."""
        if option in ["Select webhook to execute...", "No webhook shortcuts"]:
            return
            
        if option.startswith("🔗 "):
            # Extract webhook name and execute it by "dialing" it
            # Format: "🔗 alarm: http://example.com/webhook..."
            if ": " in option:
                webhook_name = option.split(": ")[0].replace("🔗 ", "")
                # Call the webhook by using the call function with the webhook name
                await self.coordinator.call_number(webhook_name)
                _LOGGER.info("Executed webhook shortcut: %s", webhook_name)
                await self.coordinator.async_request_refresh()

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        # Only available when not in a call
        if "status" in self.coordinator.data:
            call = self.coordinator.data["status"].get("call", {})
            return not call.get("active", False)
        return True


class TsuryPhoneRemoveWebhookSelect(TsuryPhoneBaseSelect):
    """Select entity for removing webhook shortcuts."""

    def __init__(self, coordinator: TsuryPhoneDataUpdateCoordinator) -> None:
        """Initialize the select."""
        super().__init__(coordinator, "remove_webhook")
        self._attr_name = "TsuryPhone Remove Webhook Shortcut"
        self._attr_icon = "mdi:webhook-off"

    @property
    def options(self) -> List[str]:
        """Return the list of available options."""
        base_options = ["Select webhook to remove..."]
        
        if "webhooks" in self.coordinator.data:
            webhook_data = self.coordinator.data["webhooks"]
            if isinstance(webhook_data, dict) and "entries" in webhook_data:
                webhook_entries = webhook_data["entries"]
                if webhook_entries:
                    for name, url in webhook_entries.items():
                        # Truncate long URLs for display
                        display_url = url[:40] + "..." if len(url) > 40 else url
                        base_options.append(f"🗑️ {name}: {display_url}")
                else:
                    base_options.append("No webhook shortcuts")
            else:
                base_options.append("No webhook shortcuts")
        else:
            base_options.append("No webhook shortcuts")
            
        return base_options

    @property
    def current_option(self) -> Optional[str]:
        """Return the current option."""
        return "Select webhook to remove..."

    async def async_select_option(self, option: str) -> None:
        """Change the selected option and remove webhook."""
        if option in ["Select webhook to remove...", "No webhook shortcuts"]:
            return
            
        if option.startswith("🗑️ "):
            # Extract webhook name and remove it
            # Format: "🗑️ alarm: http://example.com/webhook..."
            if ": " in option:
                webhook_name = option.split(": ")[0].replace("🗑️ ", "")
                await self.coordinator.remove_webhook_shortcut(webhook_name)
                _LOGGER.info("Removed webhook shortcut: %s", webhook_name)
                await self.coordinator.async_request_refresh()

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        # Always available
        return True
