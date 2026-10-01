"""KEF speaker device - polls one LS50 Wireless / LSX pair over TCP.

The speaker answers source queries even in standby (the source code is offset
by 128 when off), so power state comes from the source reply. If the TCP port
cannot be reached the speaker is reported as unavailable and polling keeps
trying until it comes back.
"""

import asyncio
import logging
from typing import Any

from ucapi_framework import PollingDevice

from uc_intg_kef_speakers.client import KEFClient, KEFMode
from uc_intg_kef_speakers.config import KEFConfig
from uc_intg_kef_speakers.const import (
    DSP_OPTION_MAPPING,
    DSP_POLL_EVERY,
    POLL_INTERVAL,
    SOURCES,
    SPEAKER_LS50,
    SPEAKER_TYPES,
    STATE_ON,
    STATE_STANDBY,
    STATE_UNAVAILABLE,
    TRANSPORT_SOURCES,
)

_LOG = logging.getLogger(__name__)


class KEFDevice(PollingDevice):
    """One KEF wireless speaker pair."""

    def __init__(self, device_config: KEFConfig, **kwargs: Any) -> None:
        super().__init__(device_config, poll_interval=POLL_INTERVAL, **kwargs)
        self._device_config = device_config
        self._client: KEFClient | None = None
        self._state: str = STATE_UNAVAILABLE
        self._poll_count: int = 0

        # Source / power.
        self.source: str = ""
        self.standby_time: int | None = None
        self.orientation: str = ""

        # Volume (0..100 raw speaker scale).
        self.volume: int = 0
        self.muted: bool = False

        # Transport (Wifi / Bluetooth only).
        self.playing: bool | None = None

        # DSP.
        self.mode: KEFMode | None = None
        self.dsp: dict[str, float | int | None] = {key: None for key in DSP_OPTION_MAPPING}

    # -- identity ------------------------------------------------------
    @property
    def identifier(self) -> str:
        return self._device_config.identifier

    @property
    def name(self) -> str:
        return self._device_config.name

    @property
    def address(self) -> str:
        return self._device_config.host

    @property
    def log_id(self) -> str:
        return f"{self.name} ({self.address})"

    @property
    def state(self) -> str:
        return self._state

    @property
    def available(self) -> bool:
        return self._state in (STATE_ON, STATE_STANDBY)

    @property
    def speaker_type(self) -> str:
        return self._device_config.speaker_type

    @property
    def model(self) -> str:
        return SPEAKER_TYPES.get(self.speaker_type, "KEF")

    @property
    def source_list(self) -> list[str]:
        return SOURCES.get(self.speaker_type, SOURCES["LSX"])

    @property
    def supports_on(self) -> bool:
        return bool(self._device_config.supports_on)

    @property
    def max_volume(self) -> int:
        return max(1, min(100, int(self._device_config.max_volume or 100)))

    @property
    def volume_step(self) -> int:
        return max(1, min(20, int(self._device_config.volume_step or 5)))

    @property
    def has_transport(self) -> bool:
        return self._state == STATE_ON and self.source in TRANSPORT_SOURCES

    @property
    def volume_percent(self) -> int:
        """Volume scaled so that ``max_volume`` maps to 100 on the Remote."""
        return max(0, min(100, round(self.volume * 100 / self.max_volume)))

    # -- connection lifecycle ------------------------------------------
    def _get_client(self) -> KEFClient:
        if self._client is None:
            self._client = KEFClient(self._device_config.host, self._device_config.port)
        return self._client

    async def establish_connection(self) -> KEFClient:
        client = self._get_client()
        try:
            await self._update_state(force_dsp=True)
        except ConnectionError as err:
            # Keep polling - the speaker may simply be unplugged right now.
            _LOG.warning("[%s] Speaker not reachable yet: %s", self.log_id, err)
            self._state = STATE_UNAVAILABLE
        self.push_update()
        return client

    async def poll_device(self) -> None:
        try:
            await self._update_state()
        except ConnectionError as err:
            if self._state != STATE_UNAVAILABLE:
                _LOG.info("[%s] Speaker became unavailable: %s", self.log_id, err)
            self._state = STATE_UNAVAILABLE
            self.playing = None
        self.push_update()

    async def _update_state(self, force_dsp: bool = False) -> None:
        client = self._get_client()
        was_available = self.available
        was_on = self._state == STATE_ON

        state = await client.get_state()
        self.source = state.source
        self.standby_time = state.standby_time
        self.orientation = state.orientation
        self._state = STATE_ON if state.is_on else STATE_STANDBY

        self.volume, self.muted = await client.get_volume()

        self.playing = None
        if self.has_transport:
            try:
                self.playing = await client.is_playing()
            except ConnectionError as err:
                _LOG.debug("[%s] Play state query failed: %s", self.log_id, err)

        if not was_available:
            _LOG.info("[%s] Speaker available (%s)", self.log_id, self._state)
            force_dsp = True
        elif self._state == STATE_ON and not was_on:
            force_dsp = True  # LS50 Wireless only reports DSP values while on

        self._poll_count += 1
        if force_dsp or self._poll_count >= DSP_POLL_EVERY:
            self._poll_count = 0
            await self._update_dsp()

    async def _update_dsp(self) -> None:
        # The LSX answers DSP queries in standby; the LS50 Wireless has to be on.
        if self.speaker_type == SPEAKER_LS50 and self._state != STATE_ON:
            return
        client = self._get_client()
        try:
            self.mode = await client.get_mode()
            for key in DSP_OPTION_MAPPING:
                self.dsp[key] = await client.get_dsp(key)
        except ConnectionError as err:
            _LOG.debug("[%s] DSP query failed: %s", self.log_id, err)

    async def disconnect(self) -> None:
        if self._client is not None:
            await self._client.close()
            self._client = None
        self._state = STATE_UNAVAILABLE
        await super().disconnect()

    # -- power ---------------------------------------------------------
    async def _wait_for_power(self, on: bool, attempts: int = 20) -> None:
        client = self._get_client()
        for _ in range(attempts):
            try:
                state = await client.get_state()
                if state.is_on == on:
                    self._state = STATE_ON if on else STATE_STANDBY
                    return
            except ConnectionError:
                pass
            await asyncio.sleep(1)

    async def power_on(self, source: str | None = None) -> None:
        if not self.supports_on:
            _LOG.warning("[%s] Power on is disabled for this speaker", self.log_id)
            return
        client = self._get_client()
        state = await client.get_state()
        target = source or state.source
        if state.is_on and target == state.source:
            self._state = STATE_ON
            self.push_update()
            return
        await client.set_source(target, state.standby_time, state.orientation, power_on=True)
        self.source = target
        await self._wait_for_power(True)
        await self._refresh(force_dsp=True)

    async def power_off(self) -> None:
        client = self._get_client()
        state = await client.get_state()
        if not state.is_on:
            self._state = STATE_STANDBY
            self.push_update()
            return
        await client.set_source(state.source, state.standby_time, state.orientation, power_on=False)
        await self._wait_for_power(False)
        await self._refresh()

    async def power_toggle(self) -> None:
        if self._state == STATE_ON:
            await self.power_off()
        else:
            await self.power_on()

    async def select_source(self, source: str) -> bool:
        if source not in self.source_list:
            _LOG.warning("[%s] Unknown source: %s", self.log_id, source)
            return False
        if self._state != STATE_ON and not self.supports_on:
            _LOG.warning("[%s] Speaker is off and power on is disabled", self.log_id)
            return False
        await self.power_on(source)
        return True

    async def set_standby_time(self, standby_time: int | None) -> None:
        client = self._get_client()
        state = await client.get_state()
        await client.set_source(state.source, standby_time, state.orientation, power_on=state.is_on)
        await self._refresh()

    async def set_orientation(self, orientation: str) -> None:
        client = self._get_client()
        state = await client.get_state()
        await client.set_source(state.source, state.standby_time, orientation, power_on=state.is_on)
        await self._refresh()

    async def _refresh(self, force_dsp: bool = False) -> None:
        try:
            await self._update_state(force_dsp=force_dsp)
        except ConnectionError as err:
            _LOG.debug("[%s] Refresh after command failed: %s", self.log_id, err)
        self.push_update()

    # -- volume --------------------------------------------------------
    async def set_volume_percent(self, percent: int) -> None:
        """Set volume from the Remote's 0..100 scale (scaled to max_volume)."""
        raw = round(max(0, min(100, int(percent))) * self.max_volume / 100)
        await self._set_volume_raw(raw)

    async def _set_volume_raw(self, raw: int) -> None:
        raw = max(0, min(self.max_volume, int(raw)))
        await self._get_client().set_volume(raw, muted=False)
        self.volume, self.muted = raw, False
        self.push_update()

    async def volume_up(self) -> None:
        volume, _ = await self._get_client().get_volume()
        await self._set_volume_raw(volume + self.volume_step)

    async def volume_down(self) -> None:
        volume, _ = await self._get_client().get_volume()
        await self._set_volume_raw(volume - self.volume_step)

    async def set_mute(self, mute: bool) -> None:
        client = self._get_client()
        volume, _ = await client.get_volume()
        await client.set_volume(volume, muted=mute)
        self.volume, self.muted = volume, mute
        self.push_update()

    async def mute_toggle(self) -> None:
        _, muted = await self._get_client().get_volume()
        await self.set_mute(not muted)

    # -- transport -----------------------------------------------------
    async def play_pause(self) -> None:
        await self._get_client().play_pause()
        await asyncio.sleep(0.3)
        await self._refresh()

    async def next_track(self) -> None:
        await self._get_client().next_track()

    async def previous_track(self) -> None:
        await self._get_client().prev_track()

    # -- DSP -----------------------------------------------------------
    async def set_mode(self, **changes: Any) -> None:
        """Change one or more mode fields, keeping the others as reported."""
        client = self._get_client()
        current = await client.get_mode()
        if current is None:
            raise ConnectionError("Speaker did not report its DSP mode (is it on?)")
        for key, value in changes.items():
            setattr(current, key, value)
        await client.set_mode(current)
        self.mode = current
        self.push_update()
        await self._refresh(force_dsp=True)

    async def set_dsp(self, which: str, value: float | int) -> None:
        await self._get_client().set_dsp(which, value)
        self.dsp[which] = value
        self.push_update()
        await self._refresh(force_dsp=True)
