"""Support for Poer WiFi Thermostats."""

from __future__ import annotations

from asyncio import timeout
from http import HTTPStatus
from typing import Any

from aiohttp import ClientSession

# from airly import Airly
# from airly.exceptions import AirlyError
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_API_KEY
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN


class PoerFlowHandler(ConfigFlow, domain=DOMAIN):
    """Config flow for Poer."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle a flow initialized by the user."""
        errors = {}

        websession = async_get_clientsession(self.hass)
        username = "testuser"
        token = "testapikey"
        if user_input is not None:
            return self.async_create_entry(
                title=username,
                data={"token": token, "username": username},
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_API_KEY): str,
                }
            ),
            errors=errors,
        )
