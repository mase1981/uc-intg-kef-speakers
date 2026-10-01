"""Setup flow: enter the speaker IP and model, verify the connection."""

import asyncio
import ipaddress
import logging
import re
from typing import Any

from ucapi import RequestUserInput
from ucapi_framework import BaseSetupFlow

from uc_intg_kef_speakers.client import KEFClient
from uc_intg_kef_speakers.config import KEFConfig
from uc_intg_kef_speakers.const import (
    DEFAULT_MAX_VOLUME,
    DEFAULT_PORT,
    DEFAULT_VOLUME_STEP,
    SPEAKER_LSX,
    SPEAKER_TYPES,
)

_LOG = logging.getLogger(__name__)


def _to_int(value: Any, default: int, low: int, high: int) -> int:
    try:
        return max(low, min(high, int(float(value))))
    except (TypeError, ValueError):
        return default


def _to_bool(value: Any, default: bool) -> bool:
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("true", "1", "yes", "on")


def _lookup_mac(host: str) -> str:
    """Resolve the speaker MAC address from the ARP table (best effort)."""
    try:
        from getmac import get_mac_address  # pylint: disable=import-outside-toplevel
    except ImportError:
        return ""
    try:
        version = ipaddress.ip_address(host).version
        kwargs = {"ip6": host} if version == 6 else {"ip": host}
    except ValueError:
        kwargs = {"hostname": host}
    try:
        mac = get_mac_address(**kwargs)
    except Exception:  # pylint: disable=broad-exception-caught
        mac = None
    if not mac or mac == "00:00:00:00:00:00":
        return ""
    return mac.lower()


class KEFSetupFlow(BaseSetupFlow[KEFConfig]):
    """Add a KEF LS50 Wireless / LSX speaker by IP address."""

    def get_manual_entry_form(self) -> RequestUserInput:
        type_items = [{"id": key, "label": {"en": label}} for key, label in SPEAKER_TYPES.items()]
        return RequestUserInput(
            {"en": "KEF Speaker Setup"},
            [
                {
                    "id": "info",
                    "label": {"en": "KEF Wireless Speakers"},
                    "field": {"label": {"value": {"en": (
                        "Enter the IP address of your KEF LS50 Wireless or LSX speaker (the primary "
                        "speaker). Give the speaker a fixed IP / DHCP reservation in your router. The "
                        "speaker must be on the same network as the Remote. Close the KEF Control / "
                        "KEF Stream app while setting up - the speaker accepts one controller at a time."
                    )}}},
                },
                {
                    "id": "host",
                    "label": {"en": "IP Address"},
                    "field": {"text": {"value": ""}},
                },
                {
                    "id": "speaker_type",
                    "label": {"en": "Speaker Model"},
                    "field": {"dropdown": {"value": SPEAKER_LSX, "items": type_items}},
                },
                {
                    "id": "name",
                    "label": {"en": "Name (optional)"},
                    "field": {"text": {"value": ""}},
                },
                {
                    "id": "max_volume",
                    "label": {"en": "Maximum Volume (%)"},
                    "field": {"number": {"value": DEFAULT_MAX_VOLUME, "min": 1, "max": 100, "steps": 1}},
                },
                {
                    "id": "volume_step",
                    "label": {"en": "Volume Step (%)"},
                    "field": {"number": {"value": DEFAULT_VOLUME_STEP, "min": 1, "max": 20, "steps": 1}},
                },
                {
                    "id": "supports_on",
                    "label": {"en": "Allow power on (disable if your speaker cannot be woken over the network)"},
                    "field": {"checkbox": {"value": True}},
                },
            ],
        )

    async def query_device(self, input_values: dict[str, Any]) -> KEFConfig | RequestUserInput:
        host = str(input_values.get("host", "")).strip()
        if not host:
            raise ValueError("Please enter the IP address of the KEF speaker.")

        speaker_type = input_values.get("speaker_type") or SPEAKER_LSX
        if speaker_type not in SPEAKER_TYPES:
            speaker_type = SPEAKER_LSX

        client = KEFClient(host, DEFAULT_PORT)
        try:
            state = await client.get_state()
            _LOG.info("KEF speaker at %s answered: source=%s on=%s", host, state.source, state.is_on)
        except ConnectionError as err:
            raise ValueError(
                f"Could not reach a KEF speaker at {host}:{DEFAULT_PORT}. Check the IP address, make "
                "sure the speaker is powered and on the same network, and close the KEF app."
            ) from err
        finally:
            await client.close()

        mac = await asyncio.to_thread(_lookup_mac, host)
        base = mac or host
        identifier = f"kef_{re.sub(r'[^A-Za-z0-9]', '_', base)}"
        name = str(input_values.get("name", "")).strip() or SPEAKER_TYPES[speaker_type]

        return KEFConfig(
            identifier=identifier,
            name=name,
            host=host,
            port=DEFAULT_PORT,
            speaker_type=speaker_type,
            mac=mac,
            max_volume=_to_int(input_values.get("max_volume"), DEFAULT_MAX_VOLUME, 1, 100),
            volume_step=_to_int(input_values.get("volume_step"), DEFAULT_VOLUME_STEP, 1, 20),
            supports_on=_to_bool(input_values.get("supports_on"), True),
        )
