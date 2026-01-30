
[![GitHub Release](https://img.shields.io/github/release/bkbilly/tpms_ble.svg?style=flat-square)](https://github.com/bkbilly/tpms_ble/releases)
[![License](https://img.shields.io/github/license/bkbilly/tpms_ble.svg?style=flat-square)](LICENSE)
[![hacs](https://img.shields.io/badge/HACS-default-orange.svg?style=flat-square)](https://hacs.xyz)


# TPMS_BLE
Integrates Bluetooth LE to Home Assistant using passive connection to get infromation from the sensors.

Exposes the following sensors:
 - Battery
 - Pressure
 - Temperature
 - Voltage
 - Data Age (minutes since last BLE update)

## Installation

Easiest install is via [HACS](https://hacs.xyz/):

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=bkbilly&repository=tpms_ble&category=integration)

`HACS -> Explore & Add Repositories -> TPMS_BLE`

The device will be autodiscovered once the data are received by any bluetooth proxy.

## Data Age Sensor

The Data Age sensor tracks how many minutes have elapsed since the last BLE advertisement was received from each TPMS sensor. This is useful for monitoring whether your sensors are actively broadcasting.

- **Value of 0**: Data is less than 1 minute old
- **Update frequency**: The sensor value updates once per minute
- **Availability**: Shows as unavailable until the first BLE update is received

### Upgrading from Previous Versions

If you are upgrading from a version without the Data Age sensor, the new sensor may initially appear as a separate "Unnamed device" entry. To fix this:

1. Delete the TPMS device from Home Assistant (Settings → Devices & Services → Devices)
2. The device will be automatically rediscovered with all sensors properly grouped
3. All previously configured attributes (names, areas, etc.) will be restored from the entity registry

## Supported Devices
### Type A
Android App: [TPMSII](https://play.google.com/store/apps/details?id=com.chaoyue.tyed) 

Product Link: [AliExpress](https://www.aliexpress.com/item/1005006129840804.html)

<img width="383" alt="typea" src="https://github.com/user-attachments/assets/0bbb5e22-e3b9-4819-bcd5-a883127a9c12" />

### Type B
Android App: [SYTPMS](https://play.google.com/store/apps/details?id=com.bekubee.sytpms)

Product Link: [AliExpress](https://www.aliexpress.com/item/1005006755884183.html)

<img width="375" alt="typeb" src="https://github.com/user-attachments/assets/ba551063-548e-49e4-985b-6ea3a79a86f1" />

### Type C (Michelin TMS)
Product Description: [Michelin](https://www.michelin.co.uk/auto/advice/tyre-pressure/tpms-tyre-pressure-monitoring-system)

<img width="375" alt="typec" src="https://github.com/user-attachments/assets/7a1d3c6b-78d1-436e-a67f-b65904de13f0" />
