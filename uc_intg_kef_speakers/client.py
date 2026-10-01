"""Async TCP client for KEF LS50 Wireless / LSX speakers (port 50001).

Implements the same binary protocol as aiokef (used by the Home Assistant
``kef`` integration), without the tenacity / async_timeout dependencies:

* GET:  ``G <which> 0x80``           -> reply ``R <which> 0x81 <value> 0xFF``
* SET:  ``S <which> 0x81 <value>``   -> reply ``R 0x11 0xFF`` (OK)

The speaker only handles one client at a time, so the connection is closed
again shortly after the last command (same 1 s keep-alive as aiokef).
"""

import asyncio
import logging
import socket
from dataclasses import dataclass

from uc_intg_kef_speakers.const import (
    BASS_EXTENSION_OPTIONS,
    DEFAULT_PORT,
    DSP_OPTION_MAPPING,
    ORIENTATION_LR,
    ORIENTATION_RL,
    STANDBY_OPTIONS,
)

_LOG = logging.getLogger(__name__)

_TIMEOUT = 2.0
_KEEP_ALIVE = 1.0
_MAX_ATTEMPTS = 3

_RESPONSE_OK = 17
_FULL_RESPONSE_OK = bytes([82, 17, 255])

_SET_START = ord("S")
_SET_MID = 129
_GET_START = ord("G")
_GET_END = 128

# Command ids.
_VOL = ord("%")
_SOURCE = ord("0")
_CONTROL = ord("1")
_MODE = 39
DSP_COMMANDS: dict[str, int] = {
    "desk_db": 40,
    "wall_db": 41,
    "treble_db": 42,
    "high_hz": 43,
    "low_hz": 44,
    "sub_db": 45,
}

_CONTROL_PLAY_PAUSE = 129
_CONTROL_NEXT = 130
_CONTROL_PREV = 131

# Source codes for 20-minute standby, L/R orientation. Other standby times add
# 16 per step, R/L orientation adds 64, "off" adds 128.
_SOURCE_CODES_BASE = {
    "Bluetooth": 9,
    "Bluetooth_paired": 15,  # reported only, cannot be set
    "Aux": 10,
    "Opt": 11,
    "Usb": 12,
    "Wifi": 2,
}

_SOURCE_SET_CODES: dict[str, dict[int | None, tuple[int, int]]] = {}
_SOURCE_RESPONSE: dict[int, tuple[str, int | None, str]] = {}
for _name, _code in _SOURCE_CODES_BASE.items():
    _mapping = {}
    for _i, _standby in enumerate(STANDBY_OPTIONS):
        _lr = _code + _i * 16
        _mapping[_standby] = (_lr, _lr + 64)
        _src = _name.replace("_paired", "")
        _SOURCE_RESPONSE[_lr] = (_src, _standby, ORIENTATION_LR)
        _SOURCE_RESPONSE[_lr + 64] = (_src, _standby, ORIENTATION_RL)
    if not _name.endswith("_paired"):
        _SOURCE_SET_CODES[_name] = _mapping
# Known alias reported by both LSX and LS50W (Wifi, R/L, 60 min) - see aiokef.
_SOURCE_RESPONSE[48] = _SOURCE_RESPONSE[82]

_BASS_EXT_BITS = {"00": "Standard", "10": "Less", "01": "Extra", "11": "Unknown"}
_BASS_EXT_BITS_INV = {v: k for k, v in _BASS_EXT_BITS.items()}


@dataclass
class KEFState:
    """Source / power state of the speaker."""

    source: str
    is_on: bool
    standby_time: int | None
    orientation: str


@dataclass
class KEFMode:
    """DSP mode bit field."""

    desk_mode: bool = False
    wall_mode: bool = False
    phase_correction: bool = False
    high_pass: bool = False
    sub_polarity: str = "+"
    bass_extension: str = "Standard"


