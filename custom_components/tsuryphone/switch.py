"""Switch platform for TsuryPhone."""
import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
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
    """Set up TsuryPhone switch based on a config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities = [
        TsuryPhoneDndForceSwitch(coordinator),
        TsuryPhoneDndScheduleSwitch(coordinator),
    ]

    async_add_entities(entities)


class TsuryPhoneBaseSwitch(CoordinatorEntity, SwitchEntity):
    """Base class for TsuryPhone switches."""

    def __init__(self, coordinator: TsuryPhoneDataUpdateCoordinator, switch_type: str) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._switch_type = switch_type
        self._attr_unique_id = f"{coordinator.base_url}_{switch_type}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.base_url)},
            "name": "TsuryPhone",
            "manufacturer": MANUFACTURER,
            "model": MODEL,
            "configuration_url": coordinator.base_url,
        }


class TsuryPhoneDndForceSwitch(TsuryPhoneBaseSwitch):
    """Switch to force Do Not Disturb on regardless of schedule."""

    def __init__(self, coordinator: TsuryPhoneDataUpdateCoordinator) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, "dnd_force")
        self._attr_name = "TsuryPhone DnD Force"
        self._attr_icon = "mdi:bell-off-outline"

    @property
    def is_on(self) -> bool:
        """Return true if DnD force is enabled."""
        if "dnd" in self.coordinator.data:
            return self.coordinator.data["dnd"].get("force_enabled", False)
        return False

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on force Do Not Disturb."""
        await self.coordinator.set_dnd_force_enabled(True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off force Do Not Disturb."""
        await self.coordinator.set_dnd_force_enabled(False)
        await self.coordinator.async_request_refresh()


class TsuryPhoneDndScheduleSwitch(TsuryPhoneBaseSwitch):
    """Switch to enable/disable Do Not Disturb schedule."""

    def __init__(self, coordinator: TsuryPhoneDataUpdateCoordinator) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, "dnd_schedule")
        self._attr_name = "TsuryPhone DnD Schedule"
        self._attr_icon = "mdi:calendar-clock"

    @property
    def is_on(self) -> bool:
        """Return true if DnD schedule is enabled."""
        if "dnd" in self.coordinator.data:
            return self.coordinator.data["dnd"].get("schedule_enabled", False)
        return False

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on Do Not Disturb schedule."""
        await self.coordinator.set_dnd_schedule_enabled(True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off Do Not Disturb schedule."""
        await self.coordinator.set_dnd_schedule_enabled(False)
        await self.coordinator.async_request_refresh()
