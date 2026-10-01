"""Configuration dataclass and manager for the KEF Speakers integration."""

from dataclasses import dataclass

from ucapi_framework import BaseConfigManager

from uc_intg_kef_speakers.const import (
    DEFAULT_MAX_VOLUME,
    DEFAULT_PORT,
    DEFAULT_VOLUME_STEP,
    SPEAKER_LSX,
)


@dataclass
class KEFConfig:
    """Configuration for a single KEF speaker pair."""

    identifier: str = ""
    name: str = ""
    host: str = ""
    port: int = DEFAULT_PORT
    speaker_type: str = SPEAKER_LSX  # "LSX" or "LS50"
    mac: str = ""
    max_volume: int = DEFAULT_MAX_VOLUME  # 1..100 (%)
    volume_step: int = DEFAULT_VOLUME_STEP  # 1..20 (%)
    supports_on: bool = True


class KEFConfigManager(BaseConfigManager[KEFConfig]):
    """Config manager bound to :class:`KEFConfig`."""