def bits_to_mode(bits: int) -> KEFMode | None:
    """Decode the mode byte. Returns None when the speaker reports 255 (off)."""
    if bits == 255:
        return None
    b = f"{bits:08b}"
    return KEFMode(
        desk_mode=b[7] == "1",
        wall_mode=b[6] == "1",
        phase_correction=b[5] == "1",
        high_pass=b[4] == "1",
        sub_polarity="-" if b[1] == "1" else "+",
        bass_extension=_BASS_EXT_BITS[b[2:4]],
    )


def mode_to_bits(mode: KEFMode) -> int:
    """Encode a mode into the byte sent to the speaker."""
    tf = {True: "1", False: "0"}
    bass = _BASS_EXT_BITS_INV.get(mode.bass_extension, "00")
    pol = "1" if mode.sub_polarity == "-" else "0"
    byte = (
        f"1{pol}{bass}{tf[mode.high_pass]}{tf[mode.phase_correction]}"
        f"{tf[mode.wall_mode]}{tf[mode.desk_mode]}"
    )
    return int(byte, 2)


def _parse_reply(message: bytes, reply: bytes) -> int:
    """Pick the matching reply frame and return its value byte."""
    frames = [b"R" + chunk for chunk in reply.split(b"R") if chunk]
    if message[0] == _GET_START:
        which = message[1]
        frame = next((f for f in frames if len(f) > 1 and f[1] == which), None)
        if frame is None:
            raise ConnectionError(f"No reply for query {which} in {reply!r}")
        if not frame.endswith(b"\xff"):
            # The value byte itself was "R" (82) and the split cut the frame.
            return 82
        return frame[-2]
    if _FULL_RESPONSE_OK in frames:
        return _RESPONSE_OK
    raise ConnectionError(f"No OK after SET command, got {reply!r}")


