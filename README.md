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
    1. Bus Stop Name: 버스정류장 이름
    2. Bus Stop: 등록을 원하는 버스정류장 선택
    3. Bus Number: 버스 번호 선택

## Options

You can configure the following options:
- Update interval (default: 60 seconds)

## Debugging

If debugging is necessary, please add the code below to configuration.yaml
```yaml
logger:
  default: info
  logs:
    custom_components.korea_bus: debug
```