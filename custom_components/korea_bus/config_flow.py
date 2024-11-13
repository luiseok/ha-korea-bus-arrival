"""Config flow for Korea Bus integration."""
import logging
import voluptuous as vol
import aiohttp
import async_timeout
import asyncio

from homeassistant.config_entries import ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.const import CONF_NAME

from .const import DOMAIN, CONF_BUS_STOP_ID, CONF_BUS_NUMBER, DEFAULT_SCAN_INTERVAL
from .kakao import KakaoBusAPI

_LOGGER = logging.getLogger(__name__)

class ConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Korea Bus."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            bus_stop_id = user_input.get(CONF_BUS_STOP_ID)
            bus_number = user_input.get(CONF_BUS_NUMBER)

            unique_id = f"{bus_stop_id}_{bus_number}"
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()

            # API 검증을 위한 KakaoBusAPI 인스턴스 생성
            try:
                async with aiohttp.ClientSession() as session:
                    api = KakaoBusAPI(session, bus_stop_id, bus_number)
                    is_valid, result = await api.validate_bus_number()

                if not is_valid:
                    errors["base"] = result
                else:
                    return self.async_create_entry(
                        title=f"{bus_number}번 버스 도착정보({bus_stop_id})",
                        data=user_input,
                    )

            except asyncio.TimeoutError:
                errors["base"] = "timeout"
            except aiohttp.ClientError:
                errors["base"] = "client_error"
            except Exception:
                errors["base"] = "unknown_error"

        return self.async_show_form(
            step_id="user",
            data_schema=self._schema(),
            errors=errors,
        )

    def _schema(self):
        """Define the data schema."""
        return vol.Schema(
            {
                vol.Required(CONF_BUS_STOP_ID): str,
                vol.Required(CONF_BUS_NUMBER): str,
                vol.Optional(CONF_NAME): str,
            }
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return KoreaBusOptionsFlow(config_entry)

class KoreaBusOptionsFlow(OptionsFlow):
    """Handle options."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        "scan_interval",
                        default=self.config_entry.options.get(
                            "scan_interval", DEFAULT_SCAN_INTERVAL
                        ),
                    ): int,
                }
            ),
        )