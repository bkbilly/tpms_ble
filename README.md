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


### Type D (WODHMIEY / ITPMS K)

Android Apps: [ITPMS (K)](https://play.google.com/store/apps/details?id=com.zl.dev.tire.itpms), [LYTPMS](https://play.google.com/store/apps/details?id=com.zl.dev.tire.lytpms)

Product Link: [WODHMIEY](https://www.amazon.de/-/en/WODHMIEY-Monitoring-Motorcycle-Temperature-Motorhome/dp/B0GWH88YSV)

<img width="375" src="https://github.com/user-attachments/assets/042d33fd-085b-4bff-99f7-eba231c5ce6d" />


### Type E (Salutica FOBO TPMS)

Android App: [FOBO TPMS](https://play.google.com/store/apps/details?id=my.com.salutica.fobotpms)

Product Description: [FOBO](https://my-fobo.com/)

<img width="375" src="https://github.com/user-attachments/assets/2795117e-633c-4e42-b7a2-a45823d64576" />


### Type F (bekubee HRTPMS)

Android App: [HRTPMS](https://play.google.com/store/apps/details?id=com.bekubee.hrtpms)

Product Description: [AotuLink](https://aotu-link.com/)

Product Link: [AliExpress](https://www.aliexpress.com/item/1005013168188255.html)

<img width="375" src="https://github.com/user-attachments/assets/f07f5c66-783f-4132-904d-87bad44f186d" />


### Type G (Ai TPMS AI-8000)

Android App: [Ai TPMS](https://play.google.com/store/apps/details?id=com.ai.tpms)

Product Links: [AliExpress, BLE TPMS AI-8000](https://www.aliexpress.com/item/1005009771707179.html), [Amazon (possible)](https://www.amazon.es/-/en/Motorcycle-Pressure-Bluetooth-External-Sensors/dp/B0CFTXR2GL)

<img width="375" src="https://github.com/user-attachments/assets/c6538ee7-bd8e-42a9-97f3-2718d0211431" />


### Type H (TC.TPMS)

Valve-cap sensors that advertise as `TC.TPMS` with service UUID `0xA828` (CR1632 battery). Sold with motorcycle CarPlay screens that show tyre pressure.

Product Links: [Amazon, WonVon 7" motorcycle CarPlay screen with TPMS](https://www.amazon.com/dp/B0GWPPHV5G). The same sensors also pair with this [5" motorcycle CarPlay screen](https://www.amazon.com/dp/B0DTHB6D3L).
