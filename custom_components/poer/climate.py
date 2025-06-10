"""Climate platform for POER Thermostat."""

from __future__ import annotations

import logging
from typing import Any

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
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import _LOGGER, DOMAIN
from .coordinator import DeviceCoordinator

DEFAULT_NAME = "POER Thermostat"
DEFAULT_MIN_TEMP = 5.0
DEFAULT_MAX_TEMP = 35.0
DEFAULT_TEMP_STEP = 0.5


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up climate platform."""
    # 从配置流获取API凭据
    api_token = entry.data.get("api_token")
    api_url = entry.data.get("api_url")

    if not api_token or not api_url:
        _LOGGER.error("API credentials missing from config entry")
        return

    # 创建协调器实例
    coordinator = DeviceCoordinator(hass, api_url, api_token)

    # 初始数据刷新
    await coordinator.async_config_entry_first_refresh()

    # 为每个设备创建实体
    entities = [
        POERThermostat(coordinator, device["device_id"]) for device in coordinator.data
    ]

    if entities:
        async_add_entities(entities)


class POERThermostat(CoordinatorEntity, ClimateEntity):
    """POER Thermostat entity."""

    _attr_has_entity_name = True
    _attr_min_temp = DEFAULT_MIN_TEMP
    _attr_max_temp = DEFAULT_MAX_TEMP
    _attr_target_temperature_step = DEFAULT_TEMP_STEP
    _attr_precision = PRECISION_HALVES
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_hvac_modes = [
        HVACMode.AUTO,
        #  HVACMode.COOL,
        HVACMode.HEAT,
        HVACMode.OFF,
    ]
    _attr_preset_modes = [
        # PRESET_NONE,
        PRESET_HOME,
        PRESET_AWAY,
        # PRESET_SLEEP,
        # PRESET_ECO,
    ]
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        # | ClimateEntityFeature.TARGET_TEMPERATURE_RANGE
        | ClimateEntityFeature.PRESET_MODE
    )

    def __init__(self, coordinator: DeviceCoordinator, device_id: str) -> None:
        """Initialize thermostat."""
        super().__init__(coordinator)
        self.device_id = device_id
        self._attr_unique_id = f"poer_thermostat_{device_id}"
        self._update_attributes()

    @property
    def device_data(self) -> dict:
        """Get current device data."""
        return next(
            (
                device
                for device in self.coordinator.data
                if device["device_id"] == self.device_id
            ),
            {},
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Update entity when coordinator updates."""
        self._update_attributes()
        self.async_write_ha_state()

    def _update_attributes(self) -> None:
        """Update entity attributes from device data."""
        data = self.device_data

        # 基本属性
        self._attr_name = data.get("name", DEFAULT_NAME)
        self._attr_current_temperature = data.get("current_temp")
        self._attr_current_humidity = data.get("current_humidity")
        self._attr_target_temperature = data.get("target_temp")
        self._attr_min_temp = data.get("min_temp")
        self._attr_max_temp = data.get("max_temp")
        # self._attr_target_temperature_low = data.get("temp_low")
        # self._attr_target_temperature_high = data.get("temp_high")

        # 设备信息
        self._attr_model = data.get("model", "Unknown Model")
        self._attr_manufacturer = "POER Inc"
        self._attr_firmware_version = data.get("firmware", "Unknown")

        # 状态映射
        self._attr_hvac_mode = self._map_hvac_mode(data.get("mode"))
        self._attr_preset_mode = self._map_preset_mode(data.get("preset"))
        self._attr_hvac_action = self._map_hvac_action(data.get("action"))
        # mode = data.get("mode")
        # if mode is not None:
        #     self._attr_hvac_mode = self._map_hvac_mode(mode)
        # preset = data.get("preset")
        # if preset is not None:
        #     self._attr_preset_mode = self._map_preset_mode(preset)

    def _map_hvac_mode(self, mode: str) -> HVACMode:
        """Map HVAC mode from device value."""
        mode_map = {
            "auto": HVACMode.AUTO,
            # "cool": HVACMode.COOL,
            "heat": HVACMode.HEAT,
            "off": HVACMode.OFF,
        }
        return mode_map.get(mode, HVACMode.OFF)

    def _map_hvac_action(self, action: str) -> HVACAction:
        """Map HVAC action from device value."""
        action_map = {
            # "cooling": HVACAction.COOLING,
            "heating": HVACAction.HEATING,
            "idle": HVACAction.IDLE,
        }
        return action_map.get(action, HVACAction.IDLE)

    def _map_preset_mode(self, preset: str) -> str:
        """Map preset mode from device value."""
        preset_map = {
            "home": PRESET_HOME,
            "away": PRESET_AWAY,
            # "sleep": PRESET_SLEEP,
            # "eco": PRESET_ECO,
            # "none": PRESET_NONE,
        }
        return preset_map.get(preset, PRESET_HOME)

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info for device registry."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.device_id)},
            name=self.name,
            manufacturer=self._attr_manufacturer,
            model=self._attr_model,
            sw_version=self._attr_firmware_version,
            # via_device=(DOMAIN, "cloud_bridge"),
        )

    async def async_set_temperature(self, **kwargs) -> None:
        """Set target temperature."""
        temp = kwargs.get(ATTR_TEMPERATURE)
        # target_temp_low = kwargs.get(ATTR_TARGET_TEMP_LOW)
        # target_temp_high = kwargs.get(ATTR_TARGET_TEMP_HIGH)

        # 准备API请求数据
        endpoint, payload = None, None

        if temp is not None:
            endpoint = "set_temp"
            payload = {"temperature": temp}
            self._attr_target_temperature = temp  # 乐观更新
        # elif target_temp_low is not None and target_temp_high is not None:
        #     endpoint = "set_temp_range"
        #     payload = {"low": target_temp_low, "high": target_temp_high}
        #     self._attr_target_temperature_low = target_temp_low  # 乐观更新
        #     self._attr_target_temperature_high = target_temp_high  # 乐观更新

        if endpoint and payload:
            success = await self.coordinator.send_command(
                self.device_id, endpoint, payload
            )

            if not success:
                self._update_attributes()  # 失败时恢复之前状态

            # 刷新数据以获取最新状态
            self.async_schedule_update_ha_state()

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set HVAC mode."""
        mode_map = {
            HVACMode.AUTO: "auto",
            # HVACMode.COOL: "cool",
            HVACMode.HEAT: "heat",
            HVACMode.OFF: "off",
        }

        if (device_mode := mode_map.get(hvac_mode)) is None:
            _LOGGER.error("Unsupported mode: %s", hvac_mode)
            return

        # 乐观更新
        self._attr_hvac_mode = hvac_mode
        self.async_write_ha_state()

        # 发送命令
        success = await self.coordinator.send_command(
            self.device_id, "set_mode", {"mode": device_mode}
        )

        if not success:
            self._update_attributes()  # 失败时恢复之前状态
            self.async_write_ha_state()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set preset mode."""
        preset_map = {
            PRESET_HOME: "home",
            PRESET_AWAY: "away",
            # PRESET_SLEEP: "sleep",
            # PRESET_ECO: "eco",
            # PRESET_NONE: "none",
        }

        if (device_preset := preset_map.get(preset_mode)) is None:
            _LOGGER.error("Unsupported preset: %s", preset_mode)
            return

        # 乐观更新
        self._attr_preset_mode = preset_mode
        self.async_write_ha_state()

        # 发送命令
        success = await self.coordinator.send_command(
            self.device_id, "set_preset", {"preset": device_preset}
        )

        if not success:
            self._update_attributes()  # 失败时恢复之前状态
            self.async_write_ha_state()
