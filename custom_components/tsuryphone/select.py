"""Select platform for TsuryPhone."""
from typing import Any, List, Optional

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, MODEL
from .coordinator import TsuryPhoneDataUpdateCoordinator


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
        self._attr_device_info = coordinator.device_info


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
        
        # Use coordinator data if available, otherwise show loading
        if "phonebook" in self.coordinator.data:
            entries = self.coordinator.data["phonebook"].get("entries", [])
            if entries:
                # Only show call options - entry number and phone number
                for entry in entries:
                    options.append(f"📞 {entry['name']}: {entry['number']}")
            else:
                options.append("No quick dial entries")
        else:
            options.append("Loading quick dial entries...")
        
        return options

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass, load phonebook data if not already loaded."""
        await super().async_added_to_hass()
        if "phonebook" not in self.coordinator.data:
            # Load phonebook data on-demand
            await self.coordinator.get_phonebook_data()
            self.async_write_ha_state()

    @property
    def current_option(self) -> Optional[str]:
        """Return the current option."""
        return "Select quick dial to call..."

    async def async_select_option(self, option: str) -> None:
        """Change the selected option and perform action."""
        if option in ["Select quick dial to call...", "No quick dial entries"]:
            return
            
        # Format: "📞 211: 0521234567"
        if ": " in option and option.startswith("📞 "):
            # Remove the call icon prefix first
            option_without_prefix = option.replace("📞 ", "")
            entry_name = option_without_prefix.split(": ")[0]
            phone_number = option_without_prefix.split(": ")[1]
            await self.coordinator.call_number(phone_number)
            # Call status will be updated via WebSocket

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
        self._attr_name = "Blocked Numbers"
        self._attr_icon = "mdi:phone-off"
        
    @property
    def options(self) -> List[str]:
        """Return the list of available options."""
        options = ["Select number to unblock..."]
        
        # Use coordinator data if available, otherwise show loading
        if "blocked" in self.coordinator.data:
            entries = self.coordinator.data["blocked"].get("blocked_numbers", [])
            if entries:
                # Only show unblock options
                for entry in entries:
                    options.append(f"🗑️ {entry}")
            else:
                options.append("No blocked numbers")
        else:
            options.append("Loading blocked numbers...")
        
        return options

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass, load blocked data if not already loaded."""
        await super().async_added_to_hass()
        if "blocked" not in self.coordinator.data:
            # Load blocked data on-demand
            await self.coordinator.get_blocked_data()
            self.async_write_ha_state()

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
            # Blocked data is already refreshed by the coordinator method

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
        
        # Use coordinator data if available, otherwise show loading
        if "phonebook" in self.coordinator.data:
            entries = self.coordinator.data["phonebook"].get("entries", [])
            if entries:
                # Show remove options with entry number and phone number for clarity
                for entry in entries:
                    options.append(f"🗑️ {entry['name']}: {entry['number']}")
            else:
                options.append("No quick dial entries")
        else:
            options.append("Loading quick dial entries...")
        
        return options

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass, load phonebook data if not already loaded."""
        await super().async_added_to_hass()
        if "phonebook" not in self.coordinator.data:
            # Load phonebook data on-demand
            await self.coordinator.get_phonebook_data()
            self.async_write_ha_state()

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
                # Phonebook data is already refreshed by the coordinator method

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        # Always available
        return True


class TsuryPhoneRemoveWebhookSelect(TsuryPhoneBaseSelect):
    """Select entity for removing webhook shortcuts."""

    def __init__(self, coordinator: TsuryPhoneDataUpdateCoordinator) -> None:
        """Initialize the select."""
        super().__init__(coordinator, "remove_webhook")
        self._attr_name = "Remove Webhook Shortcut"
        self._attr_icon = "mdi:webhook-off"

    @property
    def options(self) -> List[str]:
        """Return the list of available options."""
        base_options = ["Select webhook to remove..."]
        
        # Use async_add_entities callback to get webhooks data on-demand
        # For now, check if webhooks data is available, if not show placeholder
        if "webhooks" in self.coordinator.data:
            webhook_data = self.coordinator.data["webhooks"]
            # Handle the actual firmware format: {"webhooks": [{"number": "...", "webhook_id": "..."}]}
            if isinstance(webhook_data, dict) and "webhooks" in webhook_data:
                webhook_entries = webhook_data["webhooks"]
                if webhook_entries and isinstance(webhook_entries, list):
                    for entry in webhook_entries:
                        if isinstance(entry, dict) and "number" in entry and "webhook_id" in entry:
                            name = entry["number"]
                            webhook_id = entry["webhook_id"]
                            # Truncate long webhook IDs for display
                            display_id = webhook_id[:20] + "..." if len(webhook_id) > 20 else webhook_id
                            base_options.append(f"🗑️ {name}: {display_id}")
                else:
                    base_options.append("No webhook shortcuts")
            else:
                base_options.append("No webhook shortcuts")
        else:
            # Fetch webhooks data on-demand when needed
            base_options.append("Loading webhooks...")
            
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
                # Webhook data is already refreshed by the coordinator method

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        # Always available
        return True

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass, load webhooks data if not already loaded."""
        await super().async_added_to_hass()
        if "webhooks" not in self.coordinator.data:
            # Load webhooks data on-demand
            await self.coordinator.get_webhooks_data()
            self.async_write_ha_state()