class KEFClient:
    """Low-level async client for one KEF speaker."""

    def __init__(self, host: str, port: int = DEFAULT_PORT) -> None:
        self.host = host
        self.port = port
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._lock = asyncio.Lock()
        self._close_task: asyncio.Task | None = None

    # -- connection ----------------------------------------------------
    @property
    def _connected(self) -> bool:
        return self._writer is not None and not self._writer.is_closing()

    async def _open(self) -> None:
        if self._connected:
            return
        await self._close_now()
        try:
            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port, family=socket.AF_INET),
                timeout=_TIMEOUT,
            )
        except (asyncio.TimeoutError, OSError) as err:
            raise ConnectionError(f"KEF speaker {self.host}:{self.port} unreachable: {err}") from err

    async def _close_now(self) -> None:
        writer, self._reader, self._writer = self._writer, None, None
        if writer is not None:
            try:
                writer.close()
                await asyncio.wait_for(writer.wait_closed(), timeout=_TIMEOUT)
            except (OSError, asyncio.TimeoutError):
                pass

    async def _close_later(self) -> None:
        try:
            await asyncio.sleep(_KEEP_ALIVE)
            async with self._lock:
                await self._close_now()
        except asyncio.CancelledError:
            pass

    def _schedule_close(self) -> None:
        if self._close_task is not None and not self._close_task.done():
            self._close_task.cancel()
        self._close_task = asyncio.create_task(self._close_later())

    async def close(self) -> None:
        """Close the connection immediately."""
        if self._close_task is not None and not self._close_task.done():
            self._close_task.cancel()
        self._close_task = None
        async with self._lock:
            await self._close_now()

    async def _send(self, message: bytes) -> int:
        """Send one message and return the reply value, retrying on failure."""
        last_err: Exception | None = None
        for attempt in range(_MAX_ATTEMPTS):
            async with self._lock:
                try:
                    await self._open()
                    assert self._reader is not None and self._writer is not None
                    self._writer.write(message)
                    await self._writer.drain()
                    reply = await asyncio.wait_for(self._reader.read(100), timeout=_TIMEOUT)
                    if not reply:
                        raise ConnectionError("Connection closed by speaker")
                    value = _parse_reply(message, reply)
                    self._schedule_close()
                    return value
                except (ConnectionError, OSError, asyncio.TimeoutError) as err:
                    last_err = err
                    _LOG.debug("%s: attempt %d for %r failed: %s", self.host, attempt + 1, message, err)
                    await self._close_now()
            await asyncio.sleep(0.3 * (attempt + 1))
        raise ConnectionError(f"{self.host}: command {message!r} failed: {last_err}")

    async def _get(self, which: int) -> int:
        return await self._send(bytes([_GET_START, which, _GET_END]))

    async def _set(self, which: int, value: int) -> None:
        if await self._send(bytes([_SET_START, which, _SET_MID, value])) != _RESPONSE_OK:
            raise ConnectionError(f"{self.host}: SET {which} rejected")

    async def is_reachable(self) -> bool:
        """Return True if a TCP connection can be opened."""
        try:
            async with self._lock:
                await self._open()
            self._schedule_close()
            return True
        except ConnectionError:
            return False

    # -- source / power ------------------------------------------------
    async def get_state(self) -> KEFState:
        """Return source, power, standby time and orientation."""
        response = await self._get(_SOURCE)
        code = response % 128
        if code not in _SOURCE_RESPONSE:
            raise ConnectionError(f"{self.host}: unknown source response {response}")
        source, standby, orientation = _SOURCE_RESPONSE[code]
        return KEFState(source, response <= 128, standby, orientation)

    async def set_source(
        self,
        source: str,
        standby_time: int | None,
        orientation: str,
        power_on: bool = True,
    ) -> None:
        """Set source + standby + orientation; powers the speaker on/off as well."""
        if source not in _SOURCE_SET_CODES:
            raise ValueError(f"Unknown source {source}")
        if standby_time not in STANDBY_OPTIONS:
            standby_time = STANDBY_OPTIONS[0]
        lr, rl = _SOURCE_SET_CODES[source][standby_time]
        code = (rl if orientation == ORIENTATION_RL else lr) % 128
        if not power_on:
            code += 128
        await self._set(_SOURCE, code)

    # -- volume --------------------------------------------------------
    async def get_volume(self) -> tuple[int, bool]:
        """Return (volume 0..100, muted)."""
        raw = await self._get(_VOL)
        return raw % 128, raw >= 128

    async def set_volume(self, volume: int, muted: bool = False) -> None:
        """Set volume 0..100; ``muted`` adds the mute flag."""
        volume = max(0, min(100, int(volume)))
        await self._set(_VOL, volume + (128 if muted else 0))

    # -- transport -----------------------------------------------------
    async def play_pause(self) -> None:
        await self._set(_CONTROL, _CONTROL_PLAY_PAUSE)

    async def next_track(self) -> None:
        await self._set(_CONTROL, _CONTROL_NEXT)

    async def prev_track(self) -> None:
        await self._set(_CONTROL, _CONTROL_PREV)

    async def is_playing(self) -> bool | None:
        """Return True if playing, False if paused, None if unknown."""
        response = await self._get(_CONTROL)
        if response == 129:
            return True
        if response == 128:
            return False
        return None

    # -- DSP -----------------------------------------------------------
    async def get_mode(self) -> KEFMode | None:
        return bits_to_mode(await self._get(_MODE))

    async def set_mode(self, mode: KEFMode) -> None:
        if mode.bass_extension not in BASS_EXTENSION_OPTIONS:
            mode.bass_extension = "Standard"
        await self._set(_MODE, mode_to_bits(mode))

    async def get_dsp(self, which: str) -> float | int | None:
        """Return a DSP value from DSP_OPTION_MAPPING, or None if unknown."""
        response = await self._get(DSP_COMMANDS[which])
        options = DSP_OPTION_MAPPING[which]
        index = response - 128
        if response == 255 or not 0 <= index < len(options):
            return None
        return options[index]

    async def set_dsp(self, which: str, value: float | int) -> None:
        options = DSP_OPTION_MAPPING[which]
        as_type = type(options[0])
        index = options.index(as_type(value))
        await self._set(DSP_COMMANDS[which], index + 128)
