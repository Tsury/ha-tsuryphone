"""Data update coordinator for TsuryPhone."""
import asyncio
import json
import logging
import re
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

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
    CONF_DEVICE_NAME,
)

_LOGGER = logging.getLogger(__name__)


def parse_ring_pattern(pattern: str) -> Optional[Dict[str, Any]]:
    """Parse a ring pattern string into structured data.
    
    Examples:
        "2500,500,500,500x3" -> {"durations": [2500, 500, 500, 500], "repeats": 3}
        "1000,200,1000" -> {"durations": [1000, 200, 1000], "repeats": 1}
        "500/5" -> {"durations": [500], "repeats": 5}
    """
    if not pattern or not isinstance(pattern, str):
        return None
    
    pattern = pattern.strip()
    if not pattern:
        return None
    
    try:
        # Check for repeat syntax: pattern x number or pattern/number
        repeats = 1
        main_pattern = pattern
        
        # Handle "x3" syntax
        if 'x' in pattern:
            parts = pattern.rsplit('x', 1)
            if len(parts) == 2:
                main_pattern = parts[0]
                repeats = int(parts[1])
        # Handle "/3" syntax  
        elif '/' in pattern:
            parts = pattern.rsplit('/', 1)
            if len(parts) == 2:
                main_pattern = parts[0]
                repeats = int(parts[1])
        
        if repeats <= 0 or repeats > 100:  # Reasonable limits
            _LOGGER.error("Invalid repeat count in pattern: %s", pattern)
            return None
        
        # Parse comma-separated durations
        duration_parts = main_pattern.split(',')
        durations = []
        
        for duration_str in duration_parts:
            duration_str = duration_str.strip()
            if not duration_str:
                continue
            duration = int(duration_str)
            if duration <= 0 or duration > 30000:  # Max 30 seconds per duration
                _LOGGER.error("Invalid duration in pattern: %s", duration_str)
                return None
            durations.append(duration)
        
        if not durations:
            _LOGGER.error("No valid durations found in pattern: %s", pattern)
            return None
        
        # Validate pattern logic
        if repeats > 1 and len(durations) % 2 != 0:
            _LOGGER.error("Pattern with repeats must have even number of durations (alternating ring/pause): %s", pattern)
            return None
        
        return {
            "durations": durations,
            "repeats": repeats
        }
        
    except (ValueError, IndexError) as e:
        _LOGGER.error("Failed to parse ring pattern '%s': %s", pattern, e)
        return None


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
        self._websocket_shutdown = False  # Flag to indicate shutdown
        
        # HA server configuration (for webhooks)
        self.ha_server_url = entry.data.get(CONF_HA_SERVER_URL, "")
        
        # Device configuration
        self.device_name = entry.data.get(CONF_DEVICE_NAME, "tsuryphone")
        
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

    @property
    def device_info(self) -> Dict[str, Any]:
        """Return device info for this coordinator."""
        return {
            "identifiers": {(DOMAIN, self.base_url)},
            "name": f"TsuryPhone ({self.device_name})",
            "manufacturer": "TsuryPhone Project",
            "model": "TsuryPhone",
            "configuration_url": self.base_url,
        }

    @property
    def websocket_connected(self) -> bool:
        """Check if WebSocket is currently connected."""
        return (self._websocket is not None and 
                not self._websocket.closed and 
                self._websocket_task is not None and 
                not self._websocket_task.done())

    async def ensure_websocket_connection(self) -> None:
        """Ensure WebSocket connection is active, restart if needed."""
        if not self.websocket_connected:
            _LOGGER.warning("HA WebSocket: Connection lost, restarting...")
            await self._start_websocket()
        else:
            # Test connection health with a ping
            try:
                if self._websocket:
                    self._websocket.ping()
                    _LOGGER.debug("HA WebSocket: Connection health check ping sent")
            except Exception as ping_err:
                _LOGGER.warning("HA WebSocket: Connection health check failed: %s, restarting...", ping_err)
                await self._start_websocket()

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch data from API endpoint - only poll critical real-time data."""
        try:
            # Ensure WebSocket connection is maintained
            await self.ensure_websocket_connection()
            
            # Log WebSocket connection status periodically  
            if hasattr(self, '_last_ws_status_log'):
                time_since_last_log = time.time() - self._last_ws_status_log
                if time_since_last_log > 60:  # Log every minute
                    _LOGGER.info("HA WebSocket: Connection status - Connected: %s, Task active: %s", 
                               self.websocket_connected, 
                               self._websocket_task is not None and not self._websocket_task.done())
                    self._last_ws_status_log = time.time()
            else:
                self._last_ws_status_log = time.time()
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                # Only poll critical real-time data
                status_task = self._fetch_endpoint(session, ENDPOINT_STATUS)
                stats_task = self._fetch_endpoint(session, ENDPOINT_STATS)
                
                status, stats = await asyncio.gather(
                    status_task, stats_task,
                    return_exceptions=True
                )
                
                # Start with existing data (preserves on-demand loaded data)
                data = self.data.copy() if self.data else {}
                
                # Update with fresh real-time data
                if not isinstance(status, Exception):
                    data["status"] = status
                    # Process status for call log tracking
                    await self._process_status_for_call_log(status)
                    
                if not isinstance(stats, Exception):
                    data["stats"] = stats
                    await self._process_stats_for_call_log(stats)
                
                # Add call log to data
                data["call_log"] = await self.get_call_log()
                
                # Ensure we have at least status or stats
                if "status" not in data and "stats" not in data:
                    raise UpdateFailed("No critical data received from device")
                
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
        _LOGGER.info("HA Action: Initiating call to number: %s", number)
        await self._make_action_request(ACTION_CALL, {"number": number})
        _LOGGER.debug("HA Action: Call request sent successfully")
        
        # Add outgoing call to log
        await self._add_call_log_entry("outgoing", number, 0, "Calling")
        
        await self.async_request_refresh()

    async def hangup(self) -> None:
        """Hang up the current call."""
        _LOGGER.info("HA Action: Hanging up current call")
        await self._make_action_request(ACTION_HANGUP)
        _LOGGER.debug("HA Action: Hangup request sent successfully")
        await self.async_request_refresh()

    async def reset_device(self) -> None:
        """Reset the device."""
        await self._make_action_request(ACTION_RESET)
        await self.async_request_refresh()

    async def ring_device_with_pattern(self, pattern: str) -> None:
        """Ring the device with a specific pattern."""
        # Parse the pattern string into structured data
        parsed_pattern = parse_ring_pattern(pattern)
        if parsed_pattern is None:
            _LOGGER.error("Invalid ring pattern: %s", pattern)
            raise ValueError(f"Invalid ring pattern: {pattern}")
        
        # Send the parsed pattern data instead of raw string
        await self._make_action_request(ACTION_RING_PATTERN, {
            "durations": parsed_pattern["durations"],
            "repeats": parsed_pattern["repeats"]
        })
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
        # Refresh DND data after change
        self.data["dnd"] = await self._fetch_dnd_data()
        await self.async_request_refresh()

    async def add_phonebook_entry(self, name: str, number: str) -> None:
        """Add a phonebook entry."""
        await self._make_action_request(ACTION_QUICK_DIAL_ADD, {"name": name, "number": number})
        # Refresh phonebook data after change
        self.data["phonebook"] = await self._fetch_phonebook_data()
        await self.async_request_refresh()

    async def remove_phonebook_entry(self, name: str) -> None:
        """Remove a phonebook entry."""
        await self._make_action_request(ACTION_QUICK_DIAL_REMOVE, {"name": name})
        # Refresh phonebook data after change
        self.data["phonebook"] = await self._fetch_phonebook_data()
        await self.async_request_refresh()

    async def add_blocked_number(self, number: str) -> None:
        """Add a blocked number."""
        await self._make_action_request(ACTION_BLOCKED_ADD, {"number": number})
        # Refresh blocked data after change
        self.data["blocked"] = await self._fetch_blocked_data()
        await self.async_request_refresh()

    async def remove_blocked_number(self, number: str) -> None:
        """Remove a blocked number."""
        await self._make_action_request(ACTION_BLOCKED_REMOVE, {"number": number})
        # Refresh blocked data after change
        self.data["blocked"] = await self._fetch_blocked_data()
        await self.async_request_refresh()

    async def add_webhook_shortcut(self, name: str, webhook_id: str) -> None:
        """Add a webhook shortcut with name and webhook ID."""
        await self._make_action_request(ACTION_WEBHOOK_ADD, {"number": name, "webhook_id": webhook_id})
        # Refresh webhooks data after change
        self.data["webhooks"] = await self._fetch_webhooks_data()
        await self.async_request_refresh()

    async def remove_webhook_shortcut(self, name: str) -> None:
        """Remove a webhook shortcut."""
        await self._make_action_request(ACTION_WEBHOOK_REMOVE, {"number": name})
        # Refresh webhooks data after change
        self.data["webhooks"] = await self._fetch_webhooks_data()
        await self.async_request_refresh()

    async def set_dnd_force_enabled(self, enabled: bool) -> None:
        """Enable or disable force Do Not Disturb."""
        await self._make_action_request(ACTION_DND, {"enabled": enabled})
        # Refresh DND data after change
        self.data["dnd"] = await self._fetch_dnd_data()
        await self.async_request_refresh()

    async def set_dnd_schedule_enabled(self, enabled: bool) -> None:
        """Enable or disable Do Not Disturb schedule."""
        await self._make_action_request(ACTION_DND_SCHEDULE, {"enabled": enabled})
        # Refresh DND data after change
        self.data["dnd"] = await self._fetch_dnd_data()
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
        _LOGGER.info("HA Action: Making action request - action: %s, data: %s", action, data)
        _LOGGER.debug("HA Action: Full payload: %s", payload)
        await self._make_request("POST", ENDPOINT_ACTION, payload)
        _LOGGER.debug("HA Action: Action request completed successfully")

    async def _make_request(self, method: str, endpoint: str, data: Dict[str, Any] = None) -> None:
        """Make a request to the device."""
        url = f"{self.base_url}{endpoint}"
        _LOGGER.debug("HA HTTP: Making %s request to %s", method, url)
        if data:
            _LOGGER.debug("HA HTTP: Request data: %s", data)
        
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                if method == "POST" and data:
                    headers = {"Content-Type": "application/json"}
                    _LOGGER.debug("HA HTTP: Sending POST request with headers: %s", headers)
                    async with session.post(url, json=data, headers=headers) as response:
                        _LOGGER.debug("HA HTTP: Response status: %s", response.status)
                        response_text = await response.text()
                        _LOGGER.debug("HA HTTP: Response body: %s", response_text)
                        response.raise_for_status()
                        _LOGGER.info("HA HTTP: %s request to %s successful", method, endpoint)
                else:
                    async with session.request(method, url) as response:
                        _LOGGER.debug("HA HTTP: Response status: %s", response.status)
                        response_text = await response.text()
                        _LOGGER.debug("HA HTTP: Response body: %s", response_text)
                        response.raise_for_status()
                        _LOGGER.info("HA HTTP: %s request to %s successful", method, endpoint)
                        
        except asyncio.TimeoutError as err:
            _LOGGER.error("HA HTTP: Timeout during %s request to %s", method, url)
            raise UpdateFailed(f"Timeout during {method} request to {url}") from err
        except aiohttp.ClientError as err:
            _LOGGER.error("Error during %s request to %s: %s", method, url, err)
            raise UpdateFailed(f"Error during {method} request to {url}: {err}") from err

    async def async_setup(self) -> None:
        """Set up the coordinator."""
        # Load call log from storage
        await self._load_call_log()
        
        # Configure HA server URL on device if available
        if self.ha_server_url:
            await self._send_ha_server_config()
        
        # Start WebSocket connection (with small delay to let firmware initialize)
        await asyncio.sleep(2)
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
        _LOGGER.debug("HA Coordinator: Starting shutdown process")
        
        # Set shutdown flag to stop WebSocket reconnection attempts
        self._websocket_shutdown = True
        
        # Stop WebSocket connection
        await self._stop_websocket()
        
        # Save call log to storage
        await self._save_call_log()
        _LOGGER.debug("HA Coordinator: Shutdown complete")

    async def _start_websocket(self) -> None:
        """Start WebSocket connection for real-time updates."""
        try:
            import aiohttp
            # Cancel any existing WebSocket task first
            if self._websocket_task:
                await self._stop_websocket()
            
            self._websocket_task = asyncio.create_task(self._websocket_handler())
            _LOGGER.info("HA WebSocket: Starting WebSocket connection to %s", self.ws_url)
        except Exception as err:
            _LOGGER.error("HA WebSocket: Failed to start WebSocket connection: %s", err)

    async def _stop_websocket(self) -> None:
        """Stop WebSocket connection."""
        _LOGGER.debug("HA WebSocket: Stopping WebSocket connection")
        
        if self._websocket_task:
            _LOGGER.debug("HA WebSocket: Cancelling WebSocket task")
            self._websocket_task.cancel()
            try:
                await self._websocket_task
            except asyncio.CancelledError:
                _LOGGER.debug("HA WebSocket: WebSocket task cancelled successfully")
            except Exception as err:
                _LOGGER.warning("HA WebSocket: Error while cancelling WebSocket task: %s", err)
            self._websocket_task = None
        
        if self._websocket:
            _LOGGER.debug("HA WebSocket: Closing WebSocket connection")
            try:
                await self._websocket.close()
            except Exception as err:
                _LOGGER.warning("HA WebSocket: Error while closing WebSocket: %s", err)
            self._websocket = None

    async def _websocket_handler(self) -> None:
        """Handle WebSocket connection and messages."""
        connection_attempts = 0
        session = None
        
        while True:
            try:
                connection_attempts += 1
                _LOGGER.debug("HA WebSocket: Attempting connection #%d to %s", connection_attempts, self.ws_url)
                
                # Create new session for each connection attempt
                if session:
                    await session.close()
                session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30))
                
                self._websocket = await session.ws_connect(
                    self.ws_url,
                    heartbeat=30,  # Send ping every 30 seconds
                    compress=False,
                    timeout=30  # Connection timeout
                )
                _LOGGER.info("HA WebSocket: Successfully connected to TsuryPhone (attempt #%d)", connection_attempts)
                connection_attempts = 0  # Reset on successful connection
                
                # Send a test ping immediately after connection
                try:
                    self._websocket.ping()
                    _LOGGER.debug("HA WebSocket: Initial ping sent successfully")
                except Exception as ping_err:
                    _LOGGER.warning("HA WebSocket: Failed to send initial ping: %s", ping_err)
                
                # Handle incoming messages with periodic ping
                last_ping_time = time.time()
                async for msg in self._websocket:
                    # Send periodic ping to keep connection alive (every 25 seconds)
                    current_time = time.time()
                    if current_time - last_ping_time > 25:
                        try:
                            self._websocket.ping()
                            _LOGGER.debug("HA WebSocket: Periodic ping sent")
                            last_ping_time = current_time
                        except Exception as ping_err:
                            _LOGGER.warning("HA WebSocket: Failed to send periodic ping: %s", ping_err)
                    
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        try:
                            _LOGGER.debug("HA WebSocket: Received message: %s", msg.data)
                            data = json.loads(msg.data)
                            _LOGGER.debug("HA WebSocket: Parsed data keys: %s", list(data.keys()))
                            
                            # Log state information if present
                            if "state" in data:
                                _LOGGER.info("HA WebSocket: State update received - state: %s", data["state"])
                            if "call" in data:
                                _LOGGER.info("HA WebSocket: Call update received - %s", data["call"])
                            
                            # Process real-time status update
                            await self._process_status_for_call_log(data)
                            
                            # Update the coordinator data immediately with partial update
                            self.data = self.data or {}
                            if "status" not in self.data:
                                self.data["status"] = {}
                            
                            # Merge WebSocket data with existing status data (preserve missing fields)
                            _LOGGER.debug("HA WebSocket: Merging data before update - existing status keys: %s", 
                                         list(self.data["status"].keys()) if "status" in self.data else "None")
                            self._merge_status_data(self.data["status"], data)
                            _LOGGER.debug("HA WebSocket: Status data after merge - keys: %s", 
                                         list(self.data["status"].keys()))
                            
                            _LOGGER.debug("HA WebSocket: Notifying %d listeners of data update", 
                                         len(self.async_update_listeners._listeners) if hasattr(self.async_update_listeners, '_listeners') else 0)
                            self.async_update_listeners()
                            _LOGGER.debug("HA WebSocket: Listeners notified successfully")
                            
                        except json.JSONDecodeError as e:
                            _LOGGER.warning("HA WebSocket: Received invalid JSON: %s. Error: %s", msg.data, e)
                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        _LOGGER.error("HA WebSocket: Protocol error: %s", self._websocket.exception())
                        break
                    elif msg.type == aiohttp.WSMsgType.CLOSE:
                        _LOGGER.warning("HA WebSocket: Connection closed by server")
                        break
                    elif msg.type == aiohttp.WSMsgType.PONG:
                        _LOGGER.debug("HA WebSocket: Received pong")
                
                _LOGGER.warning("HA WebSocket: Message loop ended, connection lost")
                
            except asyncio.CancelledError:
                _LOGGER.info("HA WebSocket: Handler cancelled, shutting down")
                break
            except Exception as err:
                _LOGGER.warning("HA WebSocket: Connection error (attempt #%d): %s", connection_attempts, err)
                
            finally:
                # Clean up current connection
                if self._websocket:
                    try:
                        await self._websocket.close()
                    except Exception:
                        pass
                    self._websocket = None
            
            # Don't reconnect if we're shutting down
            if self._websocket_shutdown:
                _LOGGER.info("HA WebSocket: Shutdown requested, stopping reconnection attempts")
                break
                
            # Exponential backoff with max delay for reconnection
            if connection_attempts == 1:
                delay = 1  # First retry quickly
            elif connection_attempts <= 3:
                delay = 5  # Quick retries for first few attempts
            else:
                delay = min(10 * (2 ** min(connection_attempts - 4, 2)), 30)  # Longer delays after that
                
            _LOGGER.info("HA WebSocket: Waiting %d seconds before reconnection attempt #%d", delay, connection_attempts + 1)
            await asyncio.sleep(delay)
        
        # Final cleanup
        if session:
            await session.close()
        _LOGGER.info("HA WebSocket: Handler terminated")

    def _merge_status_data(self, existing_status: Dict[str, Any], new_status: Dict[str, Any]) -> None:
        """Merge new status data with existing data, preserving fields not in the update.
        
        This prevents sensors from becoming 'unknown' when WebSocket updates don't include
        all the data fields that are present in full status requests.
        """
        _LOGGER.debug("HA Merge: Starting merge - new keys: %s, existing keys: %s", 
                      list(new_status.keys()), list(existing_status.keys()))
        
        for key, value in new_status.items():
            _LOGGER.debug("HA Merge: Processing key '%s' with value: %s", key, value)
            
            if key == "wifi" and isinstance(value, dict) and "wifi" in existing_status:
                # For WiFi data, merge nested fields to preserve missing ones
                if not isinstance(existing_status["wifi"], dict):
                    existing_status["wifi"] = {}
                for wifi_key, wifi_value in value.items():
                    existing_status["wifi"][wifi_key] = wifi_value
                    _LOGGER.debug("HA Merge: Updated wifi.%s = %s", wifi_key, wifi_value)
                # Keep existing WiFi fields that weren't updated
            elif key == "call" and isinstance(value, dict) and "call" in existing_status:
                # For call data, merge nested fields
                if not isinstance(existing_status["call"], dict):
                    existing_status["call"] = {}
                for call_key, call_value in value.items():
                    existing_status["call"][call_key] = call_value
                    _LOGGER.debug("HA Merge: Updated call.%s = %s", call_key, call_value)
            else:
                # For other fields, update directly
                old_value = existing_status.get(key, "<not set>")
                existing_status[key] = value
                _LOGGER.debug("HA Merge: Updated %s: %s -> %s", key, old_value, value)
        
        # Log what was preserved vs updated for debugging
        if _LOGGER.isEnabledFor(logging.DEBUG):
            preserved_keys = set(existing_status.keys()) - set(new_status.keys())
            if preserved_keys:
                _LOGGER.debug("HA Merge: Preserved existing status fields: %s", preserved_keys)
            _LOGGER.debug("HA Merge: Final status keys: %s", list(existing_status.keys()))

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

    async def _fetch_webhooks_data(self) -> Dict[str, Any]:
        """Fetch webhooks data on-demand."""
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                return await self._fetch_endpoint(session, ENDPOINT_WEBHOOKS)
        except Exception as err:
            _LOGGER.warning("Failed to fetch webhooks data: %s", err)
            return {"webhooks": []}

    async def _fetch_phonebook_data(self) -> Dict[str, Any]:
        """Fetch phonebook data on-demand."""
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                return await self._fetch_endpoint(session, ENDPOINT_PHONEBOOK)
        except Exception as err:
            _LOGGER.warning("Failed to fetch phonebook data: %s", err)
            return {"entries": []}

    async def _fetch_blocked_data(self) -> Dict[str, Any]:
        """Fetch blocked numbers data on-demand."""
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                return await self._fetch_endpoint(session, ENDPOINT_BLOCKED)
        except Exception as err:
            _LOGGER.warning("Failed to fetch blocked data: %s", err)
            return {"blocked_numbers": []}

    async def _fetch_dnd_data(self) -> Dict[str, Any]:
        """Fetch DND configuration data on-demand."""
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                return await self._fetch_endpoint(session, ENDPOINT_DND)
        except Exception as err:
            _LOGGER.warning("Failed to fetch DND data: %s", err)
            return {"force_enabled": False, "schedule_enabled": False}

    async def get_webhooks_data(self) -> Dict[str, Any]:
        """Get current webhooks data."""
        if "webhooks" not in self.data:
            # Fetch webhooks data on-demand if not available
            self.data["webhooks"] = await self._fetch_webhooks_data()
        return self.data.get("webhooks", {"webhooks": []})

    async def get_phonebook_data(self) -> Dict[str, Any]:
        """Get current phonebook data."""
        if "phonebook" not in self.data:
            # Fetch phonebook data on-demand if not available
            self.data["phonebook"] = await self._fetch_phonebook_data()
        return self.data.get("phonebook", {"entries": []})

    async def get_blocked_data(self) -> Dict[str, Any]:
        """Get current blocked numbers data."""
        if "blocked" not in self.data:
            # Fetch blocked data on-demand if not available
            self.data["blocked"] = await self._fetch_blocked_data()
        return self.data.get("blocked", {"blocked_numbers": []})

    async def get_dnd_data(self) -> Dict[str, Any]:
        """Get current DND configuration data."""
        if "dnd" not in self.data:
            # Fetch DND data on-demand if not available
            self.data["dnd"] = await self._fetch_dnd_data()
        return self.data.get("dnd", {"force_enabled": False, "schedule_enabled": False})

    async def refresh_full_status(self) -> None:
        """Force a full status refresh to ensure all data is up to date."""
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                # Get fresh full status data
                status = await self._fetch_endpoint(session, ENDPOINT_STATUS)
                
                # Update status data completely
                if not self.data:
                    self.data = {}
                self.data["status"] = status
                
                # Process for call log tracking
                await self._process_status_for_call_log(status)
                
                _LOGGER.debug("Full status refresh completed")
                self.async_update_listeners()
                
        except Exception as err:
            _LOGGER.warning("Failed to refresh full status: %s", err)
