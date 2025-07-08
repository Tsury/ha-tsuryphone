"""Constants for the TsuryPhone integration."""

DOMAIN = "tsuryphone"

# Platforms
PLATFORMS = [
    "binary_sensor",
    "button", 
    "number",
    "select",
    "sensor",
    "switch",
    "text",
    "time",
]

# Configuration
CONF_HOST = "host"
CONF_PORT = "port"
CONF_HA_SERVER_URL = "ha_server_url"
CONF_HA_SERVER_PORT = "ha_server_port"

# Default values
DEFAULT_PORT = 80
DEFAULT_HA_SERVER_PORT = 8123
DEFAULT_SCAN_INTERVAL = 30  # Normal polling interval
FAST_REFRESH_INTERVAL = 1    # Fast refresh interval after actions

# Device info
MANUFACTURER = "TsuryPhone Project"
MODEL = "TsuryPhone"

# API endpoints
ENDPOINT_STATUS = "/status"
ENDPOINT_STATS = "/stats"
ENDPOINT_DND = "/dnd"
ENDPOINT_PHONEBOOK = "/phonebook"
ENDPOINT_BLOCKED = "/blocked"
ENDPOINT_WEBHOOKS = "/webhooks"
ENDPOINT_ACTION = "/action"

# Legacy endpoints (kept for backward compatibility checks)
ENDPOINT_ACTION_CALL = "/action/call"
ENDPOINT_ACTION_HANGUP = "/action/hangup"
ENDPOINT_ACTION_RESET = "/action/reset"
ENDPOINT_ACTION_RING = "/action/ring"
ENDPOINT_ACTION_MAINTENANCE_MODE = "/action/maintenance_mode"
ENDPOINT_ACTION_SWITCH_CALL_WAITING = "/action/switch_call_waiting"

# Action types for the unified endpoint
ACTION_CALL = "call_custom"
ACTION_HANGUP = "hangup"
ACTION_RING = "ring"
ACTION_RING_PATTERN = "ring_pattern"
ACTION_DND = "dnd_force"
ACTION_DND_SCHEDULE = "dnd_schedule"
ACTION_QUICK_DIAL_ADD = "add_quick_dial"
ACTION_QUICK_DIAL_REMOVE = "remove_quick_dial"
ACTION_BLOCKED_ADD = "add_blocked"
ACTION_BLOCKED_REMOVE = "remove_blocked"
ACTION_WEBHOOK_ADD = "webhook_add"
ACTION_WEBHOOK_REMOVE = "webhook_remove"
ACTION_CALL_WAITING = "switch_call_waiting"
ACTION_REFRESH = "refresh_data"
ACTION_MAINTENANCE = "maintenance_mode"
ACTION_RESET = "reset"

# Phone states
PHONE_STATES = [
    "Startup",
    "CheckHardware", 
    "CheckLine",
    "Idle",
    "InvalidNumber",
    "IncomingCall",
    "IncomingCallRing",
    "InCall",
    "Dialing",
]
