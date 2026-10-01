"""KEF speaker remote entity - full button surface for activities."""

import logging
from typing import Any

from ucapi import StatusCodes, remote
from ucapi.ui import Buttons, Size, UiPage, create_btn_mapping, create_ui_icon, create_ui_text
from ucapi_framework import RemoteEntity

from uc_intg_kef_speakers.config import KEFConfig
from uc_intg_kef_speakers.const import SOURCES, STANDBY_20, STANDBY_60, STANDBY_NEVER
from uc_intg_kef_speakers.device import KEFDevice

_LOG = logging.getLogger(__name__)


def _source_cmd(source: str) -> str:
    return f"SOURCE_{source.upper()}"


class KEFRemote(RemoteEntity):
    """Exposes all KEF functions as simple commands for activities."""

    def __init__(self, device_config: KEFConfig, device: KEFDevice) -> None:
        self._device = device
        sources = SOURCES.get(device_config.speaker_type, SOURCES["LSX"])
        self._source_cmds = {_source_cmd(src): src for src in sources}

        simple_commands = (
            ["POWER_TOGGLE", "POWER_ON", "POWER_OFF"]
            + ["VOLUME_UP", "VOLUME_DOWN", "MUTE_TOGGLE", "MUTE", "UNMUTE"]
            + ["PLAY_PAUSE", "NEXT", "PREVIOUS"]
            + list(self._source_cmds.keys())
            + ["STANDBY_20_MIN", "STANDBY_60_MIN", "STANDBY_NEVER"]
        )

        source_items = [
            create_ui_text(src, i % 4, i // 4, cmd=cmd)
            for i, (cmd, src) in enumerate(self._source_cmds.items())
        ]
        super().__init__(
            f"remote.{device_config.identifier}",
            f"{device_config.name} Remote",
            [remote.Features.ON_OFF, remote.Features.TOGGLE, remote.Features.SEND_CMD],
            {remote.Attributes.STATE: remote.States.UNKNOWN},
            simple_commands=simple_commands,
            button_mapping=[
                create_btn_mapping(Buttons.POWER, short="POWER_TOGGLE"),
                create_btn_mapping(Buttons.VOLUME_UP, short="VOLUME_UP"),
                create_btn_mapping(Buttons.VOLUME_DOWN, short="VOLUME_DOWN"),
                create_btn_mapping(Buttons.MUTE, short="MUTE_TOGGLE"),
                create_btn_mapping(Buttons.PLAY, short="PLAY_PAUSE"),
                create_btn_mapping(Buttons.NEXT, short="NEXT"),
                create_btn_mapping(Buttons.PREV, short="PREVIOUS"),
            ],
            ui_pages=[
                UiPage("main", "KEF", grid=Size(4, 6), items=[
                    create_ui_icon("uc:power-on", 0, 0, cmd="POWER_ON"),
                    create_ui_icon("uc:power-off", 3, 0, cmd="POWER_OFF"),
                    create_ui_text("Prev", 0, 2, cmd="PREVIOUS"),
                    create_ui_icon("uc:play", 1, 2, size=Size(2, 1), cmd="PLAY_PAUSE"),
                    create_ui_text("Next", 3, 2, cmd="NEXT"),
                    create_ui_icon("uc:volume-down", 0, 4, cmd="VOLUME_DOWN"),
                    create_ui_icon("uc:mute", 1, 4, size=Size(2, 1), cmd="MUTE_TOGGLE"),
                    create_ui_icon("uc:volume-up", 3, 4, cmd="VOLUME_UP"),
                ]),
                UiPage("sources", "Sources", grid=Size(4, 6), items=source_items + [
                    create_ui_text("Standby 20m", 0, 3, size=Size(2, 1), cmd="STANDBY_20_MIN"),
                    create_ui_text("Standby 60m", 2, 3, size=Size(2, 1), cmd="STANDBY_60_MIN"),
                    create_ui_text("Never Standby", 0, 4, size=Size(4, 1), cmd="STANDBY_NEVER"),
                ]),
            ],
            cmd_handler=self._handle_command,
        )
        self.subscribe_to_device(device)

    async def sync_state(self) -> None:
        if not self._device.available:
            state = remote.States.UNAVAILABLE
        elif self._device.state == "ON":
            state = remote.States.ON
        else:
            state = remote.States.OFF
        self.update({remote.Attributes.STATE: state})

    async def _handle_command(self, entity: Any, cmd_id: str, params: dict | None = None, *_a: Any) -> StatusCodes:
        try:
            if cmd_id == remote.Commands.ON:
                await self._device.power_on()
                return StatusCodes.OK
            if cmd_id == remote.Commands.OFF:
                await self._device.power_off()
                return StatusCodes.OK
            if cmd_id == remote.Commands.TOGGLE:
                await self._device.power_toggle()
                return StatusCodes.OK
            if cmd_id != remote.Commands.SEND_CMD:
                return StatusCodes.NOT_IMPLEMENTED
            return await self._run((params or {}).get("command", ""))
        except Exception as err:  # pylint: disable=broad-exception-caught
            _LOG.error("[%s] Remote command error (%s): %s", entity.id, cmd_id, err)
            return StatusCodes.SERVER_ERROR

    async def _run(self, command: str) -> StatusCodes:
        actions = {
            "POWER_TOGGLE": self._device.power_toggle,
            "POWER_ON": self._device.power_on,
            "POWER_OFF": self._device.power_off,
            "VOLUME_UP": self._device.volume_up,
            "VOLUME_DOWN": self._device.volume_down,
            "MUTE_TOGGLE": self._device.mute_toggle,
            "MUTE": lambda: self._device.set_mute(True),
            "UNMUTE": lambda: self._device.set_mute(False),
            "PLAY_PAUSE": self._device.play_pause,
            "NEXT": self._device.next_track,
            "PREVIOUS": self._device.previous_track,
            "STANDBY_20_MIN": lambda: self._device.set_standby_time(STANDBY_20),
            "STANDBY_60_MIN": lambda: self._device.set_standby_time(STANDBY_60),
            "STANDBY_NEVER": lambda: self._device.set_standby_time(STANDBY_NEVER),
        }
        if command in actions:
            await actions[command]()
            return StatusCodes.OK
        if command in self._source_cmds:
            ok = await self._device.select_source(self._source_cmds[command])
            return StatusCodes.OK if ok else StatusCodes.BAD_REQUEST
        return StatusCodes.NOT_IMPLEMENTED


def create_remote(device_config: KEFConfig, device: KEFDevice) -> list[KEFRemote]:
    return [KEFRemote(device_config, device)]
