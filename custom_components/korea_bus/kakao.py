"""Kakao Map API 연동을 위한 클래스."""
import aiohttp
import async_timeout
import asyncio
import logging

from .const import BASE_URL

_LOGGER = logging.getLogger(__name__)

class KakaoBusAPI:
    """Class to communicate with Kakao Map API."""

    def __init__(self, session: aiohttp.ClientSession, bus_stop_id: str, bus_numbers: list[str]):
        """Initialize the API class."""
        self.session = session
        self.bus_stop_id = bus_stop_id
        self.bus_numbers = bus_numbers

    async def fetch_buses(self):
        """Retrieve the list of buses for the bus stop."""
        try:
            async with async_timeout.timeout(10):
                url = f"{BASE_URL}?busStopId={self.bus_stop_id}"
                async with self.session.get(url) as response:
                    if response.status != 200:
                        _LOGGER.error("API 응답 실패: %s", response.status)
                        raise Exception(f"API 응답 실패: {response.status}")
                    data = await response.json()
            return data.get("busesList", [])
        except asyncio.TimeoutError:
            _LOGGER.error("API 요청 타임아웃")
            raise
        except aiohttp.ClientError as e:
            _LOGGER.error("API 클라이언트 오류: %s", e)
            raise
        except Exception as e:
            _LOGGER.error("예상치 못한 오류: %s", e)
            raise

    async def validate_bus_number(self):
        """Validate the bus numbers."""
        buses_list = await self.fetch_buses()
        if not buses_list:
            return False, "invalid_bus_stop_id"

        available_bus_numbers = [bus.get("name") for bus in buses_list]
        invalid_buses = [num for num in self.bus_numbers if num not in available_bus_numbers]

        if invalid_buses:
            return False, f"invalid_bus_number: {', '.join(invalid_buses)}"

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
        return buses_list