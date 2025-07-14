"""Support for Korea Bus sensors."""
from datetime import timedelta, datetime
import logging
import aiohttp
import asyncio

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    CONF_BUS_STOP_ID,
    CONF_BUS_NUMBER,
    DEFAULT_SCAN_INTERVAL,
)
from .kakao import KakaoBusAPI

_LOGGER = logging.getLogger(__name__)


def create_bus_entities(coordinator, entry):
    """Create all bus sensor entities for the given config entry."""
    bus_numbers = entry.data.get(CONF_BUS_NUMBER, [])
    entities = []
    for bus_number in bus_numbers:
        entities.append(KoreaBusSensor(coordinator, entry, bus_number))
        entities.append(KoreaBusNextSensor(coordinator, entry, bus_number))
    return entities

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
        name=DOMAIN,
        update_interval=timedelta(
            seconds=entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        ),
    )

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()

    entities = create_bus_entities(coordinator, entry)
    async_add_entities(entities)


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
            custom_headers = {
                "X-Requested-With": "XMLHttpRequest"
            }
            api = KakaoBusAPI(self.session, self.bus_stop_id, self.bus_numbers, custom_headers)
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


class KoreaBusBaseSensor(CoordinatorEntity, SensorEntity):
    """Base class for Korea Bus Sensors."""

    def __init__(self, coordinator, entry, bus_number):
        super().__init__(coordinator)
        self.entry = entry
        self.bus_number = bus_number
        self._state = None

    @property
    def device_class(self):
        return SensorDeviceClass.TIMESTAMP

    @callback
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )
        if self.coordinator.last_update_success:
            self.async_schedule_update_ha_state(True)

    @property
    def unique_id(self):
        return self._attr_unique_id

    @property
    def name(self):
        return self._attr_name

    def format_collect_datetime(self, collect_datetime_str):
        """Format collectDateTime string to readable format."""
        try:
            collect_datetime = datetime.strptime(collect_datetime_str, "%Y%m%d%H%M%S")
            return collect_datetime.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            _LOGGER.error(f"collectDateTime 형식이 유효하지 않습니다: {collect_datetime_str}")
            return "알 수 없음"


class KoreaBusSensor(KoreaBusBaseSensor):
    """Sensor for the first arriving bus."""

    ATTR_MAP = {
        "arrival_time": "arrivalTime",
        "vehicle_number": "vehicleNumber",
        "current_stop": "currentBusStopName",
        "vehicle_state_message": "vehicleStateMessage",
        "remain_seat": "remainSeat",
        "updated_at": "collectDateTime",
        "last_vehicle": "lastVehicle",
        "bus_stop_count": "busStopCount",
        "next_stop": "nextBusStopName",
        "direction": "direction",
        "bus_type": "typeName",
        "first_time": "first",
        "last_time": "last",
        "intervals": "intervals",
    }

    def __init__(self, coordinator, entry, bus_number):
        super().__init__(coordinator, entry, bus_number)
        self._attr_unique_id = f"{entry.data[CONF_BUS_STOP_ID]}_{self.bus_number}"
        self._attr_name = f"{self.bus_number}번 버스 도착 정보 ({entry.data[CONF_BUS_STOP_ID]})"

    @property
    def native_value(self):
        bus_info = self.coordinator.data.get(self.bus_number)
        if not bus_info:
            _LOGGER.debug(f"bus_info is None for bus {self.bus_number}.")
            return None
        arrival_time = bus_info.get(self.ATTR_MAP["arrival_time"], 0)
        try:
            arrival_time = int(arrival_time)
            if arrival_time <= 0:
                return None
        except (ValueError, TypeError):
            _LOGGER.error(f"arrivalTime 형식이 올바르지 않습니다: {arrival_time} for bus {self.bus_number}")
            return None
        self._state = dt_util.now() + timedelta(seconds=arrival_time)
        return self._state

    @property
    def extra_state_attributes(self):
        bus_info = self.coordinator.data.get(self.bus_number)
        if not bus_info:
            return {}
        arrival_time = bus_info.get(self.ATTR_MAP["arrival_time"], 0)
        time_left = "알 수 없음"
        arrival_datetime = None
        try:
            arrival_time = int(arrival_time)
            if arrival_time > 0:
                arrival_datetime = dt_util.now() + timedelta(seconds=arrival_time)
                minutes = arrival_time // 60
                seconds = arrival_time % 60
                time_left = f"{minutes}분 {seconds}초"
        except (ValueError, TypeError):
            pass
        collect_datetime_str = bus_info.get(self.ATTR_MAP["updated_at"], None)
        formatted_collect_dt = "알 수 없음"
        if collect_datetime_str:
            formatted_collect_dt = self.format_collect_datetime(collect_datetime_str)
        attrs = {
            "arrival_time": arrival_time,
            "time_left": time_left,
            "arrival_datetime": arrival_datetime.isoformat() if arrival_datetime else "알 수 없음",
            "vehicle_number": bus_info.get(self.ATTR_MAP["vehicle_number"], "알 수 없음"),
            "current_stop": bus_info.get(self.ATTR_MAP["current_stop"], "알 수 없음"),
            "vehicle_state_message": bus_info.get(self.ATTR_MAP["vehicle_state_message"], "알 수 없음"),
            "remain_seat": bus_info.get(self.ATTR_MAP["remain_seat"], "-1"),
            "updated_at": formatted_collect_dt,
            "last_vehicle": bus_info.get(self.ATTR_MAP["last_vehicle"], "알 수 없음"),
            "bus_stop_count": bus_info.get(self.ATTR_MAP["bus_stop_count"], "알 수 없음"),
            "next_stop": bus_info.get(self.ATTR_MAP["next_stop"], "알 수 없음"),
            "direction": bus_info.get(self.ATTR_MAP["direction"], "알 수 없음"),
            "bus_type": bus_info.get(self.ATTR_MAP["bus_type"], "알 수 없음"),
            "first_time": bus_info.get(self.ATTR_MAP["first_time"], "알 수 없음"),
            "last_time": bus_info.get(self.ATTR_MAP["last_time"], "알 수 없음"),
            "intervals": bus_info.get(self.ATTR_MAP["intervals"], "알 수 없음"),
        }
        return attrs

    @property
    def available(self) -> bool:
        bus_data = self.coordinator.data.get(self.bus_number)
        if not self.coordinator.last_update_success or not bus_data:
            return False
        arrival_time_str = bus_data.get(self.ATTR_MAP["arrival_time"], '0')
        try:
            int(arrival_time_str)
            return True
        except (ValueError, TypeError):
            return False


