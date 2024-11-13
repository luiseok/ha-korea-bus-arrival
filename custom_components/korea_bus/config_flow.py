"""Config flow for Korea Bus integration."""
import logging
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.const import CONF_NAME

from .const import DOMAIN, CONF_BUS_STOP_ID, CONF_BUS_NUMBER, DEFAULT_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)

class ConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Korea Bus."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            unique_id = f"{user_input[CONF_BUS_STOP_ID]}_{user_input[CONF_BUS_NUMBER]}"
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=f"Bus {user_input[CONF_BUS_NUMBER]} at {user_input[CONF_BUS_STOP_ID]}",
                data=user_input,
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_BUS_STOP_ID): str,
                    vol.Required(CONF_BUS_NUMBER): str,
                    vol.Optional(CONF_NAME): str,
                }
            ),
            errors=errors,
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