"""Tests for TPMS BLE parsers across all supported types."""
from __future__ import annotations

import struct
from home_assistant_bluetooth import BluetoothServiceInfo

from custom_components.tpms_ble.tpms_parser.parser import (
    TPMSBluetoothDeviceData,
    TPMSSensor,
    battery_percentage,
)


def get_sensor_values(parser: TPMSBluetoothDeviceData, info: BluetoothServiceInfo) -> dict[str, object]:
    """Helper to run update on parser and return native sensor values dict."""
    update = parser.update(info)
    return {
        key.key: value.native_value
        for key, value in update.entity_values.items()
    }


def test_type_a_tpmsii() -> None:
    """Type A (TPMSII): Company ID 256, 16-byte payload."""
    parser = TPMSBluetoothDeviceData()
    # 6 bytes padding/MAC + pressure (x100000), temp (x100), battery %, alarm bool
    payload = b"\x00" * 6 + struct.pack("=iib?", 230000, 2450, 85, False)
    info = BluetoothServiceInfo(
        name="TPMS1_123456",
        address="AA:BB:CC:DD:EE:01",
        rssi=-60,
        manufacturer_data={256: payload},
        service_data={},
        service_uuids=[],
        source="local",
    )
    values = get_sensor_values(parser, info)
    assert values[TPMSSensor.PRESSURE] == 2.3
    assert values[TPMSSensor.TEMPERATURE] == 24.5
    assert values[TPMSSensor.BATTERY] == 85


def test_type_b_sytpms() -> None:
    """Type B (SYTPMS): Service UUID 0x27A5.

    Company ID holds voltage in high byte. Data holds temperature in byte 0
    (signed 8-bit) and pressure in bytes 1-2.
    """
    parser = TPMSBluetoothDeviceData()
    # Voltage: 3.0 V (0x1E in high byte = 0x1E00).
    # Temp: 22 °C, Pressure: 0x01AE (430) -> (430 - 145) / 10 = 28.5 psi -> 1.965 bar.
    data_pos = bytes([22, 0x01, 0xAE, 0x00, 0x00])
    info_pos = BluetoothServiceInfo(
        name="TPMS_B",
        address="AA:BB:CC:DD:EE:02",
        rssi=-60,
        manufacturer_data={0x1E00: data_pos},
        service_data={},
        service_uuids=["000027a5-0000-1000-8000-00805f9b34fb"],
        source="local",
    )
    values = get_sensor_values(parser, info_pos)
    assert values[TPMSSensor.PRESSURE] == 1.965
    assert values[TPMSSensor.TEMPERATURE] == 22
    assert values[TPMSSensor.VOLTAGE] == 3.0
    assert values[TPMSSensor.BATTERY] == battery_percentage(3.0)

    # Negative temperature test (e.g. -4 °C -> 252 unsigned):
    data_neg = bytes([252, 0x01, 0xAE, 0x00, 0x00])
    info_neg = BluetoothServiceInfo(
        name="TPMS_B",
        address="AA:BB:CC:DD:EE:02",
        rssi=-60,
        manufacturer_data={0x1E00: data_neg},
        service_data={},
        service_uuids=["000027a5-0000-1000-8000-00805f9b34fb"],
        source="local",
    )
    values_neg = get_sensor_values(parser, info_neg)
    assert values_neg[TPMSSensor.TEMPERATURE] == -4


