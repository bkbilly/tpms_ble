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
    VOLTAGE = "voltage"
    SIGNAL_STRENGTH = "signal_strength"


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

        if "000027a5-0000-1000-8000-00805f9b34fb" in service_info.service_uuids:
            self.set_device_manufacturer("SYTPMS TypeB")
            self._process_tpms_b(address, local_name, mfr_data, company_id)
        elif company_id == 256:
            self.set_device_manufacturer("TPMSII TypeA")
            self._process_tpms_a(address, local_name, mfr_data)
        elif company_id == 2088:
            self.set_device_manufacturer("Michelin")
            self._process_tpms_c(address, local_name, mfr_data)
        else:
            _LOGGER.debug("Can't find the correct data type")

    def _process_tpms_a(self, address: str, local_name: str, data: bytes) -> None:
        """Parser for TPMS sensors."""
        _LOGGER.debug("Parsing TPMS TypeA sensor: %s", data)
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
        self._update_sensors(address, pressure, battery, temperature, alarm, None)

    def _process_tpms_b(self, address: str, local_name: str, data: bytes, company_id: int) -> None:
        """Parser for TPMS sensors."""
        _LOGGER.debug("Parsing TPMS TypeB sensor: (%s) %s", company_id, data)
        comp_hex = re.findall("..", hex(company_id)[2:].zfill(4))[::-1]
        comp_hex = "".join(comp_hex)
        data_hex = data.hex()

        msg_length = len(data_hex)
        if msg_length != 10:
            _LOGGER.error("Can't parse the data because the data length should be 10")
            return
        voltage = int(comp_hex[2:4], 16) / 10
        temperature = int(data_hex[0:2], 16)
        if temperature >= 2 ** 7:
            temperature -= 2 ** 8
        psi_pressure = (int(data_hex[2:6], 16) - 145) / 10

        pressure = round(psi_pressure * 0.0689476, 3)
        battery = battery_percentage(voltage)
        self._update_sensors(address, pressure, battery, temperature, None, voltage)

    def _process_tpms_c(self, address: str, local_name: str, data: bytes) -> None:
        """Parser for Michelin Tire Pressure Sensor BLE sensors (Type C)."""
        _LOGGER.debug("Parsing TPMS TypeC data: %s", data.hex())

        # Validate Product type == 0x01 = Michelin Tire Pressure Sensor
        product_type = data[0]
        if product_type != 0x01:
            _LOGGER.debug("Can't parse the data because the product type should be 0x01 for Michelin Tire Pressure Sensor. Found: %s from sensor: %s", product_type, address)
            return
        
        frame_type = data[1]
        msg_length = len(data)
        
        if frame_type == 0x02:
            if msg_length != 12:
                _LOGGER.error("Found %s bytes from sensor: %s", msg_length, address)
                return
            raw_temp, raw_volt = unpack("BB", data[2:4])
            temperature_celcius = raw_temp - 60
            battery_voltage = round((raw_volt / 100) + 1.0, 2)
            pressure_bar = None
        
        elif frame_type == 0x04:
            if msg_length != 14:
                _LOGGER.error("Found %s bytes from sensor: %s", msg_length, address)
                return
            raw_temp, raw_volt, raw_press_le = unpack("<BBH", data[2:6])
            temperature_celcius = raw_temp - 60
            battery_voltage = round((raw_volt / 100) + 1.0, 2)
            pressure_bar = max(0, round(raw_press_le / 1000, 2) - 1)
        
        elif frame_type == 0x05:
            if msg_length != 14:
                _LOGGER.error("Found %s bytes from sensor: %s", msg_length, address)
                return
            raw_temp, raw_volt = unpack("BB", data[2:4])
            raw_press_le, = unpack("<H", data[12:14])
            temperature_celcius = raw_temp - 60
            battery_voltage = round((raw_volt / 100) + 1.0, 2)
            pressure_bar = max(0, round(raw_press_le / 1000, 2) - 1)
        
        elif frame_type == 0x06:
            if msg_length != 12:
                _LOGGER.error("Found %s bytes from sensor: %s", msg_length, address)
                return
            raw_temp, raw_volt = unpack("BB", data[2:4])
            temperature_celcius = raw_temp - 60
            battery_voltage = round((raw_volt / 100) + 1.0, 2)
            pressure_bar = None
        
        elif frame_type == 0x0c:
            if msg_length != 17:
                _LOGGER.error("Found %s bytes from sensor: %s", msg_length, address)
                return
            raw_temp, raw_volt, raw_press_le = unpack("<BBH", data[2:6])
            temperature_celcius = raw_temp - 60
            battery_voltage = round((raw_volt / 100) + 1.0, 2)
            pressure_bar = max(0, round(raw_press_le / 1000, 2) - 1)
        
        else:
            _LOGGER.info("Unknown Michelin frame type %s from sensor: %s", frame_type, address)
            return
        
        battery_pct = battery_percentage(battery_voltage)

        self._update_sensors(
            address,
            pressure_bar,
            battery_pct,
            temperature_celcius,
            None,
            battery_voltage,
        )

    def _update_sensors(self, address, pressure, battery_pct, temperature, alarm, voltage):
        name = f"TPMS {short_address(address)}"
        self.set_device_type(name)
        self.set_device_name(name)
        self.set_title(name)

        if pressure is not None:
            self.update_sensor(
                key=str(TPMSSensor.PRESSURE),
                native_unit_of_measurement=None,
                native_value=pressure,
                name="Pressure",
            )

        if temperature is not None:
            self.update_sensor(
                key=str(TPMSSensor.TEMPERATURE),
                native_unit_of_measurement=None,
                native_value=temperature,
                name="Temperature",
            )

        if battery_pct is not None:
            self.update_sensor(
                key=str(TPMSSensor.BATTERY),
                native_unit_of_measurement=None,
                native_value=battery_pct,
                name="Battery",
            )

        if alarm is not None:
            self.update_binary_sensor(
                key=str(TPMSBinarySensor.ALARM),
                native_value=bool(alarm),
                name="Alarm",
            )

        if voltage is not None:
            self.update_sensor(
                key=str(TPMSSensor.VOLTAGE),
                native_unit_of_measurement=None,
                native_value=voltage,
                name="Voltage",
            )

def battery_percentage(voltage):
    discharge_curve = [
        (3.3, 100),
        (3.05, 97),
        (2.94, 91),
        (2.9, 75),
        (2.85, 25),
        (2.8, 17),
        (2.6, 0),
    ]
    if voltage >= discharge_curve[0][0]:
        return 100
    if voltage < discharge_curve[-1][0]:
        return 0
    for i in range(len(discharge_curve) - 1):
        V2, P2 = discharge_curve[i]
        V1, P1 = discharge_curve[i+1]
        if V1 < voltage <= V2:
            percentage = P1 + ((voltage - V1) / (V2 - V1)) * (P2 - P1)
            return int(round(percentage))
    return 0
