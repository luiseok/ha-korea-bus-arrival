"""Bus arrival sensor for Home Assistant."""
import logging
from datetime import timedelta
import aiohttp
import async_timeout
import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorEntity
from homeassistant.const import CONF_NAME, ATTR_ATTRIBUTION
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

_LOGGER = logging.getLogger(__name__)

# 설정값 정의
CONF_BUS_STOP_ID = "busStopId"
CONF_BUS_NUMBER = "busNumber"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_NAME = "Bus Arrival"
DEFAULT_SCAN_INTERVAL = 60

# API 엔드포인트
BASE_URL = "https://m.map.kakao.com/actions/busesInBusStopJson"

# 설정 스키마 정의
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_BUS_STOP_ID): cv.string,
    vol.Required(CONF_BUS_NUMBER): cv.string,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): cv.positive_int,
})

async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None
) -> None:
    """Set up the bus arrival sensor."""
    name = config[CONF_NAME]
    bus_stop_id = config[CONF_BUS_STOP_ID]
    bus_number = config[CONF_BUS_NUMBER]
    scan_interval = config[CONF_SCAN_INTERVAL]

    session = async_get_clientsession(hass)

    async_add_entities(
        [BusArrivalSensor(name, bus_stop_id, bus_number, session, scan_interval)],
        True,
    )

class BusArrivalSensor(SensorEntity):
    """Implementation of the bus arrival sensor."""

    def __init__(self, name, bus_stop_id, bus_number, session, scan_interval):
        """Initialize the sensor."""
        self._name = name
        self._bus_stop_id = bus_stop_id
        self._bus_number = bus_number
        self._session = session
        self._scan_interval = timedelta(seconds=scan_interval)
        self._state = None
        self._attributes = {}
        self._available = True

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{self._name} {self._bus_number}"

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return self._attributes

    @property
    def available(self):
        """Return True if entity is available."""
        return self._available

    async def async_update(self):
        """Fetch new state data for the sensor."""
        try:
            url = f"{BASE_URL}?busStopId={self._bus_stop_id}"

            async with async_timeout.timeout(10):
                async with self._session.get(url) as response:
                    if response.status != 200:
                        self._available = False
                        _LOGGER.error("Failed to get data from API: %s", response.status)
                        return
                    
                    data = await response.json()

            # 해당하는 버스 찾기
            bus_info = None
            for bus in data.get("busesList", []):
                if bus.get("name") == self._bus_number:
                    bus_info = bus
                    break

            if bus_info is None:
                self._available = False
                _LOGGER.warning("No bus found with number %s", self._bus_number)
                return

            # 상태 및 속성 업데이트
            self._available = True
            self._state = bus_info.get("vehicleStateMessage", "알 수 없음")
            
            self._attributes = {
                "vehicle_number": bus_info.get("vehicleNumber", "알 수 없음"),
                "current_stop": bus_info.get("currentBusStopName", "알 수 없음"),
                "next_stop": bus_info.get("nextBusStopName", "알 수 없음"),
                "arrival_time": bus_info.get("arrivalTime", "0"),
                "remain_seat": bus_info.get("remainSeat", "-1"),
                "direction": bus_info.get("direction", "알 수 없음"),
                "bus_type": bus_info.get("typeName", "알 수 없음"),
                "first_time": bus_info.get("first", "알 수 없음"),
                "last_time": bus_info.get("last", "알 수 없음"),
                "intervals": bus_info.get("intervals", "알 수 없음"),
                "updated_at": bus_info.get("collectDateTime", "알 수 없음")
            }

        except (aiohttp.ClientError, async_timeout.TimeoutError) as err:
            self._available = False
            _LOGGER.error("Error fetching data: %s", err)