def test_type_c_michelin_frames() -> None:
    """Type C (Michelin): Company ID 2088.

    Frame 0x02: Temperature & Voltage only (12 bytes).
    Frame 0x04: Temperature, Voltage & Pressure (14 bytes).
    """
    parser = TPMSBluetoothDeviceData()

    # Frame 0x02 (temp 21 °C, voltage 3.0 V):
    # raw_temp = 81 (81 - 60 = 21 °C), raw_volt = 200 (200/100 + 1.0 = 3.0 V)
    data_f2 = bytes([0x01, 0x02, 81, 200]) + b"\x00" * 8
    info_f2 = BluetoothServiceInfo(
        name="Michelin_02",
        address="AA:BB:CC:DD:EE:03",
        rssi=-60,
        manufacturer_data={2088: data_f2},
        service_data={},
        service_uuids=[],
        source="local",
    )
    values_f2 = get_sensor_values(parser, info_f2)
    assert values_f2[TPMSSensor.TEMPERATURE] == 21
    assert values_f2[TPMSSensor.VOLTAGE] == 3.0
    assert TPMSSensor.PRESSURE not in values_f2

    # Frame 0x04 (temp 21 °C, voltage 3.0 V, raw_press = 3200 -> max(0, 3.20 - 1) = 2.2 bar):
    data_f4 = bytes([0x01, 0x04, 81, 200, 0x80, 0x0C]) + b"\x00" * 8
    info_f4 = BluetoothServiceInfo(
        name="Michelin_04",
        address="AA:BB:CC:DD:EE:03",
        rssi=-60,
        manufacturer_data={2088: data_f4},
        service_data={},
        service_uuids=[],
        source="local",
    )
    values_f4 = get_sensor_values(parser, info_f4)
    assert values_f4[TPMSSensor.PRESSURE] == 2.2
    assert values_f4[TPMSSensor.TEMPERATURE] == 21
    assert values_f4[TPMSSensor.VOLTAGE] == 3.0


def test_type_d_wodhmiey_real_capture() -> None:
    """Type D (WODHMIEY / ITPMS (K)): Company ID 172.

    Real capture from Issue #27:
    Payload: c03e54000a17008d28111111be5d30
    byte 0 = 0xC0 (192) -> 3.14 V, 100%
    byte 1 = 0x3E (62), byte 6 = 0x00 -> pressure = round(62 * 0.03144, 2) = 1.95 bar
    byte 2 = 0x54 (84) -> 84 - 55 = 29 °C
    """
    parser = TPMSBluetoothDeviceData()
    data = bytes.fromhex("c03e54000a17008d28111111be5d30")
    info = BluetoothServiceInfo(
        name="Front wheel-305DBE",
        address="BE:5D:30:11:22:33",
        rssi=-60,
        manufacturer_data={172: data},
        service_data={},
        service_uuids=["0000fbb0-0000-1000-8000-00805f9b34fb"],
        source="local",
    )
    values = get_sensor_values(parser, info)
    assert values[TPMSSensor.PRESSURE] == 1.95
    assert values[TPMSSensor.TEMPERATURE] == 29
    assert values[TPMSSensor.VOLTAGE] == 3.14
    assert values[TPMSSensor.BATTERY] == 100


def test_type_e_fobo_manufacturer_data() -> None:
    """Type E (Salutica FOBO): Standard variant via Company ID 295."""
    parser = TPMSBluetoothDeviceData()
    # FOBO payload: last 4 bytes hold status, temp + 50, and 16-bit (pressure | battery << 10)
    # temp: 20 °C (70 - 50 = 20)
    # pressure: 220 kPa = 2.2 bar (bits 0-9)
    # battery: 30 (*100mV = 3.0V, bits 10-15) -> (30 << 10) | 220 = 30940 = 0x78DC
    data = bytes([0x00, 70, 0x78, 0xDC])
    info = BluetoothServiceInfo(
        name="FOBO Tire",
        address="AA:BB:CC:DD:EE:05",
        rssi=-60,
        manufacturer_data={295: data},
        service_data={},
        service_uuids=[],
        source="local",
    )
    values = get_sensor_values(parser, info)
    assert values[TPMSSensor.PRESSURE] == 2.2
    assert values[TPMSSensor.TEMPERATURE] == 20
    assert values[TPMSSensor.VOLTAGE] == 3.0
    assert values[TPMSSensor.BATTERY] == battery_percentage(3.0)


def test_type_e_fobo_service_data() -> None:
    """Type E (Salutica FOBO): US iBeacon variant via service_data UUID 0x012A."""
    parser = TPMSBluetoothDeviceData()
    # US FOBO iBeacon uses temp offset 40
    # temp: 22 °C -> 22 + 40 = 62
    # pressure: 210 kPa = 2.1 bar
    # battery BCD fallback in byte 0: 0x29 -> 2.9 V
    raw_val = (0 << 10) | 210  # battery code 0 -> fallback to byte 0 BCD
    data = bytes([0x29, 62, (raw_val >> 8) & 0xFF, raw_val & 0xFF])
    info = BluetoothServiceInfo(
        name="Salutica FOBO_US",
        address="AA:BB:CC:DD:EE:06",
        rssi=-60,
        manufacturer_data={},
        service_data={"0000012a-0000-1000-8000-00805f9b34fb": data},
        service_uuids=[],
        source="local",
    )
    values = get_sensor_values(parser, info)
    assert values[TPMSSensor.PRESSURE] == 2.1
    assert values[TPMSSensor.TEMPERATURE] == 22
    assert values[TPMSSensor.VOLTAGE] == 2.9
    assert values[TPMSSensor.BATTERY] == battery_percentage(2.9)


