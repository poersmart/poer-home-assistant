"""POER Thermostat coordinator."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator


from .const import DOMAIN, ISMOCK, _LOGGER


SCAN_INTERVAL = timedelta(seconds=30)


class DeviceCoordinator(DataUpdateCoordinator):
    """Device data coordinator with persistent session."""

    def __init__(self, hass: HomeAssistant, api_url: str, api_token: str) -> None:
        """Initialize coordinator with API credentials."""
        super().__init__(
            hass, _LOGGER, name="POER Devices", update_interval=SCAN_INTERVAL
        )
        self.api_url = api_url.rstrip("/")
        self.api_token = api_token
        self.session = async_get_clientsession(hass)
        self.headers = {
            "token": self.api_token,
            "Content-Type": "application/json",
        }

    async def _async_update_data(self) -> list[dict]:
        """Fetch device data from cloud."""
        if ISMOCK:
            _LOGGER.info("Mock update_data")
            return [
                {
                    "device_id": "thermo-001",
                    "name": "Living Room",
                    "model": "POER Pro",
                    "firmware": "1.2.3",
                    "current_temp": 22.5,
                    "current_humidity": 45,
                    "target_temp": 23.0,
                    "mode": "auto",
                    "action": "idle",
                    "preset": "home",
                },
                {
                    "device_id": "thermo-002",
                    "name": "Bedroom",
                    "model": "POER Lite",
                    "firmware": "1.1.2",
                    "current_temp": 20.8,
                    "current_humidity": 50,
                    "target_temp": 21.0,
                    "mode": "auto",
                    "action": "idle",
                    "preset": "home",
                },
            ]

        try:
            # 获取设备列表
            devices_url = f"{self.api_url}/api/v1/devices"
            async with self.session.get(devices_url, headers=self.headers) as response:
                if response.status != 200:
                    response_text = await response.text()
                    _LOGGER.error(
                        "API request failed: %d %s", response.status, response_text
                    )
                    raise Exception(f"API error {response.status}")

                devices = await response.json()

            # 获取每个设备的详细状态
            detailed_devices = []
            for device in devices:
                device_id = device["device_id"]
                status_url = f"{self.api_url}/api/v1/devices/{device_id}/status"
                try:
                    async with self.session.get(
                        status_url, headers=self.headers
                    ) as response:
                        if response.status != 200:
                            _LOGGER.warning(
                                "Failed to get status for device %s: %d",
                                device_id,
                                response.status,
                            )
                            status_data = {}
                        else:
                            status_data = await response.json()
                except aiohttp.ClientError as e:
                    _LOGGER.warning("Network error for device %s: %s", device_id, e)
                    status_data = {}

                device_info = {**device, **status_data}
                detailed_devices.append(device_info)

            return detailed_devices

        except aiohttp.ClientError as e:
            _LOGGER.error("Network error during update: %s", e)
            raise
        except Exception as e:
            _LOGGER.error("Unexpected error during update: %s", e)
            raise

    async def send_command(self, device_id: str, endpoint: str, payload: dict) -> bool:
        """Send command to device via API."""
        url = f"{self.api_url}/api/v1/devices/{device_id}/{endpoint}"

        if ISMOCK:
            _LOGGER.info("Mock send_command: %s %s", url, payload)
            return True

        try:
            async with self.session.post(
                url, json=payload, headers=self.headers
            ) as resp:
                if resp.status == 200:
                    return True

                response_text = await resp.text()
                _LOGGER.error(
                    "Command failed for %s: %d %s",
                    device_id,
                    resp.status,
                    response_text,
                )
                return False
        except aiohttp.ClientError as e:
            _LOGGER.error("Network error for device %s: %s", device_id, e)
            return False
