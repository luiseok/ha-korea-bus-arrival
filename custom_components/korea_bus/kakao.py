"""Kakao Map API 연동을 위한 클래스."""
import aiohttp
import asyncio
import logging

from .const import BASE_HEADER, BASE_URL, DEFAULT_TIMEOUT

_LOGGER = logging.getLogger(__name__)


class KakaoBusAPI:
    """Class to communicate with Kakao Map API."""

    def __init__(self, session: aiohttp.ClientSession, bus_stop_id: str, bus_numbers: list[str], custom_headers: dict = None):
        """Initialize the API class."""
        self.session = session
        self.bus_stop_id = bus_stop_id
        self.bus_numbers = bus_numbers
        self.custom_headers = custom_headers or {}

    async def fetch_buses(self):
        """Retrieve the list of buses for the bus stop."""
        _LOGGER.debug(
            "Fetching bus data for stop_id=%s with bus_numbers=%s",
            self.bus_stop_id,
            self.bus_numbers,
        )

        try:
            async with asyncio.timeout(DEFAULT_TIMEOUT):
                url = f"{BASE_URL}?busStopId={self.bus_stop_id}"
                default_headers = {
                    "Referer": f"{BASE_URL}?busStopId={self.bus_stop_id}"
                }
                # Merge default headers with custom headers (custom headers take precedence)
                headers = {**default_headers, **self.custom_headers, **BASE_HEADER}

                _LOGGER.debug("Requesting URL: %s", url)

                async with self.session.get(url, headers=headers) as response:
                    if response.status != 200:
                        _LOGGER.error(
                            "API request failed with status %s for bus_stop_id=%s, URL=%s",
                            response.status,
                            self.bus_stop_id,
                            url,
                        )
                        raise Exception(f"API request failed with status {response.status}")

                    data = await response.json()
                    buses_list = data.get("busesList", [])

                    _LOGGER.debug(
                        "Successfully fetched %d buses for stop_id=%s",
                        len(buses_list),
                        self.bus_stop_id,
                    )

                    return buses_list

        except asyncio.TimeoutError:
            _LOGGER.error(
                "API request timeout (>%ds) for bus_stop_id=%s, URL=%s",
                DEFAULT_TIMEOUT,
                self.bus_stop_id,
                url,
            )
            raise
        except aiohttp.ClientError as e:
            _LOGGER.error(
                "API client error for bus_stop_id=%s: %s",
                self.bus_stop_id,
                e,
                exc_info=True,
            )
            raise
        except Exception as e:
            _LOGGER.error(
                "Unexpected error fetching buses for bus_stop_id=%s: %s",
                self.bus_stop_id,
                e,
                exc_info=True,
            )
            raise

    async def validate_bus_number(self):
        """Validate the bus numbers."""
        _LOGGER.debug(
            "Validating bus numbers %s for stop_id=%s",
            self.bus_numbers,
            self.bus_stop_id,
        )

        buses_list = await self.fetch_buses()

        if not buses_list:
            _LOGGER.warning(
                "No buses found for bus_stop_id=%s. Stop may be invalid or inactive.",
                self.bus_stop_id,
            )
            return False, "invalid_bus_stop_id"

        available_bus_numbers = [bus.get("name") for bus in buses_list]
        _LOGGER.debug(
            "Available buses at stop_id=%s: %s",
            self.bus_stop_id,
            available_bus_numbers,
        )

        invalid_buses = [num for num in self.bus_numbers if num not in available_bus_numbers]

        if invalid_buses:
            _LOGGER.warning(
                "Invalid bus numbers %s for stop_id=%s. Available buses: %s",
                invalid_buses,
                self.bus_stop_id,
                available_bus_numbers,
            )
            return False, f"invalid_bus_number: {', '.join(invalid_buses)}"

        _LOGGER.info(
            "Successfully validated bus numbers %s for stop_id=%s",
            self.bus_numbers,
            self.bus_stop_id,
        )
        return True, buses_list

    async def get_bus_info(self):
        """Retrieve information for a specific bus."""
        buses_list = await self.fetch_buses()
        for bus in buses_list:
            if bus.get("name") == self.bus_number:
                return bus
        return None
    
    async def get_all_bus_info(self):
        """Retrieve all bus information."""
        buses_list = await self.fetch_buses()

        if buses_list:
            _LOGGER.debug(
                "Retrieved info for %d buses at stop_id=%s",
                len(buses_list),
                self.bus_stop_id,
            )
        else:
            _LOGGER.warning(
                "No bus information available for stop_id=%s",
                self.bus_stop_id,
            )

        return buses_list