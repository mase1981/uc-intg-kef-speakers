"""KEF speaker media_player entity."""

import logging
from typing import Any

from ucapi import StatusCodes, media_player
from ucapi_framework import MediaPlayerEntity

from uc_intg_kef_speakers.config import KEFConfig
from uc_intg_kef_speakers.const import STATE_STANDBY
from uc_intg_kef_speakers.device import KEFDevice

_LOG = logging.getLogger(__name__)


class KEFMediaPlayer(MediaPlayerEntity):
    """Media player for a KEF LS50 Wireless / LSX speaker pair."""

    def __init__(self, device_config: KEFConfig, device: KEFDevice) -> None:
        self._device = device
        features = [
            media_player.Features.VOLUME,
            media_player.Features.VOLUME_UP_DOWN,
            media_player.Features.MUTE_TOGGLE,
            media_player.Features.MUTE,
            media_player.Features.UNMUTE,
            media_player.Features.PLAY_PAUSE,
            media_player.Features.NEXT,
            media_player.Features.PREVIOUS,
            media_player.Features.SELECT_SOURCE,
        ]
        if device_config.supports_on:
            features += [media_player.Features.ON_OFF, media_player.Features.TOGGLE]
        super().__init__(
            f"media_player.{device_config.identifier}",
            device_config.name,
            features,
            {
                media_player.Attributes.STATE: media_player.States.UNKNOWN,
                media_player.Attributes.VOLUME: 0,
                media_player.Attributes.MUTED: False,
                media_player.Attributes.SOURCE: "",
                media_player.Attributes.SOURCE_LIST: device.source_list,
            },
            device_class=media_player.DeviceClasses.SPEAKER,
            cmd_handler=self._handle_command,
        )
        self.subscribe_to_device(device)

    async def sync_state(self) -> None:
        if not self._device.available:
            self.update({media_player.Attributes.STATE: media_player.States.UNAVAILABLE})
            return
        if self._device.state == STATE_STANDBY:
            state = media_player.States.OFF
        elif self._device.playing is True:
            state = media_player.States.PLAYING
        elif self._device.playing is False:
            state = media_player.States.PAUSED
        else:
            state = media_player.States.ON
        self.update(
            {
                media_player.Attributes.STATE: state,
                media_player.Attributes.VOLUME: self._device.volume_percent,
                media_player.Attributes.MUTED: self._device.muted,
                media_player.Attributes.SOURCE: self._device.source,
                media_player.Attributes.SOURCE_LIST: self._device.source_list,
            }
        )

    async def _handle_command(self, entity: Any, cmd_id: str, params: dict | None = None, *_a: Any) -> StatusCodes:
        params = params or {}
        try:
            match cmd_id:
                case media_player.Commands.ON:
                    await self._device.power_on()
                case media_player.Commands.OFF:
                    await self._device.power_off()
                case media_player.Commands.TOGGLE:
                    await self._device.power_toggle()
                case media_player.Commands.VOLUME:
                    await self._device.set_volume_percent(int(params.get("volume", 0)))
                case media_player.Commands.VOLUME_UP:
                    await self._device.volume_up()
                case media_player.Commands.VOLUME_DOWN:
                    await self._device.volume_down()
                case media_player.Commands.MUTE_TOGGLE:
                    await self._device.mute_toggle()
                case media_player.Commands.MUTE:
                    await self._device.set_mute(True)
                case media_player.Commands.UNMUTE:
                    await self._device.set_mute(False)
                case media_player.Commands.PLAY_PAUSE:
                    await self._device.play_pause()
                case media_player.Commands.NEXT:
                    await self._device.next_track()
                case media_player.Commands.PREVIOUS:
                    await self._device.previous_track()
                case media_player.Commands.SELECT_SOURCE:
                    if not await self._device.select_source(params.get("source", "")):
                        return StatusCodes.BAD_REQUEST
                case _:
                    return StatusCodes.NOT_IMPLEMENTED
            return StatusCodes.OK
        except Exception as err:  # pylint: disable=broad-exception-caught
            _LOG.error("[%s] Command error (%s): %s", entity.id, cmd_id, err)
            return StatusCodes.SERVER_ERROR


def create_media_player(device_config: KEFConfig, device: KEFDevice) -> list[KEFMediaPlayer]:
    return [KEFMediaPlayer(device_config, device)]
