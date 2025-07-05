"""Number platform for TsuryPhone."""
import logging
from typing import Any

from homeassistant.components.number import NumberEntity, NumberMode
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
    """Set up TsuryPhone number based on a config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities = [
        TsuryPhoneRingDurationNumber(coordinator),
    ]

    async_add_entities(entities)


class TsuryPhoneBaseNumber(CoordinatorEntity, NumberEntity):
    """Base class for TsuryPhone number entities."""

    def __init__(self, coordinator: TsuryPhoneDataUpdateCoordinator, number_type: str) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator)
        self._number_type = number_type
        self._attr_unique_id = f"{coordinator.base_url}_{number_type}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.base_url)},
            "name": "TsuryPhone",
            "manufacturer": MANUFACTURER,
            "model": MODEL,
            "configuration_url": coordinator.base_url,
        }


class TsuryPhoneRingDurationNumber(TsuryPhoneBaseNumber):
    """Number entity for setting custom ring duration."""

    def __init__(self, coordinator: TsuryPhoneDataUpdateCoordinator) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator, "ring_duration_seconds")
        self._attr_name = "TsuryPhone Ring Duration (Seconds)"
        self._attr_icon = "mdi:timer"
        self._attr_mode = NumberMode.BOX
        self._attr_native_min_value = 1
        self._attr_native_max_value = 30
        self._attr_native_step = 1
        self._attr_native_value = 5
        self._attr_native_unit_of_measurement = "s"

    async def async_set_native_value(self, value: float) -> None:
        """Set the ring duration value (does not ring automatically)."""
        self._attr_native_value = value
        _LOGGER.info("Set ring duration to %d seconds", value)

    @property
    def entity_description(self) -> str:
        """Return entity description."""
        return "Set ring duration in seconds (use Ring button to ring)"