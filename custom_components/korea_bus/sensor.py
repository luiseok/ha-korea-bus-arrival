"""Support for Korea Bus sensors."""
from datetime import timedelta
import logging
import aiohttp
import async_timeout
import asyncio

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import (
    DOMAIN,
    CONF_BUS_STOP_ID,
    CONF_BUS_NUMBER,
    CONF_NAME,
    DEFAULT_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

# API 엔드포인트
BASE_URL = "https://m.map.kakao.com/actions/busesInBusStopJson"

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Korea Bus sensor from config entry."""
    session = async_get_clientsession(hass)
    
    coordinator = BusDataUpdateCoordinator(
        hass,
        session,
        entry,
        _LOGGER,
        name="bus_sensor",
        update_interval=timedelta(
            seconds=entry.options.get("scan_interval", DEFAULT_SCAN_INTERVAL)
        ),
    )

    # 초기 데이터 가져오기
    await coordinator.async_config_entry_first_refresh()

    async_add_entities(
        [KoreaBusSensor(coordinator, entry)],
        False,
    )

class BusDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching bus data."""

    def __init__(
        self,
        hass: HomeAssistant,
        session: aiohttp.ClientSession,
        entry: ConfigEntry,
        logger: logging.Logger,
        name: str,
        update_interval: timedelta,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            logger,
            name=name,
            update_interval=update_interval,
        )
        self.session = session
        self.bus_stop_id = entry.data[CONF_BUS_STOP_ID]
        self.bus_number = entry.data[CONF_BUS_NUMBER]

    async def _async_update_data(self):
        """Fetch data from API."""
        try:
            async with async_timeout.timeout(10):
                url = f"{BASE_URL}?busStopId={self.bus_stop_id}"
                async with self.session.get(url) as response:
                    if response.status != 200:
                        raise UpdateFailed(f"Error communicating with API: {response.status}")
                    
                    data = await response.json()

            # 해당하는 버스 찾기
            bus_info = None
            for bus in data.get("busesList", []):
                if bus.get("name") == self.bus_number:
                    bus_info = bus
                    break

            if bus_info is None:
                raise UpdateFailed(f"No bus found with number {self.bus_number}")

            return bus_info

        except asyncio.TimeoutError as error:
            raise UpdateFailed(f"Timeout error fetching data: {error}")
        except aiohttp.ClientError as error:
            raise UpdateFailed(f"Error fetching data: {error}")
        except Exception as error:
            raise UpdateFailed(f"Unexpected error: {error}")

class KoreaBusSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Korea Bus Sensor."""

    def __init__(self, coordinator, entry):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entry = entry
        
        # Entity ID 생성
        self._attr_unique_id = f"{entry.data[CONF_BUS_STOP_ID]}_{entry.data[CONF_BUS_NUMBER]}"
        
        # 이름 설정 (설정에서 지정한 이름이 있으면 사용, 없으면 기본 이름 생성)
        self._attr_name = entry.data.get(CONF_NAME) or f"Bus {entry.data[CONF_BUS_NUMBER]}"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get("vehicleStateMessage", "알 수 없음")

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        if self.coordinator.data is None:
            return {}
            
        return {
            "vehicle_number": self.coordinator.data.get("vehicleNumber", "알 수 없음"),
            "current_stop": self.coordinator.data.get("currentBusStopName", "알 수 없음"),
            "next_stop": self.coordinator.data.get("nextBusStopName", "알 수 없음"),
            "arrival_time": self.coordinator.data.get("arrivalTime", "0"),
            "remain_seat": self.coordinator.data.get("remainSeat", "-1"),
            "direction": self.coordinator.data.get("direction", "알 수 없음"),
            "bus_type": self.coordinator.data.get("typeName", "알 수 없음"),
            "first_time": self.coordinator.data.get("first", "알 수 없음"),
            "last_time": self.coordinator.data.get("last", "알 수 없음"),
            "intervals": self.coordinator.data.get("intervals", "알 수 없음"),
            "updated_at": self.coordinator.data.get("collectDateTime", "알 수 없음")
        }

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.last_update_success and self.coordinator.data is not None