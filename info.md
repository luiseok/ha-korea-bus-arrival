{% if installed %}
## Changes

### Version 1.0.0
- Initial release

### Version 1.0.1
- Applied translation json files

### Version 1.1.0
- Fixed the bug that the attributes were not updated
- Enhanced the sensor to get the first car schedule as intended
- Fixed the bug that the sensor's name gets duplicated when the user registers multiple bus numbers with name
- Added the `time_left` to the sensor's attributes
- Added the `last_vehicle` to the sensor's attributes

### Version 1.1.1
- Fixed the bug that causes the sensor crash when `collect_datetime_str` is unavailable

### Version 1.1.2
- Added the `bus_stop_count` to the sensor's attributes
- Fixed the bug that causes the sensor to be always "now" when the bus arrival time is 0
 
### Version 1.2.0
- Code refactoring
- DEVICE_CLASS_TIMESTAMP is deprecated, so change it to SensorDeviceClass.TIMESTAMP
- Changes to bus registration config flow. See release notes for details
- Error handling when bus stop is not available


{% endif %}

## Configuration

1. Go to Settings > Devices & Services
2. Click "Add Integration"
3. Search for "Korea Bus"
4. Enter your bus stop ID and bus number