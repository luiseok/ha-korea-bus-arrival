"""Config flow for Korea Bus integration."""
import logging
import voluptuous as vol
import aiohttp
import async_timeout
import asyncio

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.const import CONF_NAME

from .const import DOMAIN, CONF_BUS_STOP_ID, CONF_BUS_NUMBER, DEFAULT_SCAN_INTERVAL
from .kakao import KakaoBusAPI

_LOGGER = logging.getLogger(__name__)

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Korea Bus."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        description_placeholders = {}

        if user_input is not None:
            bus_stop_id = user_input.get(CONF_BUS_STOP_ID)
            bus_number_input = user_input.get(CONF_BUS_NUMBER)

            # Convert bus numbers to a comma-separated list
            bus_numbers = [num.strip() for num in bus_number_input.split(",") if num.strip()]
            user_input[CONF_BUS_NUMBER] = bus_numbers

            # Validation
            valid_bus_numbers = []
            invalid_bus_numbers = []

            try:
                async with aiohttp.ClientSession() as session:
                    api = KakaoBusAPI(session, bus_stop_id, bus_numbers)
                    buses_info = await api.get_all_bus_info()

                    # Validate each bus number
                    available_bus_numbers = [bus.get("name") for bus in buses_info]
                    for bus_number in bus_numbers:
                        if bus_number in available_bus_numbers:
                            valid_bus_numbers.append(bus_number)
                        else:
                            invalid_bus_numbers.append(bus_number)

            except asyncio.TimeoutError:
                errors["base"] = "timeout"
            except aiohttp.ClientError:
                errors["base"] = "client_error"
            except Exception as e:
                _LOGGER.error("Unexpected error during validation: %s", e)
                errors["base"] = "unknown_error"

            if invalid_bus_numbers:
                errors["bus_number"] = "invalid_bus_numbers"
                description_placeholders["invalid_numbers"] = ", ".join(invalid_bus_numbers)
                _LOGGER.warning(f"Invalid bus numbers: {invalid_bus_numbers}")

            if not valid_bus_numbers and not invalid_bus_numbers:
                errors["bus_number"] = "no_valid_bus_numbers"
            elif valid_bus_numbers:
                # Prevent duplicate settings
                valid_bus_numbers = list(set(valid_bus_numbers))
                unique_id = f"{bus_stop_id}_{','.join(valid_bus_numbers)}"
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=user_input.get(CONF_NAME, f"버스(대중교통) 도착 정보 정류장 {bus_stop_id}"),
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=self._schema(),
            errors=errors,
            description_placeholders=description_placeholders,
        )

    def _schema(self):
        """Define the data schema."""
        return vol.Schema(
            {
                vol.Required(CONF_BUS_STOP_ID): str,
                vol.Required(CONF_BUS_NUMBER): str,  # Separate bus numbers with commas
                vol.Optional(CONF_NAME): str,
            }
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return KoreaBusOptionsFlow(config_entry)

class KoreaBusOptionsFlow(config_entries.OptionsFlow):
    """Handle an options flow for Korea Bus."""

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