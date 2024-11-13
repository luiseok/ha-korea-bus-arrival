"""Kakao Map API 연동을 위한 클래스."""
import aiohttp
import async_timeout
import asyncio
import logging

from .const import BASE_URL

_LOGGER = logging.getLogger(__name__)

class KakaoBusAPI:
    """Kakao Map API와 통신하는 클래스."""

    def __init__(self, session: aiohttp.ClientSession, bus_stop_id: str, bus_number: str):
        """API 클래스를 초기화합니다."""
        self.session = session
        self.bus_stop_id = bus_stop_id
        self.bus_number = bus_number

    async def fetch_buses(self):
        """버스 정류장에 해당하는 버스 목록을 가져옵니다."""
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
        """버스 번호가 유효한지 확인합니다."""
        buses_list = await self.fetch_buses()
        if not buses_list:
            return False, "invalid_bus_stop_id"
        
        bus_exists = any(bus.get("name") == self.bus_number for bus in buses_list)
        if not bus_exists:
            return False, "invalid_bus_number"
        
        return True, buses_list

    async def get_bus_info(self):
        """특정 버스의 정보를 가져옵니다."""
        buses_list = await self.fetch_buses()
        for bus in buses_list:
            if bus.get("name") == self.bus_number:
                return bus
        return None
    
    