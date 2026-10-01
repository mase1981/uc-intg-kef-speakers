"""KEF speaker sensor entities (model, source, volume)."""

import logging
from typing import Any, Callable

from ucapi import sensor
from ucapi_framework import SensorEntity

from uc_intg_kef_speakers.config import KEFConfig
from uc_intg_kef_speakers.device import KEFDevice

_LOG = logging.getLogger(__name__)


class KEFInfoSensor(SensorEntity):
    """Text sensor backed by a device getter."""

    def __init__(
        self,
        device_config: KEFConfig,
        device: KEFDevice,
        sub_id: str,
        label: str,
        getter: Callable[[KEFDevice], Any],
        always_available: bool = False,
    ) -> None:
        self._device = device
        self._getter = getter
        self._always_available = always_available
        super().__init__(
            f"sensor.{device_config.identifier}.{sub_id}",
            f"{device_config.name} {label}",
            [],
            {sensor.Attributes.STATE: sensor.States.UNKNOWN, sensor.Attributes.VALUE: ""},
            device_class=sensor.DeviceClasses.CUSTOM,
            options={sensor.Options.CUSTOM_UNIT: ""},
        )
        self.subscribe_to_device(device)

    async def sync_state(self) -> None:
        if not (self._always_available or self._device.available):
            self.update({sensor.Attributes.STATE: sensor.States.UNAVAILABLE})
            return
        self.update({sensor.Attributes.STATE: sensor.States.ON, sensor.Attributes.VALUE: self._getter(self._device)})


def create_sensors(device_config: KEFConfig, device: KEFDevice) -> list[SensorEntity]:
    return [
        KEFInfoSensor(device_config, device, "model", "Model", lambda d: d.model, always_available=True),
        KEFInfoSensor(
            device_config, device, "power", "Power",
            lambda d: {"ON": "On", "STANDBY": "Standby"}.get(d.state, "Unavailable"),
            always_available=True,
        ),
        KEFInfoSensor(device_config, device, "source", "Source", lambda d: d.source or "Unknown"),
        KEFInfoSensor(device_config, device, "volume", "Volume", lambda d: f"{d.volume}%"),
    ]
