"""KEF speaker switch entities (DSP mode toggles)."""

import logging
from typing import Any

from ucapi import StatusCodes, switch
from ucapi_framework import SwitchEntity

from uc_intg_kef_speakers.config import KEFConfig
from uc_intg_kef_speakers.device import KEFDevice

_LOG = logging.getLogger(__name__)

# KEFMode field -> label.
MODE_SWITCHES: dict[str, str] = {
    "desk_mode": "Desk Mode",
    "wall_mode": "Wall Mode",
    "phase_correction": "Phase Correction",
    "high_pass": "High-Pass Mode",
}


class KEFModeSwitch(SwitchEntity):
    """A boolean field of the KEF DSP mode."""

    def __init__(self, device_config: KEFConfig, device: KEFDevice, field: str, label: str) -> None:
        self._device = device
        self._field = field
        super().__init__(
            f"switch.{device_config.identifier}.{field}",
            f"{device_config.name} {label}",
            [switch.Features.ON_OFF, switch.Features.TOGGLE],
            {switch.Attributes.STATE: switch.States.UNKNOWN},
            cmd_handler=self._handle_command,
        )
        self.subscribe_to_device(device)

    def _value(self) -> bool | None:
        mode = self._device.mode
        return None if mode is None else bool(getattr(mode, self._field))

    async def sync_state(self) -> None:
        value = self._value()
        if not self._device.available:
            state = switch.States.UNAVAILABLE
        elif value is None:
            state = switch.States.UNKNOWN
        else:
            state = switch.States.ON if value else switch.States.OFF
        self.update({switch.Attributes.STATE: state})

    async def _handle_command(self, entity: Any, cmd_id: str, params: dict | None = None, *_a: Any) -> StatusCodes:
        try:
            if cmd_id == switch.Commands.ON:
                target = True
            elif cmd_id == switch.Commands.OFF:
                target = False
            elif cmd_id == switch.Commands.TOGGLE:
                target = not bool(self._value())
            else:
                return StatusCodes.NOT_IMPLEMENTED
            await self._device.set_mode(**{self._field: target})
            return StatusCodes.OK
        except Exception as err:  # pylint: disable=broad-exception-caught
            _LOG.error("[%s] Switch command error (%s): %s", entity.id, cmd_id, err)
            return StatusCodes.SERVER_ERROR


def create_switches(device_config: KEFConfig, device: KEFDevice) -> list[SwitchEntity]:
    return [KEFModeSwitch(device_config, device, field, label) for field, label in MODE_SWITCHES.items()]
