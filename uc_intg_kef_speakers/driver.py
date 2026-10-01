"""Integration driver for KEF LS50 Wireless / LSX speakers."""

from ucapi_framework import BaseIntegrationDriver

from uc_intg_kef_speakers.config import KEFConfig
from uc_intg_kef_speakers.device import KEFDevice
from uc_intg_kef_speakers.media_player import create_media_player
from uc_intg_kef_speakers.remote import create_remote
from uc_intg_kef_speakers.select import create_selects
from uc_intg_kef_speakers.sensor import create_sensors
from uc_intg_kef_speakers.switch import create_switches


class KEFDriver(BaseIntegrationDriver[KEFDevice, KEFConfig]):
    """Builds the entity set for each KEF speaker.

    The entity set only depends on the configured speaker type, so entities are
    registered without waiting for a connection; an offline speaker simply shows
    as unavailable until it is reachable again.
    """

    def __init__(self) -> None:
        super().__init__(
            device_class=KEFDevice,
            entity_classes=[
                create_media_player,
                create_remote,
                create_switches,
                create_selects,
                create_sensors,
            ],
            driver_id="kef_speakers",
            require_connection_before_registry=False,
        )
