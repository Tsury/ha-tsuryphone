"""Data update coordinator for TsuryPhone."""
import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List

import aiohttp
import async_timeout
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.storage import Store

from .const import (
    DOMAIN,
    DEFAULT_SCAN_INTERVAL,
    ENDPOINT_STATUS,
    ENDPOINT_STATS,
    ENDPOINT_DND,
    ENDPOINT_PHONEBOOK,
    ENDPOINT_BLOCKED,
    ENDPOINT_WEBHOOKS,
    ENDPOINT_ACTION,
    ACTION_CALL,
    ACTION_HANGUP,
    ACTION_RING,
    ACTION_RING_PATTERN,
    ACTION_DND,
    ACTION_DND_SCHEDULE,
    ACTION_QUICK_DIAL_ADD,
    ACTION_QUICK_DIAL_REMOVE,
    ACTION_BLOCKED_ADD,
    ACTION_BLOCKED_REMOVE,
    ACTION_WEBHOOK_ADD,
    ACTION_WEBHOOK_REMOVE,
    ACTION_CALL_WAITING,
    ACTION_REFRESH,
    ACTION_MAINTENANCE,
    ACTION_RESET,
    CONF_HOST,
    CONF_PORT,
    CONF_HA_SERVER_URL,
)

_LOGGER = logging.getLogger(__name__)

# Call log entry structure
class CallLogEntry:
    """Represents a call log entry."""
    
    def __init__(self, timestamp: datetime, call_type: str, number: str, duration: int = 0, state: str = ""):
        self.timestamp = timestamp
        self.call_type = call_type  # 'incoming', 'outgoing', 'blocked'
        self.number = number
        self.duration = duration  # Duration in seconds (0 for blocked calls)
        self.state = state  # Phone state during call


class TsuryPhoneDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching TsuryPhone data."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.host = entry.data[CONF_HOST]
        self.port = entry.data[CONF_PORT]
        self.base_url = f"http://{self.host}:{self.port}"
        self.ws_url = f"ws://{self.host}:{self.port}/ws"
        self._websocket = None
        self._websocket_task = None
        self._last_stats = {}
        
        # HA server configuration (for webhooks)
        self.ha_server_url = entry.data.get(CONF_HA_SERVER_URL, "")
        
        # Call log storage
        self._call_log_store = Store(hass, 1, f"{DOMAIN}_call_log_{entry.entry_id}")
        self._call_log: List[CallLogEntry] = []
        self._max_call_log_entries = 100  # Maximum number of entries to keep
        
        # State tracking for call log
        self._last_state = ""
        self._last_call_number = ""
        self._call_start_time = None
        self._last_total_calls = 0
        self._last_total_incoming = 0
        self._last_total_outgoing = 0
        self._last_total_blocked = 0
        
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch data from API endpoint."""
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                # Gather all data in parallel
                status_task = self._fetch_endpoint(session, ENDPOINT_STATUS)
                stats_task = self._fetch_endpoint(session, ENDPOINT_STATS)
                dnd_task = self._fetch_endpoint(session, ENDPOINT_DND)
                phonebook_task = self._fetch_endpoint(session, ENDPOINT_PHONEBOOK)
                blocked_task = self._fetch_endpoint(session, ENDPOINT_BLOCKED)
                webhooks_task = self._fetch_endpoint(session, ENDPOINT_WEBHOOKS)
                
                status, stats, dnd, phonebook, blocked, webhooks = await asyncio.gather(
                    status_task, stats_task, dnd_task, phonebook_task, blocked_task, webhooks_task,
                    return_exceptions=True
                )
                
                # Handle any exceptions
                data = {}
                if not isinstance(status, Exception):
                    data["status"] = status
                if not isinstance(stats, Exception):
                    data["stats"] = stats
                    await self._process_stats_for_call_log(stats)
                if not isinstance(dnd, Exception):
                    data["dnd"] = dnd
                if not isinstance(phonebook, Exception):
                    data["phonebook"] = phonebook
                if not isinstance(blocked, Exception):
                    data["blocked"] = blocked
                if not isinstance(webhooks, Exception):
                    data["webhooks"] = webhooks
                
                # Add call log to data
                data["call_log"] = await self.get_call_log()
                
                if not data:
                    raise UpdateFailed("No data received from any endpoint")
                
                # Process status for call log tracking
                if "status" in data:
                    await self._process_status_for_call_log(data["status"])
                
                return data
                
        except asyncio.TimeoutError as err:
            raise UpdateFailed(f"Timeout connecting to TsuryPhone at {self.base_url}") from err
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Error connecting to TsuryPhone at {self.base_url}: {err}") from err

    async def _fetch_endpoint(self, session: aiohttp.ClientSession, endpoint: str) -> Dict[str, Any]:
        """Fetch data from a specific endpoint."""
        url = f"{self.base_url}{endpoint}"
        _LOGGER.debug("Fetching data from %s", url)
        
        async with session.get(url) as response:
            response.raise_for_status()
            return await response.json()

    async def call_number(self, number: str) -> None:
        """Make a call to the specified number."""
        await self._make_action_request(ACTION_CALL, {"number": number})
        
        # Add outgoing call to log
        await self._add_call_log_entry("outgoing", number, 0, "Calling")
        
        await self.async_request_refresh()

    async def hangup(self) -> None:
        """Hang up the current call."""
        await self._make_action_request(ACTION_HANGUP)
        await self.async_request_refresh()

    async def reset_device(self) -> None:
        """Reset the device."""
        await self._make_action_request(ACTION_RESET)
        await self.async_request_refresh()

    async def ring_device(self, duration_ms: int) -> None:
        """Ring the device for specified duration."""
        await self._make_action_request(ACTION_RING, {"duration": duration_ms})
        await self.async_request_refresh()

    async def ring_device_with_pattern(self, pattern: str) -> None:
        """Ring the device with a specific pattern."""
        await self._make_action_request(ACTION_RING_PATTERN, {"pattern": pattern})
        await self.async_request_refresh()

    async def set_dnd_hours(self, start_hour: int, start_minute: int, end_hour: int, end_minute: int) -> None:
        """Set Do Not Disturb hours."""
        data = {
            "start_hour": start_hour,
            "start_minute": start_minute,
            "end_hour": end_hour,
            "end_minute": end_minute,
        }
        await self._make_request("POST", ENDPOINT_DND, data)
        await self.async_request_refresh()

    async def add_phonebook_entry(self, name: str, number: str) -> None:
        """Add a phonebook entry."""
        await self._make_action_request(ACTION_QUICK_DIAL_ADD, {"name": name, "number": number})
        await self.async_request_refresh()

    async def remove_phonebook_entry(self, name: str) -> None:
        """Remove a phonebook entry."""
        await self._make_action_request(ACTION_QUICK_DIAL_REMOVE, {"name": name})
        await self.async_request_refresh()

    async def add_blocked_number(self, number: str) -> None:
        """Add a blocked number."""
        await self._make_action_request(ACTION_BLOCKED_ADD, {"number": number})
        await self.async_request_refresh()

    async def remove_blocked_number(self, number: str) -> None:
        """Remove a blocked number."""
        await self._make_action_request(ACTION_BLOCKED_REMOVE, {"number": number})
        await self.async_request_refresh()

    async def add_webhook_shortcut(self, name: str, url: str) -> None:
        """Add a webhook shortcut."""
        await self._make_action_request(ACTION_WEBHOOK_ADD, {"name": name, "url": url})
        await self.async_request_refresh()

    async def remove_webhook_shortcut(self, name: str) -> None:
        """Remove a webhook shortcut."""
        await self._make_action_request(ACTION_WEBHOOK_REMOVE, {"name": name})
        await self.async_request_refresh()

    async def set_dnd_force_enabled(self, enabled: bool) -> None:
        """Enable or disable force Do Not Disturb."""
        await self._make_action_request(ACTION_DND, {"enabled": enabled})
        await self.async_request_refresh()

    async def set_dnd_schedule_enabled(self, enabled: bool) -> None:
        """Enable or disable Do Not Disturb schedule."""
        await self._make_action_request(ACTION_DND_SCHEDULE, {"enabled": enabled})
        await self.async_request_refresh()

    async def set_maintenance_mode(self, enabled: bool) -> None:
        """Enable or disable maintenance mode."""
        await self._make_action_request(ACTION_MAINTENANCE, {"enabled": enabled})
        await self.async_request_refresh()

    async def switch_to_call_waiting(self) -> None:
        """Switch to call waiting."""
        await self._make_action_request(ACTION_CALL_WAITING)
        await self.async_request_refresh()

    async def refresh_data(self) -> None:
        """Refresh device data."""
        await self._make_action_request(ACTION_REFRESH)
        await self.async_request_refresh()

    async def _make_action_request(self, action: str, data: Dict[str, Any] = None) -> None:
        """Make an action request to the unified action endpoint."""
        payload = {"action": action}
        if data:
            payload.update(data)
        await self._make_request("POST", ENDPOINT_ACTION, payload)

    async def _make_request(self, method: str, endpoint: str, data: Dict[str, Any] = None) -> None:
        """Make a request to the device."""
        url = f"{self.base_url}{endpoint}"
        
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                if method == "POST" and data:
                    headers = {"Content-Type": "application/json"}
                    async with session.post(url, json=data, headers=headers) as response:
                        response.raise_for_status()
                else:
                    async with session.request(method, url) as response:
                        response.raise_for_status()
                        
        except asyncio.TimeoutError as err:
            raise UpdateFailed(f"Timeout during {method} request to {url}") from err
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Error during {method} request to {url}: {err}") from err

    async def async_setup(self) -> None:
        """Set up the coordinator."""
        # Load call log from storage
        await self._load_call_log()
        
        # Configure HA server URL on device if available
        if self.ha_server_url:
            await self._send_ha_server_config()
        
        # Start WebSocket connection
        await self._start_websocket()

    async def _send_ha_server_config(self) -> None:
        """Send HA server configuration to the device."""
        try:
            ha_server_url = self.ha_server_url
            if not ha_server_url.startswith(('http://', 'https://')):
                ha_server_url = f"http://{ha_server_url}"
            
            data = {"server_url": ha_server_url}
            await self._make_request("POST", ENDPOINT_WEBHOOKS, data)
            _LOGGER.info("Successfully configured HA server URL on TsuryPhone device: %s", ha_server_url)
        except Exception as err:
            _LOGGER.warning("Failed to configure HA server URL on device: %s", err)
    
    async def async_shutdown(self) -> None:
        """Shutdown the coordinator."""
        # Stop WebSocket connection
        await self._stop_websocket()
        
        # Save call log to storage
        await self._save_call_log()

    async def _start_websocket(self) -> None:
        """Start WebSocket connection for real-time updates."""
        try:
            import aiohttp
            self._websocket_task = asyncio.create_task(self._websocket_handler())
            _LOGGER.info("Starting WebSocket connection to %s", self.ws_url)
        except Exception as err:
            _LOGGER.warning("Failed to start WebSocket connection: %s", err)

    async def _stop_websocket(self) -> None:
        """Stop WebSocket connection."""
        if self._websocket_task:
            self._websocket_task.cancel()
            try:
                await self._websocket_task
            except asyncio.CancelledError:
                pass
            self._websocket_task = None
        
        if self._websocket:
            await self._websocket.close()
            self._websocket = None

    async def _websocket_handler(self) -> None:
        """Handle WebSocket connection and messages."""
        import aiohttp
        
        while True:
            try:
                session = aiohttp.ClientSession()
                self._websocket = await session.ws_connect(self.ws_url)
                _LOGGER.info("WebSocket connected to TsuryPhone")
                
                async for msg in self._websocket:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        try:
                            data = json.loads(msg.data)
                            # Process real-time status update
                            await self._process_status_for_call_log(data)
                            
                            # Update the coordinator data immediately
                            self.data = self.data or {}
                            self.data["status"] = data
                            self.async_update_listeners()
                            
                        except json.JSONDecodeError:
                            _LOGGER.warning("Received invalid JSON from WebSocket: %s", msg.data)
                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        _LOGGER.error("WebSocket error: %s", self._websocket.exception())
                        break
                
            except Exception as err:
                _LOGGER.warning("WebSocket connection error: %s", err)
                if self._websocket:
                    await self._websocket.close()
                    self._websocket = None
                
                # Wait before reconnecting
                await asyncio.sleep(5)

    async def _process_status_for_call_log(self, status: Dict[str, Any]) -> None:
        """Process status data for call log tracking."""
        try:
            current_state = status.get("state", "")
            current_call = status.get("call", {})
            current_call_number = current_call.get("number", "") if current_call.get("active") else ""
            
            # Track call start
            if (current_state in ["IncomingCall", "InCall"] and 
                current_call_number and 
                (current_state != self._last_state or current_call_number != self._last_call_number)):
                
                self._call_start_time = datetime.now()
                self._last_call_number = current_call_number
                
                # Add incoming call entry
                if current_state == "IncomingCall" and self._last_state != "IncomingCall":
                    await self._add_call_log_entry("incoming", current_call_number, 0, current_state)
            
            # Track call end
            elif (self._last_state in ["IncomingCall", "InCall"] and 
                  current_state not in ["IncomingCall", "InCall"] and 
                  self._call_start_time):
                
                duration = int((datetime.now() - self._call_start_time).total_seconds())
                if self._last_state == "InCall":
                    # Call was answered, update the existing entry with duration
                    await self._update_last_call_duration(duration)
                
                self._call_start_time = None
                self._last_call_number = ""
            
            self._last_state = current_state
            
        except Exception as err:
            _LOGGER.warning("Error processing status for call log: %s", err)

    async def _process_stats_for_call_log(self, stats: Dict[str, Any]) -> None:
        """Process stats data for call log tracking."""
        try:
            total_outgoing = stats.get("total_outgoing_calls", 0)
            total_blocked = stats.get("total_blocked_calls", 0)
            
            # Track new outgoing calls
            if total_outgoing > self._last_total_outgoing:
                # We can't know the exact number from stats alone, so we'll rely on action tracking
                pass
            
            # Track new blocked calls
            if total_blocked > self._last_total_blocked:
                count_diff = total_blocked - self._last_total_blocked
                for _ in range(count_diff):
                    await self._add_call_log_entry("blocked", "Unknown", 0, "Blocked")
            
            self._last_total_outgoing = total_outgoing
            self._last_total_blocked = total_blocked
            
        except Exception as err:
            _LOGGER.warning("Error processing stats for call log: %s", err)

    async def _add_call_log_entry(self, call_type: str, number: str, duration: int, state: str) -> None:
        """Add a new call log entry."""
        entry = CallLogEntry(datetime.now(), call_type, number, duration, state)
        self._call_log.insert(0, entry)  # Insert at beginning (most recent first)
        
        # Limit the number of entries
        if len(self._call_log) > self._max_call_log_entries:
            self._call_log = self._call_log[:self._max_call_log_entries]
        
        # Save to storage periodically
        await self._save_call_log()
        
        _LOGGER.debug("Added call log entry: %s call to %s", call_type, number)

    async def _update_last_call_duration(self, duration: int) -> None:
        """Update the duration of the last call log entry."""
        if self._call_log and self._call_log[0].duration == 0:
            self._call_log[0].duration = duration
            await self._save_call_log()
            _LOGGER.debug("Updated call duration: %d seconds", duration)

    async def get_call_log(self) -> List[Dict[str, Any]]:
        """Get the call log as a list of dictionaries."""
        return [
            {
                "timestamp": entry.timestamp.isoformat(),
                "type": entry.call_type,
                "number": entry.number,
                "duration": entry.duration,
                "state": entry.state,
            }
            for entry in self._call_log
        ]

    async def _load_call_log(self) -> None:
        """Load call log from storage."""
        try:
            data = await self._call_log_store.async_load()
            if data:
                self._call_log = []
                for entry_data in data.get("entries", []):
                    entry = CallLogEntry(
                        datetime.fromisoformat(entry_data["timestamp"]),
                        entry_data["type"],
                        entry_data["number"],
                        entry_data.get("duration", 0),
                        entry_data.get("state", ""),
                    )
                    self._call_log.append(entry)
                _LOGGER.info("Loaded %d call log entries from storage", len(self._call_log))
        except Exception as err:
            _LOGGER.warning("Failed to load call log from storage: %s", err)
            self._call_log = []

    async def _save_call_log(self) -> None:
        """Save call log to storage."""
        try:
            data = {
                "entries": [
                    {
                        "timestamp": entry.timestamp.isoformat(),
                        "type": entry.call_type,
                        "number": entry.number,
                        "duration": entry.duration,
                        "state": entry.state,
                    }
                    for entry in self._call_log
                ]
            }
            await self._call_log_store.async_save(data)
        except Exception as err:
            _LOGGER.warning("Failed to save call log to storage: %s", err)
