"""Parser for TPMS BLE advertisements."""
from __future__ import annotations
from datetime import datetime, timezone

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
    DATA_AGE = "data_age"


class TPMSBinarySensor(StrEnum):
    ALARM = "alarm"


class TPMSBluetoothDeviceData(BluetoothData):
    """Data for TPMS BLE sensors."""

    def __init__(self) -> None:
        """Initialize the TPMS device data."""
        super().__init__()
        self._last_update_time: datetime | None = None
        self._last_manufacturer_data: dict[int, bytes] = {}
        self._last_company_id: int | None = None

    @property
    def last_update_time(self) -> datetime | None:
        """Return the timestamp of the last BLE update."""
        return self._last_update_time

    def _start_update(self, service_info: BluetoothServiceInfo) -> None:
        """Update from BLE advertisement data."""
        _LOGGER.debug("Parsing TPMS BLE advertisement data: %s", service_info)
        manufacturer_data = service_info.manufacturer_data
        local_name = service_info.name
        address = service_info.address

        for uuid, s_data in service_info.service_data.items():
            if "0000012a-0000-1000-8000-00805f9b34fb" in uuid and len(s_data) >= 4:
                self.set_device_manufacturer("Salutica FOBO TypeE")
                self._process_tpms_e(address, local_name, s_data, temp_offset=40)
                return

        if len(manufacturer_data) == 0:
            return None

        for company_id, mfr_data in reversed(manufacturer_data.items()):
            if local_name.startswith("AI-") or address.upper().startswith("12:30:AF"):
                self.set_device_manufacturer("Ai TPMS TypeG")
                company_id, mfr_data = self._current_manufacturer_data(service_info)
                self._process_tpms_g(address, local_name, company_id, mfr_data)
                break
            elif "000027a5-0000-1000-8000-00805f9b34fb" in service_info.service_uuids:
                self.set_device_manufacturer("SYTPMS TypeB")
                self._process_tpms_b(address, local_name, mfr_data, company_id)
                break
            elif "0000a828-0000-1000-8000-00805f9b34fb" in service_info.service_uuids:
                self.set_device_manufacturer("TC.TPMS TypeH")
                company_id, mfr_data = self._current_manufacturer_data(service_info)
                self._process_tpms_h(address, local_name, company_id, mfr_data)
                break
            elif "0000a827-0000-1000-8000-00805f9b34fb" in service_info.service_uuids:
                self.set_device_manufacturer("HRTPMS TypeF")
                self._process_tpms_f(address, local_name, mfr_data)
                break
            elif company_id == 256:
                self.set_device_manufacturer("TPMSII TypeA")
                self._process_tpms_a(address, local_name, mfr_data)
                break
            elif company_id == 2088:
                self.set_device_manufacturer("Michelin TypeC")
                self._process_tpms_c(address, local_name, mfr_data)
                break
            elif company_id == 172:
                self.set_device_manufacturer("WODHMIEY TypeD")
                self._process_tpms_d(address, local_name, mfr_data)
                break
            elif company_id == 295:
                self.set_device_manufacturer("Salutica FOBO TypeE")
                self._process_tpms_e(address, local_name, mfr_data)
                break
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
            
        elif frame_type in [0x03, 0x04]:
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

    def _process_tpms_d(self, address: str, local_name: str, data: bytes) -> None:
        """Parser for WODHMIEY / ITPMS (K) TPMS BLE sensors (Type D)."""
        _LOGGER.debug("Parsing TPMS TypeD data: %s", data.hex())

        msg_length = len(data)
        if msg_length < 7:
            _LOGGER.error("Found %s bytes from sensor: %s (expected >= 7)", msg_length, address)
            return

        if msg_length == 15:
            advertised_address = ":".join(f"{byte:02X}" for byte in data[9:15][::-1])
            if advertised_address.lower() != address.lower():
                _LOGGER.warning(
                    "TypeD manufacturer address %s does not match sensor %s, parsing payload anyway",
                    advertised_address,
                    address,
                )

        battery_voltage = round(data[0] * 0.01 + 1.22, 2)
        battery_pct = max(0, min(100, int((battery_voltage - 1.8) / 1.2 * 100)))

        temperature_celcius = data[2] - 55

        # Alarm State (0 = Normal, 1 = Leakage, 2 = Inflation, etc.)
        alarm = bool(data[3]) if msg_length > 3 else None

        # Pressure calculation
        # ITPMS APK formula: raw_press * 3.144 / 100.0 (where data[6] is pressure high flag)
        if msg_length >= 7 and data[6] in (0, 1):
            raw_press = data[1] + (256 if data[6] == 1 else 0)
            pressure_bar = round(raw_press * 0.03144, 2)
        elif msg_length >= 8:
            # Fallback formula for legacy 15-byte TypeD packets (where data[7] holds raw pressure)
            pressure_bar = round(max(0, (data[7] - 2) / 103), 2)
        else:
            pressure_bar = None

        self._update_sensors(
            address,
            pressure_bar,
            battery_pct,
            temperature_celcius,
            alarm,
            battery_voltage,
        )

    def _process_tpms_e(self, address: str, local_name: str, data: bytes, temp_offset: int = 50) -> None:
        """Parser for Salutica FOBO TPMS BLE sensors (Type E)."""
        _LOGGER.debug("Parsing TPMS TypeE (FOBO) data: %s", data.hex())

        msg_length = len(data)
        if msg_length < 4:
            _LOGGER.error("Found %s bytes from FOBO sensor: %s (expected >= 4)", msg_length, address)
            return

        # FOBO sensor payload format:
        # byte 0: status/type
        # byte 1: temperature + offset (default 50, iBeacon 40) (top bit might be a flag)
        # bytes 2-3 (big-endian 16-bit):
        #   bits 0-9: pressure in kPa
        #   bits 10-15: battery code (* 100 mV)
        #   bit 15: rotating flag
        pdata = data[-4:]
        temperature_celcius = (pdata[1] & 0x7F) - temp_offset
        raw_val = (pdata[2] << 8) | pdata[3]
        pressure_kpa = raw_val & 1023
        pressure_bar = round(pressure_kpa * 0.01, 2)
        battery_code = (raw_val >> 10) & 63
        if battery_code > 0:
            battery_mv = battery_code * 100
            battery_voltage = round(battery_mv / 1000.0, 2)
            battery_pct = battery_percentage(battery_voltage)
        else:
            # Fallback for iBeacon variants where battery is BCD in byte 0
            # For BCD: 0x29 -> 2.9V (mask top bit in case of flags)
            clean_b0 = pdata[0] & 0x7F
            high_nibble = clean_b0 >> 4
            low_nibble = clean_b0 & 0x0F
            if 0 <= high_nibble <= 9 and 0 <= low_nibble <= 9:
                battery_voltage = round(high_nibble + low_nibble * 0.1, 2)
                battery_pct = battery_percentage(battery_voltage)
            else:
                battery_voltage = None
                battery_pct = None

        self._update_sensors(
            address,
            pressure_bar,
            battery_pct,
            temperature_celcius,
            None,
            battery_voltage,
        )

    def _process_tpms_f(self, address: str, local_name: str, data: bytes) -> None:
        """Parser for TPMS sensors."""
        _LOGGER.debug("Parsing HRTPMS TypeF sensor: %s", data.hex())
        msg_length = len(data)
        if msg_length != 9:
            _LOGGER.error("Can't parse the data because the data length should be 9")
            return
        (
            voltage,
            temperature,
            pressure
        ) = unpack(">BBH", data[0:4])

        pressure_kpa = pressure - 100
        pressure_bar = round(pressure_kpa * 0.01, 2)
        temperature = temperature - 50
        voltage = voltage * 0.01 + 1.22
        battery = battery_percentage(voltage)

        self._update_sensors(address, pressure_bar, battery, temperature, None, voltage)

    def _process_tpms_g(self, address: str, local_name: str, company_id: int, data: bytes) -> None:
        """Parser for Ai TPMS sensors, app "Ai TPMS" (AI-8000) (Type G).

        The sensor writes its measurements INTO the manufacturer data:
        the 16-bit company id carries the first two frame bytes
        (little-endian), the payload bytes the rest — together a
        5-byte frame:

            byte 0:    status bits 0-3 (rotate between messages, meaning unknown)
            byte 1:    battery voltage × 10 (0x20 = 3.2 V)
            byte 2:    temperature °C
            bytes 3-4: pressure big-endian, 0.1 psi ABSOLUTE

        Detection is therefore NOT by company id but by local name
        ("AI-*") or address prefix 12:30:AF — decided by the caller.
        Gauge pressure = raw/10 − 14.696 psi (ambient), converted with
        0.0689476 bar/psi. Frames captured
        2026-10-16 — 0x0092 (no overpressure, ambient air) and 0x01AE
        (a mounted tyre; the car's factory sensor on the same wheel
        showed 1.944 bar).
        """
        _LOGGER.debug("Parsing TPMS TypeG (Ai TPMS) data: id %04x %s", company_id, data.hex())
        frame = bytes([company_id & 0xFF, (company_id >> 8) & 0xFF]) + bytes(data)
        if len(frame) != 5:
            _LOGGER.error("Can't parse the data because the data length should be 5 (2 id bytes + 3 payload bytes)")
            return

        battery_voltage = frame[1] / 10
        temperature_celcius = frame[2]
        psi_absolute = int.from_bytes(frame[3:5], "big") / 10
        pressure_bar = round(max(0.0, psi_absolute - 14.696) * 0.0689476, 3)
        battery_pct = battery_percentage(battery_voltage)

        self._update_sensors(address, pressure_bar, battery_pct, temperature_celcius, None, battery_voltage)

    def _process_tpms_h(self, address: str, local_name: str, company_id: int, data: bytes) -> None:
        """Parser for "TC.TPMS" sensors, service UUID 0xA828 (Type H).

        Same layout as Type G, but the payload carries the sensor's MAC
        address after the measurements. The 16-bit company id holds the
        first two frame bytes (little-endian):

            byte 0:    status
            byte 1:    battery voltage × 10
            byte 2:    temperature °C
            bytes 3-4: pressure big-endian, 0.1 psi ABSOLUTE
            bytes 5-10: sensor MAC address

        Gauge pressure = raw/10 − 14.6 psi. Checked 2026-10-17 against
        the vendor display: 0x01B3 → 28.9 psi, 0x01C1 → 30.3 psi.
        """
        _LOGGER.debug("Parsing TPMS TypeH (TC.TPMS) data: id %04x %s", company_id, data.hex())
        frame = bytes([company_id & 0xFF, (company_id >> 8) & 0xFF]) + bytes(data)
        if len(frame) != 11:
            _LOGGER.error("Can't parse the data because the data length should be 11 (2 id bytes + 9 payload bytes)")
            return

        battery_voltage = frame[1] / 10
        temperature_celcius = frame[2]
        psi_absolute = int.from_bytes(frame[3:5], "big") / 10
        pressure_bar = round(max(0.0, psi_absolute - 14.6) * 0.0689476, 3)
        battery_pct = battery_percentage(battery_voltage)

        self._update_sensors(address, pressure_bar, battery_pct, temperature_celcius, None, battery_voltage)

    def _current_manufacturer_data(self, service_info: BluetoothServiceInfo) -> tuple[int, bytes]:
        """Return (company id, data) of the advertisement just received.

        For sensors that put readings in the company id (Type G, Type H).
        HA merges manufacturer data across advertisements, so old readings
        pile up in the dict as extra company ids. Prefer the raw advertisement,
        which holds only the current one (ESPHome proxies send it, local
        adapters don't). Otherwise take the entry that is new or changed since
        the last update, or the one used last time if nothing changed.
        """
        manufacturer_data = service_info.manufacturer_data
        previous, self._last_manufacturer_data = self._last_manufacturer_data, dict(manufacturer_data)

        current = raw_manufacturer_data(service_info)
        if current is None:
            changed = [cid for cid, data in manufacturer_data.items() if previous.get(cid) != data]
            if changed:
                company_id = changed[-1]
            elif self._last_company_id in manufacturer_data:
                company_id = self._last_company_id
            else:
                company_id = next(reversed(manufacturer_data))
            current = (company_id, manufacturer_data[company_id])

        self._last_company_id = current[0]
        return current

    def _update_sensors(self, address, pressure, battery_pct, temperature, alarm, voltage):
        self._last_update_time = datetime.now(timezone.utc)
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

def raw_manufacturer_data(service_info: BluetoothServiceInfo) -> tuple[int, bytes] | None:
    """Return (company id, data) from the advertisement just received.

    HA merges manufacturer data across advertisements, so sensors that put
    readings in the company id pile up stale entries in the dict. The raw
    advertisement (not provided by every adapter) holds only the current one.
    """
    raw = getattr(service_info, "raw", None)
    i = 0
    while raw and i + 1 < len(raw):
        length = raw[i]
        if length == 0:
            break
        if raw[i + 1] == 0xFF and length >= 3:
            return int.from_bytes(raw[i + 2:i + 4], "little"), bytes(raw[i + 4:i + 1 + length])
        i += 1 + length
    return None


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
