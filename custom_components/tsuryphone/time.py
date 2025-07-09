"""Time platform for TsuryPhone Do Not Disturb settings."""
import logging
from datetime import time
from typing import Any

from homeassistant.components.time import TimeEntity
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
    """Set up TsuryPhone time entities based on a config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities = [
        TsuryPhoneDndStartTime(coordinator),
        TsuryPhoneDndEndTime(coordinator),
    ]

    async_add_entities(entities)


class TsuryPhoneBaseTime(CoordinatorEntity, TimeEntity):
    """Base class for TsuryPhone time entities."""

    def __init__(self, coordinator: TsuryPhoneDataUpdateCoordinator, time_type: str) -> None:
        """Initialize the time entity."""
        super().__init__(coordinator)
        self._time_type = time_type
        self._attr_unique_id = f"{coordinator.base_url}_{time_type}"
        self._attr_device_info = coordinator.device_info


class TsuryPhoneDndStartTime(TsuryPhoneBaseTime):
    """Time entity for DnD start time."""

    def __init__(self, coordinator: TsuryPhoneDataUpdateCoordinator) -> None:
        """Initialize the time entity."""
        super().__init__(coordinator, "dnd_start_time")
        self._attr_name = "DnD Start Time"
        self._attr_icon = "mdi:clock-start"

    @property
    def native_value(self) -> time | None:
        """Return the current value."""
        if "dnd" in self.coordinator.data:
            dnd_data = self.coordinator.data["dnd"]
            hour = dnd_data.get("start_hour", 0)
            minute = dnd_data.get("start_minute", 0)
            return time(hour=hour, minute=minute)
        return time(0, 0)

    async def async_set_value(self, value: time) -> None:
        """Set the value."""
        if "dnd" in self.coordinator.data:
            dnd = self.coordinator.data["dnd"]
            await self.coordinator.set_dnd_hours(
                value.hour,
                value.minute,
                dnd.get("end_hour", 0),
                dnd.get("end_minute", 0)
            )
            await self.coordinator.async_request_refresh()

    @property
    def available(self) -> bool:
        """Return if time entity is available (when DnD schedule is enabled)."""
        if "dnd" in self.coordinator.data:
            return self.coordinator.data["dnd"].get("schedule_enabled", False)
        return False


class TsuryPhoneDndEndTime(TsuryPhoneBaseTime):
    """Time entity for DnD end time."""

    def __init__(self, coordinator: TsuryPhoneDataUpdateCoordinator) -> None:
        """Initialize the time entity."""
        super().__init__(coordinator, "dnd_end_time")
        self._attr_name = "DnD End Time"
        self._attr_icon = "mdi:clock-end"

    @property
    def native_value(self) -> time | None:
        """Return the current value."""
        if "dnd" in self.coordinator.data:
            dnd_data = self.coordinator.data["dnd"]
            hour = dnd_data.get("end_hour", 0)
            minute = dnd_data.get("end_minute", 0)
            return time(hour=hour, minute=minute)
        return time(0, 0)

    async def async_set_value(self, value: time) -> None:
        """Set the value."""
        if "dnd" in self.coordinator.data:
            dnd = self.coordinator.data["dnd"]
            await self.coordinator.set_dnd_hours(
                dnd.get("start_hour", 0),
                dnd.get("start_minute", 0),
                value.hour,
                value.minute
            )
            await self.coordinator.async_request_refresh()

    @property
    def available(self) -> bool:
        """Return if time entity is available (when DnD schedule is enabled)."""
        if "dnd" in self.coordinator.data:
            return self.coordinator.data["dnd"].get("schedule_enabled", False)
        return False
