"""Constants for the KEF Speakers integration.

Protocol values are taken from aiokef (used by the Home Assistant ``kef``
integration) for the KEF LS50 Wireless and LSX (first generation) speakers.
"""

# TCP control port of the speaker.
DEFAULT_PORT = 50001

# Speaker models supported by the TCP protocol.
SPEAKER_LSX = "LSX"
SPEAKER_LS50 = "LS50"
SPEAKER_TYPES: dict[str, str] = {
    SPEAKER_LSX: "KEF LSX",
    SPEAKER_LS50: "KEF LS50 Wireless",
}

# Device reachability / power states.
STATE_ON = "ON"
STATE_STANDBY = "STANDBY"
STATE_UNAVAILABLE = "UNAVAILABLE"

# Input sources (code for 20-minute standby, L/R orientation).
SOURCE_WIFI = "Wifi"
SOURCE_BLUETOOTH = "Bluetooth"
SOURCE_AUX = "Aux"
SOURCE_OPT = "Opt"
SOURCE_USB = "Usb"

SOURCES: dict[str, list[str]] = {
    SPEAKER_LSX: [SOURCE_WIFI, SOURCE_BLUETOOTH, SOURCE_AUX, SOURCE_OPT],
    SPEAKER_LS50: [SOURCE_WIFI, SOURCE_BLUETOOTH, SOURCE_AUX, SOURCE_OPT, SOURCE_USB],
}

# Sources that support play/pause and track skipping.
TRANSPORT_SOURCES = (SOURCE_WIFI, SOURCE_BLUETOOTH)

# Auto-standby options in minutes (None = never).
STANDBY_20 = 20
STANDBY_60 = 60
STANDBY_NEVER = None
STANDBY_OPTIONS: list[int | None] = [STANDBY_20, STANDBY_60, STANDBY_NEVER]
STANDBY_LABELS: dict[int | None, str] = {
    STANDBY_20: "20 Minutes",
    STANDBY_60: "60 Minutes",
    STANDBY_NEVER: "Never",
}

ORIENTATION_LR = "L/R"
ORIENTATION_RL = "R/L"
ORIENTATION_LABELS: dict[str, str] = {
    ORIENTATION_LR: "Left / Right",
    ORIENTATION_RL: "Right / Left",
}

# Mode (bit field) options.
BASS_EXTENSION_OPTIONS = ["Less", "Standard", "Extra"]
SUB_POLARITY_OPTIONS = ["+", "-"]


def _arange(start: float, end: float, step: float) -> list:
    return [x * step for x in range(int(start / step), int(end / step) + 1)]


# DSP value tables. The speaker reports/accepts the index into these lists + 128.
DSP_DESK_DB = "desk_db"
DSP_WALL_DB = "wall_db"
DSP_TREBLE_DB = "treble_db"
DSP_HIGH_HZ = "high_hz"
DSP_LOW_HZ = "low_hz"
DSP_SUB_DB = "sub_db"

DSP_OPTION_MAPPING: dict[str, list] = {
    DSP_DESK_DB: _arange(-6, 0, 0.5),
    DSP_WALL_DB: _arange(-6, 0, 0.5),
    DSP_TREBLE_DB: _arange(-2, 2, 0.5),
    DSP_HIGH_HZ: _arange(50, 120, 5),
    DSP_LOW_HZ: _arange(40, 250, 5),
    DSP_SUB_DB: _arange(-10, 10, 1),
}

DSP_UNITS: dict[str, str] = {
    DSP_DESK_DB: "dB",
    DSP_WALL_DB: "dB",
    DSP_TREBLE_DB: "dB",
    DSP_HIGH_HZ: "Hz",
    DSP_LOW_HZ: "Hz",
    DSP_SUB_DB: "dB",
}

DSP_NAMES: dict[str, str] = {
    DSP_DESK_DB: "Desk Mode dB",
    DSP_WALL_DB: "Wall Mode dB",
    DSP_TREBLE_DB: "Treble dB",
    DSP_HIGH_HZ: "High-Pass Hz",
    DSP_LOW_HZ: "Sub Out Low-Pass Hz",
    DSP_SUB_DB: "Sub Gain dB",
}

# Setup defaults.
DEFAULT_MAX_VOLUME = 100
DEFAULT_VOLUME_STEP = 5

# Poll intervals.
POLL_INTERVAL = 10
DSP_POLL_EVERY = 6  # refresh DSP settings every N polls