class KoreaBusNextSensor(KoreaBusBaseSensor):
    """Sensor for the second arriving bus."""

    ATTR_MAP = {
        "arrival_time": "arrivalTime2",
        "vehicle_number": "vehicleNumber2",
        "current_stop": "currentBusStopName2",
        "vehicle_state_message": "vehicleStateMessage2",
        "remain_seat": "remainSeat2",
        "updated_at": "collectDateTime2",
        "last_vehicle": "lastVehicle2",
        "bus_stop_count": "busStopCount2",
    }

    def __init__(self, coordinator, entry, bus_number):
        super().__init__(coordinator, entry, bus_number)
        self._attr_unique_id = f"{entry.data[CONF_BUS_STOP_ID]}_{self.bus_number}_next"
        self._attr_name = f"다음 {self.bus_number}번 버스 도착 정보 ({entry.data[CONF_BUS_STOP_ID]})"

    @property
    def native_value(self):
        bus_info = self.coordinator.data.get(self.bus_number)
        if not bus_info:
            _LOGGER.debug(f"bus_info is None for bus {self.bus_number}.")
            return None
        arrival_time = bus_info.get(self.ATTR_MAP["arrival_time"], 0)
        try:
            arrival_time = int(arrival_time)
            if arrival_time <= 0:
                return None
        except (ValueError, TypeError):
            _LOGGER.error(f"arrivalTime2 형식이 올바르지 않습니다: {arrival_time} for bus {self.bus_number}")
            return None
        self._state = dt_util.now() + timedelta(seconds=arrival_time)
        return self._state

    @property
    def extra_state_attributes(self):
        bus_info = self.coordinator.data.get(self.bus_number)
        if not bus_info:
            return {}
        arrival_time = bus_info.get(self.ATTR_MAP["arrival_time"], 0)
        time_left = "알 수 없음"
        arrival_datetime = None
        try:
            arrival_time = int(arrival_time)
            if arrival_time > 0:
                arrival_datetime = dt_util.now() + timedelta(seconds=arrival_time)
                minutes = arrival_time // 60
                seconds = arrival_time % 60
                time_left = f"{minutes}분 {seconds}초"
        except (ValueError, TypeError):
            pass
        collect_datetime_str = bus_info.get(self.ATTR_MAP["updated_at"], None)
        formatted_collect_dt = "알 수 없음"
        if collect_datetime_str:
            formatted_collect_dt = self.format_collect_datetime(collect_datetime_str)
        attrs = {
            "arrival_time": arrival_time,
            "time_left": time_left,
            "arrival_datetime": arrival_datetime.isoformat() if arrival_datetime else "알 수 없음",
            "vehicle_number": bus_info.get(self.ATTR_MAP["vehicle_number"], "알 수 없음"),
            "current_stop": bus_info.get(self.ATTR_MAP["current_stop"], "알 수 없음"),
            "vehicle_state_message": bus_info.get(self.ATTR_MAP["vehicle_state_message"], "알 수 없음"),
            "remain_seat": bus_info.get(self.ATTR_MAP["remain_seat"], "-1"),
            "updated_at": formatted_collect_dt,
            "last_vehicle": bus_info.get(self.ATTR_MAP["last_vehicle"], "알 수 없음"),
            "bus_stop_count": bus_info.get(self.ATTR_MAP["bus_stop_count"], "알 수 없음"),
        }
        if arrival_time <= 0:
            attrs["vehicle_state_message"] = bus_info.get(self.ATTR_MAP["vehicle_state_message"], "정보 없음")
        return attrs

    @property
    def available(self) -> bool:
        bus_data = self.coordinator.data.get(self.bus_number)
        if not self.coordinator.last_update_success or not bus_data:
            return False
        arrival_time_str = bus_data.get(self.ATTR_MAP["arrival_time"], '0')
        try:
            int(arrival_time_str)
            return True
        except (ValueError, TypeError):
            return False
