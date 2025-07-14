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
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
}