def test_type_f_hrtpms_real_captures() -> None:
    """Type F (Bekubee HRTPMS): Service UUID 0xA827.

    Real capture from physical sensor (mounted: 0x0002, unplugged: 0x0006).
    """
    parser = TPMSBluetoothDeviceData()
    # 1. Mounted tyre capture: AF4500A7002D56A8B4
    # voltage: 0xAF (175) -> 175*0.01 + 1.22 = 2.97 V
    # temp: 0x45 (69) -> 69 - 50 = 19 °C
    # pressure: 0x00A7 (167) -> 167 - 100 = 67 kPa = 0.67 bar
    data_mounted = bytes.fromhex("AF4500A7002D56A8B4")
    info_mounted = BluetoothServiceInfo(
        name="TPMS",
        address="11:22:33:44:55:66",
        rssi=-60,
        manufacturer_data={0x0002: data_mounted},
        service_data={},
        service_uuids=["0000a827-0000-1000-8000-00805f9b34fb"],
        source="local",
    )
    values_mounted = get_sensor_values(parser, info_mounted)
    assert values_mounted[TPMSSensor.PRESSURE] == 0.67
    assert values_mounted[TPMSSensor.TEMPERATURE] == 19
    assert values_mounted[TPMSSensor.VOLTAGE] == 2.97

    # 2. Unplugged sensor capture: B34A0064002FA0057D
    # pressure: 0x0064 (100) -> 100 - 100 = 0 kPa = 0.0 bar
    data_unplugged = bytes.fromhex("B34A0064002FA0057D")
    info_unplugged = BluetoothServiceInfo(
        name="TPMS",
        address="11:22:33:44:55:66",
        rssi=-60,
        manufacturer_data={0x0002: data_mounted, 0x0006: data_unplugged},
        service_data={},
        service_uuids=["0000a827-0000-1000-8000-00805f9b34fb"],
        source="local",
    )
    values_unplugged = get_sensor_values(parser, info_unplugged)
    assert values_unplugged[TPMSSensor.PRESSURE] == 0.0


def test_type_g_ai_tpms_real_captures() -> None:
    """Type G (Ai TPMS AI-8000): Local name AI-* or address 12:30:AF.

    Measurements inside company ID (status | voltage<<8).
    Captured frames from PR #32:
    - Ambient air: 0x0092 -> 0.0 bar gauge
    - Mounted tyre: 0x01AE -> 1.951 bar gauge
    """
    parser = TPMSBluetoothDeviceData()

    # Ambient frame: company_id 0x2000 (status 0, 3.2V), temp 15 °C, raw 0x0092
    info_ambient = BluetoothServiceInfo(
        name="AI-8000",
        address="12:30:AF:01:02:03",
        rssi=-60,
        manufacturer_data={0x2000: b"\x0F\x00\x92"},
        service_data={},
        service_uuids=[],
        source="local",
    )
    values_ambient = get_sensor_values(parser, info_ambient)
    assert values_ambient[TPMSSensor.PRESSURE] == 0.0
    assert values_ambient[TPMSSensor.TEMPERATURE] == 15
    assert values_ambient[TPMSSensor.VOLTAGE] == 3.2

    # Mounted frame: company_id 0x2000, temp 21 °C, raw 0x01AE
    # 43.0 psi absolute - 14.696 = 28.304 psi -> 1.951 bar
    info_mounted = BluetoothServiceInfo(
        name="AI-8000",
        address="12:30:AF:01:02:03",
        rssi=-60,
        manufacturer_data={0x2000: b"\x15\x01\xAE"},
        service_data={},
        service_uuids=[],
        source="local",
    )
    values_mounted = get_sensor_values(parser, info_mounted)
    assert values_mounted[TPMSSensor.PRESSURE] == 1.951
    assert values_mounted[TPMSSensor.TEMPERATURE] == 21


