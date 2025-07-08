"""Button platform for TsuryPhone."""
import logging
from typing import Any

from homeassistant.components.button import ButtonEntity
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
    """Set up TsuryPhone button based on a config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities = [
        TsuryPhoneHangupButton(coordinator),
        TsuryPhoneResetButton(coordinator),
        TsuryPhoneRingButton(coordinator),
        TsuryPhoneSwitchCallWaitingButton(coordinator),
        TsuryPhoneRefreshDataButton(coordinator),
    ]

    async_add_entities(entities)


class TsuryPhoneBaseButton(CoordinatorEntity, ButtonEntity):
    """Base class for TsuryPhone buttons."""

    def __init__(self, coordinator: TsuryPhoneDataUpdateCoordinator, button_type: str) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self._button_type = button_type
        self._attr_unique_id = f"{coordinator.base_url}_{button_type}"
        self._attr_device_info = coordinator.device_info


class TsuryPhoneHangupButton(TsuryPhoneBaseButton):
    """Button to hang up current call."""

    def __init__(self, coordinator: TsuryPhoneDataUpdateCoordinator) -> None:
        """Initialize the button."""
        super().__init__(coordinator, "hangup")
        self._attr_name = "TsuryPhone Hangup"
        self._attr_icon = "mdi:phone-hangup"

    async def async_press(self) -> None:
        """Handle the button press."""
        await self.coordinator.hangup()
        await self.coordinator.async_request_refresh()

    @property
    def available(self) -> bool:
        """Return if button is available."""
        if "status" in self.coordinator.data:
            call = self.coordinator.data["status"].get("call", {})
            return call.get("active", False)
        return False


class TsuryPhoneResetButton(TsuryPhoneBaseButton):
    """Button to reset the device."""

    def __init__(self, coordinator: TsuryPhoneDataUpdateCoordinator) -> None:
        """Initialize the button."""
        super().__init__(coordinator, "reset")
        self._attr_name = "TsuryPhone Reset"
        self._attr_icon = "mdi:restart"

    async def async_press(self) -> None:
        """Handle the button press."""
        await self.coordinator.reset_device()


class TsuryPhoneRingButton(TsuryPhoneBaseButton):
    """Button to ring the device."""

    def __init__(self, coordinator: TsuryPhoneDataUpdateCoordinator) -> None:
        """Initialize the button."""
        super().__init__(coordinator, "ring")
        self._attr_name = "TsuryPhone Ring"
        self._attr_icon = "mdi:bell-ring"

    async def async_press(self) -> None:
        """Handle the button press."""
        # Try to get ring pattern from the text entity first
        hass = self.coordinator.hass
        pattern_entity_id = f"text.tsuryphone_ring_pattern"
        pattern_state = hass.states.get(pattern_entity_id)
        
        if pattern_state and pattern_state.state and pattern_state.state.strip():
            # Use ring pattern if available
            pattern = pattern_state.state.strip()
            await self.coordinator.ring_device_with_pattern(pattern)
            _LOGGER.info("Rang device with pattern: %s", pattern)
        else:
            # Fall back to duration-based ring for backward compatibility
            duration_ms = 5000
            
            # Try to get from number entity
            number_entity_id = f"number.tsuryphone_ring_duration_seconds"
            number_state = hass.states.get(number_entity_id)
            if number_state and number_state.state:
                try:
                    duration_ms = int(float(number_state.state) * 1000)
                except (ValueError, TypeError):
                    duration_ms = 5000
            
            await self.coordinator.ring_device(duration_ms)
            _LOGGER.info("Rang device for %d ms", duration_ms)
        
        await self.coordinator.async_request_refresh()


class TsuryPhoneSwitchCallWaitingButton(TsuryPhoneBaseButton):
    """Button to switch to call waiting."""

    def __init__(self, coordinator: TsuryPhoneDataUpdateCoordinator) -> None:
        """Initialize the button."""
        super().__init__(coordinator, "switch_call_waiting")
        self._attr_name = "TsuryPhone Switch Call Waiting"
        self._attr_icon = "mdi:phone-forward"

    async def async_press(self) -> None:
        """Handle the button press."""
        await self.coordinator.switch_to_call_waiting()
        await self.coordinator.async_request_refresh()

    @property
    def available(self) -> bool:
        """Return if button is available."""
        if "status" in self.coordinator.data:
            call = self.coordinator.data["status"].get("call", {})
            # Only available when there's a call waiting
            return call.get("has_call_waiting", False)
        return False


class TsuryPhoneRefreshDataButton(TsuryPhoneBaseButton):
    """Button to refresh all data from the device."""

    def __init__(self, coordinator: TsuryPhoneDataUpdateCoordinator) -> None:
        """Initialize the button."""
        super().__init__(coordinator, "refresh_data")
        self._attr_name = "TsuryPhone Refresh Data"
        self._attr_icon = "mdi:refresh"

    async def async_press(self) -> None:
        """Handle the button press."""
        await self.coordinator.async_request_refresh()
        _LOGGER.info("Refreshed TsuryPhone data")
