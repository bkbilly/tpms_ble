"""Parser for TPMS BLE advertisements."""
from __future__ import annotations
from datetime import datetime

import re
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

        company_id, mfr_data = next(iter(manufacturer_data.items()))
        self.set_device_manufacturer("TPMS")

        if "000027a5-0000-1000-8000-00805f9b34fb" in service_info.service_uuids:
            self._process_tpms_2(address, local_name, mfr_data, company_id)
        elif company_id == 256:
            self._process_tpms_1(address, local_name, mfr_data)
        else:
            _LOGGER.error("Can't find the correct data type")

    def _process_tpms_1(self, address: str, local_name: str, data: bytes) -> None:
        """Parser for TPMS sensors."""
        _LOGGER.debug("Parsing TPMS sensor: %s", data)
        msg_length = len(data)
        if msg_length != 16:
            _LOGGER.error("Can't parse the data because the data length should be 16")
            return
        (
            pressure,
            temperature,
            battery,
            alarm
        ) = unpack("=iib?", data[6:16])
        pressure = pressure / 100000
        temperature = temperature / 100
        self._update_sensors(pressure, battery, temperature, alarm)

    def _process_tpms_2(self, address: str, local_name: str, data: bytes, company_id: int) -> None:
        """Parser for TPMS sensors."""
        _LOGGER.debug("Parsing TPMS2 sensor: %s", data)
        comp_hex = re.findall("..", hex(company_id)[2:].zfill(4))[::-1]
        comp_hex = "".join(comp_hex)
        data_hex = data.hex()

        msg_length = len(data_hex)
        if msg_length != 5:
            _LOGGER.error("Can't parse the data because the data length should be 5")
            return
        voltage = int(comp_hex[2:4], 16) / 10
        temperature = int(data_hex[0:2], 16)
        psi_pressure = int(data_hex[2:6], 16) / 10

        pressure = round(psi_pressure * 0.0689476, 3)
        min_voltage = 2.6
        max_voltage = 3.3
        battery = ((voltage - min_voltage) / (max_voltage - min_voltage)) * 100
        battery = int(round(max(0, min(100, battery)), 0))
        self._update_sensors(pressure, battery, temperature, None)

    def _update_sensors(pressure, battery, temperature, alarm):
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
        if alarm is not None:
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