def test_type_h_tc_tpms_real_captures() -> None:
    """Type H (TC.TPMS): Service UUID 0xA828.

    Measurements inside company ID (status | voltage<<8) + 9 payload bytes.
    Real captures from PR #33 checked against vendor CarPlay screen:
    - 0x1B04 (2.7V, 18 °C, 0x01B3 = 43.5 psi abs) -> 28.9 psi (1.993 bar)
    - 0x1A05 (2.6V, 18 °C, 0x01C1 = 44.9 psi abs) -> 30.3 psi (2.089 bar)
    """
    parser = TPMSBluetoothDeviceData()

    data_h1 = bytes([18, 0x01, 0xB3, 0x11, 0x22, 0x33, 0x44, 0x55, 0x66])
    info_h1 = BluetoothServiceInfo(
        name="TC.TPMS",
        address="11:22:33:44:55:66",
        rssi=-60,
        manufacturer_data={0x1B04: data_h1},
        service_data={},
        service_uuids=["0000a828-0000-1000-8000-00805f9b34fb"],
        source="local",
    )
    values_h1 = get_sensor_values(parser, info_h1)
    assert values_h1[TPMSSensor.PRESSURE] == 1.993
    assert values_h1[TPMSSensor.TEMPERATURE] == 18
    assert values_h1[TPMSSensor.VOLTAGE] == 2.7

    data_h2 = bytes([18, 0x01, 0xC1, 0x11, 0x22, 0x33, 0x44, 0x55, 0x77])
    info_h2 = BluetoothServiceInfo(
        name="TC.TPMS",
        address="11:22:33:44:55:77",
        rssi=-60,
        manufacturer_data={0x1A05: data_h2},
        service_data={},
        service_uuids=["0000a828-0000-1000-8000-00805f9b34fb"],
        source="local",
    )
    values_h2 = get_sensor_values(parser, info_h2)
    assert values_h2[TPMSSensor.PRESSURE] == 2.089
    assert values_h2[TPMSSensor.TEMPERATURE] == 18
    assert values_h2[TPMSSensor.VOLTAGE] == 2.6


def test_stale_manufacturer_data_resolution() -> None:
    """Verify that HA's dictionary merge does not cause stale readings."""
    parser = TPMSBluetoothDeviceData()

    # Step 1: Adv with CID 0x2000 (status 0) -> pressure 30.0 psi (0x01C0 = 448 -> 44.8 - 14.696 = 30.1 psi)
    info1 = BluetoothServiceInfo(
        name="AI-8000",
        address="12:30:AF:00:11:22",
        rssi=-60,
        manufacturer_data={0x2000: b"\x15\x01\xC0"},
        service_data={},
        service_uuids=[],
        source="local",
    )
    v1 = get_sensor_values(parser, info1)
    p1 = v1[TPMSSensor.PRESSURE]

    # Step 2: Adv with CID 0x2001 (status 1) -> pressure 30.0 psi
    info2 = BluetoothServiceInfo(
        name="AI-8000",
        address="12:30:AF:00:11:22",
        rssi=-60,
        manufacturer_data={0x2000: b"\x15\x01\xC0", 0x2001: b"\x15\x01\xC0"},
        service_data={},
        service_uuids=[],
        source="local",
    )
    v2 = get_sensor_values(parser, info2)
    assert v2[TPMSSensor.PRESSURE] == p1

    # Step 3: Status rotates back to 0 (CID 0x2000), but pressure drops to 0.0 bar (0x0092)
    # In HA's merged dict, 0x2000 stays at key position 0, while 0x2001 is at the end!
    info3 = BluetoothServiceInfo(
        name="AI-8000",
        address="12:30:AF:00:11:22",
        rssi=-60,
        manufacturer_data={0x2000: b"\x15\x00\x92", 0x2001: b"\x15\x01\xC0"},
        service_data={},
        service_uuids=[],
        source="local",
    )
    v3 = get_sensor_values(parser, info3)
    # Must pick the updated 0x2000 reading (0.0 bar), NOT the stale 0x2001 at the end!
    assert v3[TPMSSensor.PRESSURE] == 0.0
