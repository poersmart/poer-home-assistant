"""POER Thermostat coordinator."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator


from .const import _LOGGER


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
            "Authorization": "beer " + self.api_token,
            "Content-Type": "application/json",
        }

    async def _async_update_data(self) -> list[dict]:
        """Fetch device data from cloud."""

        try:
            # 获取设备列表
            devices_url = f"{self.api_url}/speaker/ha/v1.0"
            payload = {
                "requestId": "111",
                "inputs": [{"intent": "action.devices.SYNC"}],
            }
            async with self.session.post(
                devices_url, json=payload, headers=self.headers
            ) as response:
                if response.status != 200:
                    response_text = await response.text()
                    _LOGGER.error(
                        "API request failed: %d %s", response.status, response_text
                    )
                    return False
                    # raise Exception(f"API error {response.status}")

                rspJson = await response.json()
                devices = rspJson["payload"]["devices"]
            # 获取每个设备的详细状态
            detailed_devices = []
            for device in devices:
                device_id = device["id"]
                payload = {
                    "requestId": "111",
                    "inputs": [
                        {
                            "intent": "action.devices.QUERY",
                            "payload": {"devices": [{"id": device_id}]},
                        }
                    ],
                }
                status_data = {}
                status_url = f"{self.api_url}/speaker/ha/v1.0"
                try:
                    async with self.session.post(
                        status_url, json=payload, headers=self.headers
                    ) as response:
                        if response.status != 200:
                            _LOGGER.warning(
                                "Failed to get status for device %s: %d",
                                device_id,
                                response.status,
                            )
                        else:
                            status_data = await response.json()
                except aiohttp.ClientError as e:
                    _LOGGER.warning("Network error for device %s: %s", device_id, e)

                poerMode = status_data["payload"]["devices"][device_id][
                    "thermostatMode"
                ]
                device_info = {
                    "device_id": device["id"],
                    "name": device["name"]["name"],
                    "model": device["deviceInfo"]["model"],
                    "firmware": device["deviceInfo"]["swVersion"],
                    "current_temp": status_data["payload"]["devices"][device_id][
                        "thermostatTemperatureAmbient"
                    ],
                    "current_humidity": status_data["payload"]["devices"][device_id][
                        "thermostatHumidityAmbient"
                    ],
                    "target_temp": status_data["payload"]["devices"][device_id][
                        "thermostatTemperatureSetpoint"
                    ],
                    "action": status_data["payload"]["devices"][device_id][
                        "thermostatAction"
                    ],
                    "min_temp": device["attributes"]["thermostatTemperatureRange"][
                        "minThresholdCelsius"
                    ],
                    "max_temp": device["attributes"]["thermostatTemperatureRange"][
                        "maxThresholdCelsius"
                    ],
                }
                poerMode = status_data["payload"]["devices"][device_id][
                    "thermostatMode"
                ]
                # poer: mode(preset): auto(home) heat/man(home) off(off) eco(away)
                # ha: mode(preset): auto(home) heat/man(home) off(home) (away)
                if poerMode in ("auto", "heat", "off"):
                    device_info["preset"] = "home"
                    device_info["mode"] = poerMode
                elif poerMode == "eco":
                    device_info["preset"] = "away"
                    device_info["mode"] = "heat"
                detailed_devices.append(device_info)

            return detailed_devices

        except aiohttp.ClientError as e:
            _LOGGER.error("Network error during update: %s", e)
            raise
        except Exception as e:
            _LOGGER.error("Unexpected error during update: %s", e)
            raise

    async def send_command(self, device_id: str, endpoint: str, data: dict) -> bool:
        """Send command to device via API."""
        payload = {
            "requestId": "112",
            "inputs": [
                {
                    "intent": "action.devices.EXECUTE",
                    "payload": {
                        "commands": [
                            {
                                "devices": [{"id": device_id}],
                                "execution": [{}],
                            }
                        ]
                    },
                }
            ],
        }
        if endpoint == "set_temp":
            execution = [
                {
                    "command": "action.devices.commands.ThermostatTemperatureSetpoint",
                    "params": {"thermostatTemperatureSetpoint": data["temperature"]},
                }
            ]
        elif endpoint == "set_mode":
            mode = data["mode"]
            preset = data["preset"]
            if preset == "away":
                mode = "eco"
            execution = [
                {
                    "command": "action.devices.commands.ThermostatSetMode",
                    "params": {"thermostatMode": mode},
                }
            ]
        payload["inputs"][0]["payload"]["commands"][0]["execution"] = execution

        url = f"{self.api_url}/speaker/ha/v1.0"

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
