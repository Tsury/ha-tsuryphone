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
        TsuryPhoneMaintenanceModeSwitch(coordinator),
    ]

    async_add_entities(entities)


class TsuryPhoneBaseSwitch(CoordinatorEntity, SwitchEntity):
    """Base class for TsuryPhone switches."""

    def __init__(self, coordinator: TsuryPhoneDataUpdateCoordinator, switch_type: str) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._switch_type = switch_type
        self._attr_unique_id = f"{coordinator.base_url}_{switch_type}"
        self._attr_device_info = coordinator.device_info


class TsuryPhoneDndForceSwitch(TsuryPhoneBaseSwitch):
    """Switch to force Do Not Disturb on regardless of schedule."""

    def __init__(self, coordinator: TsuryPhoneDataUpdateCoordinator) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, "dnd_force")
        self._attr_name = "DnD Force"
        self._attr_icon = "mdi:bell-off-outline"

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass, load DND data if not already loaded."""
        await super().async_added_to_hass()
        if "dnd" not in self.coordinator.data:
            # Load DND data on-demand
            await self.coordinator.get_dnd_data()
            self.async_write_ha_state()

    @property
    def is_on(self) -> bool:
        """Return true if DnD force is enabled."""
        if "dnd" in self.coordinator.data:
            return self.coordinator.data["dnd"].get("force_enabled", False)
        return False

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on force Do Not Disturb."""
        await self.coordinator.set_dnd_force_enabled(True)
        # DND data is already refreshed by the coordinator method

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off force Do Not Disturb."""
        await self.coordinator.set_dnd_force_enabled(False)
        # DND data is already refreshed by the coordinator method


class TsuryPhoneDndScheduleSwitch(TsuryPhoneBaseSwitch):
    """Switch to enable/disable Do Not Disturb schedule."""

    def __init__(self, coordinator: TsuryPhoneDataUpdateCoordinator) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, "dnd_schedule")
        self._attr_name = "DnD Schedule"
        self._attr_icon = "mdi:clock-outline"

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass, load DND data if not already loaded."""
        await super().async_added_to_hass()
        if "dnd" not in self.coordinator.data:
            # Load DND data on-demand
            await self.coordinator.get_dnd_data()
            self.async_write_ha_state()

    @property
    def is_on(self) -> bool:
        """Return true if DnD schedule is enabled."""
        if "dnd" in self.coordinator.data:
            return self.coordinator.data["dnd"].get("schedule_enabled", False)
        return False

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on Do Not Disturb schedule."""
        await self.coordinator.set_dnd_schedule_enabled(True)
        # DND data is already refreshed by the coordinator method

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off Do Not Disturb schedule."""
        await self.coordinator.set_dnd_schedule_enabled(False)
        # DND data is already refreshed by the coordinator method


class TsuryPhoneMaintenanceModeSwitch(TsuryPhoneBaseSwitch):
    """Switch to enable/disable maintenance mode."""

    def __init__(self, coordinator: TsuryPhoneDataUpdateCoordinator) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, "maintenance_mode")
        self._attr_name = "Maintenance Mode"
        self._attr_icon = "mdi:wrench"

    @property
    def is_on(self) -> bool:
        """Return true if maintenance mode is enabled."""
        if "status" in self.coordinator.data:
            return self.coordinator.data["status"].get("maintenance", False)
        return False

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on maintenance mode."""
        await self.coordinator.set_maintenance_mode(True)
        # Status changes will be reflected via WebSocket

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off maintenance mode."""
        await self.coordinator.set_maintenance_mode(False)
        # Status changes will be reflected via WebSocket
