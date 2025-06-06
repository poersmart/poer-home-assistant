"""Climate platform for POER Thermostat."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any, Final, List

from homeassistant.components.climate import (
    ATTR_PRESET_MODE,
    ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW,
    ATTR_TEMPERATURE,
    PRESET_AWAY,
    PRESET_ECO,
    PRESET_HOME,
    PRESET_NONE,
    PRESET_SLEEP,
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PRECISION_HALVES, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

_LOGGER: Final = logging.getLogger(__name__)

DEFAULT_NAME = "POER Thermostat"
DEFAULT_MIN_TEMP = 7.0
DEFAULT_MAX_TEMP = 35.0
DEFAULT_TEMP_STEP = 0.5

SCAN_INTERVAL = timedelta(seconds=30)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up climate platform."""
    coordinator = DeviceCoordinator(hass, entry.data)

    # Proper initialization without async_config_entry_first_refresh()
    try:
        await coordinator.async_refresh()
        if not coordinator.last_update_success:
            _LOGGER.error("Initial data refresh failed")
            return False
    except Exception as e:
        _LOGGER.error("Setup failed: %s", e)
        return False

    entities = [
        POERThermostat(coordinator, device["device_id"], device)
        for device in coordinator.data
    ]

    async_add_entities(entities)
    return True


class DeviceCoordinator(DataUpdateCoordinator):
    """Device data coordinator."""

    def __init__(self, hass: HomeAssistant, config: dict[str, Any]) -> None:
        """Initialize coordinator."""
        super().__init__(
            hass, _LOGGER, name="POER Devices", update_interval=SCAN_INTERVAL
        )
        self.config = config

    async def _async_update_data(self) -> List[dict]:
        """Fetch device data from cloud."""
        try:
            devices = await self._api_request("GET", "devices")

            detailed_devices = []
            for device in devices:
                status = await self._api_request(
                    "GET", f"device/{device['device_id']}/status"
                )
                device_info = {**device, **status}
                detailed_devices.append(device_info)

            return detailed_devices
        except Exception as e:
            _LOGGER.error("Update failed: %s", e)
            raise

    async def _api_request(self, method: str, endpoint: str, data: dict = None) -> dict:
        """Make API request to cloud."""
        # Replace with actual API call in production
        if endpoint == "devices":
            return [
                {
                    "device_id": "thermo-001",
                    "name": "Living Room",
                    "model": "POER Pro",
                    "firmware": "1.2.3",
                },
                {
                    "device_id": "thermo-002",
                    "name": "Bedroom",
                    "model": "POER Lite",
                    "firmware": "1.1.2",
                },
            ]
        elif "status" in endpoint:
            return {
                "current_temp": 22.5 if "001" in endpoint else 20.8,
                "current_humidity": 45 if "001" in endpoint else 50,
                "target_temp": 23.0 if "001" in endpoint else 21.0,
                "mode": "auto",
                "action": "idle",
                "preset": "home" if "001" in endpoint else "sleep",
            }
        return {"status": "ok"}


