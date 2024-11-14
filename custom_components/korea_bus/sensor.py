"""Support for Korea Bus sensors."""
from datetime import timedelta, datetime
import logging
import aiohttp
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
from homeassistant.const import DEVICE_CLASS_TIMESTAMP
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    CONF_BUS_STOP_ID,
    CONF_BUS_NUMBER,
    CONF_NAME,
    DEFAULT_SCAN_INTERVAL,
)
from .kakao import KakaoBusAPI

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Korea Bus sensor from a config entry."""
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

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()

    entities = []
    bus_numbers = entry.data.get(CONF_BUS_NUMBER, [])
    for bus_number in bus_numbers:
        entities.append(KoreaBusSensor(coordinator, entry, bus_number))

    async_add_entities(entities, False)

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
        self.bus_numbers = entry.data.get(CONF_BUS_NUMBER, [])

    async def _async_update_data(self):
        """Fetch data from API."""
        try:
            api = KakaoBusAPI(self.session, self.bus_stop_id, self.bus_numbers)
            buses_info = await api.get_all_bus_info()
            if not buses_info:
                _LOGGER.debug("버스 정보가 없습니다.")
                return {}  # Avoid returning an empty dictionary to avoid UpdateFailed
            
            # Convert bus information to a dictionary with bus numbers as keys
            buses_dict = {bus.get("name"): bus for bus in buses_info}
            return buses_dict
        except asyncio.TimeoutError as error:
            raise UpdateFailed(f"Timeout error fetching data: {error}")
        except aiohttp.ClientError as error:
            raise UpdateFailed(f"Error fetching data: {error}")
        except Exception as error:
            raise UpdateFailed(f"Unexpected error: {error}")

class KoreaBusSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Korea Bus Sensor."""

    def __init__(self, coordinator, entry, bus_number):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entry = entry
        self.bus_number = bus_number

        # Generate Entity ID
        self._attr_unique_id = f"{entry.data[CONF_BUS_STOP_ID]}_{self.bus_number}"
        
        # Set the name
        self._attr_name = f"{entry.data.get(CONF_NAME, '')} {self.bus_number}번 버스" if entry.data.get(CONF_NAME) else f"{self.bus_number}번 버스 도착 정보 ({entry.data[CONF_BUS_STOP_ID]})"
        
        self._state = None
        self.bus_info = None

    @property
    def native_value(self):
        """Return the state of the sensor as 도착 예정 시간 (타임스탬프)."""
        # update bus_info
        self.bus_info = self.coordinator.data.get(self.bus_number)
        
        if not self.bus_info:
            _LOGGER.debug("bus_info is None.")
            return None
        
        arrival_time = self.bus_info.get("arrivalTime", 0)
        try:
            arrival_time = int(arrival_time)
            if arrival_time < 0:
                _LOGGER.debug("유효하지 않은 arrival_time: %s", arrival_time)
                return None
        except (ValueError, TypeError):
            _LOGGER.error("arrival_time 형식이 올바르지 않습니다: %s", arrival_time)
            return None
        
        self._state = dt_util.now() + timedelta(seconds=arrival_time)
        return self._state

    async def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        old_info = self.bus_info
        self.bus_info = self.coordinator.data.get(self.bus_number)
        _LOGGER.debug(
            "버스 정보 업데이트 - 버스번호: %s, 이전: %s, 새로운: %s",
            self.bus_number,
            old_info,
            self.bus_info
        )
        self.async_write_ha_state()

    @property
    def device_class(self):
        """Return the device class."""
        return DEVICE_CLASS_TIMESTAMP

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        if not self.bus_info:
            self.bus_info = self.coordinator.data.get(self.bus_number)
            
        if not self.bus_info:
            return {}
        
        arrival_time = self.bus_info.get("arrivalTime", 0)
        time_left = "알 수 없음"
        try:
            arrival_time = int(arrival_time)
            if arrival_time > 0:
                arrival_datetime = dt_util.now() + timedelta(seconds=arrival_time)
                minutes = arrival_time // 60
                seconds = arrival_time % 60
                time_left = f"{minutes}분 {seconds}초"
            else:
                arrival_datetime = None
        except (ValueError, TypeError):
            arrival_datetime = None
            
        collect_datetime_str = self.bus_info.get("collectDateTime", "알 수 없음")
        if collect_datetime_str != "알 수 없음" and collect_datetime_str is not None:
            collect_datetime_str = self.format_collect_datetime(collect_datetime_str)
        
        return {
            "vehicle_number": self.bus_info.get("vehicleNumber", "알 수 없음"),
            "current_stop": self.bus_info.get("currentBusStopName", "알 수 없음"),
            "next_stop": self.bus_info.get("nextBusStopName", "알 수 없음"),
            "arrival_time": arrival_time,
            "time_left": time_left,
            "arrival_datetime": arrival_datetime.isoformat() if arrival_datetime else "알 수 없음",
            "vehicle_state_message": self.bus_info.get("vehicleStateMessage", "알 수 없음"),
            "remain_seat": self.bus_info.get("remainSeat", "-1"),
            "direction": self.bus_info.get("direction", "알 수 없음"),
            "bus_type": self.bus_info.get("typeName", "알 수 없음"),
            "first_time": self.bus_info.get("first", "알 수 없음"),
            "last_time": self.bus_info.get("last", "알 수 없음"),
            "intervals": self.bus_info.get("intervals", "알 수 없음"),
            "updated_at": collect_datetime_str if collect_datetime_str is not None else "알 수 없음",
            "last_vehicle": self.bus_info.get("lastVehicle", "알 수 없음"),
        }

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.last_update_success and self.bus_info is not None

    async def async_added_to_hass(self):
        """Called when entity is added to hass."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )
        # Set initial data
        self.bus_info = self.coordinator.data.get(self.bus_number)

    @property
    def unique_id(self):
        """Unique ID for the sensor."""
        return self._attr_unique_id

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._attr_name

    def format_collect_datetime(self, collect_datetime_str):
        """Format the collectDateTime string to a datetime object and then to a string."""
        try:
            # Convert the string to a datetime object (format: YYYYMMDDHHMMSS)
            collect_datetime = datetime.strptime(collect_datetime_str, "%Y%m%d%H%M%S")
            # Format to the desired format (e.g., "2024-11-14 11:27:03")
            formatted_datetime = collect_datetime.strftime("%Y-%m-%d %H:%M:%S")
            return formatted_datetime
        except ValueError:
            _LOGGER.error(f"collectDateTime 형식이 유효하지 않습니다: {collect_datetime_str}")
            return "알 수 없음"
