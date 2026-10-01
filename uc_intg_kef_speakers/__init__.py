"""KEF LS50 Wireless / LSX speaker integration for Unfolded Circle Remote Two/3."""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path


def _find_driver_json() -> str:
    """Locate driver.json in source, Docker and PyInstaller (--add-data) layouts."""
    candidates = [
        Path(getattr(sys, "_MEIPASS", "")) / "driver.json" if getattr(sys, "frozen", False) else None,
        Path(__file__).resolve().parent.parent / "driver.json",
        Path(sys.executable).resolve().parent.parent / "driver.json",
        Path.cwd() / "driver.json",
    ]
    for path in candidates:
        if path is not None and path.is_file():
            return str(path)
    return str(Path(__file__).resolve().parent.parent / "driver.json")


DRIVER_JSON = _find_driver_json()

try:
    with open(DRIVER_JSON, "r", encoding="utf-8") as f:
        __version__ = json.load(f).get("version", "0.0.0")
except (FileNotFoundError, json.JSONDecodeError):
    __version__ = "0.0.0"


async def main() -> None:
    """Integration entry point."""
    from ucapi import DeviceStates
    from ucapi_framework import BaseConfigManager, get_config_path

    from uc_intg_kef_speakers.config import KEFConfig
    from uc_intg_kef_speakers.driver import KEFDriver
    from uc_intg_kef_speakers.setup_flow import KEFSetupFlow

    level = os.getenv("UC_LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(name)-28s | %(message)s",
    )
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.getLogger("websockets").setLevel(logging.WARNING)
    logging.getLogger("websockets.server").setLevel(logging.CRITICAL)

    _LOG = logging.getLogger(__name__)
    _LOG.info("Starting KEF Speakers integration v%s", __version__)

    driver = KEFDriver()
    config_path = get_config_path(driver.api.config_dir_path or "")
    config_manager = BaseConfigManager(
        config_path,
        add_handler=driver.on_device_added,
        remove_handler=driver.on_device_removed,
        config_class=KEFConfig,
    )
    driver.config_manager = config_manager

    setup_handler = KEFSetupFlow.create_handler(driver)
    await driver.api.init(DRIVER_JSON, setup_handler)
    await driver.register_all_device_instances(connect=False)

    device_count = len(list(config_manager.all()))
    await driver.api.set_device_state(
        DeviceStates.CONNECTED if device_count > 0 else DeviceStates.DISCONNECTED
    )
    _LOG.info("KEF Speakers integration started - %d device(s) configured", device_count)
    await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