class POERThermostat(CoordinatorEntity, ClimateEntity):
    """POER Thermostat entity."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: DeviceCoordinator, device_id: str, device_data: dict
    ) -> None:
        """Initialize thermostat."""
        super().__init__(coordinator)
        self.device_id = device_id
        self._device_data = device_data

        self._attr_unique_id = device_id
        self._attr_name = device_data.get("name", DEFAULT_NAME)
        self._attr_model = device_data.get("model", "Unknown Model")
        self._attr_manufacturer = "POER Inc"
        self._attr_firmware_version = device_data.get("firmware", "Unknown")

        self._attr_supported_features = (
            ClimateEntityFeature.TARGET_TEMPERATURE
            | ClimateEntityFeature.TARGET_TEMPERATURE_RANGE
            | ClimateEntityFeature.PRESET_MODE
        )

        self._attr_min_temp = DEFAULT_MIN_TEMP
        self._attr_max_temp = DEFAULT_MAX_TEMP
        self._attr_target_temperature_step = DEFAULT_TEMP_STEP
        self._attr_precision = PRECISION_HALVES
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS

        self._attr_hvac_modes = [
            HVACMode.AUTO,
            # HVACMode.COOL,
            # HVACMode.HEAT,
            HVACMode.OFF,
        ]
        self._attr_preset_modes = [
            PRESET_NONE,
            PRESET_HOME,
            # PRESET_AWAY,
            # PRESET_SLEEP,
            PRESET_ECO,
        ]

        self._update_from_data()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Update entity from coordinator."""
        for device in self.coordinator.data:
            if device.get("device_id") == self.device_id:
                self._device_data = device
                break

        self._update_from_data()
        self.async_write_ha_state()

    def _update_from_data(self) -> None:
        """Update state from device data."""
        self._attr_current_temperature = self._device_data.get("current_temp")
        self._attr_current_humidity = self._device_data.get("current_humidity")
        self._attr_target_temperature = self._device_data.get("target_temp")
        self._attr_target_temperature_low = self._device_data.get("temp_low")
        self._attr_target_temperature_high = self._device_data.get("temp_high")

        mode_map = {
            "auto": HVACMode.AUTO,
            "cool": HVACMode.COOL,
            "heat": HVACMode.HEAT,
            "off": HVACMode.OFF,
        }
        self._attr_hvac_mode = mode_map.get(
            self._device_data.get("mode", "off"), HVACMode.OFF
        )

        action_map = {
            "cooling": HVACAction.COOLING,
            "heating": HVACAction.HEATING,
            "idle": HVACAction.IDLE,
        }
        self._attr_hvac_action = action_map.get(
            self._device_data.get("action", "idle"), HVACAction.IDLE
        )

        preset_map = {
            "home": PRESET_HOME,
            "away": PRESET_AWAY,
            "sleep": PRESET_SLEEP,
            "eco": PRESET_ECO,
            "none": PRESET_NONE,
        }
        self._attr_preset_mode = preset_map.get(
            self._device_data.get("preset", "none"), PRESET_NONE
        )

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device info."""
        return {
            "identifiers": {("poer", self.device_id)},
            "name": self.name,
            "manufacturer": self._attr_manufacturer,
            "model": self._attr_model,
            "sw_version": self._attr_firmware_version,
        }

    async def async_set_temperature(self, **kwargs) -> None:
        """Set target temperature."""
        temp = kwargs.get(ATTR_TEMPERATURE)
        target_temp_low = kwargs.get(ATTR_TARGET_TEMP_LOW)
        target_temp_high = kwargs.get(ATTR_TARGET_TEMP_HIGH)

        try:
            if temp is not None:
                await self.coordinator._api_request(
                    "POST", f"device/{self.device_id}/set_temp", {"temperature": temp}
                )
                self._attr_target_temperature = temp
            elif target_temp_low is not None and target_temp_high is not None:
                await self.coordinator._api_request(
                    "POST",
                    f"device/{self.device_id}/set_temp_range",
                    {"low": target_temp_low, "high": target_temp_high},
                )
                self._attr_target_temperature_low = target_temp_low
                self._attr_target_temperature_high = target_temp_high

            await self.coordinator.async_request_refresh()
            self.async_write_ha_state()
        except Exception as e:
            _LOGGER.error("Set temperature failed: %s", e)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set HVAC mode."""
        mode_map = {
            HVACMode.AUTO: "auto",
            HVACMode.COOL: "cool",
            HVACMode.HEAT: "heat",
            HVACMode.OFF: "off",
        }

        try:
            device_mode = mode_map.get(hvac_mode)
            if device_mode is None:
                _LOGGER.error("Unsupported mode: %s", hvac_mode)
                return

            await self.coordinator._api_request(
                "POST", f"device/{self.device_id}/set_mode", {"mode": device_mode}
            )
            self._attr_hvac_mode = hvac_mode
            await self.coordinator.async_request_refresh()
            self.async_write_ha_state()
        except Exception as e:
            _LOGGER.error("Set mode failed: %s", e)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set preset mode."""
        preset_map = {
            PRESET_HOME: "home",
            PRESET_AWAY: "away",
            PRESET_SLEEP: "sleep",
            PRESET_ECO: "eco",
            PRESET_NONE: "none",
        }

        try:
            device_preset = preset_map.get(preset_mode)
            if device_preset is None:
                _LOGGER.error("Unsupported preset: %s", preset_mode)
                return

            await self.coordinator._api_request(
                "POST", f"device/{self.device_id}/set_preset", {"preset": device_preset}
            )
            self._attr_preset_mode = preset_mode
            await self.coordinator.async_request_refresh()
            self.async_write_ha_state()
        except Exception as e:
            _LOGGER.error("Set preset failed: %s", e)
