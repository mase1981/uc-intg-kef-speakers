"""KEF speaker select entities (DSP values, bass extension, standby, orientation)."""

import logging
from typing import Any, Awaitable, Callable

from ucapi import StatusCodes, select
from ucapi_framework import SelectEntity

from uc_intg_kef_speakers.config import KEFConfig
from uc_intg_kef_speakers.const import (
    BASS_EXTENSION_OPTIONS,
    DSP_NAMES,
    DSP_OPTION_MAPPING,
    DSP_UNITS,
    ORIENTATION_LABELS,
    STANDBY_LABELS,
    SUB_POLARITY_OPTIONS,
)
from uc_intg_kef_speakers.device import KEFDevice

_LOG = logging.getLogger(__name__)


def _format(value: float | int, unit: str) -> str:
    if value == 0:
        return f"0 {unit}"
    if isinstance(value, float):
        text = f"{value:+.1f}" if unit == "dB" else f"{value:g}"
    else:
        text = f"{value:+d}" if unit == "dB" else str(value)
    return f"{text} {unit}"


class KEFSelect(SelectEntity):
    """Generic select backed by a label->value table and device getter/setter."""

    def __init__(
        self,
        device_config: KEFConfig,
        device: KEFDevice,
        sub_id: str,
        label: str,
        options: dict[str, Any],
        getter: Callable[[KEFDevice], Any],
        setter: Callable[[KEFDevice, Any], Awaitable[None]],
    ) -> None:
        self._device = device
        self._options = options
        self._getter = getter
        self._setter = setter
        super().__init__(
            f"select.{device_config.identifier}.{sub_id}",
            f"{device_config.name} {label}",
            {
                select.Attributes.STATE: select.States.UNKNOWN,
                select.Attributes.OPTIONS: list(options.keys()),
                select.Attributes.CURRENT_OPTION: "",
            },
            cmd_handler=self._handle_command,
        )
        self.subscribe_to_device(device)

    def _current(self) -> str:
        value = self._getter(self._device)
        for label, option_value in self._options.items():
            if option_value == value:
                return label
        return ""

    async def sync_state(self) -> None:
        if not self._device.available:
            self.update({select.Attributes.STATE: select.States.UNAVAILABLE})
            return
        self.update(
            {
                select.Attributes.STATE: select.States.ON,
                select.Attributes.OPTIONS: list(self._options.keys()),
                select.Attributes.CURRENT_OPTION: self._current(),
            }
        )

    async def _handle_command(self, entity: Any, cmd_id: str, params: dict | None = None, *_a: Any) -> StatusCodes:
        labels = list(self._options.keys())
        current = self._current()
        index = labels.index(current) if current in labels else 0
        match cmd_id:
            case select.Commands.SELECT_OPTION:
                option = (params or {}).get("option", "")
            case select.Commands.SELECT_FIRST:
                option = labels[0]
            case select.Commands.SELECT_LAST:
                option = labels[-1]
            case select.Commands.SELECT_NEXT:
                cycle = bool((params or {}).get("cycle", False))
                option = labels[(index + 1) % len(labels)] if cycle else labels[min(index + 1, len(labels) - 1)]
            case select.Commands.SELECT_PREVIOUS:
                cycle = bool((params or {}).get("cycle", False))
                option = labels[(index - 1) % len(labels)] if cycle else labels[max(index - 1, 0)]
            case _:
                return StatusCodes.NOT_IMPLEMENTED
        if option not in self._options:
            return StatusCodes.BAD_REQUEST
        try:
            await self._setter(self._device, self._options[option])
            return StatusCodes.OK
        except Exception as err:  # pylint: disable=broad-exception-caught
            _LOG.error("[%s] Select command error (%s): %s", entity.id, cmd_id, err)
            return StatusCodes.SERVER_ERROR


def _mode_getter(field: str) -> Callable[[KEFDevice], Any]:
    return lambda d: getattr(d.mode, field) if d.mode is not None else None


def _dsp_select(device_config: KEFConfig, device: KEFDevice, which: str) -> KEFSelect:
    unit = DSP_UNITS[which]
    options = {_format(v, unit): v for v in DSP_OPTION_MAPPING[which]}

    async def _set(d: KEFDevice, value: Any) -> None:
        await d.set_dsp(which, value)

    return KEFSelect(
        device_config, device, which, DSP_NAMES[which], options,
        lambda d: d.dsp.get(which), _set,
    )


def create_selects(device_config: KEFConfig, device: KEFDevice) -> list[SelectEntity]:
    async def _set_bass(d: KEFDevice, value: Any) -> None:
        await d.set_mode(bass_extension=value)

    async def _set_polarity(d: KEFDevice, value: Any) -> None:
        await d.set_mode(sub_polarity=value)

    async def _set_standby(d: KEFDevice, value: Any) -> None:
        await d.set_standby_time(value)

    async def _set_orientation(d: KEFDevice, value: Any) -> None:
        await d.set_orientation(value)

    entities: list[SelectEntity] = [
        KEFSelect(
            device_config, device, "bass_extension", "Bass Extension",
            {opt: opt for opt in BASS_EXTENSION_OPTIONS},
            _mode_getter("bass_extension"), _set_bass,
        ),
        KEFSelect(
            device_config, device, "sub_polarity", "Sub Polarity",
            {opt: opt for opt in SUB_POLARITY_OPTIONS},
            _mode_getter("sub_polarity"), _set_polarity,
        ),
        KEFSelect(
            device_config, device, "standby_time", "Auto Standby",
            {label: value for value, label in STANDBY_LABELS.items()},
            # standby_time None means "Never" - only trust it once the source was read.
            lambda d: d.standby_time if d.orientation else "unknown", _set_standby,
        ),
        KEFSelect(
            device_config, device, "orientation", "Speaker Orientation",
            {label: value for value, label in ORIENTATION_LABELS.items()},
            lambda d: d.orientation, _set_orientation,
        ),
    ]
    entities += [_dsp_select(device_config, device, which) for which in DSP_OPTION_MAPPING]
    return entities
