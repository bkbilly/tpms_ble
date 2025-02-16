
[![GitHub Release](https://img.shields.io/github/release/bkbilly/tpms_ble.svg?style=flat-square)](https://github.com/bkbilly/tpms_ble/releases)
[![License](https://img.shields.io/github/license/bkbilly/tpms_ble.svg?style=flat-square)](LICENSE)
[![hacs](https://img.shields.io/badge/HACS-default-orange.svg?style=flat-square)](https://hacs.xyz)


# TPMS_BLE
Integrates Bluetooth LE to Home Assistant using passive connection to get infromation from the sensors.

Exposes the following sensors:
 - Battery
 - Pressure
 - Temperature

## Installation

Easiest install is via [HACS](https://hacs.xyz/):

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=bkbilly&repository=tpms_ble&category=integration)

`HACS -> Explore & Add Repositories -> TPMS_BLE`

The device will be autodiscovered once the data are received by any bluetooth proxy.

## Supported Devices
### Type A
Android App: [TPMSII](https://play.google.com/store/apps/details?id=com.chaoyue.tyed) 

Product Link: [AliExpress](https://www.aliexpress.com/item/1005006129840804.html)

<img width="383" alt="type1" src="https://github.com/user-attachments/assets/0bbb5e22-e3b9-4819-bcd5-a883127a9c12" />

### Type B
Android App: [SYTPMS](https://play.google.com/store/apps/details?id=com.bekubee.sytpms)

Product Link: [AliExpress](https://www.aliexpress.com/item/1005006755884183.html)

<img width="375" alt="type2" src="https://github.com/user-attachments/assets/ba551063-548e-49e4-985b-6ea3a79a86f1" />

