# Korea Bus Arrival for Home Assistant

Home Assistant integration for Korean bus arrival information.

## Installation

### HACS (Recommended)
1. Add this repository to HACS
2. Search for "버스(대중교통) 도착 정보" in HACS
3. Install the integration
4. Restart Home Assistant

### Manual Installation
1. Copy the `custom_components/korea_bus` folder to your Home Assistant's `custom_components` folder
2. Restart Home Assistant

## Configuration

1. Go to Settings > Devices & Services
2. Click "Add Integration"
3. Search for "버스(대중교통) 도착 정보"
4. Enter your bus stop ID and bus number
    1. Bus stop ID: 버스 정류장 ID (You can find it in the URL of the bus stop page on the [Kakao Map's bus stop search page](https://m.map.kakao.com/actions/searchView).)
    2. Bus number: 버스 번호 (쉼표로 구분)
    3. Name: 버스 정류장 이름

## Options

You can configure the following options:
- Update interval (default: 60 seconds)