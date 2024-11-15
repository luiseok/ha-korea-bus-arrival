"""Constants for Korea Bus integration."""
DOMAIN = "korea_bus"

CONF_BUS_STOP_NAME = "bus_stop_name"
CONF_BUS_STOP_ID = "bus_stop_id"
CONF_BUS_STOP = "bus_stop"
CONF_BUS_NUMBER = "bus_number"

DEFAULT_SCAN_INTERVAL = 60
BASE_URL = "https://m.map.kakao.com/actions/busesInBusStopJson"
SEARCH_URL = "https://m.map.kakao.com/actions/searchView"
STATION_URL = "https://m.map.kakao.com/actions/busStationInfo"

BASE_HEADER = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36"
}