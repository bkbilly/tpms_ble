"""Parser for TPMS BLE advertisements."""
from __future__ import annotations
from datetime import datetime

import logging
from struct import unpack
from dataclasses import dataclass
from enum import Enum, auto

from bluetooth_data_tools import short_address
from bluetooth_sensor_state_data import BluetoothData
from home_assistant_bluetooth import BluetoothServiceInfo
from sensor_state_data.enum import StrEnum

_LOGGER = logging.getLogger(__name__)


class TPMSSensor(StrEnum):

    PRESSURE = "pressure"
    TEMPERATURE = "temperature"
    BATTERY = "battery"
    SIGNAL_STRENGTH = "signal_strength"
    TIMESTAMP = "timestamp"


class TPMSBinarySensor(StrEnum):
    ALARM = "alarm"


class TPMSBluetoothDeviceData(BluetoothData):
    """Data for TPMS BLE sensors."""

    def _start_update(self, service_info: BluetoothServiceInfo) -> None:
        """Update from BLE advertisement data."""
        _LOGGER.debug("Parsing TPMS BLE advertisement data: %s", service_info)
        manufacturer_data = service_info.manufacturer_data
        local_name = service_info.name
        address = service_info.address
        if len(manufacturer_data) == 0:
            return None

        mfr_data = next(iter(manufacturer_data.values()))
        self.set_device_manufacturer("TPMS")

        self._process_mfr_data(address, local_name, mfr_data)

    def _process_mfr_data(
        self,
        address: str,
        local_name: str,
        data: bytes,
    ) -> None:
        """Parser for TPMS sensors."""
        _LOGGER.debug("Parsing TPMS sensor: %s", data)
        msg_length = len(data)
        if msg_length != 16:
            return
        (
            pressure,
            temperature,
            battery,
            alarm
        ) = unpack("=iib?", data[6:16])
        pressure = pressure / 100000
        temperature = temperature / 100

        name = f"TPMS {short_address(address)}"
        self.set_device_type(name)
        self.set_device_name(name)
        self.set_title(name)

        self.update_sensor(
            key=str(TPMSSensor.PRESSURE),
            native_unit_of_measurement=None,
            native_value=pressure,
            name="Pressure",
        )
        self.update_sensor(
            key=str(TPMSSensor.TEMPERATURE),
            native_unit_of_measurement=None,
            native_value=temperature,
            name="Temperature",
        )
        self.update_sensor(
            key=str(TPMSSensor.BATTERY),
            native_unit_of_measurement=None,
            native_value=battery,
            name="Battery",
        )
        self.update_binary_sensor(
            key=str(TPMSBinarySensor.ALARM),
            native_value=bool(alarm),
            name="Alarm",
        )
        self.update_sensor(
            key=str(TPMSSensor.TIMESTAMP),
            native_unit_of_measurement=None,
            native_value=datetime.now().astimezone(),
            name="Last Update",
        )
