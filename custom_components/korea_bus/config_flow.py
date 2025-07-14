"""Config flow for Korea Bus integration."""
import logging
import re
import voluptuous as vol
import aiohttp
import asyncio
import urllib.parse

from bs4 import BeautifulSoup

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.helpers.aiohttp_client import async_create_clientsession
import homeassistant.helpers.config_validation as cv

from .const import (
    DOMAIN,
    CONF_BUS_STOP_NAME,
    CONF_BUS_STOP,
    CONF_BUS_STOP_ID,
    CONF_BUS_NUMBER,
    DEFAULT_SCAN_INTERVAL,
    STATION_URL,
    SEARCH_URL,
    BASE_HEADER
)

_LOGGER = logging.getLogger(__name__)


class KoreaBusConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Korea Bus."""

    VERSION = 1
    _bus_data: dict = dict()

    async def fetch_bus_stop_list(self, session: aiohttp.ClientSession, bus_stop_name: str) -> dict[str, dict]:
        """Fetch the list of bus stops."""
        url = f"{SEARCH_URL}?q={urllib.parse.quote(bus_stop_name)}&lvl=2#!/all/list/bus"

        async with session.get(url, headers=BASE_HEADER, timeout=10) as response:
            if response.status != 200:
                _LOGGER.error("Fetching bus stop list failed with status code: %s", response.status)
                return 
            
            soup = BeautifulSoup(await response.text(), "html.parser")
            bus_stops = soup.find_all("li", class_="search_item")

            results = {}
            for stop in bus_stops:
                data_id = stop.get("data-id")
                data_title = stop.get("data-title")
            
                stop_number_element = stop.find("span", class_="screen_out", string="버스 정류장 번호 : ")
                stop_number = stop_number_element.next_sibling.strip() \
                    if stop_number_element and isinstance(stop_number_element.next_sibling, str) else None
            
                direction_element = stop.find("span", class_="txt_bar")
                direction = direction_element.next_sibling.strip() \
                    if direction_element and isinstance(direction_element.next_sibling, str) else None
            
                location = stop.find("span", class_="txt_ginfo").text.strip() if stop.find("span", class_="txt_ginfo") else "Unknown"
                bus_types = [bus_type.text for bus_type in stop.find_all("span", class_=lambda x: x and x.startswith("bus_type"))]
            
                # "Unknown"이 아닌 경우만 결과에 추가
                if stop_number and direction:
                    results[data_id] = {
                        "stop_number": stop_number,
                        "direction": direction,
                        "location": location,
                        "bus_types": bus_types,
                        "title": f"{data_title}({stop_number}) - {direction}"
                    }
            return results
    
    async def fetch_bus_number_list(self, session: aiohttp.ClientSession, bus_stop_id: str) -> list[dict]:
        """Fetch the list of bus numbers."""
        url = f"{STATION_URL}?busStopId={bus_stop_id}"

        async with session.get(url, timeout=10, headers=BASE_HEADER) as response:
            if response.status != 200:
                _LOGGER.error("Fetching bus number list failed with status code: %s", response.status)
                return 
            
            soup = BeautifulSoup(await response.text(), "html.parser")
            bus_items = soup.find_all("li", {"data-id": True})
    
            buses = []
            for bus in bus_items:
                bus_number = bus.find("strong", {"class": "tit_g"})
                if bus_number:
                    bus_type_elem = bus.find("span", {'class': re.compile("bus_type.*")})
                    bus_type = bus_type_elem.text if bus_type_elem else "Unknown"
            
                    bus_info = {
                        "number": bus_number.text.strip(),
                        "type": bus_type.strip()
                    }
                    buses.append(bus_info)
            return buses
    
    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            bus_stop_name = user_input[CONF_BUS_STOP_NAME]

            try:
                self._bus_data[CONF_BUS_STOP] = await self.fetch_bus_stop_list(
                    async_create_clientsession(self.hass), bus_stop_name
                )
                if not self._bus_data[CONF_BUS_STOP]:
                    errors["base"] = "no_bus_stop"
                else:
                    return await self.async_step_select_stop()

            except asyncio.TimeoutError as e:
                _LOGGER.error(e)
                errors["base"] = "timeout_error"
            except aiohttp.ClientError as e:
                _LOGGER.error(e)
                errors["base"] = "client_error"
            except Exception as e:
                _LOGGER.error("Unexpected error during initial step: %s", e)
                errors["base"] = "unknown_error"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_BUS_STOP_NAME): str,
            }),
            errors=errors,
        )
    
    async def async_step_select_stop(self, user_input=None):
        """Handle the bus stop selection step."""
        errors = {}
        
        if user_input is not None:
            self._bus_data[CONF_BUS_STOP_ID] = user_input[CONF_BUS_STOP]

            try:
                self._bus_data[CONF_BUS_NUMBER] = await self.fetch_bus_number_list(
                    async_create_clientsession(self.hass), self._bus_data[CONF_BUS_STOP_ID]
                )
                return await self.async_step_select_number()

            except asyncio.TimeoutError as e:
                _LOGGER.error(e)
                errors["base"] = "timeout_error"
            except aiohttp.ClientError as e:
                _LOGGER.error(e)
                errors["base"] = "client_error"
            except Exception as e:
                _LOGGER.error("Unexpected error during initial step: %s", e)
                errors["base"] = "unknown_error"

        return self.async_show_form(
            step_id="select_stop",
            data_schema=vol.Schema({
                vol.Required(CONF_BUS_STOP): vol.In(
                    {k: v["title"] for k, v in self._bus_data[CONF_BUS_STOP].items()}
                )
            }),
        )
    
    async def async_step_select_number(self, user_input=None):
        """Handle the bus number selection step."""
        errors = {}

        if user_input is not None:
            self._bus_data[CONF_BUS_NUMBER] = user_input[CONF_BUS_NUMBER]

            unique_id = f"{self._bus_data[CONF_BUS_STOP_ID]}_{''.join(self._bus_data[CONF_BUS_NUMBER])}"
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=f"버스(대중교통) 도착 정보 정류장 {self._bus_data[CONF_BUS_STOP_ID]}",
                data=self._bus_data,
            )
        
        bus_options = {
            bus["number"]: f"{bus['type']} {bus['number']}"
            for bus in self._bus_data[CONF_BUS_NUMBER]
        }

        return self.async_show_form(
            step_id="select_number",
            data_schema=vol.Schema({
                vol.Required(CONF_BUS_NUMBER): cv.multi_select(bus_options)
            }),
            errors=errors
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
            data_schema=vol.Schema({
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=self.config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                ): int,
            }),
        )
