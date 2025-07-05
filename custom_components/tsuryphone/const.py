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

# Default values
DEFAULT_PORT = 80
DEFAULT_SCAN_INTERVAL = 30

# Device info
MANUFACTURER = "TsuryPhone Project"
MODEL = "TsuryPhone"

# API endpoints
ENDPOINT_STATUS = "/status"
ENDPOINT_STATS = "/stats"
ENDPOINT_DND = "/dnd"
ENDPOINT_PHONEBOOK = "/phonebook"
ENDPOINT_SCREENED = "/screened"
ENDPOINT_ACTION_CALL = "/action/call"
ENDPOINT_ACTION_HANGUP = "/action/hangup"
ENDPOINT_ACTION_RESET = "/action/reset"
ENDPOINT_ACTION_RING = "/action/ring"
ENDPOINT_ACTION_DOWNLOAD_MODE = "/action/download_mode"
ENDPOINT_ACTION_SWITCH_CALL_WAITING = "/action/switch_call_waiting"

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
