"""Support for Poer WiFi Thermostats."""

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .const import DOMAIN, CNURL, EUURL


class POERConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for POER Thermostat."""

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            api_token = user_input.get("api_key")
            valid = True
            api_url = ""

            if api_token.startswith("cn"):
                api_url = CNURL
            elif api_token.startswith("eu"):
                api_url = EUURL
            else:
                valid = False
            if valid:
                api_token = api_token[2:]
                valid = await self._test_credentials(api_url, api_token)
            if valid:
                return self.async_create_entry(
                    title="POER Thermostat",
                    data={"api_token": api_token, "api_url": api_url},
                )
            errors["base"] = "invalid api key"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("api_key"): str,
                }
            ),
            errors=errors,
        )

    async def _test_credentials(self, api_url: str, api_token: str) -> bool:
        """Test if the credentials are valid."""
        session = async_create_clientsession(self.hass)
        headers = {"Authorization": "beer " + api_token}

        try:
            url = f"{api_url.rstrip('/')}/speaker/ha/v1.0/ping"
            async with session.get(url, headers=headers) as resp:
                return resp.status == 200
        except Exception:
            return False
